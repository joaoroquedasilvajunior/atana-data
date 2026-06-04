"""Luminate Year-End 2025 — top markets / paid-stream concentration → Parquet.

Phase 5c. Second of four `atana.luminate` tables.

The catalog-saturation finding of the global headline table gets its
distributional companion here: half of the world's *paid* ondemand audio
streams come from just four countries. This is the **Note #08 extension
candidate** the W23 briefing flagged — a concentration cell that pairs
naturally with CISAC's LATAM-contracting evidence and IFPI's LATAM-
leading-region evidence (both at label/CMO side, opposite sides of the
same gap).

For Brazil specifically: large volume, but its premium-stream growth
(+38.6 bn YoY) was *third* among the four, and Brazil simultaneously
shows up as a "most-local market" (separate table).

GRAIN
-----
One row per (year, country). 4 rows × 2025.
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

COLUMNS = ["year", "country", "rank_paid_streams",
           "share_global_paid_streams_pct",
           "paid_streams_volume_growth_yoy_bn",
           "source_url", "notes"]

ROWS = [
    (2025, "United States", 1, 31.0, 65.5, LUMINATE_REPORT,
     "Largest single paid-stream market. ~31 % of global premium "
     "ondemand audio streams. Volume growth +65.5 bn YoY — largest absolute."),
    (2025, "Mexico", 2, None, 50.9, LUMINATE_REPORT,
     "Second-largest absolute volume growth in paid streams (+50.9 bn YoY). "
     "Mexico's #10 IFPI global position (+13.3 % retail) coheres with this. "
     "Triangulates with INEGI CSCM 2024 Música y conciertos +14.9 %."),
    (2025, "Brazil", 3, None, 38.6, LUMINATE_REPORT,
     "Third-largest absolute volume growth in paid streams (+38.6 bn YoY). "
     "Brazil's #8 IFPI rank (+14.1 % retail) coheres with this. "
     "Cross-lens: CISAC LATAM −0.6 %, IFPI LATAM +17.1 %, Luminate volume "
     "third-largest — three different camera angles on the same year."),
    (2025, "Germany", 4, None, None, LUMINATE_REPORT,
     "Completes the 4-country half-of-global-paid-streams concentration. "
     "Volume growth not separately reported by MBW."),
]


def build():
    df = pd.DataFrame([dict(zip(COLUMNS, r)) for r in ROWS], columns=COLUMNS)
    df["year"] = df["year"].astype("int32")
    df["rank_paid_streams"] = df["rank_paid_streams"].astype("int32")
    return df


def validate(df):
    print("Validating...")
    assert len(df) == 4
    countries = set(df["country"])
    assert countries == {"United States", "Mexico", "Brazil", "Germany"}
    print(f"  ✓ 4 countries: {sorted(countries)}")
    us = df[df["country"] == "United States"].iloc[0]
    assert us["rank_paid_streams"] == 1
    assert us["share_global_paid_streams_pct"] == 31.0
    print(f"  ✓ US #1 with 31 % of global paid streams")
    growths = df["paid_streams_volume_growth_yoy_bn"].dropna().sort_values(ascending=False).tolist()
    assert growths == [65.5, 50.9, 38.6], growths
    print(f"  ✓ volume growth ordering: US (65.5) > MX (50.9) > BR (38.6) bn YoY")


def write_parquet(df):
    out_path = OUT / "ye2025_top_markets_paid_share.parquet"
    con = duckdb.connect()
    con.register("df_data", df)
    con.execute(f"COPY df_data TO '{out_path}' (FORMAT PARQUET, COMPRESSION ZSTD)")
    print(f"  ✓ {out_path.relative_to(REPO_ROOT)} — {len(df)} rows, "
          f"{out_path.stat().st_size/1024:.1f} KB")
    return out_path


def write_meta(out_path, df):
    meta = {
        "table": out_path.stem, "schema": "luminate",
        "description": "Luminate Year-End 2025 — the 4 countries that "
                       "account for ~half of global premium ondemand audio "
                       "streams (USA 31 %, Mexico, Brazil, Germany). "
                       "Volume growth of premium streams: USA +65.5 bn, "
                       "Mexico +50.9 bn, Brazil +38.6 bn YoY. The Note #08 "
                       "extension cell — paid-stream concentration as the "
                       "demand-side counterpart to CISAC/IFPI divergence.",
        "source": "Luminate Year-End 2025 Music Industry Report; MBW coverage.",
        "source_pages": [LUMINATE_REPORT, MBW_COVERAGE],
        "fetch_date": "2026-06-04",
        "etl_script": "etl/luminate__ye2025_top_markets_paid_share_to_parquet.py",
        "etl_run_date": str(date.today()),
        "licence": "Luminate published figures; MBW press coverage.",
        "grain": "one row per (year, country)", "row_count": int(len(df)),
        "notes": "Only USA share is independently reported; the 4-country "
                 "concentration is the summary claim. Germany volume growth "
                 "not reported by MBW (NULL preserved, not zero).",
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
    print("Building atana.luminate.ye2025_top_markets_paid_share...")
    df = build(); validate(df)
    out_path = write_parquet(df); write_meta(out_path, df)
    maybe_push(df, "luminate", "ye2025_top_markets_paid_share")
    print("Done.")


if __name__ == "__main__":
    main()
