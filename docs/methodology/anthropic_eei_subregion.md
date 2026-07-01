# `atana.anthropic_eei.subregion_usage_by_country` — Phase 6b.3

**Source:** Anthropic Economic Index (AEI), `release_2026_06_26` ("Cadences").
**Vintage:** May 2026 window (`date_end = 2026-06-01`), the corpus-primary window (matches the AEI country tables).
**ETL:** `etl/anthropic_eei__subregion_to_parquet.py` → `raw/anthropic_eei/subregion_usage_by_country.parquet` (+ `.meta.json`).
**Rows:** 1,224 = 24 Brazilian UFs × 51 metrics. Idempotent (byte-identical rerun).

## What it is

The June AEI release added a `subregion` geography level to the long-format file. For Brazil that is **24 of the 27 UFs** (BR-XX, ISO 3166-2). This table lifts those rows into the corpus so revealed AI use can be read **inside Brazil, by state** — the geographic seed that Phase 6b.2 flagged and deferred.

It is a faithful long-format slice: one row per `(subregion, metric)`, all 51 `overall` / hierarchy-0 metrics kept, so the table is reusable without a re-pull:

- `usage_pct` — the subregion's **share of Brazil's Claude.ai use** (BR-XX sum ≈ 99.7 ≈ 100).
- `collaboration_bucket_automation_pct` / `augmentation_pct` — the 2-mode do-vs-learn lean, by state.
- `artifact_*_pct` — the June **artifact classifier** (30+ deliverable types), by state, incl. the creative outputs (creative_writing, image, video, audio, marketing, translation).
- `use_case_work/personal/coursework_pct`, `ai_autonomy_mean`, `ai_education_years_mean`, `human_only_ability_pct`, `multitasking_pct`.

## Schema

| column | type | notes |
|---|---|---|
| `geo_id` | VARCHAR | ISO 3166-2, e.g. `BR-SP` |
| `country_iso2` | VARCHAR | `BR` |
| `subregion` | VARCHAR | UF two-letter `SP` — **= `rais.sigla_uf`, `salic.UF`, `lpg.uf`** (join key) |
| `metric_id` | VARCHAR | e.g. `usage_pct` (51 distinct) |
| `value` | DOUBLE | metric value (May window) |
| `date_start`, `date_end` | DATE | `2026-05-01` / `2026-06-01` |

## Headline read (May window)

`usage_pct` by UF: **SP 37.8%**, RJ 9.4%, MG 7.9%, PR 6.3%, SC 5.6%, RS 5.0%, then a long tail. Per capita (share ÷ population share): DF 2.15, SP 1.72, SC 1.49, RJ 1.18 above the national line; the North/Northeast (PA, MA, PI) well below. AI use concentrates in the Southeast/South — the **Rouanet geography**, not the population-spread PNAB one.

## Scope and extension

`COUNTRIES = ["BR"]` in the ETL — the load-bearing scope per the corpus accretion criterion (`_atana_intel/phase6_corpus_criterion_and_vol2_scoping.md`). The release carries subregions for 130+ countries (US 52, JP 33, MX 25, CO 18, AR 13, CL 6, CR 3…). To extend to LATAM UFs/provinces, widen `COUNTRIES` and rerun — no other change; the table name already generalises.

## Caveats (foregrounded)

1. **Usage ≠ exposure ≠ automation risk.** Same lens caveat as the AEI country tables — a subregion's `usage_pct` is its share of a *selected population* (Claude.ai users), not a measure of exposure or displacement risk.
2. **24 of 27 UFs.** AC, AP and RR are **not** in the June subregion release for Brazil (below the sampling threshold). Absence is not zero.
3. **May 2026 window only.** The April window (`date_end = 2026-05-01`) is dropped for consistency with the country tables.
4. **`usage_pct` is a within-country share**, not a per-capita rate. Divide by population share (as the map does) to read over/under-indexing.
5. **Refresh** is a DB-updater job: `anthropic_eei__to_parquet.py --refresh` re-pulls the shared `_source` CSV; this script re-reads it. AEI updates ~quarterly.

## Crosswalk

No new `domain_crosswalk` row — this is an additional geography of the existing `anthropic_eei`→(transversal, revealed-use ★) frame, not a new source. FCS coverage unchanged (13/14).

## Consumers

- `atana_site/data_uf_ai.json` (via `scripts/build_uf_ai_dataset.py`, `fetch_ai()`) → the `/data/brasil-ia/` map.
- The brasil-ia Note ("AI use is a Rouanet geography") pairing with Notes #11 / #21 / #29.
