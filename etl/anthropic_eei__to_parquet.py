"""Anthropic Economic Index (AEI) — Tier 1 ingest → schema `atana.anthropic_eei`.

Phase 6b.1 of the Atana Data expansion. Passes the accretion criterion gate 1
(Vol 2 minimum corpus — phase6_corpus_criterion_and_vol2_scoping.md §3):
the revealed-usage counterpart to `atana.oecd_ai`'s expert-rated AI-capability
frame. Two epistemologies, one question — house-style pairing (cf. Note #18).

WHAT THE AEI IS
---------------
Anthropic's open dataset of how Claude is actually used, built by classifying
real (privacy-preserved) conversations onto O*NET tasks, collaboration
patterns and geographies. CC-licensed, on Hugging Face
(Anthropic/EconomicIndex). Five releases 2025-02 → 2026-03; this ingest uses:
  · release_2026_03_24 — the geography × facet long file (week of
    2026-02-05→12, Claude.ai Free/Pro/Max): country-level usage including
    **Brazil-native rows** (269 O*NET tasks) — verified at probe time.
  · release_2025_03_27 — the global task-share file (task_pct_v2) +
    O*NET task→occupation statements, from which a global occupation-level
    usage table is DERIVED here.

TABLES (4)
----------
  country_usage              — all countries × usage share of global Claude.ai
  task_usage_by_country      — 7 geos (GLOBAL, US + the 5 corpus countries)
                               × O*NET task × count/pct
  collaboration_by_country   — same 7 geos × collaboration pattern
                               (automation-vs-augmentation, country-level)
  occupation_usage_global_v2 — DERIVED: SOC occupation × global usage share
                               (task shares apportioned equally across the
                               occupations sharing a task statement —
                               documented methodological choice)

CENTRAL CAVEATS (foregrounded; full list in docs/methodology/anthropic_eei.md)
  1. Usage ≠ exposure ≠ automation risk — the AEI measures what people DO
     with Claude, a different construct from OECD No. 59's capability ratings.
  2. Selected population — Claude.ai users skew toward coding/writing/EN.
  3. Vintages differ across tables: occupation table = global v2 (Mar 2025);
     country tables = one week of Feb 2026. Do not mix without saying so.
  4. The AEI updates ~quarterly — refresh is a DB-updater job (--refresh).

Sources cached under raw/anthropic_eei/_source/ (the 103 MB raw geography
file is GITIGNORED — only the small derived Parquet tables are committed).
Idempotent; byte-identical reruns. MotherDuck sync manual — NEW schema,
João's checkpoint.

Usage:
    python etl/anthropic_eei__to_parquet.py            # uses cache
    python etl/anthropic_eei__to_parquet.py --refresh  # re-pull from HF
"""
import hashlib
import json
import sys
import urllib.request
from datetime import date
from pathlib import Path

import duckdb
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parent.parent
OUT = REPO_ROOT / "raw" / "anthropic_eei"
SRC = OUT / "_source"
OUT.mkdir(parents=True, exist_ok=True)
SRC.mkdir(parents=True, exist_ok=True)
REFRESH = "--refresh" in sys.argv

HF = "https://huggingface.co/datasets/Anthropic/EconomicIndex/resolve/main"
FILES = {
    "task_pct_v2.csv": f"{HF}/release_2025_03_27/task_pct_v2.csv",
    "onet_task_statements.csv": f"{HF}/release_2025_03_27/onet_task_statements.csv",
    "SOC_Structure.csv": f"{HF}/release_2025_03_27/SOC_Structure.csv",
    "aei_raw_claude_ai_2026.csv":
        f"{HF}/release_2026_03_24/data/"
        "aei_raw_claude_ai_2026-02-05_to_2026-02-12.csv",
}
GEOS = ["GLOBAL", "US", "BR", "MX", "CO", "AR", "CR"]
RAW_VINTAGE = "2026-02-05_to_2026-02-12 (release_2026_03_24)"
V2_VINTAGE = "global v2 (release_2025_03_27)"


def ensure_sources():
    for name, url in FILES.items():
        p = SRC / name
        if p.exists() and not REFRESH:
            continue
        print(f"  · downloading {name} …")
        req = urllib.request.Request(url, headers={"User-Agent": "atana-data ETL"})
        with urllib.request.urlopen(req, timeout=300) as r:
            p.write_bytes(r.read())


def write_parquet(con, df, table):
    out = OUT / f"{table}.parquet"
    con.register("df_x", df)
    con.execute(f"COPY df_x TO '{out}' (FORMAT PARQUET, COMPRESSION ZSTD)")
    con.unregister("df_x")
    print(f"  ✓ {out.relative_to(REPO_ROOT)} — {len(df):,} rows, "
          f"{out.stat().st_size/1024:.1f} KB")
    return out


def write_meta(out_path, description, sources, vintage):
    meta = {
        "table": out_path.stem,
        "description": description,
        "source": "Anthropic Economic Index (AEI), Hugging Face "
                  "Anthropic/EconomicIndex",
        "source_url": "https://huggingface.co/datasets/Anthropic/EconomicIndex",
        "vintage": vintage,
        "source_files": [{"file": s, "sha256": hashlib.sha256(
            (SRC / s).read_bytes()).hexdigest()} for s in sources],
        "fetch_date": str(date.today()),
        "etl_script": "etl/anthropic_eei__to_parquet.py",
        "etl_run_date": str(date.today()),
        "licence": "AEI data released openly by Anthropic (see dataset card)",
    }
    p = out_path.with_suffix(".meta.json")
    p.write_text(json.dumps(meta, indent=2, ensure_ascii=False))
    print(f"  ✓ {p.relative_to(REPO_ROOT)}")


