# Does a promotional e-mail actually drive sales? An A/B test analysis

Analysis of a randomized e-mail marketing experiment with **64,000 customers** and three arms: men's campaign, women's campaign and a no-email control group. The goal is to measure the **incremental** effect of each campaign on visits, conversions and spend, and to recommend **who should receive which e-mail**.

> **Status:** 🚧 in progress. Notebook 01 (data checks and main effects) is done; notebooks 02 and 03 are next.

---

## Key results


- **Recommendation:** ⏳

---

## The experiment

| | |
|---|---|
| Data | [Kevin Hillstrom MineThatData E-Mail Analytics Challenge (2008)](https://blog.minethatdata.com/2008/03/minethatdata-e-mail-analytics-and-data.html) |
| Population | 64,000 customers who purchased in the previous 12 months |
| Arms | `Mens E-Mail` · `Womens E-Mail` · `No E-Mail` (control), randomized ~1/3 each |
| Outcomes (2 weeks) | `visit`, `conversion`, `spend` |
| Pre-treatment covariates | recency, past-year spend (`history`), bought men's/women's, new customer, zip-code type, channel |

## Approach

1. **Data-quality checks in SQL**: missing values, logical consistency (no conversion without a visit, etc.), group profiles. See [`sql/01_data_checks.sql`](sql/01_data_checks.sql).
2. **Experiment health**: sample ratio mismatch (chi-square) and covariate balance (standardized mean differences).
3. **Main effects**: absolute and relative lift with 95% CIs; Holm correction for multiple comparisons; bootstrap CIs for the heavy-tailed spend metric.
4. **Variance reduction (CUPED)**: past-year spend as the pre-period covariate, to tighten the confidence intervals.
5. **Power and MDE**: which effects this sample can and cannot detect, and the sample size a follow-up test would need.
6. **Heterogeneous effects**: which customer segments respond to which campaign.
7. **Business recommendation**: targeting rules and incremental revenue per 1,000 e-mails, summarized in a one-page memo.

## Repository structure

```
├── notebooks/
│   ├── 01_data_checks_and_main_effects.ipynb   ✅
│   ├── 02_cuped_power_segments.ipynb           ⏳
│   └── 03_targeting_recommendation.ipynb       ⏳
├── sql/
│   └── 01_data_checks.sql        # data-quality and experiment-health queries
├── src/
│   ├── data.py                   # download, schema validation, SQLite loading
│   └── stats_utils.py            # SRM, balance, lift CIs, bootstrap, Holm, CUPED, power
├── reports/
│   └── memo.pdf                  # one-page summary for stakeholders  ⏳
├── data/                         # raw CSV (downloaded automatically, not committed)
└── requirements.txt
```

## How to run

```bash
pip install -r requirements.txt
jupyter notebook notebooks/01_data_checks_and_main_effects.ipynb
```

The first run downloads the data into `data/`. If the download fails, see [`data/README.md`](data/README.md).

## Tools

Python (pandas, NumPy, SciPy, matplotlib) · SQL (SQLite) · Jupyter
