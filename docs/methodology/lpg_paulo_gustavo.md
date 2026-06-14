# `atana.lpg` — Lei Paulo Gustavo (LC 195/2022) execution data

> **Status (2026-06-14):** GitHub ✅ `128a657` on origin/main · MotherDuck ✅ live · 4 tables / 45,727 rows in `curated/lpg/`

**Ingest date:** 2026-06-14
**Source publisher:** Ministério da Cultura, DFD/SEFIC — *dados.cultura.gov.br* (Portal de Dados da Cultura)
**License:** Brazilian public-domain convention (verify on each resource page)
**Update cadence:** monthly
**Sibling schema:** `atana.pnab` (same legal vehicle LC 195/2022 + Decreto 11.453/2023, different fiscal scope)

---

## 1. Legal frame

The **Lei Paulo Gustavo** is the popular name for the federal cultural-emergency law established by **Lei Complementar 195/2022** (8 July 2022), enacted to provide post-pandemic cultural support with an audiovisual focus. The law allocates **R$ 3,86 bilhões** total, transferred from the União to estates, the Federal District, and municípios. Implementation is governed by **Decreto 11.453/2023** (administered jointly with the permanent Política Nacional Aldir Blanc framework).

LPG is named after Brazilian actor and filmmaker Paulo Gustavo (1978–2021), who died in the pandemic.

## 2. Scope of this ingest

The MinC dataset **"Lei Paulo Gustavo (LPG)"** on dados.cultura.gov.br exposes the **full R$ 3,86 bi LPG** distributed across all entes federados. The split is encoded as `Meta do Plano`:

| Meta | Valor total recebido | Share |
|---|---:|---:|
| Audiovisual | R$ 2,80 bi | 72,4 % |
| Outras Áreas | R$ 1,07 bi | 27,6 % |
| **Total** | **R$ 3,86 bi** | 100 % |

**Correction to prior scoping (2026-06-13).** A scoping memo written before the data was inspected assumed the LPG audiovisual portion (~R$ 2,79 bi) flowed through the **Fundo Setorial do Audiovisual (FSA)** administered by **ANCINE**, with only the R$ 1,07 bi generalist portion exposed by this dataset. The data inspection on 2026-06-14 disproved that. **All R$ 3,86 bi flows through the same MinC ente-federado pipe; there is no separate FSA channel in this dataset.** The `Meta do Plano` flag distinguishes the audiovisual-targeted money from the generalist portion within a single fiscal stream.

This matters for cross-source analysis: the LPG audiovisual money sits next to the generalist money in the same execução tables, keyed on the same `cod_ibge`, governed by the same Decreto. It is not a separate ANCINE/FSA-administered pipe.

## 3. Source files

Six files placed in `raw/lpg/_source/` (gitignored):

| File | Shape | Rows | Note |
|---|---|---:|---|
| `adesaoestadoslpg.csv` | CSV, 3 cols | 26 | Estados aderentes + valor disponível |
| `adesaomunicipioslpg.csv` | CSV, 4 cols | 5.568 | Municípios aderentes |
| `execucaofinanceiraestadoslpg.csv` | CSV, 8 cols | 53 | Estados × 2 metas (AV + Outras) |
| `execucaofinanceiramunicipioslpg.csv` | CSV, 10 cols (has IBGE code) | 10.929 | Municípios × ~2 metas |
| `extratobancariolpg.xlsx` | XLSX Sheet1, 10 cols | 10.967 | Extratos de conta bancária por plano de ação |
| `relatoriogestaolpg.xlsx` | XLSX Sheet1, 6 cols | 18.180 | **Narrative + execução-física granular por ação/edital** |

Differences from the PNAB dataset shape: LPG uses **single-row CSV headers** (no DAX layer), splits estados from municípios into separate files (PNAB used multi-sheet xlsx), and exposes a uniquely rich `relatorio_gestao` table with per-edital prose + execution percentages — granularity PNAB does not have.

## 4. Output tables (`atana.lpg`)

Four curated Parquet tables, BRL nominal (no deflation applied at ingest):

### 4.1 `adesao_entes` (5.596 rows)

Adhesion status + total available per ente, harmonized across estados ∪ municípios.

