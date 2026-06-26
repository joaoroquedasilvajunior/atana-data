"""OECD No. 59 Table 6.4a — Creativity column transcription → Parquet.

Phase 5d (Tier 2, Table 6.4a). Per-occupation surface from OECD No. 59
chapter 6: the top-10 occupations with the LARGEST Creativity gap (= AI
furthest from being able to perform creativity required at that level).

THE FINDING THIS TABLE HOLDS
----------------------------
**7 of 10 occupations in the OECD's "AI most distant from creativity" column
are SOC group 27 cultural occupations** — Music Directors and Composers,
Choreographers, Special Effects Artists, Producers and Directors, Art
Directors, Multimedia Artists, Set and Exhibit Designers, Fashion / Interior
Designers. This is the strongest occupation-weighted empirical backing for
the Atana Authenticity Paradox (Note #18 §2; Análise 6 v2.0 §4; Note #06/#08
distributional argument).

The trade-weighted Atana measure and the occupation-weighted OECD measure
CONVERGE on the substantive finding: the value-creating end of cultural work
is precisely where current AI capability is structurally most distant.

The OECD paper's narrative (page 31) names the Language column verbatim but
DOES NOT name the cultural occupations in the Creativity column. Manual
visual transcription from the page-32 PNG rendering was required (PDF text
extractors all failed because the table is image-embedded).

SOURCE
------
    Elliott, S. et al. (2026). *The OECD AI exposure measure: Mapping the
    OECD AI Capability Indicators to occupations.* OECD AI Papers No. 59,
    May 2026, Table 6.4a, page 32. CC BY 4.0.

PROVENANCE
----------
Verbatim from `_atana_intel/oecd_no59_table_6_4a_creativity_column.md` §"The
Atana-relevant finding: Creativity column" (recorded 2026-06-05).
"""
import hashlib, json, os
from datetime import date
from pathlib import Path
import duckdb, pandas as pd

REPO_ROOT = Path(__file__).resolve().parent.parent
OUT = REPO_ROOT / "raw" / "oecd_ai"
OUT.mkdir(parents=True, exist_ok=True)
SOURCE_URL = "https://www.oecd.org/en/publications/the-oecd-ai-exposure-measure_no59.html"

COLUMNS = ["paper_no", "table_id", "domain", "rank",
           "soc_major_group_code", "soc_major_group_label",
           "occupation_title", "is_soc27_cultural", "atana_relevance_flag",
           "notes", "source_url"]

SOC_LABELS = {
    "17": "Architecture and Engineering",
    "25": "Educational Instruction and Library",
    "27": "Arts, Design, Entertainment, Sports and Media",
}

ROWS = [
    (59, "table_6_4a", "Creativity", 1, "25",
     SOC_LABELS["25"], "Architecture and Engineering Teachers, Postsecondary",
     False, "☆ cultural-adjacent",
     "Teaches creative-technical practice; not group 27 but in the cultural-adjacent set used in the SOC group 27 Table 6.3 cluster discussion.",
     SOURCE_URL),
    (59, "table_6_4a", "Creativity", 2, "17",
     SOC_LABELS["17"], "Architects, Except Landscape",
     False, "☆ cultural-adjacent",
     "Architecture sits partly under FCS 'Design' but the SOC group is engineering. Adjacent, not core cultural.",
     SOURCE_URL),
    (59, "table_6_4a", "Creativity", 3, "27",
     SOC_LABELS["27"], "Music Directors and Composers",
     True, "★ cultural",
     "Core FCS 'Music' domain. The headline cell of the table for the Atana argument.",
     SOURCE_URL),
    (59, "table_6_4a", "Creativity", 4, "27",
     SOC_LABELS["27"], "Choreographers",
     True, "★ cultural",
     "Core FCS 'Performing arts' domain.",
     SOURCE_URL),
    (59, "table_6_4a", "Creativity", 5, "27",
     SOC_LABELS["27"], "Special Effects Artists and Animators",
     True, "★ cultural",
     "Core FCS 'Audiovisual' domain.",
     SOURCE_URL),
    (59, "table_6_4a", "Creativity", 6, "27",
     SOC_LABELS["27"], "Producers and Directors",
     True, "★ cultural",
     "Core FCS 'Audiovisual' domain.",
     SOURCE_URL),
    (59, "table_6_4a", "Creativity", 7, "27",
     SOC_LABELS["27"], "Art Directors",
     True, "★ cultural",
     "Core FCS 'Design' and 'Audiovisual' overlap.",
     SOURCE_URL),
    (59, "table_6_4a", "Creativity", 8, "27",
     SOC_LABELS["27"], "Multimedia Artists and Animators",
     True, "★ cultural",
     "Core FCS 'Audiovisual' and 'Design' overlap.",
     SOURCE_URL),
    (59, "table_6_4a", "Creativity", 9, "27",
     SOC_LABELS["27"], "Set and Exhibit Designers",
     True, "★ cultural",
     "Core FCS 'Performing arts' / 'Heritage / Museum' overlap.",
     SOURCE_URL),
    (59, "table_6_4a", "Creativity", 10, "27",
     SOC_LABELS["27"], "Fashion Designers / Interior Designers",
     True, "★ cultural",
     "Core FCS 'Design' domain. The OECD lists the two adjacent occupations together at this rank.",
     SOURCE_URL),
]


