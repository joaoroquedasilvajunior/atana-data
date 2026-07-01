"""Anthropic Economic Index — subregion usage → `atana.anthropic_eei.subregion_usage_by_country`.

Phase 6b.3 of the Atana Data expansion. The June 2026 "Cadences" release
(release_2026_06_26) added a `subregion` geography level: for many countries it
carries state/province splits. For Brazil that is all 24 major UFs (BR-XX),
which is what this table ingests — the geographic seed that lets the corpus read
revealed AI use *inside* Brazil, by state (the /data/brasil-ia/ map, and the
"AI use is a Rouanet geography" finding that pairs with Notes #11/#21/#29).

WHY A SEPARATE TABLE
--------------------
The Phase 6b.2 refresh (anthropic_eei__to_parquet.py) deliberately preserved the
March table shape (country-level, ISO-2, 4 tables) and deferred the new
`subregion` dimension to this phase. This ETL is that phase — additive, no change
to the four existing tables.

SHAPE
-----
Long format, one row per (subregion, metric), May 2026 window
(`date_end = 2026-06-01`, the corpus-primary vintage, matching the country
tables). Columns:
    geo_id        — e.g. 'BR-SP'  (ISO 3166-2 subregion code)
    country_iso2  — 'BR'
    subregion     — 'SP'          (the UF two-letter, = RAIS sigla_uf, SALIC UF)
    metric_id     — 'usage_pct', 'collaboration_bucket_automation_pct',
                    'artifact_creative_writing_pct', 'ai_autonomy_mean', … (51)
    value         — the metric value for that subregion (May window)
    date_start, date_end
`usage_pct` at the subregion level = the subregion's SHARE of that country's
Claude.ai use (BR-XX sum ≈ 100 across Brazil). All 51 `overall`/hierarchy-0
metrics are kept so the table is reusable (collaboration lean, artifact
classifier, use-case split, autonomy/education means) without a re-pull.

SCOPE
-----
COUNTRIES defaults to Brazil only (the load-bearing scope per the corpus
accretion criterion — phase6_corpus_criterion_and_vol2_scoping.md). The release
carries subregions for 130+ countries; widen COUNTRIES (e.g. add LATAM UFs:
MX, CO, AR, CL, CR) to extend — no other change needed.

CAVEATS (foregrounded; see docs/methodology/anthropic_eei_subregion.md)
  1. Usage ≠ exposure ≠ automation risk (same lens caveat as the AEI country
     tables). A subregion's usage_pct is its share of a selected population.
  2. AC, AP and RR are NOT in the June subregion release for Brazil (below the
     sampling threshold) — 24 of 27 UFs. Absence is not zero.
  3. May 2026 window only; the April window (date_end 2026-05-01) is dropped for
     consistency with the country tables.
  4. Refresh is a DB-updater job (--refresh re-pulls the shared _source CSV via
     the main ETL; this script only re-reads it).

USAGE
    python etl/anthropic_eei__subregion_to_parquet.py
    # requires raw/anthropic_eei/_source/aei_claude_ai_2026-06-26.csv
    # (fetched by anthropic_eei__to_parquet.py --refresh)
"""
import hashlib
import json
import sys
from datetime import date
from pathlib import Path

import duckdb

REPO_ROOT = Path(__file__).resolve().parent.parent
OUT = REPO_ROOT / "raw" / "anthropic_eei"
SRC = OUT / "_source"
RAW_CSV = SRC / "aei_claude_ai_2026-06-26.csv"

MAY_DATE_END = "2026-06-01"          # corpus-primary vintage (May 2026 window)
COUNTRIES = ["BR"]                    # load-bearing scope; widen to extend
TABLE = "subregion_usage_by_country"


def write_meta(out_path, n_rows, n_subregions, metrics):
    src_sha = (hashlib.sha256(RAW_CSV.read_bytes()).hexdigest()
               if RAW_CSV.exists() else None)
    meta = {
        "table": out_path.stem,
        "description": (
            "AEI subregion-level metrics (long format), May 2026 window. "
            "Brazil UFs (BR-XX): each subregion's share of the country's "
            "Claude.ai use plus the full overall/hierarchy-0 metric set "
            "(collaboration lean, artifact classifier, use-case, autonomy)."),
        "source": "Anthropic Economic Index (AEI), release_2026_06_26 'Cadences'",
        "source_url": "https://huggingface.co/datasets/Anthropic/EconomicIndex",
        "vintage": f"May 2026 window (date_end={MAY_DATE_END})",
        "countries": COUNTRIES,
        "n_rows": n_rows,
        "n_subregions": n_subregions,
        "n_metrics": len(metrics),
        "metrics": metrics,
        "source_files": [{"file": RAW_CSV.name, "sha256": src_sha}],
        "fetch_date": str(date.today()),
        "etl_script": "etl/anthropic_eei__subregion_to_parquet.py",
        "etl_run_date": str(date.today()),
        "licence": "AEI data released openly by Anthropic (see dataset card)",
    }
    p = out_path.with_suffix(".meta.json")
    p.write_text(json.dumps(meta, indent=2, ensure_ascii=False))
    print(f"  ✓ {p.relative_to(REPO_ROOT)}")


def main():
    if not RAW_CSV.exists():
        sys.exit(f"missing {RAW_CSV.relative_to(REPO_ROOT)} — run "
                 f"anthropic_eei__to_parquet.py --refresh first")
    con = duckdb.connect()
    raw = RAW_CSV.as_posix()
    like = " OR ".join(f"r.geo_id LIKE '{c}-%'" for c in COUNTRIES)
    df = con.execute(f"""
        SELECT
            r.geo_id                        AS geo_id,
            LEFT(r.geo_id, 2)               AS country_iso2,
            RIGHT(r.geo_id, LENGTH(r.geo_id) - 3) AS subregion,
            r.metric_id                     AS metric_id,
            r.value                         AS value,
            r.date_start                    AS date_start,
            r.date_end                      AS date_end
        FROM '{raw}' r
        WHERE r.geo_level = 'subregion'
          AND ({like})
          AND r.category_name = 'overall'
          AND r.hierarchy_level = 0
          AND r.date_end = '{MAY_DATE_END}'
        ORDER BY country_iso2, subregion, metric_id
    """).fetchdf()

    out = OUT / f"{TABLE}.parquet"
    con.register("df_x", df)
    con.execute(f"COPY df_x TO '{out}' (FORMAT PARQUET, COMPRESSION ZSTD)")
    con.unregister("df_x")

    n_sub = df["geo_id"].nunique()
    metrics = sorted(df["metric_id"].unique().tolist())
    print(f"  ✓ {out.relative_to(REPO_ROOT)} — {len(df):,} rows, "
          f"{n_sub} subregions × {len(metrics)} metrics, "
          f"{out.stat().st_size/1024:.1f} KB")
    write_meta(out, len(df), n_sub, metrics)

    # eyeball: usage share leaders
    top = con.execute(f"""
        SELECT subregion, value FROM '{out}'
        WHERE metric_id='usage_pct' ORDER BY value DESC LIMIT 6""").fetchall()
    print("  top usage share:", ", ".join(f"{u} {v:.1f}%" for u, v in top))
    tot = con.execute(f"SELECT SUM(value) FROM '{out}' "
                      f"WHERE metric_id='usage_pct'").fetchone()[0]
    print(f"  usage_pct sums to {tot:.1f} (within-country share)")


if __name__ == "__main__":
    main()