| Column | Type | Description |
|---|---|---|
| `tipo_ente` | varchar | `Estado` or `Município` |
| `cod_ibge` | int | IBGE 2-digit code for estados; IBGE 7-digit for municípios; NULL for municípios in this table because the adesão CSV omits the IBGE column (use `execucao_financeira` for muni IBGE codes) |
| `uf` | varchar | 2-letter UF abbreviation |
| `ente` | varchar | Name |
| `situacao_plano` | varchar | e.g. `Autorizado` |
| `valor_disponivel_brl` | double | Total available BRL |

### 4.2 `execucao_financeira` (10.984 rows)

Per-ente × per-meta financial execution. **This is the workhorse table.** Each ente typically appears twice (once for `Audiovisual`, once for `Outras Áreas`).

| Column | Type | Description |
|---|---|---|
| `tipo_ente` | varchar | `Estado` / `Município` |
| `cod_ibge` | int | IBGE code (2-digit estado / 7-digit muni) — **uniform**, populated for every row |
| `uf` | varchar | |
| `ente` | varchar | |
| `meta_plano` | varchar | **`Audiovisual` or `Outras Áreas` — the key split** |
| `data_pagamento` | varchar | ISO YYYY-MM-DD |
| `valor_recebido_brl` | double | From União; called "Valor Transferido" in muni CSV, "Valor Recebido" in estado CSV — unified here |
| `rendimento_brl` | double | Interest income accrued in conta |
| `saldo_brl` | double | Balance |
| `valor_utilizado_brl` | double | Spent |
| `pct_utilizado_decimal` | double | Spent / received as decimal |

### 4.3 `extratos_bancarios` (10.967 rows)

Bank-account-level extracts per `Código Plano de Ação`. Each plano de ação may span multiple bank accounts.

| Column | Type | Description |
|---|---|---|
| `nome_programa` | varchar | `MINC - LEI PAULO GUSTAVO - ESTADOS` / `... - MUNICÍPIOS` |
| `codigo_plano_acao` | varchar | E.g., `30882120230001-008099` |
| `uf_recebedor`, `municipio_recebedor` | varchar | Where the money landed |
| `cnpj_solicitante`, `nome_solicitante` | varchar | The legal entity (secretaria, fundo, etc.) |
| `banco`, `agencia`, `conta` | varchar | Bank-account identifiers |
| `saldo_em_conta_brl` | double | Current balance |

### 4.4 `relatorio_gestao` (18.180 rows)

**The richest table — per-edital / per-ação narrative + execução física.** Each plano de ação has multiple metas (Art. 6º incisos), each with multiple ações (call-for-proposals), each tracked with a `Execução Física (%)` 0–1 scale. This is the data layer that lets us see *what the money was actually used for*, not just *how much was spent*.

| Column | Type | Description |
|---|---|---|
| `codigo_plano_acao` | varchar | Joins to `extratos_bancarios.codigo_plano_acao` |
| `link_plano_acao` | varchar | URL to the transferegov.sistema.gov.br page |
| `situacao_relatorio` | varchar | E.g., `ENVIADO_ANALISE` |
| `meta_artigo` | varchar | The LPG article + inciso defining the policy goal (e.g., `Art. 6º, inciso I`) |
| `acao_descricao` | varchar | **Free-text description of what the edital is funding (typically rich, AV-specific)** |
| `execucao_fisica_decimal` | double | Reported execution as decimal 0–1 |

The `acao_descricao` field is a candidate for NLP analysis: typology of audiovisual editais (long-feature production, gaming, short-form documentary, festival support, etc.) at the municipal level.

## 5. Headline findings ready to report

| Finding | Value | Source |
|---|---:|---|
| Total LPG distributed (recebido) | R$ 3,86 bi | `execucao_financeira` SUM |
| Audiovisual share | 72,4 % (R$ 2,80 bi) | meta_plano filter |
| Generalist (Outras Áreas) share | 27,6 % (R$ 1,07 bi) | meta_plano filter |
| Taxa de execução agregada | 101,9 % | SUM utilizado ÷ SUM recebido (>100 % from interest income) |
| Estados taxa de execução | 105,1 % | tipo_ente = Estado |
| Municípios taxa de execução | 97,9 % | tipo_ente = Município |
| Número de municípios atendidos | 5.568 | adesao_entes |
| Número de estados atendidos | 26 | adesao_entes |

## 6. Cross-source joins this schema unlocks

LPG was ingested specifically to enable cross-source analytical questions that the corpus could not previously answer. The main four:

### 6.1 `atana.lpg × atana.salic` on UF + ano — Rouanet AV crowding-out

