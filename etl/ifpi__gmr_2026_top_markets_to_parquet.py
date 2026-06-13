"""IFPI GMR 2026 — top markets / per-country signals → Parquet.

Phase 5b. Fourth of four `atana.ifpi` tables. Per-country YoY values explicitly
named in the IFPI press release prose — twelve countries with 2025 growth
figures and (where stated) the global ranking + rank change. NOT a full
country-by-country table (Premium Edition paywalled); this is the
named-in-press-release subset that's already public.

CORPUS RELEVANCE
----------------
- **Brazil +14.1 %, moved up to #8 globally** — the corpus's home market in a
  global recorded-music ranking for the first time.
- **Mexico +13.3 %, #10 globally** — joins atana.cisac's "Mexico = the only
  LATAM country in the GCR leading-smaller-markets-by-digital-share" cell
  (65.1 % in CISAC) and atana.inegi's CSCM 2024 (música y conciertos
  +14.9 %), three independent signals pointing at the Mexican music economy.

SOURCE
------
    IFPI GMR 2026 press release.

OUTPUT
------
    raw/ifpi/gmr_2026_top_markets.parquet  (+ .meta.json)

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

COLUMNS = ["year", "country", "country_iso3", "global_rank_2025",
           "rank_change_yoy", "yoy_pct", "notes", "source_page"]

# Verbatim from the press release. Rank and rank-change NULL where not stated.
ROWS = [
    (2025, "USA",          "USA",  1,  None,  3.3,
     "The world's single largest recorded-music market.", SOURCE_PAGE),
    (2025, "Japan",        "JPN",  2,  None,  8.9,
     "World's second-largest market; returned to growth in 2025.", SOURCE_PAGE),
    (2025, "China",        "CHN",  4,  None, 20.1,
     "Overtook Germany to become #4; fastest-growing market in the top 20.", SOURCE_PAGE),
    (2025, "UK",           "GBR",  None, None,  4.8,
     "Top-3 market in Europe.", SOURCE_PAGE),
    (2025, "Germany",      "DEU",  None, None,  1.7,
     "Top-3 market in Europe; dropped behind China in 2025.", SOURCE_PAGE),
    (2025, "France",       "FRA",  None, None,  3.7,
     "Top-3 market in Europe.", SOURCE_PAGE),
    (2025, "Brazil",       "BRA",  8,  1,    14.1,
     "Moved up one rank to #8 globally; largest LATAM market.", SOURCE_PAGE),
    (2025, "Canada",       "CAN",  9,  -1,    5.6,
     "Dropped one place to #9 globally.", SOURCE_PAGE),
    (2025, "Mexico",       "MEX",  10, None, 13.3,
     "Climbed to #10 globally. Largest LATAM after Brazil; corpus also reads "
     "Mexico via atana.cisac (65.1 % digital share) and atana.inegi CSCM 2024 "
     "(música y conciertos +14.9 %).", SOURCE_PAGE),
    (2025, "Australia",    "AUS",  13, -2,    1.2,
     "Dropped two places to #13 globally.", SOURCE_PAGE),
    (2025, "New Zealand",  "NZL",  None, None,  3.0,
     "15.2 % of Australasian regional revenue.", SOURCE_PAGE),
    (2025, "South Africa", "ZAF",  None, None, 12.9,
     "78.1 % of Sub-Saharan Africa regional revenue.", SOURCE_PAGE),
]


def build() -> pd.DataFrame:
    df = pd.DataFrame(
        [dict(zip(COLUMNS, r)) for r in ROWS], columns=COLUMNS)
    # Sort: ranked countries by global_rank, then by yoy_pct desc
    df = df.sort_values(
        ["year", "global_rank_2025", "yoy_pct"],
        ascending=[True, True, False], na_position="last"
    ).reset_index(drop=True)
    df["year"] = df["year"].astype("int32")
    df["global_rank_2025"] = df["global_rank_2025"].astype("Int32")
    df["rank_change_yoy"] = df["rank_change_yoy"].astype("Int32")
    return df


def validate(df: pd.DataFrame) -> None:
    print("Validating...")
    assert len(df) == 12, f"expected 12 rows, got {len(df)}"
    assert df["country_iso3"].nunique() == 12, "country_iso3 not unique"
    assert all(len(c) == 3 and c.isupper() for c in df["country_iso3"])
    print(f"  ✓ 12 countries, distinct alpha-3 codes")

    ranked = df[df["global_rank_2025"].notna()]
    expected_ranked = {("USA", 1), ("Japan", 2), ("China", 4), ("Brazil", 8),
                       ("Canada", 9), ("Mexico", 10), ("Australia", 13)}
    got = set(zip(ranked["country"], ranked["global_rank_2025"]))
    assert got == expected_ranked, f"ranked countries mismatch: {got}"
    print(f"  ✓ ranked subset (7 countries): USA #1, Japan #2, China #4, "
          f"Brazil #8, Canada #9, Mexico #10, Australia #13")

    # LATAM duo specifically
    latam = df[df["country"].isin(["Brazil", "Mexico"])]
    assert all(latam["yoy_pct"] > 12), "Brazil and Mexico must both be > 12 % YoY"
    print(f"  ✓ Brazil +14.1 % (#8) and Mexico +13.3 % (#10) — LATAM in top-10 confirmed")


def write_parquet(df: pd.DataFrame) -> Path:
    out_path = OUT / "gmr_2026_top_markets.parquet"
    con = duckdb.connect()
    con.register("df_data", df)
    con.execute(f"COPY df_data TO '{out_path}' (FORMAT PARQUET, COMPRESSION ZSTD)")
    print(f"  ✓ {out_path.relative_to(REPO_ROOT)} — {len(df)} rows, "
          f"{out_path.stat().st_size/1024:.1f} KB")
    return out_path


def write_meta(out_path: Path, df: pd.DataFrame) -> None:
    meta = {
        "table": out_path.stem, "schema": "ifpi",
        "description": "IFPI GMR 2026 — 12 countries with 2025 growth named "
                       "verbatim in the press release. 7 countries also carry "
                       "a global rank (USA #1, Japan #2, China #4, Brazil #8, "
                       "Canada #9, Mexico #10, Australia #13). Brazil + "
                       "Mexico in the top-10 is the corpus headline.",
        "source": "IFPI Global Music Report 2026 (press release).",
        "source_pages": [SOURCE_PAGE], "fetch_date": "2026-06-01",
        "etl_script": "etl/ifpi__gmr_2026_top_markets_to_parquet.py",
        "etl_run_date": str(date.today()),
        "licence": "IFPI published figures — public press release.",
        "grain": "one row per (year, country)", "row_count": int(len(df)),
        "notes": "NOT the complete top-20 / top-200 country list — that lives in "
                 "the paywalled GMR 2026 Premium Edition. This table is the "
                 "named-in-press-release subset.",
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
    print("Building atana.ifpi.gmr_2026_top_markets...")
    df = build(); validate(df)
    out_path = write_parquet(df); write_meta(out_path, df)
    maybe_push(df, "ifpi", "gmr_2026_top_markets")
    print("Done.")


if __name__ == "__main__":
    main()
