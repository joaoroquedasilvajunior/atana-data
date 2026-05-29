"""CISAC GCR 2025 — global collections by income stream → Parquet.

Phase 5a of the Atana Data expansion — first ingest of the CISAC Global
Collections Report (GCR) into `atana.cisac`. Tier 1 of the CISAC scoping
(`_atana_intel/scoping_cisac_gcr_2025_2026-05-29.md`).

WHAT IT IS
----------
The headline 2024 split of global creator-royalty collections by income
stream, as published on the public landing page of the CISAC Global
Collections Report 2025. Four rows: Digital, Live & background, Broadcast
(TV & radio), and Total.

⚠️ THE NAMED-STREAMS GAP
------------------------
Digital + Live & background + Broadcast = €12.68 bn; Total = €13.97 bn.
The €1.29 bn (~9.2 %) gap is absorbed by two minor streams the landing
page calls out in prose but not as headline figures — **physical formats**
(falling — "−37.7 % below the 2015 figure") and **private copying** (also
fell). Those two are NOT in this table by design: the corpus convention is
to ingest verbatim what the source publishes as headline rows, never to
allocate inferred residuals. The gap is the documented anomaly (like ECAD's
1.25 % distribution-by-segment gap).

GRAIN
-----
One row per (year, stream). 2024 only at v1 launch (4 rows); future GCR
editions extend by year with the same schema.

SOURCE
------
    https://www.cisac.org/cisac-global-collections-report-2025
    GCR 2025 landing page (public, no login required).

OUTPUT
------
    raw/cisac/gcr_2025_global_by_stream.parquet  (+ .meta.json)

Idempotent: inline data → DuckDB COPY to Parquet (no pyarrow); byte-identical
reruns. MotherDuck push gated behind a token (skipped when ATANA_ETL_SKIP_PUSH
is set). Schema: atana.cisac.

Usage:
    python etl/cisac__gcr_2025_global_by_stream_to_parquet.py
"""
import hashlib
import json
import os
from datetime import date
from pathlib import Path

import duckdb
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parent.parent
OUT = REPO_ROOT / "raw" / "cisac"
OUT.mkdir(parents=True, exist_ok=True)

SOURCE_PAGE = "https://www.cisac.org/cisac-global-collections-report-2025"

COLUMNS = [
    "year",
    "stream",            # 'Digital' / 'Live & background' / 'Broadcast' / 'Total'
    "eur_mi",            # EUR millions, current prices
    "yoy_pct",           # year-on-year growth %, verbatim
    "source_page",
]

# Verbatim from the GCR 2025 landing page (2024 reference year).
ROWS = [
    (2024, "Digital",            5140.0, 11.2),
    (2024, "Live & background",  3600.0,  9.6),
    (2024, "Broadcast",          3940.0,  0.8),  # TV & radio combined
    (2024, "Total",             13970.0,  6.6),
]


def build() -> pd.DataFrame:
    df = pd.DataFrame(
        [{"year": r[0], "stream": r[1], "eur_mi": r[2], "yoy_pct": r[3],
          "source_page": SOURCE_PAGE} for r in ROWS],
        columns=COLUMNS,
    )
    df = df.sort_values(["year", "eur_mi"], ascending=[True, False]).reset_index(drop=True)
    df["year"] = df["year"].astype("int32")
    return df


def validate(df: pd.DataFrame) -> None:
    print("Validating...")
    assert len(df) == 4, f"expected 4 rows, got {len(df)}"
    assert set(df["stream"]) == {"Digital", "Live & background",
                                 "Broadcast", "Total"}, \
        f"unexpected stream set: {sorted(df['stream'])}"
    print(f"  ✓ 4 rows, streams ∈ {{Digital, Live & background, Broadcast, Total}}")

    # The three named streams + the residual (physical + private copying) = Total.
    total = float(df.loc[df["stream"] == "Total", "eur_mi"].iloc[0])
    named = float(df.loc[df["stream"] != "Total", "eur_mi"].sum())
    residual = total - named
    pct_residual = residual / total * 100
    assert 800.0 <= residual <= 1800.0, \
        f"residual (physical + private copying) {residual:.0f} mi outside expected ~1000-1500 mi band"
    print(f"  ✓ named-streams sum €{named:,.0f} mi vs total €{total:,.0f} mi — "
          f"residual €{residual:,.0f} mi ({pct_residual:.1f} % = physical + private "
          f"copying, documented anomaly)")

    # YoY 2024 values match the landing page verbatim
    yoy = df.set_index("stream")["yoy_pct"].to_dict()
    assert yoy == {"Digital": 11.2, "Live & background": 9.6,
                   "Broadcast": 0.8, "Total": 6.6}, f"YoY off: {yoy}"
    print(f"  ✓ 2024 YoY: Total +6.6 · Digital +11.2 · Live & background +9.6 · Broadcast +0.8")


