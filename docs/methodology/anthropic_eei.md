# `atana.anthropic_eei` — Anthropic Economic Index (revealed-usage frame)

> **Status (2026-06-30):** GitHub ❌ pending push — Phase 6b.2 in-place refresh built locally · MotherDuck sync pending · 4 tables in `raw/anthropic_eei/`. Row counts change per refresh — see §2 for May 2026 window.

> Methodology note. Phase 6b.1 ingested 2026-06-10 (release_2026_03_24). **Phase 6b.2 refresh 2026-06-30** to release_2026_06_26 ("Cadences" report, April-May 2026 monthly aggregates). ETL: `etl/anthropic_eei__to_parquet.py`.
> Accretion-criterion gate 1: Vol 2 minimum corpus (`phase6_corpus_criterion_and_vol2_scoping.md` §3).
> **Consumed by:** Atana Index Vol 2 (the two-epistemology exposure read) · Note #18 (published — the OECD × AEI pairing anchor).

## 1. What the source is

The **Anthropic Economic Index (AEI)** is Anthropic's open dataset on how Claude is
actually used: real (privacy-preserved) Claude.ai conversations classified onto
O*NET tasks, collaboration patterns, and geographies. Published on Hugging Face
(`Anthropic/EconomicIndex`), quarterly releases 2025-02 → 2026-06. It is the corpus's
first **revealed-usage** lens on the AI-and-work question — the empirical
counterpart to `atana.oecd_ai`'s **expert-rated** capability frame. Same question,
opposite epistemologies; their divergence is the finding (house style, Note #18).

### 1.1 Phase 6b.2 refresh (2026-06-30) — schema migration in-place

The June 2026 release ("Cadences" report) is a **schema rewrite**, not a drop-in
refresh. The ETL was migrated in Phase 6b.2 to consume the new long-format schema
while preserving the corpus's 4-table shape for downstream analytical continuity
(Note #18 published, Análise 6, Atana Index Vol 1). Six specific migrations:

1. **Wide → long format** — March had `variable`/`facet`/`cluster_name` columns; June has `category_name`/`hierarchy_level`/`metric_id`/`node_name`/`value`.
2. **ISO-2 → ISO-3 country codes** — March had `BR`/`MX`; June has `BRA`/`MEX`. The ETL maps back to ISO-2 for the 7 corpus geos + `CHL` (Phase 7a groundwork) via `ISO3_TO_ISO2`; the wider country universe keeps ISO-3 in a new `geo_id_iso3` column.
3. **Count columns dropped** — Anthropic no longer publishes `usage_count`/`task_count`/`collaboration_count`. Kept in schema as NULL for continuity. Do not sum NULLs.
4. **Collaboration expanded** — March had 2 buckets (automation, augmentation); June has those PLUS 6 pattern splits (directive / feedback_loop / task_iteration / learning / validation / none). Path B (this refresh) keeps only the 2 buckets; the 6 patterns are **Phase 6b.3**.
5. **Weekly → monthly aggregates** — March vintage was 2026-02-05 → 02-12 (one week). June vintage is April 2026 and May 2026 monthly aggregates. ETL uses **May** (`date_end='2026-06-01'`) as primary.
6. **Subregion published for the first time** — 24 Brazilian UFs (BR-SP, BR-RJ, BR-MG, BR-BA, BR-RS, BR-PR, BR-SC, BR-GO, BR-PE, BR-CE, BR-DF, BR-AM, BR-MT, BR-MS, BR-PA, BR-PB, BR-MA, BR-RO, BR-ES, BR-TO, BR-SE, BR-AL, BR-PI, BR-RN) are in the release. Ingest deferred to Phase 6b.3.

## 2. Tables (Tier 1 — 4 tables)

| Table | Rows (Jun 2026) | Vintage | What |
|---|---:|---|---|
| `country_usage` | ~180 | May 2026 monthly | Share of global Claude.ai usage by country (ISO-2, with ISO-3 sidecar). `usage_count` NULL. BR share now measured over the May 2026 monthly window, not the Feb 2026 week — do not compare directly to Phase 6b.1 numbers. |
| `task_usage_by_country` | ~4,000-6,000 | May 2026 monthly | Leaf-level O*NET-task usage (`hierarchy_level=0`, `metric_id='pct'`) for GLOBAL, US and the five corpus countries. `task_count` NULL. Node label is the exact O*NET task statement. |
| `collaboration_by_country` | 14 (7 geos × 2 buckets) | May 2026 monthly | Automation / augmentation buckets by geo. `n` NULL. The 6 new pattern splits deferred to Phase 6b.3. |
| `occupation_usage_global_v2` | 749 | global v2 (early 2025) | **DERIVED** — unchanged. Static across refreshes; the release_2025_03_27 source files are stable. |

### 2.1 The March → June continuity break

The Phase 6b.1 vintage was a single February 2026 week, ~9M measured
conversations. The Phase 6b.2 vintage is a full May 2026 month with a broader
Claude.ai population (includes Cowork plans introduced during Q2 2026).
**BR's usage_pct value will shift**; historical continuity is possible only
by holding aside the Phase 6b.1 parquets under `raw/anthropic_eei/_archive/`
if downstream analyses (Note #18) need the March values as-cited. If yes,
document at the parquet level not by rerunning `--refresh`.

### The derivation in `occupation_usage_global_v2`

Anthropic publishes task-level shares (`task_pct_v2`) but not an occupation table;
the occupation view is built here by joining task shares to O*NET task statements
(lowercased-text match) and **apportioning each task's share equally across the
occupations that share its statement**. The equal apportionment is an **Atana
methodological choice**, not an Anthropic figure — alternatives (employment-weighted
apportionment, primary-occupation assignment) would shift individual occupations.
98.22 % of published task share matches a statement; the residual is unmatched text
('not_classified', 'none', wording drift).

## 3. Headline probe findings (2026-06-10, scouting grade)

- **Cultural occupations (SOC 27-\*) = 9.41 %** of all occupation-matched global
  Claude usage. Top: Technical Writers (1.35), Actors (1.04 — see caveat 5),
  Copy Writers (0.92), Interpreters & Translators (0.89), Editors (0.84),
  Poets/Lyricists/Creative Writers (0.73). **This 9.41 % is a *global* figure** —
  the occupation table is global v2; Brazil has *task-level* revealed use only
  (`geo_id='BR'`), not occupation-level, until the 6b.2 CBO↔SOC crosswalk. It must
  not be read as a Brazilian share (caveat 2 selection bias applies in full).
- **Brazil's collaboration mix is more automation-leaning than global:** directive
  35.0 % (global 32.6), task iteration 29.9 (25.6), **learning 16.7 (22.4)** —
  Brazil uses Claude more to *do* and less to *learn* than the global average.
- Brazil's top classified tasks are software-modification and **culture-adjacent
  writing tasks** (copy editing; "develop themes, plots, characterizations…";
  advertising copy) — direct empirical contact with the Análise 17–20 ground.

## 4. Central caveats

1. **Usage ≠ exposure ≠ automation risk.** The AEI measures what people do with
   one AI product. OECD No. 59 rates what AI *could* do. Different constructs —
   pair them, never substitute one for the other.
2. **Selected population.** Claude.ai users skew toward coding, writing, English,
   higher-income geographies. Country shares confound adoption with population
   and with product availability.
3. **Vintage mismatch across tables** — occupation table is global v2 (early
   2025); country tables are one week of Feb 2026. Do not join across vintages
   without saying so.
4. **`not_classified` is large** (25.8 % of Brazil's task rows) — task-level
   percentages are shares of a partially classified whole.
5. **Task-statement matching produces artifacts** — e.g. Actors ranks high partly
   because actor task statements ("study and rehearse roles from scripts…") match
   general text-work; treat single-occupation readings with care, families
   (27-3 media/communication vs 27-1 art/design) are more robust.
6. **The full occupation-level OECD pairing is gated** on an `oecd_ai` Tier 2
   ingest (Paper No. 59's occupation tables — currently headlines only). Logged
   as a Vol 2 input; the §3 findings are scouting until then.
7. **Quarterly-ish releases** — refresh via `--refresh` is a DB-updater job;
   the schema is vintage-aware by table.

## 5. Crosswalk

`canonical.domain_crosswalk` 90 → **91 rows**: one `anthropic_eei` row →
*Intellectual property* (transversal), ★-flagged as a methodological frame, same
anchor and same cross-sector caveat as the `oecd_ai` row. FCS coverage meter
unchanged at 13/14.

## 6. Citation

> Anthropic. *The Anthropic Economic Index.* Hugging Face dataset
> `Anthropic/EconomicIndex`, releases 2025-02-10 → 2026-03-24.
> https://huggingface.co/datasets/Anthropic/EconomicIndex
> Derived occupation table: Atana, `atana-data`, CC BY 4.0 (derivation §2).

---

*Pairs with `oecd_ai_papers.md` (the expert-rated frame) and the Phase 6 scoping
memo. Phase 6b.2 (CBO 2002 ↔ ISCO-08 ↔ SOC crosswalk, for the RAIS join) remains
a separately checkpointed candidate — its urgency is reduced but not eliminated by
the Brazil-native task rows (occupation-level Brazilian usage still needs it).*
