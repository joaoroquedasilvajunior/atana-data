"""IFPI GMR 2026 — global by region → Parquet.

Phase 5b. Third of four `atana.ifpi` tables. 2025 recorded-music revenue split
by IFPI's 7 regions: USA & Canada, Europe, Asia, Latin America, Australasia,
MENA, Sub-Saharan Africa. Each row carries what the press release names — some
regions have share_pct, some have absolute usd_mi, some have stream_share_pct;
NULL where not stated. Every region grew in 2025.

CORPUS RELEVANCE
----------------
- **Latin America +17.1 % — 16th consecutive year of growth**, streaming 88.1 %
  of regional revenue (the highest in the report after MENA's 97.5 %).
  Contrast with CISAC GCR 2025 which showed LATAM −0.6 % in author-royalty
  collection — the two music-money lenses disagree by ~17.7 pp on direction.
  This is the data point that anchors the proposed 'three music-money lenses'
  cross-source Note.

SOURCE
------
    IFPI GMR 2026 press release.

OUTPUT
------
    raw/ifpi/gmr_2026_global_by_region.parquet  (+ .meta.json)

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

COLUMNS = ["year", "region", "share_pct", "usd_mi", "yoy_pct",
           "streaming_share_pct", "notes", "source_page"]

# Verbatim from the press release.
ROWS = [
    (2025, "USA & Canada",         38.7, None,  3.5, None,
     "Largest region; +US$ 400 mi added. USA +3.3 % (single largest market); "
     "Canada +5.6 % (dropped to #9 globally).",
     SOURCE_PAGE),
    (2025, "Europe",               30.4, None,  5.6, None,
     "Second largest region; +US$ 500 mi added. UK +4.8 %, Germany +1.7 %, "
     "France +3.7 %.",
     SOURCE_PAGE),
    (2025, "Asia",                 None, None, 10.9, None,
     "45.1 % of global PHYSICAL revenues (region's specific strength). Japan "
     "+8.9 %; China +20.1 % (overtook Germany to become #4 — fastest-growing "
     "market in the top 20).",
     SOURCE_PAGE),
    (2025, "Latin America",        None, None, 17.1, 88.1,
     "Fastest-growing region; 16th consecutive year of growth. Streaming = 88.1 % "
     "of regional revenues. Brazil +14.1 % (#8 globally, moved up); Mexico "
     "+13.3 % (#10).",
     SOURCE_PAGE),
    (2025, "Australasia",          None,  623,  1.5, None,
     "Australia +1.2 % (#13, dropped 2). New Zealand +3.0 %, 15.2 % of regional revenue.",
     SOURCE_PAGE),
    (2025, "MENA",                 None, None, 15.2, 97.5,
     "Joint second-fastest growing region. Streaming = 97.5 % of regional revenues "
     "— the highest streaming share of any region.",
     SOURCE_PAGE),
    (2025, "Sub-Saharan Africa",   None,  120, 15.2, None,
     "Joint second-fastest growing region. South Africa is 78.1 % of regional revenue "
     "(+12.9 %).",
     SOURCE_PAGE),
]


def build() -> pd.DataFrame:
    df = pd.DataFrame(
        [dict(zip(COLUMNS, r)) for r in ROWS], columns=COLUMNS)
    df = df.sort_values(
        ["year", "yoy_pct"], ascending=[True, False]
    ).reset_index(drop=True)
    df["year"] = df["year"].astype("int32")
    df["usd_mi"] = df["usd_mi"].astype("Int32")
    return df


def validate(df: pd.DataFrame) -> None:
    print("Validating...")
    assert len(df) == 7, f"expected 7 rows, got {len(df)}"
    expected = {"USA & Canada", "Europe", "Asia", "Latin America",
                "Australasia", "MENA", "Sub-Saharan Africa"}
    assert set(df["region"]) == expected, f"region set off: {sorted(df['region'])}"
    print(f"  ✓ 7 regions (USA & Canada, Europe, Asia, LATAM, Australasia, MENA, SSA)")

    # Every region grew (key narrative point)
    assert (df["yoy_pct"] > 0).all(), "every region must show growth in 2025"
    print(f"  ✓ every region grew in 2025")

    # LATAM is fastest
    fastest = df.sort_values("yoy_pct", ascending=False).iloc[0]
    assert fastest["region"] == "Latin America" and fastest["yoy_pct"] == 17.1, \
        f"LATAM must be fastest at 17.1 %; got {fastest['region']} {fastest['yoy_pct']}"
    print(f"  ✓ LATAM fastest at +17.1 %, streaming {fastest['streaming_share_pct']} % "
          f"(contrast with CISAC LATAM −0.6 % author-royalties)")

    # MENA stream share dominance
    mena = df[df["region"] == "MENA"].iloc[0]
    assert mena["streaming_share_pct"] == 97.5
    print(f"  ✓ MENA streaming share 97.5 % is the highest in the table")


def write_parquet(df: pd.DataFrame) -> Path:
    out_path = OUT / "gmr_2026_global_by_region.parquet"
    con = duckdb.connect()
    con.register("df_data", df)
    con.execute(f"COPY df_data TO '{out_path}' (FORMAT PARQUET, COMPRESSION ZSTD)")
    print(f"  ✓ {out_path.relative_to(REPO_ROOT)} — {len(df)} rows, "
          f"{out_path.stat().st_size/1024:.1f} KB")
    return out_path


def write_meta(out_path: Path, df: pd.DataFrame) -> None:
    meta = {
        "table": out_path.stem, "schema": "ifpi",
        "description": "IFPI GMR 2026 — 2025 recorded-music revenue by region. 7 "
                       "rows. LATAM (+17.1 %) is the fastest-growing region; "
                       "MENA streaming share 97.5 % the highest. Critical "
                       "cross-lens row: LATAM +17.1 % here vs CISAC GCR 2025's "
                       "LATAM −0.6 % author-royalties — same market, opposite "
                       "direction by lens.",
        "source": "IFPI Global Music Report 2026 (press release).",
        "source_pages": [SOURCE_PAGE], "fetch_date": "2026-06-01",
        "etl_script": "etl/ifpi__gmr_2026_global_by_region_to_parquet.py",
        "etl_run_date": str(date.today()),
        "licence": "IFPI published figures — public press release.",
        "grain": "one row per (year, region)", "row_count": int(len(df)),
        "notes": "share_pct, usd_mi, streaming_share_pct NULL where the press "
                 "release does not state them. See methodology §3 on the "
                 "IFPI ↔ CISAC LATAM divergence.",
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
    print("Building atana.ifpi.gmr_2026_global_by_region...")
    df = build(); validate(df)
    out_path = write_parquet(df); write_meta(out_path, df)
    maybe_push(df, "ifpi", "gmr_2026_global_by_region")
    print("Done.")


if __name__ == "__main__":
    main()
