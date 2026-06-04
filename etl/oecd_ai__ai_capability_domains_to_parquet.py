"""OECD AI Papers — capability domains (Paper No. 59) → Parquet.

Phase 5c. Second of two `atana.oecd_ai` tables. The 9 AI capability
domains defined by OECD Paper No. 59 (*The OECD AI exposure measure*,
May 2026) — the unit of mapping between AI capability and occupational
requirements that the OECD's AI Capability Gap Index is built on.

CORPUS RELEVANCE
----------------
The **`creativity`** domain is the one direct entry-point for Atana
cultural-occupation analysis: occupations weighted high on creativity in
CBO terms (musicians, designers, artists) can be cross-referenced with
this OECD framework's exposure scoring.

SOURCE
------
    https://www.oecd.org/en/publications/2026/05/the-oecd-ai-exposure-measure_489cfd42.html
"""
import hashlib, json, os
from datetime import date
from pathlib import Path
import duckdb, pandas as pd

REPO_ROOT = Path(__file__).resolve().parent.parent
OUT = REPO_ROOT / "raw" / "oecd_ai"
OUT.mkdir(parents=True, exist_ok=True)
SOURCE_PAGE = ("https://www.oecd.org/en/publications/2026/05/"
               "the-oecd-ai-exposure-measure_489cfd42.html")

COLUMNS = ["paper_no", "domain", "description", "atana_relevance", "source_url"]

ROWS = [
    (59, "language",
     "Generation, understanding, and translation of natural language.",
     "Most occupations have a language component; cultural translation, "
     "literary work, publishing tightly tied. AI closer to this domain than most.",
     SOURCE_PAGE),
    (59, "social interaction",
     "Reading, modelling and responding to other agents in social contexts.",
     "Performing arts, teaching, cultural mediation, audience engagement.",
     SOURCE_PAGE),
    (59, "problem solving",
     "Reasoning to a solution under constraint.",
     "Design, curation, production planning, cultural policy analysis.",
     SOURCE_PAGE),
    (59, "creativity",
     "Production of novel and valuable outputs — the canonical 'human' domain in the OECD framework.",
     "★ The Atana direct entry-point. Music composition, visual art, design, "
     "literary production. The domain Notes #06/#08 and Análises 17-20 sit in.",
     SOURCE_PAGE),
    (59, "metacognition/critical thinking",
     "Reflecting on, evaluating, and revising one's own reasoning.",
     "Cultural critique, research, archival evaluation, editorial judgment.",
     SOURCE_PAGE),
    (59, "knowledge",
     "Storage and recall of factual or procedural information.",
     "Archives, libraries, museums; literacy and traditional-knowledge work.",
     SOURCE_PAGE),
    (59, "learning/memory",
     "Acquiring and retaining new information from experience.",
     "Teaching, training, cultural transmission across generations.",
     SOURCE_PAGE),
    (59, "vision",
     "Perception and interpretation of visual scenes.",
     "Visual arts, photography, film, exhibition, design.",
     SOURCE_PAGE),
    (59, "manipulation",
     "Fine motor control, handling of physical objects.",
     "Crafts, artesanías, instrument-making, physical performance, restoration.",
     SOURCE_PAGE),
    (59, "robotic intelligence",
     "Integrated planning and acting in the physical world.",
     "Stage automation, immersive installations; otherwise marginal for cultural occupations.",
     SOURCE_PAGE),
]


def build():
    df = pd.DataFrame([dict(zip(COLUMNS, r)) for r in ROWS], columns=COLUMNS)
    df["paper_no"] = df["paper_no"].astype("int32")
    return df


def validate(df):
    print("Validating...")
    assert len(df) == 10, f"expected 10 domains (OECD lists 10 incl. robotic), got {len(df)}"
    assert "creativity" in df["domain"].values
    print(f"  ✓ 10 capability domains; creativity present (Atana direct entry-point)")
    starred = df[df["atana_relevance"].str.startswith("★", na=False)]
    assert len(starred) == 1 and starred["domain"].iloc[0] == "creativity"
    print(f"  ✓ exactly 1 ★ row (creativity)")


def write_parquet(df):
    out_path = OUT / "ai_capability_domains.parquet"
    con = duckdb.connect()
    con.register("df_data", df)
    con.execute(f"COPY df_data TO '{out_path}' (FORMAT PARQUET, COMPRESSION ZSTD)")
    print(f"  ✓ {out_path.relative_to(REPO_ROOT)} — {len(df)} rows, "
          f"{out_path.stat().st_size/1024:.1f} KB")
    return out_path


def write_meta(out_path, df):
    meta = {
        "table": out_path.stem, "schema": "oecd_ai",
        "description": "OECD AI Paper No. 59 — the 10 AI capability domains "
                       "mapped against occupational requirements (language, "
                       "social interaction, problem solving, creativity, "
                       "metacognition, knowledge, learning/memory, vision, "
                       "manipulation, robotic intelligence). Creativity is "
                       "the direct entry-point for Atana cultural analysis.",
        "source": "OECD Artificial Intelligence Papers No. 59 (May 2026).",
        "source_pages": [SOURCE_PAGE], "fetch_date": "2026-06-04",
        "etl_script": "etl/oecd_ai__ai_capability_domains_to_parquet.py",
        "etl_run_date": str(date.today()),
        "licence": "OECD published findings — public release.",
        "grain": "one row per capability domain", "row_count": int(len(df)),
        "notes": "Domain definitions from the OECD AI Capability Indicators "
                 "framework. atana_relevance column carries the cultural-"
                 "occupation entry-point for each domain.",
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
    print("Building atana.oecd_ai.ai_capability_domains...")
    df = build(); validate(df)
    out_path = write_parquet(df); write_meta(out_path, df)
    maybe_push(df, "oecd_ai", "ai_capability_domains")
    print("Done.")


if __name__ == "__main__":
    main()
