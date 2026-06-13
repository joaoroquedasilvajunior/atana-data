"""IFPI GMR 2026 — global headline → Parquet.

Phase 5b of the Atana Data expansion — first ingest of the IFPI Global Music
Report into `atana.ifpi`. The recorded-music (master / label) lens, distinct
from the author-royalty (CMO) lens carried by atana.ecad + atana.cisac.
Together: three music-money lenses on the same market.

Headline 2025 — first of four small Tier-1 tables.

SOURCE
------
    https://www.ifpi.org/global-music-report-2026-global-recorded-music-revenues-grow-6-4-as-record-companies-drive-innovation/
    IFPI press release (public), 18 March 2026.

OUTPUT
------
    raw/ifpi/gmr_2026_global_headline.parquet  (+ .meta.json)

Idempotent; ATANA_ETL_SKIP_PUSH guard. Schema: atana.ifpi.
"""
import hashlib, json, os
from datetime import date
from pathlib import Path
import duckdb, pandas as pd

REPO_ROOT = Path(__file__).resolve().parent.parent
OUT = REPO_ROOT / "raw" / "ifpi"
OUT.mkdir(parents=True, exist_ok=True)
SOURCE_PAGE = "https://www.ifpi.org/global-music-report-2026-global-recorded-music-revenues-grow-6-4-as-record-companies-drive-innovation/"

COLUMNS = ["year", "total_usd_bn", "yoy_pct",
           "paid_streaming_users_mi", "consecutive_growth_years",
           "notes", "source_page"]

ROWS = [
    (2025, 31.7, 6.4, 837, 11,
     "IFPI GMR 2026 reports 2025 global recorded music revenue at US$ 31.7 bn, "
     "+6.4 % YoY, 11th consecutive year of growth, 837 mi paid streaming users.",
     SOURCE_PAGE),
]


def build() -> pd.DataFrame:
    df = pd.DataFrame(
        [dict(zip(COLUMNS, r)) for r in ROWS], columns=COLUMNS)
    df["year"] = df["year"].astype("int32")
    df["paid_streaming_users_mi"] = df["paid_streaming_users_mi"].astype("Int32")
    df["consecutive_growth_years"] = df["consecutive_growth_years"].astype("Int32")
    return df


def validate(df: pd.DataFrame) -> None:
    print("Validating...")
    assert len(df) == 1, f"expected 1 row, got {len(df)}"
    r = df.iloc[0]
    assert r["total_usd_bn"] == 31.7 and r["yoy_pct"] == 6.4, \
        f"headline numbers off: {r['total_usd_bn']} / {r['yoy_pct']}"
    print(f"  ✓ 2025 global headline: US$ {r['total_usd_bn']} bn (+{r['yoy_pct']} %), "
          f"{r['paid_streaming_users_mi']} mi paid users, "
          f"{r['consecutive_growth_years']}th consecutive growth year")


def write_parquet(df: pd.DataFrame) -> Path:
    out_path = OUT / "gmr_2026_global_headline.parquet"
    con = duckdb.connect()
    con.register("df_data", df)
    con.execute(f"COPY df_data TO '{out_path}' (FORMAT PARQUET, COMPRESSION ZSTD)")
    print(f"  ✓ {out_path.relative_to(REPO_ROOT)} — {len(df)} rows, "
          f"{out_path.stat().st_size/1024:.1f} KB")
    return out_path


def write_meta(out_path: Path, df: pd.DataFrame) -> None:
    meta = {
        "table": out_path.stem, "schema": "ifpi",
        "description": "IFPI GMR 2026 — 2025 global recorded-music headline. "
                       "US$ 31.7 bn, +6.4 %, 11th consecutive year of growth, "
                       "837 mi paid streaming users. Recorded-music lens, "
                       "distinct from the author-royalty lens (atana.cisac, atana.ecad).",
        "source": "IFPI Global Music Report 2026 (press release, 18 March 2026).",
        "source_pages": [SOURCE_PAGE], "fetch_date": "2026-06-01",
        "etl_script": "etl/ifpi__gmr_2026_global_headline_to_parquet.py",
        "etl_run_date": str(date.today()),
        "licence": "IFPI published figures — public press release.",
        "grain": "one row per reference year", "row_count": int(len(df)),
        "notes": "Tier 1 — public press release only. Premium Edition has "
                 "country-level detail (paywalled). See docs/methodology/ifpi_gmr.md.",
    }
    out_path.with_suffix(".meta.json").write_text(
        json.dumps(meta, indent=2, ensure_ascii=False))
    print(f"  ✓ {out_path.with_suffix('.meta.json').relative_to(REPO_ROOT)}")


def maybe_push(df: pd.DataFrame, schema: str, table: str) -> None:
    if os.environ.get("ATANA_ETL_SKIP_PUSH"):
        print(f"  · push skipped for atana.{schema}.{table} (ATANA_ETL_SKIP_PUSH)")
        return

    def _jwt(t):
        t = (t or "").strip()
        return t if (t.startswith("eyJ") and t.count(".") == 2) else ""
    token = _jwt(os.environ.get("MOTHERDUCK_TOKEN"))
    if not token:
        tf = REPO_ROOT / ".motherduck_token"
        token = _jwt(tf.read_text()) if tf.exists() else ""
    if not token:
        print(f"  · MotherDuck push skipped for atana.{schema}.{table} — no valid token.")
        return
    con = duckdb.connect(f"md:atana?motherduck_token={token}")
    con.execute(f"CREATE SCHEMA IF NOT EXISTS atana.{schema}")
    con.register("df_data", df)
    con.execute(f"CREATE OR REPLACE TABLE atana.{schema}.{table} AS SELECT * FROM df_data")
    n = con.execute(f"SELECT COUNT(*) FROM atana.{schema}.{table}").fetchone()[0]
    print(f"  ✓ Synced atana.{schema}.{table} ({n} rows)")


def main():
    print("Building atana.ifpi.gmr_2026_global_headline...")
    df = build(); validate(df)
    out_path = write_parquet(df); write_meta(out_path, df)
    maybe_push(df, "ifpi", "gmr_2026_global_headline")
    print("Done.")


if __name__ == "__main__":
    main()
