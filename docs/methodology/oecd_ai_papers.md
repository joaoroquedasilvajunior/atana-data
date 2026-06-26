# OECD AI Papers — methodological frame for the Atana AI Exposure Index

> **Status (2026-06-26):** Sandbox-side ⏳ built · GitHub ❌ pending push · MotherDuck ❌ pending sync — 6 tables / 57 rows in `raw/oecd_ai/`.
>
> **Extension (2026-06-26 — Phase 5d Tier 2):** added three PDF-extracted occupation-level tables from No. 59 chapter 6: `occupations_creativity_distance` (10 rows × Table 6.4a), `exposure_extremes_ranking` (20 rows × Table 6.5), `felten_oecd_correlations` (10 rows × Table 6.6). The Path A (full 770-880-row OECD per-occupation CSV from oecd.ai) remains pending — JS-rendered, blocked from sandbox fetch; scoping memo `_atana_intel/scoping_oecd_no59_occupations_2026-06-26.md`.
>
> **Extension (2026-06-22):** added `skill_demand_high_exposure` (6 rows) carrying No. 59's demand-side findings — originality demand in high-AI-exposure vacancies rose 25% → 33% (the cognitive sub-skill rising fastest). It is the OECD/expert corner of the three-corner creativity read (OECD demand × `anthropic_eei` revealed use × `rais` wages).

**Schema:** `atana.oecd_ai` · **Tables:** 6 · **Rows:** 57 · **Ingested:** 2026-06-04 (Phase 5c) · **Extended:** 2026-06-22 (Tier 1+) and 2026-06-26 (Tier 2)

The OECD's *Artificial Intelligence Papers* series (OECD-OPSI) publishes short, methodology-rich papers framing the public-sector AI conversation across OECD members. This schema captures Tier 1 — headline framing — of two papers the Atana AI Exposure Index (Vol. 1) and the upcoming Vol. 2 directly triangulate against.

## §1. Why this schema exists

The Atana AI Exposure Index (introduced in *Atana_Index_Vol1.html* §3) is a country-level composite. Its credibility depends on being readable against external methodologies. Two May-June 2026 OECD papers give it exactly that backbone:

- **Paper No. 59** — *The OECD AI exposure measure: Mapping the OECD AI Capability Indicators to occupations* (May 2026, 58 pp). Defines **9 AI capability domains** (Language, Social interaction, Problem solving, Creativity, Metacognition/critical thinking, Knowledge/learning/memory, Vision, Manipulation, Robotic intelligence), scores AI's current capability against occupational requirements, and ranks OECD-member labour markets on an *AI Capability Gap Index*. Critically for Atana, **creativity** is one of the 9 domains — explicitly, not as residual. Caveat from chapter 6 of the paper: level 5 of the creativity scale captures exceptional/world-class creativity rarely required of whole occupations, which compresses the active range — the small measured creativity gap (0.1 average across major groups) is partly artifactual. Cultural-trade value disproportionately driven by level-5 creativity is precisely what No. 59 acknowledges it cannot fully capture — the methodological space Atana operates in.