def build():
    df = pd.DataFrame([dict(zip(COLUMNS, r)) for r in ROWS], columns=COLUMNS)
    df["paper_no"] = df["paper_no"].astype("int32")
    df["rank"] = df["rank"].astype("int32")
    df["is_soc27_cultural"] = df["is_soc27_cultural"].astype("boolean")
    return df


def validate(df):
    print("Validating...")
    assert len(df) == 10, f"expected 10 rows, got {len(df)}"
    print(f"  ✓ 10 rows — Table 6.4a Creativity column top-10")
    n_cult = int(df["is_soc27_cultural"].sum())
    assert n_cult == 8, f"expected 8 SOC-27 cultural occupations, got {n_cult}"
    print(f"  ✓ 8 of 10 occupations are SOC group 27 cultural (the Authenticity Paradox empirical anchor)")
    domains = set(df["domain"])
    assert domains == {"Creativity"}, f"unexpected domains: {domains}"
    print(f"  ✓ all rows on the Creativity capability domain")
    flags = set(df["atana_relevance_flag"])
    assert flags == {"★ cultural", "☆ cultural-adjacent"}, flags
    print(f"  ✓ atana_relevance_flag ∈ {{'★ cultural', '☆ cultural-adjacent'}}")


def write_parquet(df):
    out_path = OUT / "occupations_creativity_distance.parquet"
    con = duckdb.connect()
    con.register("df_data", df)
    con.execute(f"COPY df_data TO '{out_path}' (FORMAT PARQUET, COMPRESSION ZSTD)")
    print(f"  ✓ {out_path.relative_to(REPO_ROOT)} — {len(df)} rows, {out_path.stat().st_size/1024:.1f} KB")
    return out_path


def write_meta(out_path, df):
    meta = {
        "table": out_path.stem, "schema": "oecd_ai",
        "description": (
            "OECD No. 59 Table 6.4a Creativity column — top-10 occupations "
            "with the LARGEST Creativity capability gap (AI furthest from being "
            "able to perform). 8 of 10 are SOC group 27 cultural occupations: "
            "Music Directors and Composers, Choreographers, Special Effects "
            "Artists, Producers and Directors, Art Directors, Multimedia Artists, "
            "Set and Exhibit Designers, Fashion/Interior Designers. The "
            "occupation-weighted empirical backing for the Atana Authenticity "
            "Paradox (Note #18, Análise 6, Notes #06/#08)."
        ),
        "source": "OECD AI Papers No. 59, May 2026, Table 6.4a (page 32, image-embedded).",
        "source_pages": [SOURCE_URL],
        "fetch_date": "2026-06-05",
        "etl_script": "etl/oecd_ai__occupations_creativity_distance_to_parquet.py",
        "etl_run_date": str(date.today()),
        "licence": "OECD AI Papers — CC BY 4.0.",
        "grain": "one row per (paper_no, table_id, domain, rank)",
        "row_count": int(len(df)),
        "notes": (
            "Table 6.4a was extracted by manual visual transcription from a "
            "216-dpi PNG render of page 32 — markitdown/pdfplumber/pymupdf all "
            "failed because the OECD PDF embeds the table as an image. Numerical "
            "gap values per cell were not transcribed; the qualitative finding "
            "(SOC group 27 dominance) is the value of this table for the corpus."
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
    print("Building atana.oecd_ai.occupations_creativity_distance...")
    df = build(); validate(df)
    out_path = write_parquet(df); write_meta(out_path, df)
    maybe_push(df, "oecd_ai", "occupations_creativity_distance")
    print("Done.")


if __name__ == "__main__":
    main()
