"""OECD AI Papers — skill demand in high-exposure vacancies (Paper No. 59) → Parquet.

Extension to `atana.oecd_ai` (2026-06-22). Third table in the schema. Captures the
demand-side findings of *The OECD AI exposure measure* (Paper No. 59): which skill
groups employers ask for in vacancies belonging to HIGH-AI-exposure occupations,
and how that demand shifted between the measure's base and end years.

WHY THIS TABLE EXISTS
---------------------
No. 59 already anchors the Atana AI Exposure Index (`ai_capability_domains`,
`papers_headline`). Its *capability* side compresses creativity (the level-5
artefact documented in the methodology note). Its *demand* side, by contrast,
reports that originality is the cognitive sub-skill rising fastest in
high-exposure vacancies: from 25% to 33% of such vacancies. That single fact is
the OECD/expert corner of Atana's three-corner creativity read
(OECD demand × anthropic_eei revealed use × RAIS wages). This table carries the
number with provenance so the Note and Vol. 2 can cite the corpus, not a webpage.

TIER
----
Tier 1 (headline) figures, read from the OECD publication's public summary and
corroborating write-ups. The base/end YEARS and the full per-skill series are in
the PDF body (Tier 2, Vol. 2 input) — see `qualifier`/`notes` and the methodology
doc. `social & emotional` and `digital` carry qualifier='floor' because OECD
reports them as "over 50%", not an exact share.

SOURCE
------
    https://www.oecd.org/en/publications/2026/05/the-oecd-ai-exposure-measure_489cfd42.html
    (corroboration: OECD f3da0f0a-en landing page; Digital Watch Observatory write-up)
"""
import json, os
from datetime import date
from pathlib import Path
import duckdb, pandas as pd

REPO_ROOT = Path(__file__).resolve().parent.parent
OUT = REPO_ROOT / "raw" / "oecd_ai"
OUT.mkdir(parents=True, exist_ok=True)
SOURCE_PAGE = ("https://www.oecd.org/en/publications/2026/05/"
               "the-oecd-ai-exposure-measure_489cfd42.html")

COLUMNS = ["paper_no", "skill_group", "metric", "value_pct",
           "qualifier", "atana_relevance", "source_url"]

ROWS = [
    (59, "originality (cognitive)", "demand_share_high_exposure_base", 25.0, "exact",
     "★ The creativity/originality demand signal. Base-year share of high-AI-exposure "
     "vacancies demanding originality-related skills.",
     SOURCE_PAGE),
    (59, "originality (cognitive)", "demand_share_high_exposure_end", 33.0, "exact",
     "★ End-year share. +8pp; originality is the cognitive sub-skill with the GREATEST "
     "rise in demand. Headline number for the three-corner creativity read "
     "(OECD demand x anthropic_eei use x RAIS wages).",
     SOURCE_PAGE),
    (59, "management", "demand_share_high_exposure", 72.0, "exact",
     "Share of high-exposure vacancies requiring at least one management skill.",
     SOURCE_PAGE),
    (59, "business processes", "demand_share_high_exposure", 67.0, "exact",
     "Share requiring at least one business-process skill.",
     SOURCE_PAGE),
    (59, "social & emotional", "demand_share_high_exposure", 50.0, "floor",
     "OECD reports 'over 50%'. Stored as a floor (>=50), not an exact share.",
     SOURCE_PAGE),
    (59, "digital", "demand_share_high_exposure", 50.0, "floor",
     "OECD reports 'over 50%'. Stored as a floor (>=50), not an exact share.",
     SOURCE_PAGE),
]


def build():
    df = pd.DataFrame([dict(zip(COLUMNS, r)) for r in ROWS], columns=COLUMNS)
    df["paper_no"] = df["paper_no"].astype("int32")
    df["value_pct"] = df["value_pct"].astype("float64")
    return df


def validate(df):
    print("Validating...")
    assert len(df) == 6, f"expected 6 rows, got {len(df)}"
    base = df[df["metric"] == "demand_share_high_exposure_base"]["value_pct"].iloc[0]
    end = df[df["metric"] == "demand_share_high_exposure_end"]["value_pct"].iloc[0]
    assert (base, end) == (25.0, 33.0), f"originality must be 25->33, got {base}->{end}"
    assert set(df["qualifier"]) <= {"exact", "floor"}
    starred = df[df["atana_relevance"].str.startswith("★", na=False)]
    assert len(starred) == 2, "exactly the 2 originality rows are starred"
    print(f"  ✓ 6 rows; originality 25.0 -> 33.0; 2 ★ rows; qualifier vocab OK")


def write_parquet(df):
    out_path = OUT / "skill_demand_high_exposure.parquet"
    con = duckdb.connect()
    con.register("df_data", df)
    con.execute(f"COPY df_data TO '{out_path}' (FORMAT PARQUET, COMPRESSION ZSTD)")
    print(f"  ✓ {out_path.relative_to(REPO_ROOT)} — {len(df)} rows, "
          f"{out_path.stat().st_size/1024:.1f} KB")
    return out_path


def write_meta(out_path, df):
    meta = {
        "table": out_path.stem, "schema": "oecd_ai",
        "description": "OECD AI Paper No. 59 — demand-side findings. Share of "
                       "vacancies in HIGH-AI-exposure occupations requiring each "
                       "skill group, and the base->end shift for originality "
                       "(25% -> 33%, the cognitive sub-skill rising fastest). "
                       "Complements ai_capability_domains (the capability/supply "
                       "side, which compresses creativity at level 5). The "
                       "originality rows are the OECD/expert corner of Atana's "
                       "three-corner creativity read.",
        "source": "OECD Artificial Intelligence Papers No. 59 (May 2026), demand-side summary.",
        "source_pages": [SOURCE_PAGE,
                         "https://www.oecd.org/en/publications/the-oecd-ai-exposure-measure_f3da0f0a-en.html",
                         "https://dig.watch/updates/oecd-ai-exposure-measure"],
        "fetch_date": "2026-06-22",
        "etl_script": "etl/oecd_ai__skill_demand_to_parquet.py",
        "etl_run_date": str(date.today()),
        "licence": "OECD published findings — public release.",
        "grain": "one row per skill group x metric",
        "row_count": int(len(df)),
        "notes": "Tier 1 headline shares. Base/end YEARS and the full per-skill "
                 "series are in the PDF body (Tier 2, Vol. 2 input). "
                 "social & emotional / digital carry qualifier='floor' because "
                 "OECD reports them as 'over 50%'.",
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
    print("Building atana.oecd_ai.skill_demand_high_exposure...")
    df = build(); validate(df)
    out_path = write_parquet(df); write_meta(out_path, df)
    maybe_push(df, "oecd_ai", "skill_demand_high_exposure")
    print("Done.")


if __name__ == "__main__":
    main()
