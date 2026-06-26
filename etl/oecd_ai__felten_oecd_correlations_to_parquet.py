"""OECD No. 59 Table 6.6 — Felten × OECD correlations per domain → Parquet.

Phase 5d (Tier 2, Table 6.6). The methodological diagnostic that proves
Felten et al.'s widely-cited "AI Occupational Exposure" measure is
structurally blind to creativity-specific gap.

KEY FINDING THIS TABLE HOLDS
----------------------------
**Felten × OECD overall index correlation is only 0.34.** They are formally
different measures, not interchangeable. The per-domain breakdown is sharper:

- Language / Social interaction / Problem solving / Metacognition / Knowledge:
  correlations 0.59-0.69 with OECD's gap — both track similar cognitive content.
- **Creativity is the diagnostic outlier — correlation with OECD GAP is only
  0.25, but with OECD capability DEMANDS is 0.61.** Felten recognises WHEN an
  occupation is creative but cannot tell WHETHER AI can do it. This is the
  empirical proof Felten is creativity-blind, which sits at the centre of the
  Atana Note #18 argument.
- Vision / Manipulation / Robotic intelligence: NEGATIVE correlations (−0.58 to
  −0.77) — Felten and OECD disagree on physical-domain exposure (Felten was
  language- and info-processing centred).

SOURCE
------
    OECD AI Papers No. 59, May 2026, Table 6.6, page 36. CC BY 4.0.

PROVENANCE
----------
Verbatim from `_atana_intel/oecd_no59_tables_6_5_6_6_6_7_index_construction.md`
§"Table 6.6 — Correlations with Felten et al." (recorded 2026-06-05).
"""
import hashlib, json, os
from datetime import date
from pathlib import Path
import duckdb, pandas as pd

REPO_ROOT = Path(__file__).resolve().parent.parent
OUT = REPO_ROOT / "raw" / "oecd_ai"
OUT.mkdir(parents=True, exist_ok=True)
SOURCE_URL = "https://www.oecd.org/en/publications/the-oecd-ai-exposure-measure_no59.html"

COLUMNS = ["paper_no", "table_id", "domain_key", "domain_label",
           "is_composite", "corr_felten_oecd_gap", "corr_felten_oecd_demand",
           "atana_relevance_note", "source_url"]

ROWS = [
    (59, "table_6_6", "language",             "Language",                            False, 0.69, 0.82,
     "Both measures agree on language exposure; Felten was designed around this domain.", SOURCE_URL),
    (59, "table_6_6", "social_interaction",   "Social interaction",                  False, 0.61, 0.63,
     "Moderate agreement.", SOURCE_URL),
    (59, "table_6_6", "problem_solving",      "Problem solving",                     False, 0.69, 0.66,
     "High agreement on cognitive-analytical work.", SOURCE_URL),
    (59, "table_6_6", "creativity",           "Creativity",                          False, 0.25, 0.61,
     "★ The diagnostic outlier. Felten recognises WHEN creative but cannot tell WHETHER AI can do it. Empirical proof Felten is creativity-blind — the centrepiece of the Atana Note #18 argument.", SOURCE_URL),
    (59, "table_6_6", "metacognition",        "Metacognition and critical thinking", False, 0.68, 0.71,
     "Both measures agree.", SOURCE_URL),
    (59, "table_6_6", "knowledge_lrn_mem",    "Knowledge, learning and memory",      False, 0.59, 0.56,
     "Moderate agreement.", SOURCE_URL),
    (59, "table_6_6", "vision",               "Vision",                              False, -0.58, -0.72,
     "Strong NEGATIVE correlation. Felten's language-centred measure under-counts visual work; OECD captures it via the dedicated Vision domain.", SOURCE_URL),
    (59, "table_6_6", "manipulation",         "Manipulation",                        False, -0.77, -0.84,
     "Strongest negative correlation. Felten effectively ignores physical manipulation; OECD captures it as a first-class domain.", SOURCE_URL),
    (59, "table_6_6", "robotic_intelligence", "Robotic intelligence",                False, -0.69, -0.81,
     "Negative correlation; Felten was not designed for the embodied/robotic-judgement axis.", SOURCE_URL),
    (59, "table_6_6", "overall_index",        "Overall AI Capability Gap Index",     True,  0.34, None,
     "★ The headline correlation. Felten and OECD agree about one third of the way. Composite-only readings hide the per-domain disagreement, especially on creativity and embodied work.", SOURCE_URL),
]


