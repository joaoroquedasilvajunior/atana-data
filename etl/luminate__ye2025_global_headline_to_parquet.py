"""Luminate Year-End 2025 — global headline → Parquet.

Phase 5c. First of four `atana.luminate` tables. Adds the **fourth music-
money lens** to the corpus: catalog-supply / consumer-platform side.

The Atana music-money frame now reads:
  - `atana.ecad`   (BR author distribution — collected royalties paid out)
  - `atana.cisac`  (global author collection — CMO side)
  - `atana.ifpi`   (global recorded music — label side)
  - `atana.luminate` (consumer / catalog supply — streaming surface)

Each lens at a different point in the value chain.

WHAT THIS TABLE COVERS
----------------------
2025 global headline from Luminate's Year-End 2025 Music Report (Connect
data platform). Single row carrying the catalog-saturation and
consumption-volume aggregates that frame the briefing's Note #08
extension candidate.

SOURCE
------
    https://luminatedata.com/reports/yearend-music-industry-report-2025
    Numbers verified against Music Business Worldwide coverage
    (Jan 22, 2026), which reports figures from the Luminate report.
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

COLUMNS = ["year",
           "ondemand_audio_streams_global_tri",
           "ondemand_audio_streams_global_yoy_pct",
           "ondemand_audio_streams_ex_us_tri",
           "ondemand_audio_streams_ex_us_yoy_pct",
           "ondemand_audio_streams_us_tri",
           "ondemand_audio_streams_us_yoy_pct",
           "total_tracks_on_streaming_mi",
           "tracks_added_yoy_mi",
           "tracks_added_per_day_k",
           "tracks_under_10_streams_mi",
           "source_url", "notes"]

ROWS = [
    (2025, 5.1, 9.6, 3.7, 11.6, 1.4, 4.6,
     253.0, 37.9, 106, 120.5,
     LUMINATE_REPORT,
     "Luminate Year-End 2025 Report. 5.1 tn global ondemand audio streams "
     "(+9.6 % YoY); ex-US 3.7 tn (+11.6 %). 253 mi tracks on streaming at "
     "year-end (+37.9 mi YoY = ~106 k uploaded per day). 120.5 mi tracks "
     "(47.6 %) received fewer than 10 streams in 2025 — the 'long tail of "
     "almost-zero' that supports the Atana Note #08 extension on catalog "
     "saturation. Figures verified against MBW coverage 22 Jan 2026."),
]


def build():
    df = pd.DataFrame([dict(zip(COLUMNS, r)) for r in ROWS], columns=COLUMNS)
    df["year"] = df["year"].astype("int32")
    df["tracks_added_per_day_k"] = df["tracks_added_per_day_k"].astype("Int32")
    return df


def validate(df):
    print("Validating...")
    assert len(df) == 1
    r = df.iloc[0]
    # Internal consistency: ex-US + US ≈ global (3.7 + 1.4 = 5.1)
    implied = r["ondemand_audio_streams_ex_us_tri"] + r["ondemand_audio_streams_us_tri"]
    assert abs(implied - r["ondemand_audio_streams_global_tri"]) <= 0.05
    print(f"  ✓ ex-US ({r['ondemand_audio_streams_ex_us_tri']} tn) + US "
          f"({r['ondemand_audio_streams_us_tri']} tn) ≈ global "
          f"({r['ondemand_audio_streams_global_tri']} tn)")
    # "Long tail" share
    long_tail_share = r["tracks_under_10_streams_mi"] / r["total_tracks_on_streaming_mi"] * 100
    assert 40 <= long_tail_share <= 55
    print(f"  ✓ long-tail share = {long_tail_share:.1f} % "
          f"({r['tracks_under_10_streams_mi']:.1f} / {r['total_tracks_on_streaming_mi']:.0f} mi tracks under 10 streams)")
    # Daily upload rate
    implied_daily = r["tracks_added_yoy_mi"] * 1000 / 365.0  # mi → k, /365
    assert abs(implied_daily - r["tracks_added_per_day_k"]) <= 6
    print(f"  ✓ daily upload rate ~ {r['tracks_added_per_day_k']} k "
          f"(implied {implied_daily:.0f} k from YoY tracks added)")


def write_parquet(df):
    out_path = OUT / "ye2025_global_headline.parquet"
    con = duckdb.connect()
    con.register("df_data", df)
    con.execute(f"COPY df_data TO '{out_path}' (FORMAT PARQUET, COMPRESSION ZSTD)")
    print(f"  ✓ {out_path.relative_to(REPO_ROOT)} — {len(df)} rows, "
          f"{out_path.stat().st_size/1024:.1f} KB")
    return out_path


def write_meta(out_path, df):
    meta = {
        "table": out_path.stem, "schema": "luminate",
        "description": "Luminate Year-End 2025 — global headline: 5.1 tn "
                       "ondemand audio streams (+9.6 %), ex-US 3.7 tn "
                       "(+11.6 %), US 1.4 tn (+4.6 %), 253 mi tracks on "
                       "streaming, 120.5 mi (~47 %) under 10 streams. The "
                       "catalog-supply/consumer-platform lens — fourth in "
                       "the corpus's music-money frame.",
        "source": "Luminate Year-End 2025 Music Industry Report. Figures "
                  "verified via MBW (22 Jan 2026).",
        "source_pages": [LUMINATE_REPORT, MBW_COVERAGE],
        "fetch_date": "2026-06-04",
        "etl_script": "etl/luminate__ye2025_global_headline_to_parquet.py",
        "etl_run_date": str(date.today()),
        "licence": "Luminate published figures; MBW press coverage.",
        "grain": "one row per reference year", "row_count": int(len(df)),
        "notes": "The Luminate Year-End PDF is downloadable from "
                 "luminatedata.com/reports/yearend-music-industry-report-2025; "
                 "headline figures are publicly cited. May 2026 'State of the "
                 "Industry' conference deck is a SEPARATE Luminate release, "
                 "PDF-gated behind a lead form — not in this ingest.",
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
    print("Building atana.luminate.ye2025_global_headline...")
    df = build(); validate(df)
    out_path = write_parquet(df); write_meta(out_path, df)
    maybe_push(df, "luminate", "ye2025_global_headline")
    print("Done.")


if __name__ == "__main__":
    main()
