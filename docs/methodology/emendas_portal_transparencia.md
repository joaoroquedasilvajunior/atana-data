# atana.emendas — Portal da Transparência methodology

*Written 2026-07-19 with the Phase 11 Tier 1 ingest.*

## 1. Scope

`atana.emendas` registers the **fourth federal cultural-funding pipe** the
Atana corpus tracks — Emendas Parlamentares Federais executed as federal
contracts. It sits alongside:

- `atana.salic` — Lei Rouanet (indirect, fiscal renunciation)
- `atana.pnab` — Política Nacional Aldir Blanc (direct, generalist)
- `atana.lpg` — Lei Paulo Gustavo (direct, AV-specific)
- `atana.emendas` — Emendas Parlamentares (this schema)

The fourth pipe has a distinct architectural logic: parlamentar (deputado /
senador / bancada / comissão) discretion at the municipal-line level, executed
as federal transfers with the função-13 (Cultura) or adjacent budget code.

## 2. Tiering

**Tier 1 (this release) — headline scope.** Annual aggregates only, two scopes:

- `all_functions` — total emendas (all functions) — hand-transcribed from
  Agência Brasil (2023) and Gazeta do Povo (2024). Sizes the pipe as a whole:
  R$ 20,6 bi in 2023 → R$ 31,4 bi in 2024 (+52 %).
- `funcao_13_cultura` — subset filtered to Função 13. Placeholder rows
  registered 2018–2025; values populated when the Portal da Transparência
  API key is available and the ETL is rerun with `--refresh`.

**Tier 2 (deferred, ~3 sessions).** Full ingest per Phase 11 scoping §3:
`emendas_cultura` (≈200-350k rows), `emendas_por_parlamentar`,
`contratos_shows_federal` (elemento 33.90.39 + palavras culturais),
`inexigibilidade_cultura`, `cache_reference` sidecar. Trigger: Note #23 or
Vol 2 chapter kickoff. See `_atana_intel/phase11_emendas_scoping.md`.

## 3. Data access — API key requirement

**Endpoint.** `api.portaldatransparencia.gov.br/api-de-dados/emendas`

