"""Load the Hillstrom MineThatData e-mail experiment (64,000 customers)."""
from __future__ import annotations

from pathlib import Path
import sqlite3
import urllib.request

import pandas as pd

DATA_DIR = Path(__file__).resolve().parents[1] / "data"
RAW_FILE = DATA_DIR / "hillstrom.csv"

# Public copies of the same file. If one is down, the next is tried.
SOURCES = [
    "https://hillstorm1.s3.us-east-2.amazonaws.com/hillstorm_no_indices.csv.gz",
    "http://www.minethatdata.com/Kevin_Hillstrom_MineThatData_E-MailAnalytics_DataMiningChallenge_2008.03.20.csv",
]

EXPECTED_COLUMNS = ["recency", "history_segment", "history", "mens", "womens", "zip_code",
                    "newbie", "channel", "segment", "visit", "conversion", "spend"]

CONTROL = "No E-Mail"
TREATMENTS = ["Mens E-Mail", "Womens E-Mail"]


def download(force: bool = False) -> Path:
    """Download the raw CSV into data/ (skipped if it already exists)."""
    DATA_DIR.mkdir(exist_ok=True)
    if RAW_FILE.exists() and not force:
        return RAW_FILE
    last_err = None
    for url in SOURCES:
        try:
            df = pd.read_csv(url)
            df.to_csv(RAW_FILE, index=False)
            print(f"Downloaded {len(df):,} rows from {url}")
            return RAW_FILE
        except Exception as err:  # try the next mirror
            last_err = err
    raise RuntimeError(
        "Could not download the data automatically. Download the CSV manually from "
        "https://blog.minethatdata.com/2008/03/minethatdata-e-mail-analytics-and-data.html "
        f"and save it as {RAW_FILE}. Last error: {last_err}")


def load(path: Path | str = RAW_FILE) -> pd.DataFrame:
    """Read the CSV and validate its schema."""
    df = pd.read_csv(path)
    df.columns = [c.strip().lower() for c in df.columns]
    missing = set(EXPECTED_COLUMNS) - set(df.columns)
    if missing:
        raise ValueError(f"Unexpected file layout, missing columns: {sorted(missing)}")
    return df[EXPECTED_COLUMNS]


def to_sqlite(df: pd.DataFrame, table: str = "customers") -> sqlite3.Connection:
    """Load the data into an in-memory SQLite database for the SQL checks."""
    con = sqlite3.connect(":memory:")
    df.to_sql(table, con, index=False)
    return con


def read_named_queries(sql_path: Path | str) -> dict[str, str]:
    """Split a .sql file into {name: query} using '-- name: <name>' markers."""
    queries, name, buf = {}, None, []
    for line in Path(sql_path).read_text(encoding="utf-8").splitlines():
        if line.strip().lower().startswith("-- name:"):
            if name:
                queries[name] = "\n".join(buf).strip()
            name, buf = line.split(":", 1)[1].strip(), []
        elif name:
            buf.append(line)
    if name:
        queries[name] = "\n".join(buf).strip()
    return queries