- **Paper No. 60** — *Benefits of AI Openness* (3 Jun 2026, 46 pp; G7 discussion paper at the French presidency's request). Three structural findings: (i) open models reach ~90 % of closed performance at substantially lower cost, (ii) open-source AI activity has a positive significant correlation with growth across 33 countries, (iii) AI openness shifts value capture downstream — to SMEs, public institutions, and creators.

Together, with the Stanford HAI Foundation Model Transparency Index (58 → 40 between editions), the three sources form a methodological three-corner frame for Atana Index Vol. 2: **exposure × openness × transparency**.

## §2. Tables

### `papers_headline` (2 rows × 2026)

One row per paper. Columns: `paper_no`, `title`, `date_published`, `pages`, `headline_finding_{1,2,3}`, `atana_relevance`, `source_url`, `notes`.

The three headline findings per paper are publicly cited from the OECD landing page and the press write-ups; the `atana_relevance` column situates each paper in the Atana corpus (Vol. 1 framework, Vol. 2 triangulation lens).

### `ai_capability_domains` (9 rows × Paper No. 59)

One row per capability domain, with the OECD's domain label, a short description, and the `atana_relevance` flag. The **creativity** row is marked ★ — it is the direct entry-point into LATAM cultural occupations via the CBO crosswalk (musicians, designers, artists). The remaining 9 domains (language, social interaction, problem solving, metacognition/critical thinking, knowledge, learning/memory, vision, manipulation, robotic intelligence) all have secondary cultural-occupation reads (e.g., social interaction → performing arts and cultural mediation; manipulation → crafts and instrument-making).

### `skill_demand_high_exposure` (6 rows × Paper No. 59, demand side)

Added 2026-06-22. Where `ai_capability_domains` carries the **supply/capability** side of No. 59 (what AI can do, with creativity compressed at level 5), this table carries the **demand** side: the share of vacancies *in high-AI-exposure occupations* that require each skill group, and how that demand shifted between the measure's base and end years. Columns: `paper_no`, `skill_group`, `metric`, `value_pct`, `qualifier` (`exact` | `floor`), `atana_relevance`, `source_url`.

The two ★ rows are the headline: demand for **originality**-related skills in high-exposure vacancies rose from **25% to 33%** — the cognitive sub-skill with the *greatest* rise. The other rows give the surrounding demand profile (management 72%, business processes 67%, social/emotional and digital each "over 50%", stored as a floor of 50 with `qualifier='floor'`).

This is the analytic point of the extension. No. 59's *capability* scale underweights creativity (the level-5 artefact); No. 59's *demand* data shows employers asking for more originality precisely where AI exposure is highest. Even within one OECD measure the two sides pull against each other — and that internal tension is the OECD/expert corner of Atana's three-corner creativity read against `anthropic_eei` (revealed AI use, most-cultural in Brazil) and `rais` (creative wages falling).

**Tier / caveat:** Tier 1 headline shares. The base/end **years** and the full per-skill series live in the PDF body (Tier 2, Vol. 2 input). The 25%→33% figure is OECD-wide vacancy data across the measure's country sample, not Brazil-specific and not the same construct as the FCS creative-domain spine — it is a demand signal for a *skill*, used in conjunction with the Brazilian lenses, not as a substitute for them.

### `occupations_creativity_distance` (10 rows × Table 6.4a, Tier 2)

Added 2026-06-26. The Creativity-column top-10 of No. 59 Table 6.4a — occupations with the LARGEST Creativity capability gap (AI furthest from being able to perform). **8 of 10 are SOC group 27 cultural occupations**: Music Directors and Composers · Choreographers · Special Effects Artists and Animators · Producers and Directors · Art Directors · Multimedia Artists and Animators · Set and Exhibit Designers · Fashion / Interior Designers. The other 2 are cultural-adjacent (Architects, Architecture and Engineering Teachers).

**Why this matters.** The OECD paper's prose (page 31) names the Language column verbatim but does NOT name the cultural occupations in the Creativity column — they had to be transcribed by visual read of the page-32 PNG render (markitdown / pdfplumber / pymupdf all failed because the table is image-embedded in the PDF). This table is therefore the **occupation-weighted empirical anchor of the Atana Authenticity Paradox**: where Atana's trade-weighted measure (Notes #06, #08, Análise 6) shows cultural exports holding value at the artisanal pole, OECD's occupation-weighted measure shows AI capability is furthest from the cultural cluster precisely on the Creativity dimension. Two methods, one finding.

Columns: `paper_no`, `table_id`, `domain`, `rank`, `soc_major_group_code`, `soc_major_group_label`, `occupation_title`, `is_soc27_cultural`, `atana_relevance_flag` (★ cultural / ☆ cultural-adjacent), `notes`, `source_url`.

### `exposure_extremes_ranking` (20 rows × Table 6.5, Tier 2)

Added 2026-06-26. The overall AI exposure ranking from No. 59 Table 6.5 — top-10 most exposed (smallest composite gap) + top-10 least exposed (largest composite gap). The most-exposed tail is dominated by clerical work (Billing/Bookkeeping/Data Entry, SOC group 43, tied at 0.00 gap); the least-exposed tail by chief executives (gap 11.71), medical specialists, firefighters / police, and **lawyers (9.53) and judges (9.53)** — the last two being the most dramatic Felten × OECD disagreements (Felten places them at #67 and #6 most-exposed; OECD at #5 and #6 least-exposed).

**Zero SOC group 27 cultural occupations appear in EITHER tail.** The cultural cluster sits at the middle of the distribution (Table 6.3 reports group 27 total gap = 4.2) despite dominating the Creativity column. **This is the structural argument for the Atana per-domain decomposition over composite-only reading:** the cultural cluster has one extreme score (creativity) that gets diluted by 8 other domains in the composite, hiding the finding that matters.

Columns: `paper_no`, `table_id`, `tail` (`most_exposed` | `least_exposed`), `rank`, `soc_major_group_code`, `occupation_title`, `total_capability_gap`, `is_soc27_cultural`, `notes`, `source_url`.

### `felten_oecd_correlations` (10 rows × Table 6.6, Tier 2)

Added 2026-06-26. Per-domain correlations between Felten et al.'s widely-cited *AI Occupational Exposure* measure and OECD's Capability Gap Index across the 610 matched occupations. The **headline correlation is only 0.34** — the two are formally different measures, not interchangeable. The diagnostic outlier is **Creativity (0.25)**: Felten recognises WHEN an occupation is creative but cannot tell WHETHER AI can do it. The "demand" column (`corr_felten_oecd_demand`) clarifies this — 0.61 on Creativity vs OECD demands, but only 0.25 vs OECD gap. Vision / Manipulation / Robotic intelligence carry NEGATIVE correlations (−0.58 to −0.77) — Felten was language-centred and structurally misses physical-domain exposure.

**This is the empirical proof Felten is creativity-blind and physical-domain-blind**, which sits at the centre of the Atana Note #18 methodological argument: a single composite AI exposure number cannot do what the OECD per-domain construction does, and most published exposure measures (Felten among them) are creativity-blind by design.

Columns: `paper_no`, `table_id`, `domain_key`, `domain_label`, `is_composite`, `corr_felten_oecd_gap`, `corr_felten_oecd_demand`, `atana_relevance_note`, `source_url`.

## §3. What this schema is NOT

- **Not** an AI exposure score for LATAM countries. The papers measure OECD labour markets directly; LATAM is not in the analytical scope of either paper.
- **Not** a cultural classification. The OECD AI capability framework is sector-agnostic; the **creativity** domain is one of 10, not a cultural-domain spine. This is why `canonical.domain_crosswalk` maps the schema to FCS *Intellectual property* (the AI-IP frontier) with `approximate` confidence and a ★ note.
- **Not** the underlying microdata. Paper No. 59's occupation-level scores and Paper No. 60's 33-country growth-correlation dataset are not in this ingest — they are Tier 2 (PDF and supplementary tables).

## §4. Atana use

- **Index Vol. 1** — Paper No. 59 gives an OECD-grade exposure framework with an explicit creativity domain. Vol. 1 should cite §3 of the Atana publication against No. 59's capability domain list; the Index's *AI Exposure Index* is consistent with No. 59 in scope but uses UNCTAD creative trade as its denominator (an Atana methodological choice).
- **Index Vol. 2** — the three-corner frame (No. 59 exposure × No. 60 openness × HAI 2026 transparency) is the methodological backbone we propose for Vol. 2's revisited country scoring.
- **Análise 20 follow-up** — No. 60's openness-shifts-value-downstream finding is the closest external evidence to scenario **D** (Economia Agêntica Completa) and partly to **B** (Licenciamento Coletivo BR via ECAD-AI); it does not bear on **A** (Status Quo Acelerado), which dominates probability mass.
- **Atana Note candidate** — the AI Openness × Foundation Model Transparency Index counter-trajectory (openness rising, transparency falling) is the structural shape behind the briefing's flagged "AI sandwich" piece.

## §5. Sources

- Paper No. 59 landing page: <https://www.oecd.org/en/publications/2026/05/the-oecd-ai-exposure-measure_489cfd42.html>
- Paper No. 60 landing page: <https://www.oecd.org/en/publications/benefits-of-ai-openness_746e8c9a-en.html>
- OECD-OPSI AI Papers series: <https://oecd.ai/en/papers>

## §6. Caveats

- v1 is Tier 1 only — headline framings transcribed inline. Full-PDF extraction (the underlying capability score tables and the 33-country dataset) is Tier 2 work, currently not scheduled.
- The `creativity` domain in OECD No. 59 is defined functionally ("production of novel and valuable outputs"); it is *not* the same construct as the FCS creative-domain spine. Mapping is at the methodological-frame level, not classification-equivalence level.
- OECD AI capability scoring updates roughly annually; this schema should be rotated when No. 59's successor paper drops. (Curious Scientist monitors.)

## §7. Crosswalk position

`canonical.domain_crosswalk` → 1 row: `oecd_ai / ai-exposure-frame → Intellectual property (transversal, approximate)`, ★-flagged as methodological frame. FCS coverage meter unchanged at 13/14 (only *Intangible cultural heritage* remains unreached, by scope decision).