def write_parquet(df: pd.DataFrame) -> Path:
    out_path = OUT / "gcr_2025_global_by_stream.parquet"
    con = duckdb.connect()
    con.register("df_data", df)
    con.execute(f"COPY df_data TO '{out_path}' (FORMAT PARQUET, COMPRESSION ZSTD)")
    size_kb = out_path.stat().st_size / 1024
    print(f"  ✓ {out_path.relative_to(REPO_ROOT)} — {len(df)} rows, {size_kb:.1f} KB")
    return out_path


def write_meta(out_path: Path, df: pd.DataFrame) -> None:
    meta = {
        "table": out_path.stem,
        "schema": "cisac",
        "description": "CISAC Global Collections Report 2025 — 2024 global "
                       "royalty collections by income stream (Digital, Live & "
                       "background, Broadcast, Total). EUR millions. The three "
                       "named streams sum to €12.68 bn; the €1.29 bn residual "
                       "to the €13.97 bn total = physical formats + private "
                       "copying (documented in methodology §3).",
        "source": "CISAC Global Collections Report 2025 — public landing page.",
        "source_pages": [SOURCE_PAGE],
        "fetch_date": "2026-05-29",
        "etl_script": "etl/cisac__gcr_2025_global_by_stream_to_parquet.py",
        "etl_run_date": str(date.today()),
        "licence": "CISAC published figures — public release",
        "grain": "one row per (year, stream)",
        "row_count": int(len(df)),
        "notes": "2024 reference year. Future GCR editions append rows without "
                 "schema change. Reporting currency: EUR. See "
                 "docs/methodology/cisac_gcr.md.",
    }
    out_path.with_suffix(".meta.json").write_text(
        json.dumps(meta, indent=2, ensure_ascii=False))
    print(f"  ✓ {out_path.with_suffix('.meta.json').relative_to(REPO_ROOT)}")


def maybe_push(df: pd.DataFrame, schema: str, table: str) -> None:
    """Push to MotherDuck if a valid JWT token is available.

    Skipped entirely when ATANA_ETL_SKIP_PUSH is set — for build-only / sandbox
    runs where the Parquet is produced but the sync stays with João.
    """
    if os.environ.get("ATANA_ETL_SKIP_PUSH"):
        print(f"  · push skipped for atana.{schema}.{table} (ATANA_ETL_SKIP_PUSH)")
        return

    def _jwt(t) -> str:
        t = (t or "").strip()
        return t if (t.startswith("eyJ") and t.count(".") == 2) else ""
    token = _jwt(os.environ.get("MOTHERDUCK_TOKEN"))
    if not token:
        tf = REPO_ROOT / ".motherduck_token"
        token = _jwt(tf.read_text()) if tf.exists() else ""
    if not token:
        print(f"  · MotherDuck push skipped for atana.{schema}.{table} — no "
              f"valid token.")
        return
    con = duckdb.connect(f"md:atana?motherduck_token={token}")
    con.execute(f"CREATE SCHEMA IF NOT EXISTS atana.{schema}")
    con.register("df_data", df)
    con.execute(
        f"CREATE OR REPLACE TABLE atana.{schema}.{table} AS SELECT * FROM df_data")
    n = con.execute(f"SELECT COUNT(*) FROM atana.{schema}.{table}").fetchone()[0]
    print(f"  ✓ Synced atana.{schema}.{table} ({n} rows)")


def main() -> None:
    print("Building atana.cisac.gcr_2025_global_by_stream...")
    df = build()
    validate(df)
    out_path = write_parquet(df)
    write_meta(out_path, df)
    maybe_push(df, "cisac", "gcr_2025_global_by_stream")
    print("Done.")


if __name__ == "__main__":
    main()
