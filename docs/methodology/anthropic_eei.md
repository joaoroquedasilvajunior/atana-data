# `atana.anthropic_eei` — Anthropic Economic Index (revealed-usage frame)

> **Status (2026-06-14):** GitHub ✅ `9d435b3` on origin/main · MotherDuck ⏳ pending first sync · 4 tables / 6,290 rows in `raw/anthropic_eei/`

> Methodology note. Phase 6b.1, ingested 2026-06-10. ETL: `etl/anthropic_eei__to_parquet.py`.
> Accretion-criterion gate 1: Vol 2 minimum corpus (`phase6_corpus_criterion_and_vol2_scoping.md` §3).
> **Consumed by:** Atana Index Vol 2 (the two-epistemology exposure read) · candidate method Note (pairing with `atana.oecd_ai`, cf. Note #18).

## 1. What the source is

The **Anthropic Economic Index (AEI)** is Anthropic's open dataset on how Claude is
actually used: real (privacy-preserved) Claude.ai conversations classified onto
O*NET tasks, collaboration patterns, and geographies. Published on Hugging Face
(`Anthropic/EconomicIndex`), five releases 2025-02 → 2026-03. It is the corpus's
first **revealed-usage** lens on the AI-and-work question — the empirical
counterpart to `atana.oecd_ai`'s **expert-rated** capability frame. Same question,
opposite epistemologies; their divergence is the finding (house style, Note #18).

## 2. Tables (Tier 1 — 4 tables)

| Table | Rows | Vintage | What |
|---|---:|---|---|
| `country_usage` | 178 | week of 2026-02-05→12 | Share of global Claude.ai usage by country (ISO-2). **BR = 2.5548 %** of global. |
| `task_usage_by_country` | 5,321 | week of 2026-02-05→12 | O*NET-task usage (count + pct) for GLOBAL, US and the five corpus countries. **Brazil-native revealed usage — 269 tasks** — verified at probe time; the projection caveat of any US→BR mapping does *not* apply to these rows. |
| `collaboration_by_country` | 42 | week of 2026-02-05→12 | Collaboration patterns (directive / task iteration / learning / feedback loop / validation) by geo — the automation-vs-augmentation family. |
| `occupation_usage_global_v2` | 749 | global v2 (early 2025) | **DERIVED** — global usage share by O*NET-SOC occupation. |

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
  Poets/Lyricists/Creative Writers (0.73).
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
