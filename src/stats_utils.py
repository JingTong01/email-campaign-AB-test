"""Small, dependency-light helpers for analysing randomized experiments.

Only numpy / pandas / scipy are used so every step stays transparent.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats


# ---------------------------------------------------------------------------
# 1. Sample ratio mismatch (SRM)
# ---------------------------------------------------------------------------
def srm_test(counts: pd.Series, expected_shares: dict | None = None) -> dict:
    """Chi-square goodness-of-fit test: did randomization split users as planned?

    counts: number of users per group (index = group name).
    expected_shares: planned share per group; defaults to an equal split.
    A very small p-value (e.g. < 0.001) signals a broken assignment.
    """
    n = counts.sum()
    if expected_shares is None:
        expected = np.full(len(counts), n / len(counts))
    else:
        expected = np.array([expected_shares[g] * n for g in counts.index])
    chi2, p = stats.chisquare(counts.values, expected)
    return {"chi2": chi2, "p_value": p, "n_total": int(n)}


# ---------------------------------------------------------------------------
# 2. Covariate balance
# ---------------------------------------------------------------------------
def standardized_mean_diff(x_treat: pd.Series, x_ctrl: pd.Series) -> float:
    """SMD = (mean_t - mean_c) / pooled SD. |SMD| < 0.1 is the usual 'balanced' rule."""
    pooled_sd = np.sqrt((x_treat.var(ddof=1) + x_ctrl.var(ddof=1)) / 2)
    return (x_treat.mean() - x_ctrl.mean()) / pooled_sd if pooled_sd > 0 else 0.0


def balance_table(df: pd.DataFrame, group_col: str, control: str, covariates: list[str]) -> pd.DataFrame:
    """SMD of every covariate for each treatment arm vs. control."""
    ctrl = df[df[group_col] == control]
    rows = []
    for arm in [g for g in df[group_col].unique() if g != control]:
        treat = df[df[group_col] == arm]
        for cov in covariates:
            rows.append({"arm": arm, "covariate": cov,
                         "mean_treatment": treat[cov].mean(),
                         "mean_control": ctrl[cov].mean(),
                         "smd": standardized_mean_diff(treat[cov], ctrl[cov])})
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# 3. Binary metrics (visit, conversion): difference in proportions
# ---------------------------------------------------------------------------
def diff_in_proportions(y_treat: pd.Series, y_ctrl: pd.Series, alpha: float = 0.05) -> dict:
    """Absolute and relative lift with a Wald CI and a two-sided z-test (pooled SE)."""
    n_t, n_c = len(y_treat), len(y_ctrl)
    p_t, p_c = y_treat.mean(), y_ctrl.mean()
    diff = p_t - p_c

    se_unpooled = np.sqrt(p_t * (1 - p_t) / n_t + p_c * (1 - p_c) / n_c)
    z_crit = stats.norm.ppf(1 - alpha / 2)
    ci = (diff - z_crit * se_unpooled, diff + z_crit * se_unpooled)

    p_pool = (y_treat.sum() + y_ctrl.sum()) / (n_t + n_c)
    se_pooled = np.sqrt(p_pool * (1 - p_pool) * (1 / n_t + 1 / n_c))
    z = diff / se_pooled
    p_value = 2 * (1 - stats.norm.cdf(abs(z)))

    return {"rate_treatment": p_t, "rate_control": p_c,
            "abs_lift": diff, "ci_low": ci[0], "ci_high": ci[1],
            "rel_lift": diff / p_c if p_c > 0 else np.nan,
            "z": z, "p_value": p_value, "n_treatment": n_t, "n_control": n_c}


# ---------------------------------------------------------------------------
# 4. Continuous, heavy-tailed metrics (spend): bootstrap
# ---------------------------------------------------------------------------
def bootstrap_mean_diff(y_treat: pd.Series, y_ctrl: pd.Series, n_boot: int = 5000,
                        alpha: float = 0.05, seed: int = 42) -> dict:
    """Percentile-bootstrap CI for the difference in means.

    Spend is mostly zeros with a long right tail, so normal-theory CIs can mislead.
    """
    rng = np.random.default_rng(seed)
    t, c = np.asarray(y_treat, float), np.asarray(y_ctrl, float)
    boots = np.empty(n_boot)
    for i in range(n_boot):
        boots[i] = rng.choice(t, t.size).mean() - rng.choice(c, c.size).mean()
    lo, hi = np.quantile(boots, [alpha / 2, 1 - alpha / 2])
    # two-sided bootstrap p-value: how often the resampled diff crosses zero
    p_boot = 2 * min((boots <= 0).mean(), (boots >= 0).mean())
    return {"mean_treatment": t.mean(), "mean_control": c.mean(),
            "diff": t.mean() - c.mean(), "ci_low": lo, "ci_high": hi,
            "p_value_boot": max(p_boot, 1 / n_boot)}


# ---------------------------------------------------------------------------
# 5. Multiple comparisons
# ---------------------------------------------------------------------------
def holm_adjust(p_values: list[float]) -> list[float]:
    """Holm-Bonferroni step-down adjustment (controls family-wise error rate)."""
    p = np.asarray(p_values, float)
    order = np.argsort(p)
    m = len(p)
    adjusted = np.empty(m)
    running_max = 0.0
    for rank, idx in enumerate(order):
        running_max = max(running_max, (m - rank) * p[idx])
        adjusted[idx] = min(running_max, 1.0)
    return adjusted.tolist()


# ---------------------------------------------------------------------------
# 6. CUPED variance reduction
# ---------------------------------------------------------------------------
def cuped_adjust(y: pd.Series, x_pre: pd.Series) -> pd.Series:
    """Y_cuped = Y - theta * (X - mean(X)),  theta = cov(Y, X) / var(X).

    X must be measured BEFORE treatment (here: past-year spend `history`).
    The mean of Y is unchanged; only noise unrelated to treatment is removed.
    """
    theta = np.cov(y, x_pre, ddof=1)[0, 1] / np.var(x_pre, ddof=1)
    return y - theta * (x_pre - x_pre.mean())


# ---------------------------------------------------------------------------
# 7. Power / minimum detectable effect
# ---------------------------------------------------------------------------
def mde_two_proportions(p_base: float, n_per_group: int, alpha: float = 0.05, power: float = 0.8) -> float:
    """Smallest absolute lift detectable with the given sample size (normal approximation)."""
    z_a, z_b = stats.norm.ppf(1 - alpha / 2), stats.norm.ppf(power)
    return (z_a + z_b) * np.sqrt(2 * p_base * (1 - p_base) / n_per_group)


def n_per_group_two_proportions(p_base: float, abs_lift: float, alpha: float = 0.05, power: float = 0.8) -> int:
    """Users needed per group to detect `abs_lift` over baseline `p_base`."""
    p_t = p_base + abs_lift
    z_a, z_b = stats.norm.ppf(1 - alpha / 2), stats.norm.ppf(power)
    var = p_base * (1 - p_base) + p_t * (1 - p_t)
    return int(np.ceil((z_a + z_b) ** 2 * var / abs_lift ** 2))
