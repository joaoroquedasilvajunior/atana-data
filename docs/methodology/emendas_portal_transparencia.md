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

### `headlines_annual` schema

| Column | Type | Notes |
|---|---|---|
| `year` | INT32 | 2018-2025 |
| `scope` | VARCHAR | `all_functions` \| `funcao_13_cultura` |
| `valor_autorizado_brl_mi` | DOUBLE | R$ mi correntes; null pre-refresh for cultura |
| `valor_pago_brl_mi` | DOUBLE | R$ mi correntes; null pre-refresh |
| `n_emendas` | INT32 | count; null pre-refresh |
| `source_page` | VARCHAR | citation |
| `notes` | VARCHAR | caveats |
| `fetch_date` | VARCHAR | ISO date |

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

## 8. Availability status

- [x] Table registered in `atana.emendas` schema
- [x] All-functions benchmark rows (2023, 2024) populated
- [x] Cultura placeholder rows (2018-2025) registered
- [x] Domain crosswalk extended
- [ ] Cultura values populated — awaits Portal API key (João, Tier 1b)
- [ ] Tier 2 ingest — deferred until Note #23 or Vol 2 chapter (per scoping §9)