def build():
    df = pd.DataFrame([dict(zip(COLUMNS, r)) for r in ROWS], columns=COLUMNS)
    df["paper_no"] = df["paper_no"].astype("int32")
    df["is_composite"] = df["is_composite"].astype("boolean")
    df["corr_felten_oecd_gap"] = df["corr_felten_oecd_gap"].astype("float64")
    df["corr_felten_oecd_demand"] = df["corr_felten_oecd_demand"].astype("Float64")
    return df


def validate(df):
    print("Validating...")
    assert len(df) == 10, f"expected 10 rows, got {len(df)}"
    print(f"  ✓ 10 rows — 9 domains + 1 overall composite")
    n_composite = int(df["is_composite"].sum())
    assert n_composite == 1
    print(f"  ✓ exactly 1 composite row (Overall AI Capability Gap Index)")
    # Headline correlations
    creat = df[df["domain_key"] == "creativity"]
    assert len(creat) == 1 and creat["corr_felten_oecd_gap"].iloc[0] == 0.25
    print(f"  ✓ Creativity row: corr_felten_oecd_gap = 0.25 (the diagnostic outlier)")
    overall = df[df["domain_key"] == "overall_index"]
    assert len(overall) == 1 and overall["corr_felten_oecd_gap"].iloc[0] == 0.34
    print(f"  ✓ Overall row: corr_felten_oecd_gap = 0.34 (the headline correlation)")
    # Physical-domain negatives
    phys = df[df["domain_key"].isin(["vision", "manipulation", "robotic_intelligence"])]
    assert (phys["corr_felten_oecd_gap"] < 0).all()
    print(f"  ✓ Vision/Manipulation/Robotic intelligence all carry negative correlation with Felten (3 rows)")
    # demand column NULL on composite row, non-null elsewhere
    null_demand = df["corr_felten_oecd_demand"].isna()
    assert null_demand.sum() == 1
    print(f"  ✓ corr_felten_oecd_demand NULL only on the composite row (Table 6.6 reports demand correlations per-domain only)")


def write_parquet(df):
    out_path = OUT / "felten_oecd_correlations.parquet"
    con = duckdb.connect()
    con.register("df_data", df)
    con.execute(f"COPY df_data TO '{out_path}' (FORMAT PARQUET, COMPRESSION ZSTD)")
    print(f"  ✓ {out_path.relative_to(REPO_ROOT)} — {len(df)} rows, {out_path.stat().st_size/1024:.1f} KB")
    return out_path


def write_meta(out_path, df):
    meta = {
        "table": out_path.stem, "schema": "oecd_ai",
        "description": (
            "OECD No. 59 Table 6.6 — per-domain correlations between Felten et "
            "al.'s widely-cited 'AI Occupational Exposure' measure and OECD's "
            "Capability Gap Index. The overall correlation is 0.34. Creativity "
            "is the diagnostic outlier (0.25 vs OECD GAP, 0.61 vs OECD DEMANDS — "
            "Felten recognises WHEN creative but not WHETHER AI can do it). "
            "Vision / Manipulation / Robotic intelligence carry NEGATIVE "
            "correlations. The empirical proof that Felten is creativity-blind "
            "and physical-domain-blind, at the centre of the Atana Note #18 "
            "methodological argument."
        ),
        "source": "OECD AI Papers No. 59, May 2026, Table 6.6 (page 36).",
        "source_pages": [SOURCE_URL],
        "fetch_date": "2026-06-05",
        "etl_script": "etl/oecd_ai__felten_oecd_correlations_to_parquet.py",
        "etl_run_date": str(date.today()),
        "licence": "OECD AI Papers — CC BY 4.0.",
        "grain": "one row per (paper_no, table_id, domain_key)",
        "row_count": int(len(df)),
        "notes": (
            "Table 6.6's correlations are at the rank level across the 610-"
            "occupation matched universe. The demand column (vs OECD capability "
            "demands) is NULL on the composite row because the OECD table "
            "reports it per-domain only."
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
    print("Building atana.oecd_ai.felten_oecd_correlations...")
    df = build(); validate(df)
    out_path = write_parquet(df); write_meta(out_path, df)
    maybe_push(df, "oecd_ai", "felten_oecd_correlations")
    print("Done.")


if __name__ == "__main__":
    main()
