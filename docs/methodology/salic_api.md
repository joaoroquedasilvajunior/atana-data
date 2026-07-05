# `atana.salic` — Lei Rouanet Microdata (SALIC API)

> **Status (2026-07-05):** GitHub ✅ `4e48176` on origin/main · MotherDuck ✅ live · 6 tables in `raw/salic/`. Coverage state audit 2026-07-05 revealed the canonical count is **48,189 projects** in `projetos` (not 26,203 as previously documented — that figure was `projetos_v2`, the legacy filtered subset). See §1 for the reframe.

> Methodology note. Phase 2 (foundational corpus). ETL: `etl/salic__bulk_download.py` + `etl/salic__jsonl_to_parquet.py`.
> **Consumed by:** Análise 7 *Sondagem da API SALIC* · Análise 8 *Anatomia de R$ 35,1 bilhões — a Lei Rouanet em 9 atos* (the corpus's culture-fomento anchor) · Análise 19 (Funk e sertanejo) · Análise 25 (Design & software 4-lens) · Note #21.

## 1. What the source is

The **SALIC** is the *Sistema de Apoio às Leis de Incentivo à Cultura* — the MinC's authoritative microdata system for the **Lei Rouanet** (Lei nº 8.313/91), Brazil's main federal cultural-incentive law. SALIC exposes a public REST API at `api.salic.cultura.gov.br/api/v1`.

`atana.salic` is a **bulk-downloaded corpus of every PRONAC project, every proponent, every incentivador (donor), and the per-project execution graph** — **48,189 projects, 2019–2026, ≈85 % of the universe of approved Rouanet projects in the ingest window** (canonical table `projetos`). The 2019–2022 window has been re-refreshed multiple times; the most recent refresh (13/06/2026, commit `4e48176`) re-pulled 2023+ data through the Bright Data + FlareSolverr WAF bypass after the SALIC portal's anti-bot defenses tightened.

The schema is the empirical engine of the SALIC analyses: the 9-act narrative of Análise 8 (33 years, R$ 35.1 bn), the 6-piste sondagem of Análise 7, and the Rouanet leg of Note #21 all run directly against this corpus.

### 1.1 Coverage state clarification (2026-07-05 audit)

Prior versions of this document, of the manifest, of `CLAUDE.md`, of Análise 7 (§1), and of the atana.studio /data/ page all cited SALIC coverage as **26,203 projects, ~46 % of universe**. That figure was the count of `projetos_v2` — a stricter historical subset used as the "canonical clean" table pre-June 2026. The actual live `projetos` table has been at **48,189 projects since commit `4e48176` (2026-06-13)** and MotherDuck has both tables unified at 48,189 (only GitHub's `projetos_v2.parquet` still holds the legacy 26k snapshot as a compat artifact).

**Canonical citation going forward:** 48,189 projects, ~85 % of universe. `projetos_v2` is documented as a legacy compat table; new analyses should query `projetos`. Published Notes and Análises (as of publication date) that cite the earlier 26,203 / 46 % are correct at time of writing — no retroactive rewrite; new work uses the fuller state.

**Year distribution of the 48,189:** 2019: 3,150 · 2020: 4,394 · 2021: 2,320 · 2022: 2,346 · 2023: 9,436 · 2024: 10,388 · 2025: 13,197 · 2026 (partial): 2,958.

## 2. Tables (6 tables)

| Table | Rows | What |
|---|---:|---|
| **`projetos`** *(canonical)* | **48,189** | The canonical project table — one row per PRONAC. Carries the headline financials (`aprovado`, `captado`, `taxa_captacao`), classification (`area`, `segmento`, `mecanismo` Art. 18 vs Art. 26), geography (`uf_proponente`, `municipio_proponente`), and life-cycle (`situacao`, `data_termino`, `data_inicio`, `valor_aprovado`, `valor_captado`, `local_realizacao`). ~85 % of universe 2019–2026. |
| `projetos_v2` *(legacy compat)* | 26,203 on GitHub · 48,189 on MotherDuck | Legacy "canonical clean" subset — pre-June 2026 filter, kept for backward compatibility with published analyses (Análise 7 §1, Note #21). Superseded by `projetos`; new work should not depend on it. GitHub / MotherDuck divergence documented in §3 below. |
| `edges_pronac_incent` | 8,504 | The donor-graph edges — one row per (incentivador × PRONAC) tuple. Powers the "Itaú is in 38 % of the top-100 PRONACs" finding of Análise 7, and the Análise 19 doador-by-genre cross. ⚠️ Parquet currently missing from local storage — table exists on MotherDuck. See §3 W8. |
| `corporate_canon` | 5,735 | Canonical-form mapping for donor companies — multiple razões sociais per economic group (Itaú has 24 distinct entities in SALIC; this table collapses them). The canonicalisation is hand-curated and reviewed quarterly. |
| `edges_incentivador` | 8,504 | Incentivador-level aggregation — one row per incentivador entity, with cumulative R$ donated and PRONAC count. |
| `cycle_status_map` | 67 | Status-flow map — the ATTRition funnel from `aprovacao` to `captacao` to `execucao` (per Análise 7 §2 — the canonical 4-stage funnel). |

Bonus table not in the primary six but present in `raw/salic/`:

| Table | Rows / size | What |
|---|---:|---|
| `propostas_recentes` | 13.3 MB parquet, ~50k+ rows | Propostas (proposal-stage projects, prior to PRONAC assignment). Not currently used by any published Análise; available for future proposal-vs-approval funnel analyses. |

## 3. Methodology / ingest notes

- **ETL pattern:** `salic__bulk_download.py` orchestrates paginated API calls against the 8 endpoints, persisting raw JSONL into `raw/salic/_source/`. `salic__jsonl_to_parquet.py` then flattens to Parquet. Idempotent; byte-identical reruns when WAF behaviour is stable.
- **WAF bypass (v3.1):** as of June 2026, the SALIC portal sits behind a Cloudflare-tier defense that breaks naive `requests` calls. The bulk downloader uses Bright Data residential proxy + FlareSolverr challenge-solving. API hits are throttled to 1 req/sec; bulk runs take ~6 hours for a full refresh. **Both `api.salic.cultura.gov.br` and `dados.cultura.gov.br` are now Cloudflare-Turnstile-gated** (Phase 9 audit 2026-07-05; see `_atana_intel/phase9_dados_gov_salic_scoping.md`).
- **CNPJ:** SALIC carries CNPJ for both proponente PJ and incentivador. This enables direct CNPJ joins with `atana.rais` (after de-canonicalisation), and is the only Brazilian schema in the corpus carrying joinable CNPJ at scale.
- **Refresh cadence:** quarterly recommended; the 2026-06-13 refresh (commit `4e48176`) is the current vintage.
- **Canonical donor groups:** the `corporate_canon` table is curated, not derived — when a new donor enters the top-100, the canonical mapping needs a manual review pass.
- **`projetos` vs `projetos_v2` divergence:** on GitHub, `projetos.parquet` (48,189 rows) and `projetos_v2.parquet` (26,203 rows) are distinct; on MotherDuck, both tables return 48,189 rows. This is because a prior MotherDuck sync unified `projetos_v2` to the fuller `projetos` state without a matching GitHub push. Downstream queries against MotherDuck always resolve to 48k regardless of table name; local queries against the GitHub parquets differ. New analyses should query `projetos` in both environments to avoid the ambiguity.

## 4. Caveats (W1–W8)

| # | Alert |
|---|---|
| W1 | **The 48,189 projects = ~85 % of the universe** of approved Rouanet projects 2019–2026. The residual gap is dominated by projects in *aprovado* status with `cap=0` and `prazo` expired — formally approved but never captated. These cells may still be present in `projetos` but with sparse fields. **Prior version of this caveat cited 26,203 / 46 %** — that number reflected the legacy `projetos_v2` subset; see §1.1 for the coverage-state clarification. |
| W2 | **Self-cancellation by proponente** is not separately flagged — the `situacao` field collapses several termination reasons. For the bimodality narrative (50 % captated 0 %, 22 % captated ~100 %) this doesn't matter; for any analysis of *why* projects fail, look at the cycle_status_map for the explicit transitions. |
| W3 | **Genre / segmento classification is textual** — the segments inside `area = Música` (Música Popular Cantada, Erudita, Regional) are MinC labels applied by the parecerista at submission. Funk inside Música Popular Cantada has a vernacular cross-classification that the SALIC labels do not reliably carry — Análise 19 §3 does a textual-search proxy for genre (Funk / Sertanejo / Pagode mentions in título / ementa) that is *not* in the schema. The genre layer is Análise 19's, not SALIC's. |
| W4 | **Article 18 vs Article 26 mecanismo** flag is reliable and is the analytical engine of the +30.69 pp gap in Análise 8 §4 (Art. 18 confers 100 % deduction within 6 % of IR due; Art. 26 confers 30/40/40 % depending on genre). The Lei 14.568 reclassifications of 2023+ (Música Regional moved to Art. 18) are the cross-section experiment of Análise 8 §9. |
| W5 | **Incentivador identity is messy** — same economic group declares under multiple razões sociais; the `corporate_canon` table resolves this for top names but the tail is uncurated. Treat individual razão social counts as upper bounds, canonical counts as lower bounds. |
| W6 | **No worker / employment information** — SALIC is project-level. The labor implications of Rouanet are inferred via município × CNAE × ano joins with `atana.rais`; there is no direct PRONAC → employment record. |
| W7 | **2026 partial year** — the 2026 vintage at refresh time (June) is partial (2,958 records); growth comparisons across the full year aren't possible until end-of-year. The Período Lula (2023–2026) decomposition in Análise 8 §8 carries this caveat. |
| W8 | **`edges_pronac_incent.parquet` is not on disk locally** as of the 2026-07-05 audit. Only `edges_incentivador.parquet` (entity-level aggregation) is present in `raw/salic/`. The finer-grained per-project-per-donor edges (needed for the Itaú-in-38%-of-top-100 finding of Análise 7) exist on MotherDuck (`atana.salic.edges_pronac_incent`) but weren't checked into GitHub in the `4e48176` commit. Regenerate from `_source/edges_pronac_incent.jsonl` if source JSONL is recoverable, or export from MotherDuck if not, before the next full refresh cycle. |

## 5. References

- The **Data Context Skill** for SALIC lives at `.claude/skills/salic-api/` (SKILL.md, endpoints.md, key_findings_2026.md, recipes.md, warnings.md).
- Análise 7 (`analise_07_salic_api_sondagem.md`) — the field-mapping sondagem and 6 analytical leads.
- Análise 8 (`analise_08_salic_anatomia.md`) — the canonical 9-act narrative for the book; Vol. 2 of the academic paper sits inside §9.
- CLAUDE.md §9 (Análise 7 + 8 anchors) and the publication_pipeline tracker.
