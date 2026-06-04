"""OECD AI Papers — methodological insumo for Vol. 2 → Parquet.

Phase 5c of the Atana Data expansion. First ingest of OECD AI Papers
(`atana.oecd_ai`). Tier 1 — headline framing of two papers the Atana Index
framework directly relies on:

- **Paper No. 59** — *The OECD AI exposure measure: Mapping the OECD AI
  Capability Indicators to occupations* (May 2026). Maps 9 AI capability
  domains (incl. explicit *creativity*) to occupational requirements;
  builds an AI Capability Gap Index across the OECD.
- **Paper No. 60** — *Benefits of AI Openness* (03/06/2026, G7 discussion
  paper, 46 pp, French presidency). Three structural findings: (i) open
  models ≈90 % of closed performance, lower cost; (ii) positive
  significant correlation between open-source AI activity and growth
  across 33 countries; (iii) AI openness shifts value capture downstream
  — to SMEs, public institutions, and creators.

CORPUS RELEVANCE
----------------
- The Atana AI Exposure Index method (Vol. 1) and the Authenticity Paradox
  framing now have an OECD aparatus to triangulate against, with an
  explicit creativity domain (No. 59) and an openness-vs-value-capture
  lens (No. 60).
- Together with HAI 2026's Foundation Model Transparency Index (58→40),
  this is a three-corner methodological frame for Atana Index Vol. 2.

GRAIN
-----
One row per paper. 2 rows at v1 launch. Schema: atana.oecd_ai.

SOURCES
-------
    Paper No. 59:
      https://www.oecd.org/en/publications/2026/05/the-oecd-ai-exposure-measure_489cfd42.html
    Paper No. 60:
      https://www.oecd.org/en/publications/benefits-of-ai-openness_746e8c9a-en.html

OUTPUT
------
    raw/oecd_ai/papers_headline.parquet  (+ .meta.json)

Idempotent; ATANA_ETL_SKIP_PUSH guard.
"""
import hashlib, json, os
from datetime import date
from pathlib import Path
import duckdb, pandas as pd

REPO_ROOT = Path(__file__).resolve().parent.parent
OUT = REPO_ROOT / "raw" / "oecd_ai"
OUT.mkdir(parents=True, exist_ok=True)

COLUMNS = ["paper_no", "title", "date_published", "pages",
           "headline_finding_1", "headline_finding_2", "headline_finding_3",
           "atana_relevance", "source_url", "notes"]

ROWS = [
    (59,
     "The OECD AI exposure measure: Mapping the OECD AI Capability Indicators to occupations",
     "2026-05-26", 58,
     "Maps 9 AI capability domains (language, social interaction, problem solving, creativity, metacognition/critical thinking, knowledge, learning/memory, vision, manipulation, robotic intelligence) against occupational requirements.",
     "Builds an AI Capability Gap Index comparing AI performance with what occupations require across 39 OECD-member labour markets.",
     "Finds AI is closer to occupations involving routine information processing, and farther from those depending on other skill types (manual, social, judgment-heavy).",
     "Direct methodological insumo for Atana's AI Exposure Index (Index Vol. 1) — provides an OECD-grade apparatus with an EXPLICIT *creativity* domain, making it a usable triangulation lens for LATAM cultural occupations via CBO crosswalk.",
     "https://www.oecd.org/en/publications/2026/05/the-oecd-ai-exposure-measure_489cfd42.html",
     "Series: OECD Artificial Intelligence Papers No. 59."),
    (60,
     "Benefits of AI openness",
     "2026-06-03", 46,
     "Open models reach ~90 % of closed models' performance at substantially lower cost — favourable price-quality for budget-constrained adopters (PMEs, public institutions, LATAM ministries).",
     "Open-source AI activity shows a positive and significant correlation with growth across 33 countries.",
     "AI openness shifts value capture DOWNSTREAM in the stack — to where SMEs, public institutions and creators operate. Counter-image of the Authenticity Paradox: openness widens, opacity narrows.",
     "Counterpart to Stanford HAI 2026 Foundation Model Transparency Index falling 58→40. Together with No. 59 (exposure) and HAI (transparency), forms a three-corner methodological frame for Atana Index Vol. 2: exposure × openness × transparency.",
     "https://www.oecd.org/en/publications/benefits-of-ai-openness_746e8c9a-en.html",
     "G7 discussion paper, requested by the French presidency 2026."),
]


def build():
    df = pd.DataFrame(
        [dict(zip(COLUMNS, r)) for r in ROWS], columns=COLUMNS)
    df = df.sort_values("paper_no").reset_index(drop=True)
    df["paper_no"] = df["paper_no"].astype("int32")
    df["pages"] = df["pages"].astype("int32")
    df["date_published"] = pd.to_datetime(df["date_published"]).dt.date
    return df


def validate(df):
    print("Validating...")
    assert len(df) == 2
    assert set(df["paper_no"]) == {59, 60}
    print(f"  ✓ 2 rows — Papers No. 59 + No. 60")
    for _, r in df.iterrows():
        for f in ("headline_finding_1", "headline_finding_2", "headline_finding_3"):
            assert isinstance(r[f], str) and len(r[f]) > 30, f"{f} too short on paper {r['paper_no']}"
    print(f"  ✓ all 3 headline findings present for each paper")
    assert "creativity" in df.loc[df["paper_no"] == 59, "headline_finding_1"].iloc[0].lower()
    print(f"  ✓ Paper 59 row carries the explicit 'creativity' domain reference")


def write_parquet(df):
    out_path = OUT / "papers_headline.parquet"
    con = duckdb.connect()
    con.register("df_data", df)
    con.execute(f"COPY df_data TO '{out_path}' (FORMAT PARQUET, COMPRESSION ZSTD)")
    print(f"  ✓ {out_path.relative_to(REPO_ROOT)} — {len(df)} rows, "
          f"{out_path.stat().st_size/1024:.1f} KB")
    return out_path


def write_meta(out_path, df):
    meta = {
        "table": out_path.stem, "schema": "oecd_ai",
        "description": "OECD AI Papers — headline framing of Papers No. 59 "
                       "(AI Exposure Measure, May 2026, 9 capability domains "
                       "incl. creativity) and No. 60 (Benefits of AI Openness, "
                       "03/06/2026, G7 discussion paper, 33-country growth "
                       "correlation). Methodological insumo for Atana Index Vol. 2.",
        "source": "OECD Artificial Intelligence Papers series (2026).",
        "fetch_date": "2026-06-04",
        "etl_script": "etl/oecd_ai__papers_headline_to_parquet.py",
        "etl_run_date": str(date.today()),
        "licence": "OECD published findings — public release.",
        "grain": "one row per paper", "row_count": int(len(df)),
        "notes": "v1 captures headline findings from publication landing pages "
                 "and press materials. Full-PDF deeper extraction (e.g. the "
                 "33-country dataset behind No. 60's openness-growth "
                 "correlation) is Tier 2.",
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
    print("Building atana.oecd_ai.papers_headline...")
    df = build(); validate(df)
    out_path = write_parquet(df); write_meta(out_path, df)
    maybe_push(df, "oecd_ai", "papers_headline")
    print("Done.")


if __name__ == "__main__":
    main()
