"""Luminate Year-End 2025 — US genre share → Parquet.

Phase 5c. Third of four `atana.luminate` tables. The US-only genre cut
from Luminate Year-End 2025 — the lens against which LATAM share-gain
narratives (IFPI LATAM +17.1 %, paid-stream concentration in 4 markets
including Mexico and Brazil) are typically benchmarked.

WHY US-ONLY
-----------
Luminate publishes genre breakdowns by market. The US table is the
publicly cited one and is the comparison the trade press uses (e.g.,
Latin music in the US grew faster than overall in 2025). For non-US
genre detail, see future Tier 2 ingests.

GRAIN
-----
One row per (year, country, genre). 5 rows × USA × 2025.
"""
import hashlib, json, os
from datetime import date
from pathlib import Path
import duckdb, pandas as pd

REPO_ROOT = Path(__file__).resolve().parent.parent
OUT = REPO_ROOT / "raw" / "luminate"
OUT.mkdir(parents=True, exist_ok=True)
LUMINATE_REPORT = "https://luminatedata.com/reports/yearend-music-industry-report-2025"
MBW_COVERAGE = ("https://www.musicbusinessworldwide.com/"
                "half-of-all-paid-music-streams-globally-derive-from-just-4-countries-and-other-highlights-from-luminates-latest-report")

COLUMNS = ["year", "country", "genre", "rank",
           "ondemand_audio_streams_bn",
           "share_us_streams_pct",
           "share_change_yoy_pp",
           "source_url", "notes"]

ROWS = [
    (2025, "United States", "R&B/Hip-Hop", 1, 351.1, 25.5, -0.8, LUMINATE_REPORT,
     "Still #1 by share, but lost ground YoY (−0.8 pp). The format the "
     "Authenticity Paradox originated from — global majors capture, "
     "creators rarely. US genre share down despite global volume up."),
    (2025, "United States", "Rock", 2, 211.4, 15.3, 0.0, LUMINATE_REPORT,
     "Flat share."),
    (2025, "United States", "Pop", 3, 174.0, 12.6, 0.3, LUMINATE_REPORT,
     "Slight gain."),
    (2025, "United States", "Latin", 4, 110.5, 8.0, 0.6, LUMINATE_REPORT,
     "Largest gainer among top US genres. Coheres with IFPI LATAM "
     "+17.1 % and Mexico/Brazil paid-stream growth — Latin music's "
     "global salience showing up inside the US market too. Note: the "
     "US Latin market is itself a label-side phenomenon (mostly "
     "Universal/Sony/Warner Latin) — captures the same Authenticity "
     "Paradox dynamic Note #06 describes."),
    (2025, "United States", "Christian/Gospel", 5, 47.7, 3.5, 0.4, LUMINATE_REPORT,
     "Gainer — coheres with reports of religious-music streaming growth."),
]


def build():
    df = pd.DataFrame([dict(zip(COLUMNS, r)) for r in ROWS], columns=COLUMNS)
    df["year"] = df["year"].astype("int32")
    df["rank"] = df["rank"].astype("int32")
    return df


def validate(df):
    print("Validating...")
    assert len(df) == 5
    assert all(df["country"] == "United States")
    print(f"  ✓ 5 US genre rows for 2025")
    # Streams sum-check (top 5 = ~65 % of US streams; ≤ US total)
    top5_streams = df["ondemand_audio_streams_bn"].sum()
    assert 800 <= top5_streams <= 950, top5_streams
    print(f"  ✓ top-5 US streams = {top5_streams:.1f} bn (within US 1.4 tn total)")
    # Hip-Hop #1
    top = df.sort_values("rank").iloc[0]
    assert top["genre"] == "R&B/Hip-Hop" and top["share_us_streams_pct"] == 25.5
    print(f"  ✓ R&B/Hip-Hop #1 at 25.5 % US share")
    # Latin is the largest gainer among ranked top
    gainers = df[df["share_change_yoy_pp"] > 0].sort_values("share_change_yoy_pp", ascending=False)
    assert gainers["genre"].iloc[0] == "Latin"
    print(f"  ✓ Latin is the largest share gainer (+0.6 pp)")


def write_parquet(df):
    out_path = OUT / "ye2025_us_genre_share.parquet"
    con = duckdb.connect()
    con.register("df_data", df)
    con.execute(f"COPY df_data TO '{out_path}' (FORMAT PARQUET, COMPRESSION ZSTD)")
    print(f"  ✓ {out_path.relative_to(REPO_ROOT)} — {len(df)} rows, "
          f"{out_path.stat().st_size/1024:.1f} KB")
    return out_path


def write_meta(out_path, df):
    meta = {
        "table": out_path.stem, "schema": "luminate",
        "description": "Luminate Year-End 2025 — US genre breakdown of "
                       "ondemand audio streams. Top 5: R&B/Hip-Hop 25.5 % "
                       "(−0.8 pp), Rock 15.3 % (flat), Pop 12.6 % (+0.3), "
                       "Latin 8.0 % (+0.6 pp = largest gainer), Christian/"
                       "Gospel 3.5 % (+0.4). Latin's US-share gain coheres "
                       "with the IFPI LATAM +17.1 % regional narrative.",
        "source": "Luminate Year-End 2025 Music Industry Report; MBW coverage.",
        "source_pages": [LUMINATE_REPORT, MBW_COVERAGE],
        "fetch_date": "2026-06-04",
        "etl_script": "etl/luminate__ye2025_us_genre_share_to_parquet.py",
        "etl_run_date": str(date.today()),
        "licence": "Luminate published figures; MBW press coverage.",
        "grain": "one row per (year, country, genre)",
        "row_count": int(len(df)),
        "notes": "US-only. Non-US genre breakdowns are publicly cited only "
                 "for headline 'most-local' shares (separate table).",
    }
    out_path.with_suffix(".meta.json").write_text(
        json.dumps(meta, indent=2, ensure_ascii=False))
    print(f"  ✓ {out_path.with_suffix('.meta.json').relative_to(REPO_ROOT)}")


def maybe_push(df, schema, table):
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
    print("Building atana.luminate.ye2025_us_genre_share...")
    df = build(); validate(df)
    out_path = write_parquet(df); write_meta(out_path, df)
    maybe_push(df, "luminate", "ye2025_us_genre_share")
    print("Done.")


if __name__ == "__main__":
    main()
