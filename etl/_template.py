"""ETL template — copy this when creating a new pipeline.

Convention: each script reads from a single source (xlsx, JSONL, API),
writes Parquet to raw/<source>/<table>.parquet, and optionally pushes
the result to MotherDuck (atana.<schema>.<table>).

Idempotent: rerunning produces identical output.
"""
import os
from pathlib import Path

import duckdb
import pandas as pd

# Paths
REPO_ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = REPO_ROOT / "raw"

# MotherDuck token from env (never hardcode)
MD_TOKEN = os.environ.get("MOTHERDUCK_TOKEN")

# -----------------------------------------------------------------------------
# 1. Extract — read from source
# -----------------------------------------------------------------------------
def extract():
    raise NotImplementedError

# -----------------------------------------------------------------------------
# 2. Transform — normalize columns, types, units
# -----------------------------------------------------------------------------
def transform(df: pd.DataFrame) -> pd.DataFrame:
    raise NotImplementedError

# -----------------------------------------------------------------------------
# 3. Load — write Parquet locally + optionally to MotherDuck
# -----------------------------------------------------------------------------
def load(df: pd.DataFrame, schema: str, table: str):
    out_path = RAW_DIR / schema / f"{table}.parquet"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(out_path, index=False, compression="snappy")
    print(f"  Wrote {len(df):,} rows → {out_path}")

    # Push to MotherDuck if token available
    if MD_TOKEN:
        con = duckdb.connect(f"md:atana?motherduck_token={MD_TOKEN}")
        con.execute(f"CREATE SCHEMA IF NOT EXISTS atana.{schema}")
        con.execute(f"CREATE OR REPLACE TABLE atana.{schema}.{table} AS SELECT * FROM df")
        n = con.execute(f"SELECT COUNT(*) FROM atana.{schema}.{table}").fetchone()[0]
        print(f"  Synced atana.{schema}.{table} ({n:,} rows)")

# -----------------------------------------------------------------------------
# Entrypoint
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    raw = extract()
    clean = transform(raw)
    load(clean, schema="<schema>", table="<table>")
