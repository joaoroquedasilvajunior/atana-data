# `atana.rais` — Formal Cultural Employment (RAIS / MTE)

> **Status (2026-06-14):** GitHub ✅ `5fa9c34` on origin/main · MotherDuck ✅ live · 39 tables / 19,829,011 rows in `raw/rais/_reference/`

> Methodology note. Phase 2 (foundational corpus). ETL: `etl/rais__bigquery_to_parquet.py` + `etl/rais__deflate_ipca.py` + `etl/rais__build_reference_tables.py`. Companion long-form methodology lives at **`docs/rais_methodology.md`** (12 sections, ~2,200 words) — referenced rather than duplicated here.
> **Consumed by:** Análise 11 *A moldura formal: o emprego cultural brasileiro nos registros da RAIS (2014–2025)* — the corpus's formal-employment anchor · Análise 17 (música) · Análise 18 (cinco portas) · Análise 19 (geografia da captura) · Análise 22 (geografia regional) · Análise 25 (Brazilian Design & Software 4-lens) · the H0 paper draft.

## 1. What the source is

The **RAIS** is the *Relação Anual de Informações Sociais*, Brazil's annual mandatory administrative declaration of formal employment, run by the Ministério do Trabalho e Emprego (MTE). Every legal employer files for every formal employee (CLT, sócio, intermitente, etc.) once per calendar year. Coverage is intended to be the universe of formal employment in Brazil.

`atana.rais` is the **de-identified cultural cut**, 2014–2025: every active employment-year record (`vínculo`) where at least one of the following holds:
- **Cut A** — the establishment is classified in a **cultural CNAE** (33 subclasses on the cultural codelist).
- **Cut B** — the worker's **CBO occupation is cultural** (62 occupation families on the cultural codelist).

`A ∩ B` = the specialised cultural workforce (worker in cultural occupation *and* in cultural establishment). `A ∪ B` = the full cultural workforce (the broader denominator). Most analyses publish A∪B as primary and A∩B as sensitivity. The reference codelists are themselves Parquet (`cnae_cultural.parquet`, `cbo_cultural.parquet`) for full reproducibility.

Vintage: 2014–2025 (12 years). The 2024 + 2025 ingest was the work of Phase 2 v41 (CLAUDE.md). Source ingest is via Base dos Dados (`br_me_rais`) — IBGE-supervised, de-identified mirror.

## 2. Tables (39 tables)

The schema groups into three logical layers — the working panel + reference tables + IPCA support.

| Family | Tables | What |
|---|---|---|
| **Working panel (3)** | `vinculos_culturais`, `estabelecimentos_culturais`, `panel_cnae_municipio_ano` | The cultural panel: ~17 M vínculos-year records 2014–2025; ~2.4 M establishment-years; the per-CNAE-5-digit × município × ano grain panel (~120 k rows) for spatial analyses. **All monetary values deflated to BRL 2024** via `etl/rais__deflate_ipca.py`. |
| **Reference (2)** | `cnae_cultural`, `cbo_cultural` | The 33-CNAE + 62-CBO cultural codelists. Reproducibility relies on these being checked in. |
| **IPCA deflator (1)** | `ipca_annual_mean` | Per-year IPCA index (Jan 2014 = 100), source BCB SGS 433. The same deflator used by `etl/rais__deflate_ipca.py` for the panel. |
| **Per-year `vinculos_yyyy` slices (12)** | `vinculos_2014` … `vinculos_2025` | Per-year cuts of the panel for ergonomics — equivalent to `vinculos_culturais WHERE ano = yyyy` but bypasses the ~17 M-row scan. |
| **Per-year `estabelecimentos_yyyy` slices (12)** | Same convention for the establishment level. |
| **eSocial-shock decompositions (multiple)** | Tables used in Análise 18 §4 to isolate the eSocial 2018+ break in CBO 2624 (músicos) — see Análise 18 §4 for the empirical recipe. |

Total: 39 Parquet tables. Three are the primary analytical surface; the rest are reference + ergonomics.

## 3. Methodology / ingest notes

The companion file **`docs/rais_methodology.md`** has the full 12-section methodology, including the eSocial discontinuity rule (Step 4.5 — `IGNORADO` UF apparent only from 2022+, `mes_admissao=0` convention). Do not duplicate; if a downstream analysis needs methodology context, link to that file.

Key choices summarised here:

- **De-identification:** the Base dos Dados RAIS is desidentificada — no CNPJ, no PIS, no individual identifier. Worker-level joins are impossible from this corpus. The H1 causal paper (firm-level Rouanet → employment) requires identified RAIS via IBGE PDET data room or a Path B academic partnership; this is documented in `notes/rais_phase2b_mte_ftp_scoping.md` (Phase 2b was cancelled when the FTP also turned out to be desidentificada).
- **Convention:** vínculos ativos em **31 de dezembro** of each year are the canonical headline measure. "Vínculos do ano" (including terminated contracts) gives a different number — be explicit which convention is in play.
- **Deflation:** BRL 2024 throughout the panel; IPCA Jan 2014 = 100; the deflator is the BCB SGS 433 annual mean.
- **eSocial migration 2018 →** affects CBO 2624 (músicos) materially: the +17,968 vínculos-year growth in 2018–2023 is concentrated in non-cultural CNAEs (TI, telecom, *diverso*), suggesting cover-of-formalisation rather than sector growth. Análise 18 §4 has the decomposition.

## 4. Caveats (W1–W6)

| # | Alert |
|---|---|
| W1 | **Formal employment only.** RAIS doesn't see conta-própria, MEIs without employees, autônomos sem CNPJ. The "200 k autônomos da porta (e)" of Análise 18 are entirely invisible here — that is the point of pairing RAIS with PNADC and CEMPRE. |
| W2 | **2014–2023 → 2014–2025 extension changed the recovery narrative.** The "recovery to near-2014 levels" reading of Análise 11 v1 is invalid in v2 (with 2024 + 2025): in 2025, vínculos +1.5 % vs 2014 but real wages −16.9 % vs 2014 — the precarisation accelerated. Use v2 narrative. |
| W3 | **2022 → 2023 establishment count discontinuity** (180 k → 350 k, +94 %) is largely the eSocial migration, not real establishment creation. Flag this artefact when computing per-establishment ratios across this boundary. |
| W4 | **Design domain is heavily inflated by CNAE 73190** (publicidade) — 92 % of Design's +98 % decade-growth is in 73190, where wages are 30–40 % below the rest of Design. The growth is real; the welfare implication is dim. |
| W5 | **The de-identified RAIS supports descriptive sample-selection (H0) but not firm-level causal claims (H1).** The H1 paper is in development via Path C (aggregate DiD at município × CNAE × ano grain) — see CLAUDE.md §11. |
| W6 | **`atana.salic` carries CNPJ for funded projects** — Rouanet × RAIS joins must work via município × CNAE proxies, not direct CNPJ match. |

## 5. References

- **`docs/rais_methodology.md`** — the long-form methodology (canonical).
- **`etl/RAIS_2024_INGEST_RUNBOOK.md`** — operational runbook for the annual refresh, including the BigQuery (basedosdados) → Parquet → MotherDuck pipeline.
- Análise 11 — primary analytical anchor.
- `notes/rais_phase2b_mte_ftp_scoping.md` — the cancellation memo for the MTE FTP path, including the three alternative paths for H1 causal evidence.
