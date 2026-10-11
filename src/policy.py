"""Evaluate targeting policies ("who gets which e-mail") with randomized experiment data.

Because customers were randomized, the value of ANY policy can be estimated from the
experiment itself with inverse-probability weighting (IPW):

    V(policy) = mean_i [ 1{arm_i == policy(x_i)} / P(arm_i) * y_i ]

i.e. we keep the customers who happened to receive the arm the policy would have chosen,
and up-weight them by 1 / (probability of receiving that arm). No model is needed.
"""
from __future__ import annotations

from typing import Callable

import numpy as np
import pandas as pd

Policy = Callable[[pd.DataFrame], pd.Series]


def ipw_contributions(df: pd.DataFrame, assigned: pd.Series, outcome: np.ndarray,
                      arm_col: str = "segment") -> np.ndarray:
    """Per-customer IPW terms; their mean is the estimated value of the policy."""
    arm_share = df[arm_col].value_counts(normalize=True)
    match = (df[arm_col].values == assigned.values)
    weights = 1.0 / df[arm_col].map(arm_share).values
    return match * weights * outcome


def profit_outcome(df: pd.DataFrame, assigned: pd.Series, margin: float, cost_per_email: float,
                   control: str) -> np.ndarray:
    """Profit per customer = margin * spend - e-mail cost (if the policy sends an e-mail)."""
    sends_email = (assigned.values != control).astype(float)
    return margin * df["spend"].values - cost_per_email * sends_email


def policy_value(df: pd.DataFrame, policy: Policy, margin: float, cost_per_email: float,
                 control: str) -> tuple[float, np.ndarray]:
    assigned = policy(df)
    y = profit_outcome(df, assigned, margin, cost_per_email, control)
    contrib = ipw_contributions(df, assigned, y)
    return contrib.mean(), contrib


def paired_bootstrap_diff(contrib_a: np.ndarray, contrib_b: np.ndarray, n_boot: int = 2000,
                          seed: int = 7) -> tuple[float, float, float]:
    """Mean difference (a - b) with a percentile bootstrap CI, resampling customers jointly."""
    rng = np.random.default_rng(seed)
    d = contrib_a - contrib_b
    boots = np.array([d[rng.integers(0, d.size, d.size)].mean() for _ in range(n_boot)])
    return d.mean(), *np.quantile(boots, [0.025, 0.975])


# ---------------------------------------------------------------------------
# Policies
# ---------------------------------------------------------------------------
def everyone(arm: str) -> Policy:
    return lambda d: pd.Series(arm, index=d.index)


def match_past_purchase(d: pd.DataFrame) -> pd.Series:
    """Business-intuition rule: send the e-mail that matches what the customer bought before."""
    return pd.Series(np.where(d["past_purchase"] == "Womens only", "Womens E-Mail", "Mens E-Mail"),
                     index=d.index)


def learn_cell_rule(train: pd.DataFrame, cell_cols: list[str], margin: float, cost_per_email: float,
                    control: str) -> dict:
    """For every cell (combination of cell_cols), pick the arm with the highest mean profit in `train`."""
    t = train.assign(profit=margin * train["spend"] - cost_per_email * (train["segment"] != control))
    means = t.groupby(cell_cols + ["segment"])["profit"].mean().unstack("segment")
    return means.idxmax(axis=1).to_dict()


def apply_cell_rule(rule: dict, cell_cols: list[str], fallback: str) -> Policy:
    def policy(d: pd.DataFrame) -> pd.Series:
        keys = list(zip(*[d[c] for c in cell_cols])) if len(cell_cols) > 1 else list(d[cell_cols[0]])
        return pd.Series([rule.get(k, fallback) for k in keys], index=d.index)
    return policy
