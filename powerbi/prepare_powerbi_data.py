"""Prepare the data for Power BI and export reference values for cross-checking.

Run from the project root:   python powerbi/prepare_powerbi_data.py

Outputs
- data/hillstrom_powerbi.csv              -> import this file into Power BI (not committed)
- powerbi/reference_values_from_python.csv -> every number the dashboard shows, computed in Python
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src import data  # noqa: E402

df = data.load(data.download())
df["past_purchase"] = np.select(
    [(df["mens"] == 1) & (df["womens"] == 1), df["mens"] == 1, df["womens"] == 1],
    ["Both", "Mens only", "Womens only"], default="Neither")
df["customer_type"] = np.where(df["newbie"] == 1, "New", "Existing")
df["test_group"] = df["segment"].map({"Mens E-Mail": "Men's e-mail",
                                      "Womens E-Mail": "Women's e-mail",
                                      "No E-Mail": "Control (no e-mail)"})
df.insert(0, "customer_id", np.arange(1, len(df) + 1))

out_csv = ROOT / "data" / "hillstrom_powerbi.csv"
df.to_csv(out_csv, index=False)
print(f"Wrote {len(df):,} rows to {out_csv}")

# ---------------------------------------------------------------- reference values
rows = []

def add(scope, level, frame):
    ctrl = frame[frame["segment"] == data.CONTROL]
    for grp, g in frame.groupby("test_group"):
        is_ctrl = grp.startswith("Control")
        rows.append({
            "scope": scope, "level": level, "test_group": grp, "customers": len(g),
            "visit_rate_pct": round(g["visit"].mean() * 100, 2),
            "conversion_rate_pct": round(g["conversion"].mean() * 100, 2),
            "spend_per_customer": round(g["spend"].mean(), 4),
            "visit_lift_pp": None if is_ctrl else round((g["visit"].mean() - ctrl["visit"].mean()) * 100, 2),
            "conversion_lift_pp": None if is_ctrl else round((g["conversion"].mean() - ctrl["conversion"].mean()) * 100, 2),
            "spend_lift": None if is_ctrl else round(g["spend"].mean() - ctrl["spend"].mean(), 4),
            "revenue_per_1000": None if is_ctrl else round((g["spend"].mean() - ctrl["spend"].mean()) * 1000, 1),
        })

add("Overall", "All customers", df)
for var in ["past_purchase", "customer_type", "channel", "zip_code"]:
    for level, g in df.groupby(var):
        add(var, level, g)
for (pp, ct), g in df.groupby(["past_purchase", "customer_type"]):
    add("past_purchase x customer_type", f"{pp} / {ct}", g)

ref = pd.DataFrame(rows)
ref_path = ROOT / "powerbi" / "reference_values_from_python.csv"
ref.to_csv(ref_path, index=False)
print(f"Wrote {len(ref)} reference rows to {ref_path}")
print(ref[ref["scope"] == "Overall"].to_string(index=False))
