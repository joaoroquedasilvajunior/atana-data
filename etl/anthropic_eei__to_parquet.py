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
(Anthropic/EconomicIndex). This ingest uses:
  · release_2026_06_26 — the "Cadences" report (April and May 2026 monthly
    aggregates, Claude.ai Free/Pro/Max/Cowork). Long-format schema:
    `date_start`/`date_end` × `geo_id` (ISO-3) × `geo_level` × `category_name`
    × `hierarchy_level` × `metric_id` × `value`. May window (`date_end =
    2026-06-01`) is the primary vintage below.
  · release_2025_03_27 — the global task-share file (task_pct_v2) +
    O*NET task→occupation statements, from which a global occupation-level
    usage table is DERIVED here (UNCHANGED across refreshes).

PHASE 6b.2 REFRESH (2026-06-30) — path B, in-place
--------------------------------------------------
Anthropic rewrote the AEI schema in the June release:
  · wide (facet, variable, cluster_name) → long (category_name, metric_id,
    node_name, hierarchy_level)
  · 2-letter ISO codes → 3-letter ISO alpha-3
  · raw *_count columns were DROPPED; only percentages remain
  · collaboration expanded from 2 buckets → 2 buckets + 6 pattern splits
  · geography expanded from `country` → `country` + `subregion` (all 24
    major Brazilian UFs are now in the release — the seed for Phase 6b.3)

This ETL preserves the March table shape (same 4 tables, same column names,
same geo_id encoding in ISO-2 for continuity of downstream analyses) — the
new dimensions are deferred to Phase 6b.3. `usage_count`, `task_count`,
`collaboration_count` columns kept for schema stability but populated with
NULL (Anthropic no longer publishes them).

TABLES (4)
----------
  country_usage              — all countries × usage share of global Claude.ai
  task_usage_by_country      — 7 geos (GLOBAL, US + the 5 corpus countries)
                               × O*NET task × pct  (task_count now NULL)
  collaboration_by_country   — same 7 geos × collaboration pattern
                               (automation-vs-augmentation, country-level)
  occupation_usage_global_v2 — DERIVED: SOC occupation × global usage share
                               (task shares apportioned equally across the
                               occupations sharing a task statement —
                               documented methodological choice, unchanged)

CENTRAL CAVEATS (foregrounded; full list in docs/methodology/anthropic_eei.md)
  1. Usage ≠ exposure ≠ automation risk — the AEI measures what people DO
     with Claude, a different construct from OECD No. 59's capability ratings.
  2. Selected population — Claude.ai users skew toward coding/writing/EN.
  3. Vintages differ across tables: occupation table = global v2 (Mar 2025);
     country tables = May 2026 monthly aggregate from the "Cadences" report.
     Do not mix without saying so.
  4. The AEI updates ~quarterly — refresh is a DB-updater job (--refresh).
  5. *_count columns are NULL for the June refresh — Anthropic dropped raw
     counts in the schema rewrite. Do not sum NULLs.

Sources cached under raw/anthropic_eei/_source/ (the 219 MB Cadences
geography file is GITIGNORED — only the small derived Parquet tables are
committed). Idempotent; byte-identical reruns. MotherDuck sync manual —
schema version bump on refresh (João's checkpoint).

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
    "aei_claude_ai_2026-06-26.csv":
        f"{HF}/release_2026_06_26/data/aei_claude_ai_2026-06-26.csv",
}

# Legacy sources kept for --refresh cross-check; not consumed by any table
# (schema-migration audit trail — the March file must NOT be depended on).
LEGACY_MARCH_FILE = "aei_raw_claude_ai_2026.csv"

# GEOS_ISO3 — the June release publishes 3-letter ISO alpha-3. We map back to
# 2-letter for continuity of the March-shape corpus tables (Path B).
GEOS_ISO3 = ["GLOBAL", "USA", "BRA", "MEX", "COL", "ARG", "CRI"]
ISO3_TO_ISO2 = {
    "GLOBAL": "GLOBAL", "USA": "US", "BRA": "BR", "MEX": "MX",
    "COL": "CO", "ARG": "AR", "CRI": "CR",
    # Not currently in the 7-geo cross but supported for Phase 6b.3:
    "CHL": "CL",
}
# The Path B geo set for backward-compatibility with the March corpus tables:
GEOS = [ISO3_TO_ISO2[c] for c in GEOS_ISO3]

# May 2026 window is the primary vintage; date_end is exclusive per Anthropic.
MAY_DATE_END = "2026-06-01"