The DB-updater sweep on 2026-06-12 named *caso 5.2 da Análise 8 Opção B (crowding-out LPG × Rouanet AV)* as the load-bearing consumer for this ingest. The question is whether municípios receiving LPG audiovisual money also showed reduced Rouanet audiovisual captação in the same period. Filter `atana.salic.projetos_v2` to AV segments (`Audiovisual`, `Música em audiovisual`, etc.) and join on UF + ano.

### 6.2 `atana.lpg × atana.pnab` on `cod_ibge` — execution-rate comparison

Same ente, two pipes (LPG audiovisual-emergency single-cycle vs PNAB generalist-permanent). Are municípios with weak governance scoring execucao faster or slower in the audiovisual pipe? Joining on `cod_ibge` produces a paired sample of municípios appearing in both schemas.

### 6.3 `atana.lpg × atana.tcu` — does the PNAB audit extend?

TCU's Acórdão 1709/2025 rated PNAB's Gestão de Riscos at 1/4 (não institucionalizada). Because LPG is administered through the same DFD/SEFIC structure and Decreto 11.453/2023, the audit findings likely extend by structural inheritance to LPG. The data layer can confirm or refute via the same governance scaffolding (conselho/plano/fundo presence, though that comes from `atana.pnab.governanca_entes`, not the LPG dataset itself).

### 6.4 `atana.lpg.relatorio_gestao` — typology of audiovisual editais

The 18.180-row narrative table is a candidate for topic-modeling (LDA or embedding-based clustering) over `acao_descricao` to surface the **typology of municipal/state audiovisual editais** funded by LPG: short-form vs long-form production, gaming vs traditional film, festival support vs production support, etc.

## 7. Caveats (LPG-W1 .. LPG-W6)

| # | Caveat |
|---|---|
| **LPG-W1** | **All values BRL nominal** — no deflation applied. Use `atana.macro.fx_brl_usd_annual` (or BCB SGS 433 IPCA via `rais__deflate_ipca.py` pattern) at analytical step. Most LPG payments cluster 2023-2024; deflator to R$ 2024 is light. |
| **LPG-W2** | **No FSA portion is missing** — the dataset includes the full R$ 3,86 bi LPG. The 2026-06-13 scoping memo's hypothesis of a separate ANCINE/FSA channel was wrong. |
| **LPG-W3** | **"Valor Utilizado" inflates beyond 100 % when interest income (rendimento) was reinvested before the spending deadline.** Estados aggregate at 105,1 %, not because they overspent the law but because they earned interest on the conta and applied that interest. This is structurally legitimate. |
| **LPG-W4** | **Extratos may include internal transfers and automatic financial applications** (same caveat as PNAB extratos — DB-updater log 2026-06-13). Summing `extratos_bancarios.saldo_em_conta_brl` is NOT equivalent to summing actual cultural spending. Use `execucao_financeira.valor_utilizado_brl` as the canonical "gasto" figure. |
| **LPG-W5** | **`adesao_entes.cod_ibge` is NULL for municípios** because the adhesion CSV from MinC does not expose the IBGE code on that table; use `execucao_financeira` for IBGE-keyed muni joins. |
| **LPG-W6** | **`relatorio_gestao.execucao_fisica_decimal` is self-reported by entes** to MinC, not externally audited (the TCU audit on PNAB used different inputs). Treat as a self-reported signal, not measurement. |

## 8. Refresh path

The MinC dataset updates monthly. The `etl/lpg__to_parquet.py` script is idempotent — on each new vintage:

1. Download the new CSV/XLSX resources from dados.cultura.gov.br
2. Replace files in `raw/lpg/_source/`
3. Re-run `python3 etl/lpg__to_parquet.py`
4. Diff the resulting parquets against the prior commit; commit + push if material

## 9. Cross-reference

- **`docs/methodology/pnab_aldir_blanc.md`** — the sibling Aldir Blanc methodology
- **`_atana_intel/scoping_lpg_ingest_2026-06-13.md`** — the prior-day scoping memo; **note this memo's hypothesis about FSA-routing was wrong** and is corrected here
- **`_atana_intel/db_update_log.md`** entry 2026-06-12 (sweep) and 2026-06-13 (PNAB ingest) — context for why both schemas were brought in this week
- **`canonical.domain_crosswalk`** row `lpg / paulo_gustavo_lc195` → `Audiovisual` (cultural, focused, "good" confidence)

---

*Methodology version 1.0 — 2026-06-14. Ingested by Atana Assistant; verified by 4-table row-count + financial-total reconciliation (R$ 3,86 bi).*
