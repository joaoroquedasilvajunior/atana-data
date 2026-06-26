"""OECD No. 59 Table 6.5 — overall exposure ranking (top/bottom 10) → Parquet.

Phase 5d (Tier 2, Table 6.5). The headline OECD ranking of the 610 occupations
in the No. 59 universe by composite AI Capability Gap: smaller = more exposed.

KEY FINDING THIS TABLE HOLDS
----------------------------
**Zero SOC group 27 cultural occupations in either tail.** The cultural cluster
(SOC group 27, total gap 4.2 per Table 6.3) sits in the middle of the
distribution, despite dominating the Creativity column of Table 6.4a (see
`occupations_creativity_distance`).

This is the structural argument the Atana Index Vol 2 makes against composite-
only readings: the cultural cluster has one extreme score (creativity gap) but
composite indexes dilute that single domain across the other 8 domains. The
per-domain decomposition matters; the composite number alone hides the
finding.

SOURCE
------
    OECD AI Papers No. 59, May 2026, Table 6.5, page 34. CC BY 4.0.

PROVENANCE
----------
Verbatim from `_atana_intel/oecd_no59_tables_6_5_6_6_6_7_index_construction.md`
§"Table 6.5 — Overall AI exposure ranking" (recorded 2026-06-05).
"""
import hashlib, json, os
from datetime import date
from pathlib import Path
import duckdb, pandas as pd

REPO_ROOT = Path(__file__).resolve().parent.parent
OUT = REPO_ROOT / "raw" / "oecd_ai"
OUT.mkdir(parents=True, exist_ok=True)
SOURCE_URL = "https://www.oecd.org/en/publications/the-oecd-ai-exposure-measure_no59.html"

COLUMNS = ["paper_no", "table_id", "tail", "rank", "soc_major_group_code",
           "occupation_title", "total_capability_gap", "is_soc27_cultural",
           "notes", "source_url"]

# tail ∈ {"most_exposed", "least_exposed"}
ROWS = [
    # Top 10 HIGHEST AI exposure (smallest gap) — most automatable
    (59, "table_6_5", "most_exposed", 1, "43", "Billing and Posting Clerks", 0.00, False, "Tied at 0.00 with 4 other clerical occupations.", SOURCE_URL),
    (59, "table_6_5", "most_exposed", 2, "43", "Word Processors and Typists", 0.00, False, "Tied at 0.00.", SOURCE_URL),
    (59, "table_6_5", "most_exposed", 3, "43", "File Clerks", 0.00, False, "Tied at 0.00.", SOURCE_URL),
    (59, "table_6_5", "most_exposed", 4, "43", "Bookkeeping, Accounting, and Auditing Clerks", 0.00, False, "Tied at 0.00.", SOURCE_URL),
    (59, "table_6_5", "most_exposed", 5, "43", "Data Entry Keyers", 0.00, False, "Tied at 0.00.", SOURCE_URL),
    (59, "table_6_5", "most_exposed", 6, "43", "Weighers, Measurers, Checkers, and Samplers, Recordkeeping", 0.02, False, "", SOURCE_URL),
    (59, "table_6_5", "most_exposed", 7, "43", "Payroll and Timekeeping Clerks", 0.03, False, "", SOURCE_URL),
    (59, "table_6_5", "most_exposed", 8, "43", "Shipping, Receiving, and Inventory Clerks", 0.08, False, "", SOURCE_URL),
    (59, "table_6_5", "most_exposed", 9, "43", "Statistical Assistants", 0.08, False, "", SOURCE_URL),
    (59, "table_6_5", "most_exposed", 10, "31", "Medical Transcriptionists", 0.09, False, "Only non-43 occupation in the top 10.", SOURCE_URL),
    # Top 10 LOWEST AI exposure (largest gap) — least automatable
    (59, "table_6_5", "least_exposed", 1, "11", "Chief Executives", 11.71, False, "Top of the gap distribution. Composite of strategic judgement, social interaction, knowledge.", SOURCE_URL),
    (59, "table_6_5", "least_exposed", 2, "29", "Ophthalmologists, Except Pediatric", 10.94, False, "Healthcare professional with embodied + diagnostic + relational dimensions.", SOURCE_URL),
    (59, "table_6_5", "least_exposed", 3, "33", "Firefighters", 10.65, False, "Embodied + emergency-judgement; OECD's manipulation/robotic-intelligence domains hit hard.", SOURCE_URL),
    (59, "table_6_5", "least_exposed", 4, "29", "Obstetricians and Gynecologists", 10.48, False, "", SOURCE_URL),
    (59, "table_6_5", "least_exposed", 5, "33", "Police and Sheriff's Patrol Officers", 10.14, False, "", SOURCE_URL),
    (59, "table_6_5", "least_exposed", 6, "29", "Urologists", 10.06, False, "", SOURCE_URL),
    (59, "table_6_5", "least_exposed", 7, "29", "Psychiatrists", 9.76, False, "", SOURCE_URL),
    (59, "table_6_5", "least_exposed", 8, "23", "Lawyers", 9.53, False, "Contradicts Felten ranking (Felten #67 most-exposed). The Lawyer cell is one of the strongest OECD × Felten disagreements (Table 6.7 Panel D).", SOURCE_URL),
    (59, "table_6_5", "least_exposed", 9, "23", "Judges, Magistrate Judges, and Magistrates", 9.53, False, "Contradicts Felten ranking (Felten #6 most-exposed) — the most dramatic single-occupation disagreement between the two measures.", SOURCE_URL),
    (59, "table_6_5", "least_exposed", 10, "29", "Anesthesiologists", 9.48, False, "", SOURCE_URL),
]


