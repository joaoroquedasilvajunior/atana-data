"""Luminate 2026 Midyear Report — Tier-1 headline tables → Parquet.

Extends atana.luminate (which held only the YE2025 tables) with the 2026 Midyear
Report (published 2026-07-15, covering H1 2026). Same Tier-1 posture as the
ye2025 ETL: headline figures transcribed VERBATIM from the public report page,
not the auth-walled full PDF.

VERIFICATION (2026-07-20): every figure below was cross-checked against the live
report at luminatedata.com/blog/luminate-2026-midyear-report-... (fetched this
session). Quotes preserved in `notes` for audit.

Four tables:
  midyear2026_global_headline     — global / ex-US / US ODA streams H1 2026
  midyear2026_us_language_share   — English / Spanish share + casual Latin peak
  midyear2026_export_power        — stated Export Power Rankings movers (KR #3, BR #8)
  midyear2026_ai_musicians        — gen-AI sentiment/use + top AI-assisted song

⚠️ SCOPE: the report press page names only SOME rankings (KR #3, BR #8) and the
US language split (Spanish; Portuguese is NOT broken out — it does not cross into
the US language stats, which is itself the finding for the language Análise). The
full country×language matrix + the complete Export Power top-10 are in the
auth-walled full report = Tier 2, deferred.

OUTPUT: raw/luminate/midyear2026_*.parquet (+ .meta.json)
Idempotent; DuckDB COPY; ATANA_ETL_SKIP_PUSH guard. Schema: atana.luminate.

Usage: python etl/luminate__midyear2026_to_parquet.py
"""
import json
import os
from datetime import date
from pathlib import Path

import duckdb
import pandas as pd

REPO = Path(__file__).resolve().parent.parent
OUT = REPO / "raw" / "luminate"
OUT.mkdir(parents=True, exist_ok=True)
SRC = ("Luminate 2026 Midyear Report (luminatedata.com/blog/"
       "luminate-2026-midyear-report-trends-in-music-television-film), "
       "published 2026-07-15, covering H1 2026. Verified 2026-07-20.")

# ── 1. global headline ───────────────────────────────────────────────────────
GLOBAL = [
    ("global", 9.8, 2.8, "Global On-Demand Audio streams +9.8% H1 2026 to 2.8 "
     "trillion (accel. from 9.6% FY2025)."),
    ("ex_us", 11.8, 2.0, "Ex-U.S. ODA +11.8% to 2.0 trillion (accel. from 11.6% FY2025)."),
    ("us", 4.8, 0.7327, "U.S. ODA +4.8% to 732.7B (accel. from 4.6% FY2025)."),
]

# ── 2. US language share ─────────────────────────────────────────────────────
LANG = [
    ("English", 87.1, "English-language consumption fell to a new low of 87.1%."),
    ("Spanish", 9.4, "Nearly 1 in 10 US streams (9.4%; Total ODA+Video) in Spanish."),
    ("Latin genre (casual monthly listenership peak)", 54.0,
     "US casual monthly listenership of the Latin genre peaked at 54% in Q1 2026. "
     "NB: a genre/listenership metric, not a language-share metric — kept here "
     "for the language story. Portuguese is NOT broken out in the US stats."),
]

# ── 3. export power rankings (only the stated movers) ────────────────────────
EXPORT = [
    ("South Korea", 3, "BTS", "Rose to #3 in Export Power Rankings, driven by BTS."),
    ("Brazil", 8, "Alok; Anitta", "Rose to #8 ('continued its steady multi-year "
     "ascent'), driven by Alok and Anitta. Both export via code-switching out of "
     "Portuguese: Alok = largely non-lyrical electronic; Anitta records in PT/ES/EN."),
]

# ── 4. AI & musicians ────────────────────────────────────────────────────────
AI = [
    ("musicians_positive_genai_pct", 54.0, "musicians",
     "54% of US musicians show positive feelings/acceptance toward gen-AI tools."),
    ("nonmusicians_positive_genai_pct", 35.0, "non-musicians",
     "vs 35% of non-musicians."),
    ("musicians_use_ai_edit_remix_pct", 18.0, "musicians",
     "18% of US musicians use AI to edit/remix existing music."),
    ("nonmusicians_use_ai_edit_remix_pct", 6.0, "non-musicians",
     "vs 6% of non-musicians."),
    ("top_ai_assisted_song_global_rank", 282.0, "market",
     "Highest-ranking AI-assisted song globally = Chill77, Unjaps 'Papaoutai "
     "(Afro Soul)' at #282 (210.7M global audio streams wks 1-24 2026)."),
]