def main():
    ensure_sources()
    con = duckdb.connect()
    raw = (SRC / "aei_raw_claude_ai_2026.csv").as_posix()
    geos_sql = "(" + ",".join(f"'{g}'" for g in GEOS) + ")"

    # ── 1. country_usage (all countries) ────────────────────────────────
    cu = con.execute(f"""
        SELECT geo_id,
               max(CASE WHEN variable='usage_count' THEN value END) AS usage_count,
               max(CASE WHEN variable='usage_pct' THEN value END)  AS usage_pct
        FROM '{raw}'
        WHERE geography='country' AND facet='country'
          AND variable IN ('usage_count','usage_pct')
        GROUP BY 1 ORDER BY usage_pct DESC NULLS LAST, geo_id""").fetchdf()
    p = write_parquet(con, cu, "country_usage")
    write_meta(p, "Share of global Claude.ai usage by country (ISO-2), one "
               "week of Feb 2026. Selected population — see methodology.",
               ["aei_raw_claude_ai_2026.csv"], RAW_VINTAGE)

    # ── 2. task_usage_by_country (7 geos) ───────────────────────────────
    tu = con.execute(f"""
        SELECT geo_id, cluster_name AS onet_task,
               max(CASE WHEN variable='onet_task_count' THEN value END) AS task_count,
               max(CASE WHEN variable='onet_task_pct' THEN value END)  AS task_pct
        FROM '{raw}'
        WHERE facet='onet_task' AND geo_id IN {geos_sql}
          AND variable IN ('onet_task_count','onet_task_pct')
        GROUP BY 1,2 ORDER BY geo_id, task_pct DESC NULLS LAST,
                 onet_task""").fetchdf()
    p = write_parquet(con, tu, "task_usage_by_country")
    write_meta(p, "O*NET-task usage shares for GLOBAL, US and the five Atana "
               "corpus countries (BR/MX/CO/AR/CR), one week of Feb 2026. "
               "Includes 'not_classified'/'none' rows as published.",
               ["aei_raw_claude_ai_2026.csv"], RAW_VINTAGE)

    # ── 3. collaboration_by_country (7 geos) ────────────────────────────
    cb = con.execute(f"""
        SELECT geo_id, cluster_name AS collaboration_pattern,
               max(CASE WHEN variable='collaboration_count' THEN value END) AS n,
               max(CASE WHEN variable='collaboration_pct' THEN value END)  AS pct
        FROM '{raw}'
        WHERE facet='collaboration' AND geo_id IN {geos_sql}
        GROUP BY 1,2 ORDER BY geo_id, pct DESC NULLS LAST,
                 collaboration_pattern""").fetchdf()
    p = write_parquet(con, cb, "collaboration_by_country")
    write_meta(p, "Human-AI collaboration patterns (automation vs "
               "augmentation family) by geo, one week of Feb 2026.",
               ["aei_raw_claude_ai_2026.csv"], RAW_VINTAGE)

    # ── 4. occupation_usage_global_v2 (derived) ─────────────────────────
    occ = con.execute(f"""
        WITH stmts AS (
          SELECT lower(trim("Task")) AS task_key,
                 "O*NET-SOC Code" AS onet_soc_code, "Title" AS occupation
          FROM '{(SRC / 'onet_task_statements.csv').as_posix()}'),
        nshare AS (
          SELECT task_key, count(*) AS n_occ FROM stmts GROUP BY 1),
        tp AS (
          SELECT lower(trim(task_name)) AS task_key, pct
          FROM '{(SRC / 'task_pct_v2.csv').as_posix()}')
        SELECT s.onet_soc_code, s.occupation,
               sum(tp.pct / ns.n_occ) AS usage_pct_global_v2,
               count(*) AS n_tasks_matched
        FROM tp JOIN stmts s USING (task_key) JOIN nshare ns USING (task_key)
        GROUP BY 1,2 ORDER BY usage_pct_global_v2 DESC,
                 onet_soc_code""").fetchdf()
    p = write_parquet(con, occ, "occupation_usage_global_v2")
    write_meta(p, "DERIVED — global Claude.ai usage share by O*NET-SOC "
               "occupation, v2 (early 2025): task shares apportioned "
               "equally across occupations sharing a task statement. The "
               "apportionment is an Atana methodological choice, not an "
               "Anthropic figure. Pairs with atana.oecd_ai (expert-rated "
               "frame) — full occupation-level pairing gated on oecd_ai "
               "Tier 2.", ["task_pct_v2.csv", "onet_task_statements.csv"],
               V2_VINTAGE)

    # ── Validation ───────────────────────────────────────────────────────
    br = cu[cu.geo_id == "BR"]["usage_pct"].iloc[0]
    assert 2.5 < br < 2.6, br                       # probe: 2.5548
    t = tu[(tu.geo_id == "BR")].nlargest(2, "task_pct")
    assert t.iloc[0]["onet_task"] == "not_classified"
    assert 5.0 < t.iloc[1]["task_pct"] < 5.2        # probe: 5.0767
    assert len(occ) > 600 and occ["usage_pct_global_v2"].sum() < 100.01
    assert set(tu.geo_id) == set(GEOS)
    print(f"  · validation OK — country_usage {len(cu)} · task_usage "
          f"{len(tu)} · collaboration {len(cb)} · occupations {len(occ)}; "
          f"BR usage {br:.4f}% of global")
    print("  · MotherDuck sync manual — NEW schema atana.anthropic_eei "
          "(João's checkpoint).")


if __name__ == "__main__":
    main()
