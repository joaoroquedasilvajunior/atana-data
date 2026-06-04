"""Luminate Year-End 2025 — most-local markets → Parquet.

Phase 5c. Fourth and last of `atana.luminate` Tier-1 tables.

THE CELL THAT MATTERS FOR ATANA
-------------------------------
The countries where domestic-language repertoire dominates streaming.
Brazil at 75.2 % means three of every four streams in Brazil come from
artists in Portuguese (mostly sertanejo, funk, MPB, gospel, pagode) —
yet the *paid-stream growth* (+38.6 bn YoY, third in the world) still
lands in the four-country concentration cell.

THE STRUCTURAL READING
----------------------
- IFPI LATAM +17.1 % (recorded music label receipt)
- CISAC LATAM −0.6 % (author royalty collection)
- Luminate Brazil paid-stream growth #3 absolute (+38.6 bn)
- Luminate Brazil = 75.2 % local repertoire

Putting the four together: Brazil consumes massively local repertoire
on streaming; the platform side captures a large premium-stream volume
growth; the recorded-music side (IFPI) captures regional growth; but
the *authors* (CISAC LATAM) collected less in 2024. That is the
**Authenticity Paradox in stereo** — a quantified instance of the gap
where the value flows to platform + label, not to creator + CMO, even
in markets where local repertoire dominates.

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

COLUMNS = ["year", "country",
           "local_repertoire_share_pct",
           "rank_among_most_local",
           "source_url", "notes"]

ROWS = [
    (2025, "India", 79.2, 1, LUMINATE_REPORT,
     "Highest local-repertoire share globally. Hindi/Tamil/Telugu "
     "domestic music continues to dominate Indian streaming."),
    (2025, "Brazil", 75.2, 2, LUMINATE_REPORT,
     "Three of four streams in Brazil are Portuguese-language domestic "
     "repertoire (sertanejo, funk, MPB, pagode, gospel). Brazil is "
     "simultaneously #3 in absolute paid-stream growth (+38.6 bn YoY) — "
     "the joint condition that grounds the Authenticity Paradox: "
     "massive local consumption × massive volume growth × CISAC LATAM "
     "contracting authors. Pairs directly with Análise 19 (funk/sertanejo "
     "geographic capture) and Note #06."),
    (2025, "Turkey", 69.9, 3, LUMINATE_REPORT,
     "Turkish-language domestic repertoire dominates streaming."),
    (2025, "Nigeria", 62.2, 4, LUMINATE_REPORT,
     "Nigerian afrobeats / domestic genres lead local streaming. "
     "Notable: afrobeats has become globally exported — the Nigerian "
     "case is local dominance + outbound flow, distinct from Brazil's "
     "local dominance + author-collection deficit."),
]


def build():
    df = pd.DataFrame([dict(zip(COLUMNS, r)) for r in ROWS], columns=COLUMNS)
    df["year"] = df["year"].astype("int32")
    df["rank_among_most_local"] = df["rank_among_most_local"].astype("int32")
    return df


def validate(df):
    print("Validating...")
    assert len(df) == 4
    assert all(df["local_repertoire_share_pct"] > 50)
    print(f"  ✓ 4 most-local markets; all > 50 % local repertoire share")
    # Brazil specifically
    br = df[df["country"] == "Brazil"].iloc[0]
    assert br["local_repertoire_share_pct"] == 75.2
    assert br["rank_among_most_local"] == 2
    print(f"  ✓ Brazil = 75.2 % local repertoire share, rank #2 among most-local markets")
    # India at the top
    top = df.sort_values("rank_among_most_local").iloc[0]
    assert top["country"] == "India" and top["local_repertoire_share_pct"] == 79.2
    print(f"  ✓ India #1 most-local market at 79.2 %")


def write_parquet(df):
    out_path = OUT / "ye2025_most_local_markets.parquet"
    con = duckdb.connect()
    con.register("df_data", df)
    con.execute(f"COPY df_data TO '{out_path}' (FORMAT PARQUET, COMPRESSION ZSTD)")
    print(f"  ✓ {out_path.relative_to(REPO_ROOT)} — {len(df)} rows, "
          f"{out_path.stat().st_size/1024:.1f} KB")
    return out_path


def write_meta(out_path, df):
    meta = {
        "table": out_path.stem, "schema": "luminate",
        "description": "Luminate Year-End 2025 — countries where domestic-"
                       "language repertoire dominates streaming most: India "
                       "79.2 %, Brazil 75.2 %, Turkey 69.9 %, Nigeria 62.2 %. "
                       "Brazil 75.2 % paired with Brazil #3 in absolute "
                       "paid-stream growth (+38.6 bn YoY) grounds the "
                       "Authenticity Paradox in a single year of evidence: "
                       "local consumption massive, volume growth massive, "
                       "CISAC LATAM author collection contracting.",
        "source": "Luminate Year-End 2025 Music Industry Report; MBW coverage.",
        "source_pages": [LUMINATE_REPORT, MBW_COVERAGE],
        "fetch_date": "2026-06-04",
        "etl_script": "etl/luminate__ye2025_most_local_markets_to_parquet.py",
        "etl_run_date": str(date.today()),
        "licence": "Luminate published figures; MBW press coverage.",
        "grain": "one row per (year, country)", "row_count": int(len(df)),
        "notes": "Luminate measures 'local' as repertoire whose primary "
                 "language matches the country's primary language. Not the "
                 "same as country-of-rights-ownership (which often sits with "
                 "global majors). The label/CMO gap maps to that distinction.",
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
    print("Building atana.luminate.ye2025_most_local_markets...")
    df = build(); validate(df)
    out_path = write_parquet(df); write_meta(out_path, df)
    maybe_push(df, "luminate", "ye2025_most_local_markets")
    print("Done.")


if __name__ == "__main__":
    main()