RAW_VINTAGE = "2026-05-01_to_2026-06-01 (release_2026_06_26, May 2026 window)"
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
    raw = (SRC / "aei_claude_ai_2026-06-26.csv").as_posix()
    geos_iso3_sql = "(" + ",".join(f"'{g}'" for g in GEOS_ISO3) + ")"

    # Register the ISO3→ISO2 mapping so it can be joined in SQL
    iso_map_df = pd.DataFrame(
        [(k, v) for k, v in ISO3_TO_ISO2.items()],
        columns=["geo_id_iso3", "geo_id"])
    con.register("iso_map", iso_map_df)

    # For all-countries reads, we don't have a mapping for every ISO-3 in the
    # AEI universe (only the 7 corpus geos + CHL are in ISO3_TO_ISO2). For
    # country_usage we keep the ISO-3 code as geo_id_iso3 alongside a
    # coalesced geo_id (ISO-2 where mapped, ISO-3 fallback where not).

    # ── 1. country_usage (all countries) — May 2026 window ─────────────
    # Filter path: geo_level='country' AND category_name='overall' AND
    # metric_id='usage_pct'. Anthropic dropped usage_count in June — kept
    # in schema as NULL for continuity.
    cu = con.execute(f"""
        SELECT
            COALESCE(m.geo_id, r.geo_id) AS geo_id,
            r.geo_id AS geo_id_iso3,
            CAST(NULL AS DOUBLE) AS usage_count,
            r.value AS usage_pct
        FROM '{raw}' r
        LEFT JOIN iso_map m ON m.geo_id_iso3 = r.geo_id
        WHERE r.geo_level = 'country'
          AND r.category_name = 'overall'
          AND r.metric_id = 'usage_pct'
          AND r.date_end = '{MAY_DATE_END}'
        ORDER BY usage_pct DESC NULLS LAST, geo_id""").fetchdf()
    p = write_parquet(con, cu, "country_usage")
    write_meta(p, "Share of global Claude.ai usage by country, May 2026 "
               "monthly aggregate. geo_id in ISO-2 for continuity where "
               "mapped (7 Atana corpus geos + CHL); geo_id_iso3 always "
               "present. usage_count is NULL — Anthropic dropped raw counts "
               "in the June 2026 schema rewrite. Selected population — see "
               "methodology.",
               ["aei_claude_ai_2026-06-26.csv"], RAW_VINTAGE)

    # ── 2. task_usage_by_country (7 geos, hierarchy_level=0 = leaf task) ─
    # Filter: geo_level='country' (plus GLOBAL synthesized) AND
    # category_name='onet' AND hierarchy_level=0 AND metric_id='pct'.
    # GLOBAL row for onet is at geo_level='global' with geo_id='GLOBAL'.
    tu = con.execute(f"""
        SELECT
            COALESCE(m.geo_id, r.geo_id) AS geo_id,
            r.node_name AS onet_task,
            CAST(NULL AS DOUBLE) AS task_count,
            r.value AS task_pct
        FROM '{raw}' r
        LEFT JOIN iso_map m ON m.geo_id_iso3 = r.geo_id
        WHERE (
            (r.geo_level = 'country' AND r.geo_id IN {geos_iso3_sql})
            OR (r.geo_level = 'global' AND r.geo_id = 'GLOBAL')
          )
          AND r.category_name = 'onet'
          AND r.hierarchy_level = 0
          AND r.metric_id = 'pct'
          AND r.date_end = '{MAY_DATE_END}'
        ORDER BY geo_id, task_pct DESC NULLS LAST, onet_task""").fetchdf()
    p = write_parquet(con, tu, "task_usage_by_country")
    write_meta(p, "O*NET-task (leaf-level) usage shares for GLOBAL, US and "
               "the five Atana corpus countries (BR/MX/CO/AR/CR), May 2026 "
               "monthly aggregate. task_count is NULL — Anthropic dropped "
               "raw counts in the June 2026 schema rewrite. May include "
               "unresolved tasks depending on Anthropic's classifier "
               "coverage this vintage.",
               ["aei_claude_ai_2026-06-26.csv"], RAW_VINTAGE)

    # ── 3. collaboration_by_country (7 geos × automation vs augmentation) ─
    # Path B preserves the 2-bucket March shape. The 6 new pattern metrics
    # (directive / feedback_loop / task_iteration / learning / validation /
    # none) are deferred to Phase 6b.3.
    # Filter: category_name='overall' AND metric_id in the 2 bucket columns.
    cb = con.execute(f"""
        WITH bkt AS (
            SELECT
                COALESCE(m.geo_id, r.geo_id) AS geo_id,
                CASE r.metric_id
                    WHEN 'collaboration_bucket_automation_pct' THEN 'automation'
                    WHEN 'collaboration_bucket_augmentation_pct' THEN 'augmentation'
                END AS collaboration_pattern,
                r.value AS pct
            FROM '{raw}' r
            LEFT JOIN iso_map m ON m.geo_id_iso3 = r.geo_id
            WHERE (
                (r.geo_level = 'country' AND r.geo_id IN {geos_iso3_sql})
                OR (r.geo_level = 'global' AND r.geo_id = 'GLOBAL')
              )
              AND r.category_name = 'overall'
              AND r.metric_id IN (
                'collaboration_bucket_automation_pct',
                'collaboration_bucket_augmentation_pct')
              AND r.date_end = '{MAY_DATE_END}'
        )
        SELECT geo_id, collaboration_pattern,
               CAST(NULL AS DOUBLE) AS n,
               pct
        FROM bkt
        ORDER BY geo_id, pct DESC NULLS LAST, collaboration_pattern""").fetchdf()
    p = write_parquet(con, cb, "collaboration_by_country")
    write_meta(p, "Human-AI collaboration buckets (automation vs "
               "augmentation) by geo, May 2026 monthly aggregate. n is NULL "
               "— Anthropic dropped raw counts. Only the two headline "
               "buckets are exported here; the six pattern splits published "
               "in June 2026 (directive / feedback_loop / task_iteration / "
               "learning / validation / none) are deferred to Phase 6b.3.",
               ["aei_claude_ai_2026-06-26.csv"], RAW_VINTAGE)

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
    # Vintage-agnostic assertions (usage patterns shift between refreshes):

    # 1. Corpus geos present & mapped ISO-3 → ISO-2 correctly
    assert set(tu.geo_id) == set(GEOS), (
        f"expected {GEOS}, got {sorted(set(tu.geo_id))}")

    # 2. BR usage_pct plausible: 0.5% floor, 10% ceiling. March was 2.55%.
    br = cu[cu.geo_id == "BR"]["usage_pct"].iloc[0]
    assert 0.5 < br < 10.0, f"BR usage_pct out of plausible range: {br}"

    # 3. Task list per country not empty (May window must have populated pct)
    for g in ["BR", "US", "GLOBAL"]:
        n = len(tu[tu.geo_id == g])
        assert n > 20, f"{g} task_usage has only {n} rows (expected > 20)"

    # 4. Collaboration buckets present for every corpus geo, 2 rows each
    for g in GEOS:
        rows = cb[cb.geo_id == g]
        assert len(rows) == 2, f"{g}: {len(rows)} collab rows (expected 2)"
        pats = set(rows["collaboration_pattern"])
        assert pats == {"automation", "augmentation"}, f"{g}: {pats}"

    # 5. Occupation-usage table integrity (unchanged from March)
    assert len(occ) > 600 and occ["usage_pct_global_v2"].sum() < 100.01

    # 6. count columns must be NULL (June schema dropped them)
    assert cu["usage_count"].isnull().all(), "usage_count should be NULL"
    assert tu["task_count"].isnull().all(), "task_count should be NULL"
    assert cb["n"].isnull().all(), "collaboration n should be NULL"

    br_iso3 = cu[cu.geo_id == "BR"]["geo_id_iso3"].iloc[0]
    assert br_iso3 == "BRA", f"expected BR→BRA mapping, got {br_iso3}"

    # 7. Anthropic Usage Index (per-capita), if available, offers a Phase
    # 6b.3 preview. Not asserted here — just log if present.
    per_capita_present = con.execute(f"""
        SELECT count(*) FROM '{raw}'
        WHERE metric_id='usage_per_capita_index'
          AND geo_level='country' AND date_end='{MAY_DATE_END}'""").fetchone()[0]
    print(f"  · validation OK — country_usage {len(cu):,} · task_usage "
          f"{len(tu):,} · collaboration {len(cb):,} · occupations "
          f"{len(occ):,}; BR (BRA) usage {br:.4f}% of global (May 2026)")
    print(f"  · Phase 6b.3 preview — usage_per_capita_index available for "
          f"{per_capita_present:,} country rows (May 2026)")
    print("  · MotherDuck sync manual — schema-version bump for the "
          "release_2026_06_26 refresh (João's checkpoint).")


if __name__ == "__main__":
    main()
