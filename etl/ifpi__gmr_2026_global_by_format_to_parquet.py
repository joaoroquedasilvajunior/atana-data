"""IFPI GMR 2026 — global by format → Parquet.

Phase 5b. Second of four `atana.ifpi` tables. 2025 recorded-music revenue split
by named format, as published verbatim in the press release. Mixes share_pct
(stated for some formats) with usd_bn (stated for others); NULL means the
press release does not give that field. The corpus convention is to never
fabricate residuals — Downloads + sync are not separately stated in the press
release and therefore are NOT in this table; the named-format coverage is the
documented gap (≈ 21 % of the headline total).

SOURCE
------
    IFPI GMR 2026 press release.

OUTPUT
------
    raw/ifpi/gmr_2026_global_by_format.parquet  (+ .meta.json)

Idempotent; ATANA_ETL_SKIP_PUSH guard.
"""
import hashlib, json, os
from datetime import date
from pathlib import Path
import duckdb, pandas as pd

REPO_ROOT = Path(__file__).resolve().parent.parent
OUT = REPO_ROOT / "raw" / "ifpi"
OUT.mkdir(parents=True, exist_ok=True)
SOURCE_PAGE = "https://www.ifpi.org/global-music-report-2026-global-recorded-music-revenues-grow-6-4-as-record-companies-drive-innovation/"
HEADLINE_USD_BN_2025 = 31.7

COLUMNS = ["year", "format", "share_pct", "usd_bn", "yoy_pct",
           "is_subcategory_of", "notes", "source_page"]

# Verbatim from the press release. Paid subscription streaming is a SUBCATEGORY
# of total streaming (the press release calls this out explicitly).
ROWS = [
    (2025, "Streaming (total)",         69.6, 22.0, None, None,
     "Total streaming revenues surpassed US$ 22 bn (69.6 % of global). "
     "YoY for the streaming aggregate is not stated in the press release.",
     SOURCE_PAGE),
    (2025, "Paid subscription streaming", 52.4, None, 8.8, "Streaming (total)",
     "Subset of total streaming. 837 mi paid streaming users globally.",
     SOURCE_PAGE),
    (2025, "Physical",                  None, None, 8.0, None,
     "Returned to growth (+8.0 %). Vinyl +13.7 %, 19th consecutive year of growth. "
     "Absolute USD value not stated in the press release.",
     SOURCE_PAGE),
    (2025, "Performance rights",        None, 2.9, 0.3, None,
     "5th successive year of revenue growth.",
     SOURCE_PAGE),
    (2025, "Total",                     100.0, HEADLINE_USD_BN_2025, 6.4, None,
     "11th consecutive year of growth.",
     SOURCE_PAGE),
]


def build() -> pd.DataFrame:
    df = pd.DataFrame(
        [dict(zip(COLUMNS, r)) for r in ROWS], columns=COLUMNS)
    df = df.sort_values(
        ["year", "share_pct"], ascending=[True, False], na_position="last"
    ).reset_index(drop=True)
    df["year"] = df["year"].astype("int32")
    return df


def validate(df: pd.DataFrame) -> None:
    print("Validating...")
    assert len(df) == 5, f"expected 5 rows, got {len(df)}"
    expected = {"Streaming (total)", "Paid subscription streaming",
                "Physical", "Performance rights", "Total"}
    assert set(df["format"]) == expected, f"format set off: {sorted(df['format'])}"
    print(f"  ✓ 5 formats — Streaming(total) + Paid sub-stream + Physical + "
          f"Performance rights + Total")

    # Sanity: streaming 22.0 bn / 31.7 bn = 69.4 % ≈ 69.6 % stated; tolerance 0.5 pp
    implied = 22.0 / HEADLINE_USD_BN_2025 * 100
    assert abs(implied - 69.6) < 0.5, \
        f"streaming share implied from USD ({implied:.1f}) inconsistent with stated 69.6 %"
    print(f"  ✓ streaming US$ 22 bn / 31.7 bn = {implied:.1f} % ≈ stated 69.6 %")

    # Performance rights 2.9 bn / 31.7 bn ≈ 9.1 %
    pr = 2.9 / HEADLINE_USD_BN_2025 * 100
    print(f"  · performance rights US$ 2.9 bn / 31.7 bn = {pr:.1f} % "
          f"(physical + downloads/sync absorb the remainder, not stated)")


def write_parquet(df: pd.DataFrame) -> Path:
    out_path = OUT / "gmr_2026_global_by_format.parquet"
    con = duckdb.connect()
    con.register("df_data", df)
    con.execute(f"COPY df_data TO '{out_path}' (FORMAT PARQUET, COMPRESSION ZSTD)")
    print(f"  ✓ {out_path.relative_to(REPO_ROOT)} — {len(df)} rows, "
          f"{out_path.stat().st_size/1024:.1f} KB")
    return out_path


def write_meta(out_path: Path, df: pd.DataFrame) -> None:
    meta = {
        "table": out_path.stem, "schema": "ifpi",
        "description": "IFPI GMR 2026 — 2025 global recorded-music revenue by "
                       "format. 5 rows (Streaming total / Paid sub-stream / "
                       "Physical / Performance rights / Total). share_pct and "
                       "usd_bn each NULL where the press release does not state "
                       "them. Downloads + sync are not separately named — "
                       "implied residual ≈ 21 %, documented as a coverage gap.",
        "source": "IFPI Global Music Report 2026 (press release, 18 March 2026).",
        "source_pages": [SOURCE_PAGE], "fetch_date": "2026-06-01",
        "etl_script": "etl/ifpi__gmr_2026_global_by_format_to_parquet.py",
        "etl_run_date": str(date.today()),
        "licence": "IFPI published figures — public press release.",
        "grain": "one row per (year, format)", "row_count": int(len(df)),
        "notes": "Paid subscription streaming is a SUBSET of total streaming "
                 "(is_subcategory_of column). Same convention as the CISAC named-"
                 "stream-residual treatment. See docs/methodology/ifpi_gmr.md.",
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
    print("Building atana.ifpi.gmr_2026_global_by_format...")
    df = build(); validate(df)
    out_path = write_parquet(df); write_meta(out_path, df)
    maybe_push(df, "ifpi", "gmr_2026_global_by_format")
    print("Done.")


if __name__ == "__main__":
    main()