**Auth.** Free API key required. Signup:
[portaldatransparencia.gov.br/api-de-dados/cadastrar-email](https://portaldatransparencia.gov.br/api-de-dados/cadastrar-email)
(5 min via gov.br account). Header: `chave-api-dados: xxx`.

**Rate limit.** 30 req/min free tier. Full cultura pull (~2018-2025) budgets
~2-4 hours wall-clock at page-15 default.

**Sandbox status.** Not reachable from Atana's build sandbox — the ETL is
scaffolded and ready; João runs `--refresh` locally with the key exported.
Placeholder rows document the gap explicitly.

## 4. Tables

| Table | Rows | Grain |
|---|---:|---|
| `headlines_annual` | 10 (Tier 1) | (year × scope) |

Tier 2 will add: `emendas_cultura`, `emendas_por_parlamentar`,
`contratos_shows_federal`, `inexigibilidade_cultura`, `cache_reference`.

### `headlines_annual` schema (v2 — certification-driven, 2026-07-19)

| Column | Type | Notes |
|---|---|---|
| `year` | INT32 | 2018-2025 |
| `scope` | VARCHAR | `all_functions` \| `funcao_13_cultura` |
| `valor_empenhado_brl_mi` | DOUBLE | Committed. (v1 mis-named this `valor_autorizado` — the API has no `valorAutorizado` field.) |
| `valor_liquidado_brl_mi` | DOUBLE | Liquidated in-year. NULL for `all_functions`. |
| `valor_pago_ano_brl_mi` | DOUBLE | Paid **in-year** only. |
| `valor_resto_pago_brl_mi` | DOUBLE | Paid later via *restos a pagar*. |
| `valor_pago_total_brl_mi` | DOUBLE | **= pago_ano + resto_pago — the TRUE disbursement.** Use this for any execution-rate claim. |
| `n_linhas_execucao` | INT32 | Execution-line count. |
| `n_emendas_distintas` | INT32 | Distinct `codigoEmenda` (< lines: RP-9 relator emendas share the sentinel code `"REL. GERAL"`). |
| `source_page` | VARCHAR | citation |
| `notes` | VARCHAR | caveats |
| `fetch_date` | VARCHAR | ISO date |

**Why restos a pagar matter (certification C1 finding).** A typical cultural emenda commits in year Y and pays most of the money in Y+1/Y+2 through *restos a pagar*, not through in-year `valorPago`. Sample (2024, autor RICARDO BARROS): empenhado R$ 23.200, pago-no-ano R$ 734, restoPago R$ 22.466 — **97 % of the disbursement came via restos**. Reading in-year `valorPago` alone understates true payment roughly 5× and would produce a false "low execution" narrative. `valor_pago_total_brl_mi` is the honest disbursement figure.

## 5. Domain crosswalk mapping

Extends `canonical.domain_crosswalk` by one row (93 → 94):

| source_schema | source_code | fcs2025_domain | fcs2025_domain_type | mapping_confidence | notes |
|---|---|---|---|---|---|
| `emendas` | `funcao_13` | *Public funding* | Transversal (financing lens) | `good` | ★ Fourth federal cultural-funding pipe; parlamentar discretion at municipal grain. |

The FCS 2025 UNESCO framework does not have a dedicated "public funding"
transversal — Emendas map to the same lens Rouanet/PNAB/LPG cover (public
resources reaching cultural producers). The `notes` flag ★ signals it's a
lens-completion move, not new domain coverage.

## 6. Central caveats (foregrounded)

| # | Alert |
|---|---|
| E1 | **All-functions row is NOT cultura.** The R$ 31,4 bi 2024 headline covers all functions. Cultura subset requires Portal API key. Documented in the row `notes`. |
| E2 | **Cultura filter recall 70-85 %.** Even with the API, Função 13 misses Turismo (Função 23 sub 695) and Cidadania cultural sub-actions. Documented modeling choice. See scoping §2 for the expanded filter. |
| E3 | **Data lag.** Portal usually 3-6 months behind current execution. Any downstream analysis carries "as of DD/MM/YYYY" caveat. |
| E4 | **CNPJ ambiguity.** Same economic group appears under multiple razões sociais. Same canonicalization pattern as `atana.salic.corporate_canon`; Tier 2 will extend. |
| E5 | **Political sensitivity.** Every emenda has a parlamentar author. Publication of Note #23 or downstream analytics requires editorial review — sharper than Rouanet/PNAB/LPG. |
| E6 | **Tier 1 is scaffold + benchmark.** The cultura-specific numbers are NOT in the corpus yet. Analytical use of `funcao_13_cultura` rows must check `valor_autorizado_brl_mi IS NOT NULL` before consuming. |

## 7. Handoff — how João populates the Cultura rows

```bash
# 1. Sign up (once): portaldatransparencia.gov.br/api-de-dados/cadastrar-email
# 2. Verify the key works:
export PORTAL_TRANSPARENCIA_API_KEY=xxx
python3 _atana_intel/phase11_emendas_probe.py

# 3. Populate cultura rows + push to MotherDuck:
cd atana-data
python3 etl/emendas__headlines_annual_to_parquet.py --refresh

# 4. Commit + push:
git add raw/emendas/ etl/emendas__* docs/methodology/emendas_portal_transparencia.md \
        curated/domain_crosswalk.parquet* etl/canonical__build_domain_crosswalk.py \
        docs/methodology/canonical_domain_crosswalk.md manifest.md
git commit -m "Phase 11 Tier 1: atana.emendas.headlines_annual (10 rows) + cultura refresh"
git push
```

Curious Scientist quarterly probe registered in `_atana_intel/sources.yaml`
under `emendas_portal_transparencia`.

## 7b. Certification record (2026-07-19)

The source was certified via `_atana_intel/phase11_emendas_certify.py`, an
independent re-derivation (does NOT import the ETL) plus
`_atana_intel/phase11_emendas_dup_probe.py`. Five checks:

| Check | Result | Detail |
|---|---|---|
| **C1** Field semantics | ⚠️→fixed | No `valorAutorizado` field exists → column renamed to `valor_empenhado`. Restos a pagar dominate disbursement → added `valor_liquidado`, `valor_resto_pago`, `valor_pago_total`. Schema v2. |
| **C2** Pagination complete | ✅ PASS | Independent recount reproduced ETL `n` every year; 12-22 pages/year; loop terminates on the first short page (no hardcoded size trusted). |
| **C3** Dedup | ✅ PASS (benign) | Only 2019 had repeated `codigoEmenda` — the sentinel `"REL. GERAL"` (RP-9 relator emendas, no individual code), appearing as 4 distinct execution lines with different subfunção/valores. Money sums across lines are correct; not a double-count. |
| **C4** Invariants | ✅ PASS | `valorPago ≤ valorLiquidado ≤ valorEmpenhado`, all ≥ 0, per emenda, every year. |
| **C5** ETL fidelity | ✅ PASS | Independent Σ reproduced the parquet exactly. Manual Portal-UI cross-check (Ano=2024, Função=Cultura) recommended once by eye. |

**Verdict:** certified for Tier 1 headline use, with the E2 floor caveat and the
`valor_pago_total` (not `pago_ano`) rule foregrounded. The v1 pull is superseded
by the v2 schema.

## 8. Availability status

- [x] Table registered in `atana.emendas` schema
- [x] All-functions benchmark rows (2023, 2024) populated
- [x] Cultura placeholder rows (2018-2025) registered
- [x] Domain crosswalk extended
- [ ] Cultura values populated — awaits Portal API key (João, Tier 1b)
- [ ] Tier 2 ingest — deferred until Note #23 or Vol 2 chapter (per scoping §9)