def build():
    df = pd.DataFrame([dict(zip(COLUMNS, r)) for r in ROWS], columns=COLUMNS)
    df["paper_no"] = df["paper_no"].astype("int32")
    df["rank"] = df["rank"].astype("int32")
    df["total_capability_gap"] = df["total_capability_gap"].astype("float64")
    df["is_soc27_cultural"] = df["is_soc27_cultural"].astype("boolean")
    return df


def validate(df):
    print("Validating...")
    assert len(df) == 20, f"expected 20 rows, got {len(df)}"
    print(f"  ✓ 20 rows — top-10 most exposed + top-10 least exposed")
    most = df[df["tail"] == "most_exposed"]; least = df[df["tail"] == "least_exposed"]
    assert len(most) == 10 and len(least) == 10
    print(f"  ✓ 10 + 10 split between most/least exposed")
    n_cult = int(df["is_soc27_cultural"].sum())
    assert n_cult == 0
    print(f"  ✓ 0 SOC group 27 cultural occupations in EITHER tail — the structural finding")
    max_most = float(most["total_capability_gap"].max())
    min_least = float(least["total_capability_gap"].min())
    assert max_most < min_least, f"tails overlap: most max={max_most} ≥ least min={min_least}"
    print(f"  ✓ tail-separation invariant: most-exposed max {max_most:.2f} < least-exposed min {min_least:.2f}")


def write_parquet(df):
    out_path = OUT / "exposure_extremes_ranking.parquet"
    con = duckdb.connect()
    con.register("df_data", df)
    con.execute(f"COPY df_data TO '{out_path}' (FORMAT PARQUET, COMPRESSION ZSTD)")
    print(f"  ✓ {out_path.relative_to(REPO_ROOT)} — {len(df)} rows, {out_path.stat().st_size/1024:.1f} KB")
    return out_path


def write_meta(out_path, df):
    meta = {
        "table": out_path.stem, "schema": "oecd_ai",
        "description": (
            "OECD No. 59 Table 6.5 — overall AI exposure ranking, top-10 most "
            "exposed (smallest gap, mostly clerical) + top-10 least exposed "
            "(largest gap, executives/medical/protective/legal). Zero SOC group "
            "27 cultural occupations in either tail — the cultural cluster sits "
            "at the middle of the distribution despite dominating the Creativity "
            "column (occupations_creativity_distance), the structural argument "
            "for per-domain decomposition over composite-only reading."
        ),
        "source": "OECD AI Papers No. 59, May 2026, Table 6.5 (page 34).",
        "source_pages": [SOURCE_URL],
        "fetch_date": "2026-06-05",
        "etl_script": "etl/oecd_ai__exposure_extremes_ranking_to_parquet.py",
        "etl_run_date": str(date.today()),
        "licence": "OECD AI Papers — CC BY 4.0.",
        "grain": "one row per (paper_no, table_id, tail, rank)",
        "row_count": int(len(df)),
        "notes": (
            "Total universe is 610 occupations; this table is only the extremes. "
            "Full per-occupation dataset awaits Path A (manual download from "
            "oecd.ai; scoping memo `_atana_intel/scoping_oecd_no59_occupations_2026-06-26.md`)."
        ),
    }
    out_path.with_suffix(".meta.json").write_text(
        json.dumps(meta, indent=2, ensure_ascii=False, default=str))
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
    print("Building atana.oecd_ai.exposure_extremes_ranking...")
    df = build(); validate(df)
    out_path = write_parquet(df); write_meta(out_path, df)
    maybe_push(df, "oecd_ai", "exposure_extremes_ranking")
    print("Done.")


if __name__ == "__main__":
    main()
