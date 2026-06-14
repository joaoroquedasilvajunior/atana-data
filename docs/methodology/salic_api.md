# `atana.salic` — Lei Rouanet Microdata (SALIC API)

> **Status (2026-06-14):** GitHub ✅ `bc1c2e6` on origin/main · MotherDuck ✅ live · 6 tables / 91,698 rows in `raw/salic/`

> Methodology note. Phase 2 (foundational corpus). ETL: `etl/salic__bulk_download.py` + `etl/salic__jsonl_to_parquet.py`.
> **Consumed by:** Análise 7 *Sondagem da API SALIC* · Análise 8 *Anatomia de R$ 35,1 bilhões — a Lei Rouanet em 9 atos* (the corpus's culture-fomento anchor) · Análise 19 (Funk e sertanejo) · Análise 25 (Design & software 4-lens).

## 1. What the source is

The **SALIC** is the *Sistema de Apoio às Leis de Incentivo à Cultura* — the MinC's authoritative microdata system for the **Lei Rouanet** (Lei nº 8.313/91), Brazil's main federal cultural-incentive law. SALIC exposes a public REST API at `api.salic.cultura.gov.br/api/v1`.

`atana.salic` is a **bulk-downloaded corpus of every PRONAC project, every proponent, every incentivador (donor), and the per-project execution graph** — 26,203 projects, 2019–2026, ≈46 % of the universe of approved Rouanet projects in the ingest window. The 2019–2022 window has been re-refreshed multiple times; the most recent refresh (13/06/2026, commit `bc1c2e6`) re-pulled 2023+ data through the Bright Data + FlareSolverr WAF bypass after the SALIC portal's anti-bot defenses tightened.

The schema is the empirical engine of the SALIC analyses: the 9-act narrative of Análise 8 (33 years, R$ 35.1 bn) and the 6-piste sondagem of Análise 7 both run directly against this corpus.

## 2. Tables (6 tables)

| Table | What |
|---|---|
| `projetos_master` | The canonical project table — 26,203 rows, one per PRONAC. Carries the headline financials (`aprovado`, `captado`, `taxa_captacao`), classification (`area`, `segmento`, `mecanismo` Art. 18 vs Art. 26), geography (`uf_proponente`, `municipio_proponente`), and life-cycle (`situacao`, `data_aprovacao`). |
| `projetos_v2` | Re-pulled refresh of the project table including 2023+ corrections post-WAF — supersedes `projetos_master` for any pivot crossing 2023. |
| `edges_pronac_incent` | The donor-graph edges — 8,504 rows, one per (incentivador × PRONAC) tuple. Powers the "Itaú is in 38 % of the top-100 PRONACs" finding of Análise 7, and the Análise 19 doador-by-genre cross. |
| `corporate_canon` | Canonical-form mapping for donor companies — multiple razões sociais per economic group (Itaú has 24 distinct entities in SALIC; this table collapses them). The canonicalisation is hand-curated and reviewed quarterly. |
| `edges_incentivador` | Incentivador-level aggregation — one row per incentivador entity, with cumulative R$ donated and PRONAC count. |
| `cycle_status_map` | Status-flow map — the ATTRition funnel from `aprovacao` to `captacao` to `execucao` (per Análise 7 §2 — the canonical 4-stage funnel). |

## 3. Methodology / ingest notes

- **ETL pattern:** `salic__bulk_download.py` orchestrates paginated API calls against the 8 endpoints, persisting raw JSONL into `raw/salic/_source/`. `salic__jsonl_to_parquet.py` then flattens to Parquet. Idempotent; byte-identical reruns when WAF behaviour is stable.
- **WAF bypass (v3.1):** as of June 2026, the SALIC portal sits behind a Cloudflare-tier defense that breaks naive `requests` calls. The bulk downloader uses Bright Data residential proxy + FlareSolverr challenge-solving (see commit `bc1c2e6` and the methodology doc inline). API hits are throttled to 1 req/sec; bulk runs take ~6 hours for a full refresh.
- **CNPJ:** SALIC carries CNPJ for both proponente PJ and incentivador. This enables direct CNPJ joins with `atana.rais` (after de-canonicalisation), and is the only Brazilian schema in the corpus carrying joinable CNPJ at scale.
- **Refresh cadence:** quarterly recommended; the 2026-06-13 refresh is the current vintage.
- **Canonical donor groups:** the `corporate_canon` table is curated, not derived — when a new donor enters the top-100, the canonical mapping needs a manual review pass.

## 4. Caveats (W1–W7)

| # | Alert |
|---|---|
| W1 | **The 26,203 projects = 46 % of the universe** of approved Rouanet projects 2019–2026 (per Análise 7 §1 funnel). The gap is dominated by projects in *aprovado* status with `cap=0` and `prazo` expired — formally approved but never captated. These cells are present in the raw SALIC but were filtered as not analytically meaningful. |
| W2 | **Self-cancellation by proponente** is not separately flagged — the `situacao` field collapses several termination reasons. For the bimodality narrative (50 % captated 0 %, 22 % captated ~100 %) this doesn't matter; for any analysis of *why* projects fail, look at the cycle_status_map for the explicit transitions. |
| W3 | **Genre / segmento classification is textual** — the segments inside `area = Música` (Música Popular Cantada, Erudita, Regional) are MinC labels applied by the parecerista at submission. Funk inside Música Popular Cantada has a vernacular cross-classification that the SALIC labels do not reliably carry — Análise 19 §3 does a textual-search proxy for genre (Funk / Sertanejo / Pagode mentions in título / ementa) that is *not* in the schema. The genre layer is Análise 19's, not SALIC's. |
| W4 | **Article 18 vs Article 26 mecanismo** flag is reliable and is the analytical engine of the +30.69 pp gap in Análise 8 §4 (Art. 18 confers 100 % deduction within 6 % of IR due; Art. 26 confers 30/40/40 % depending on genre). The Lei 14.568 reclassifications of 2023+ (Música Regional moved to Art. 18) are the cross-section experiment of Análise 8 §9. |
| W5 | **Incentivador identity is messy** — same economic group declares under multiple razões sociais; the `corporate_canon` table resolves this for top names but the tail is uncurated. Treat individual razão social counts as upper bounds, canonical counts as lower bounds. |
| W6 | **No worker / employment information** — SALIC is project-level. The labor implications of Rouanet are inferred via município × CNAE × ano joins with `atana.rais`; there is no direct PRONAC → employment record. |
| W7 | **2026 partial year** — the 2026 vintage at refresh time (June) is partial; growth comparisons across the full year aren't possible until end-of-year. The Período Lula (2023–2026) decomposition in Análise 8 §8 carries this caveat. |

## 5. References

- The **Data Context Skill** for SALIC lives at `.claude/skills/salic-api/` (SKILL.md, endpoints.md, key_findings_2026.md, recipes.md, warnings.md).
- Análise 7 (`analise_07_salic_api_sondagem.md`) — the field-mapping sondagem and 6 analytical leads.
- Análise 8 (`analise_08_salic_anatomia.md`) — the canonical 9-act narrative for the book; Vol. 2 of the academic paper sits inside §9.
- CLAUDE.md §9 (Análise 7 + 8 anchors) and the publication_pipeline tracker.