def maybe_push(name, df):
    """CREATE OR REPLACE atana.luminate.<name> on MotherDuck if a token exists."""
    if os.environ.get("ATANA_ETL_SKIP_PUSH"):
        return False
    def _jwt(t): t=(t or "").strip(); return t if (t.startswith("eyJ") and t.count(".")==2) else ""
    token = _jwt(os.environ.get("MOTHERDUCK_TOKEN")) or _jwt(
        (REPO/".motherduck_token").read_text() if (REPO/".motherduck_token").exists() else "")
    if not token:
        print(f"  · MotherDuck push skipped for {name} — no valid token.")
        return False
    con = duckdb.connect(f"md:atana?motherduck_token={token}")
    con.execute("CREATE SCHEMA IF NOT EXISTS atana.luminate")
    con.register("d", df)
    con.execute(f"CREATE OR REPLACE TABLE atana.luminate.{name} AS SELECT * FROM d")
    n = con.execute(f"SELECT COUNT(*) FROM atana.luminate.{name}").fetchone()[0]
    print(f"  ✓ Synced atana.luminate.{name} ({n} rows)")
    return True


def build_and_write(name, df, desc, grain):
    p = OUT / f"{name}.parquet"
    con = duckdb.connect(); con.register("d", df)
    con.execute(f"COPY d TO '{p}' (FORMAT PARQUET, COMPRESSION ZSTD)")
    meta = {"table": name, "schema": "luminate", "description": desc,
            "source": SRC, "grain": grain, "fetch_date": "2026-07-20",
            "etl_script": "etl/luminate__midyear2026_to_parquet.py",
            "etl_run_date": str(date.today()), "row_count": int(len(df)),
            "tier": "Tier-1 (public report page). Full matrix = Tier-2, auth-walled."}
    p.with_suffix(".meta.json").write_text(json.dumps(meta, indent=2, ensure_ascii=False))
    print(f"  ✓ {p.relative_to(REPO)} — {len(df)} rows")
    maybe_push(name, df)
    return df


def main():
    print("Building atana.luminate 2026 Midyear tables...")
    g = pd.DataFrame([{"year": 2026, "half": "H1", "scope": s,
                       "oda_streams_yoy_pct": y, "oda_streams_tri": v, "notes": n}
                      for s, y, v, n in GLOBAL])
    build_and_write("midyear2026_global_headline", g,
        "Luminate 2026 Midyear — On-Demand Audio stream growth, H1 2026, by scope.",
        "one row per scope (global/ex_us/us)")

    la = pd.DataFrame([{"year": 2026, "market": "United States", "language": l,
                        "share_or_metric_pct": p, "notes": n} for l, p, n in LANG])
    build_and_write("midyear2026_us_language_share", la,
        "Luminate 2026 Midyear — US language share (English low 87.1%, Spanish "
        "9.4%) + Latin-genre casual-listenership peak (54%). Portuguese NOT "
        "broken out (the language Análise's core seam).",
        "one row per language/metric")

    ex = pd.DataFrame([{"year": 2026, "country": c, "export_power_rank": r,
                        "driving_artists": a, "notes": n} for c, r, a, n in EXPORT])
    build_and_write("midyear2026_export_power", ex,
        "Luminate 2026 Midyear — Export Power Rankings stated movers (KR #3, BR "
        "#8). Full top-10 is Tier-2 (auth-walled).",
        "one row per stated country")

    ai = pd.DataFrame([{"year": 2026, "metric": m, "value": v, "cohort": c, "notes": n}
                       for m, v, c, n in AI])
    build_and_write("midyear2026_ai_musicians", ai,
        "Luminate 2026 Midyear — gen-AI sentiment/use among US musicians vs "
        "non-musicians + top AI-assisted song global rank (#282).",
        "one row per metric")

    # ── validation ───────────────────────────────────────────────────────────
    print("Validating...")
    assert abs(la[la.language=="English"]["share_or_metric_pct"].iloc[0]-87.1)<1e-6
    assert abs(la[la.language=="Spanish"]["share_or_metric_pct"].iloc[0]-9.4)<1e-6
    assert ex[ex.country=="Brazil"]["export_power_rank"].iloc[0]==8
    assert ex[ex.country=="South Korea"]["export_power_rank"].iloc[0]==3
    assert abs(ai[ai.metric=="top_ai_assisted_song_global_rank"]["value"].iloc[0]-282)<1e-6
    print("  ✓ key figures match the verified report (Eng 87.1, Spa 9.4, BR #8, KR #3, AI #282)")

    if os.environ.get("ATANA_ETL_SKIP_PUSH"):
        print("  · MotherDuck push skipped (ATANA_ETL_SKIP_PUSH) — parquet only.")
    print("Done.")


if __name__ == "__main__":
    main()
