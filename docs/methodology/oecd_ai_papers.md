# OECD AI Papers — methodological frame for the Atana AI Exposure Index

**Schema:** `atana.oecd_ai` · **Tables:** 2 · **Rows:** 12 · **Ingested:** 2026-06-04 (Phase 5c)

The OECD's *Artificial Intelligence Papers* series (OECD-OPSI) publishes short, methodology-rich papers framing the public-sector AI conversation across OECD members. This schema captures Tier 1 — headline framing — of two papers the Atana AI Exposure Index (Vol. 1) and the upcoming Vol. 2 directly triangulate against.

## §1. Why this schema exists

The Atana AI Exposure Index (introduced in *Atana_Index_Vol1.html* §3) is a country-level composite. Its credibility depends on being readable against external methodologies. Two May-June 2026 OECD papers give it exactly that backbone:

- **Paper No. 59** — *The OECD AI exposure measure: Mapping the OECD AI Capability Indicators to occupations* (May 2026, 58 pp). Defines 10 AI capability domains, scores AI's current capability against occupational requirements, and ranks OECD-member labour markets on an *AI Capability Gap Index*. Critically for Atana, **creativity** is one of the 10 domains — explicitly, not as residual.

- **Paper No. 60** — *Benefits of AI Openness* (3 Jun 2026, 46 pp; G7 discussion paper at the French presidency's request). Three structural findings: (i) open models reach ~90 % of closed performance at substantially lower cost, (ii) open-source AI activity has a positive significant correlation with growth across 33 countries, (iii) AI openness shifts value capture downstream — to SMEs, public institutions, and creators.

Together, with the Stanford HAI Foundation Model Transparency Index (58 → 40 between editions), the three sources form a methodological three-corner frame for Atana Index Vol. 2: **exposure × openness × transparency**.

## §2. Tables

### `papers_headline` (2 rows × 2026)

One row per paper. Columns: `paper_no`, `title`, `date_published`, `pages`, `headline_finding_{1,2,3}`, `atana_relevance`, `source_url`, `notes`.

The three headline findings per paper are publicly cited from the OECD landing page and the press write-ups; the `atana_relevance` column situates each paper in the Atana corpus (Vol. 1 framework, Vol. 2 triangulation lens).

### `ai_capability_domains` (10 rows × Paper No. 59)

One row per capability domain, with the OECD's domain label, a short description, and the `atana_relevance` flag. The **creativity** row is marked ★ — it is the direct entry-point into LATAM cultural occupations via the CBO crosswalk (musicians, designers, artists). The remaining 9 domains (language, social interaction, problem solving, metacognition/critical thinking, knowledge, learning/memory, vision, manipulation, robotic intelligence) all have secondary cultural-occupation reads (e.g., social interaction → performing arts and cultural mediation; manipulation → crafts and instrument-making).

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
