# Atana Data Manifest

Canonical catalog of every table available in this repository and in `md:atana`. Keep this file synchronized when adding or modifying datasets.

**Last updated:** 2026-05-22

---

## Conventions

- **Schemas** are organized by source: `unctad`, `ibge_pnadc`, `ibge_comex`, `salic`, `lexml`, `inegi`, `dane`, `canonical`
- **Table names** are snake_case, prefixed by the table number when applicable: `tab_6_10`, `tab_10_1`
- **Curated tables** live in the `canonical` schema and represent ready-to-consume snapshots used in published analyses
- **Currency**: each table documents its native currency (R$ corrente, R$ FOB, US$ corrente, etc.) — never mixed in one column

---

## `atana.unctad` — UNCTAD Creative Economy

Source: UNCTADstat ([https://unctadstat.unctad.org](https://unctadstat.unctad.org))

### `unctad.goods_value`
Bilateral trade of creative goods at HS-6 detail level, by reporter × partner × year × product.

| Column | Type | Description |
|---|---|---|
| Year | BIGINT | Reference year |
| Economy | VARCHAR | ISO 3-digit code of reporting country |
| Economy Label | VARCHAR | Country name |
| Partner | VARCHAR | ISO code of partner ('0000' = World) |
| Partner Label | VARCHAR | Partner name |
| Flow | VARCHAR | '01' = Imports, '02' = Exports |
| Flow Label | VARCHAR | "Imports" / "Exports" |
| Product | VARCHAR | CER code (CER000=all; CER010-CER070; CER021-027 leaf) |
| Product Label | VARCHAR | Category name |
| US$ at current prices in millions | DOUBLE | Trade value |
| Percentage of total world | DOUBLE | Share of global creative trade |
| Percentage by destination | DOUBLE | Share by destination |
| Percentage of total merchandise trade | DOUBLE | Share of country's total goods trade |

**Rows:** ~25.4 M | **Coverage:** 200+ economies, 1995–2024 | **Key:** (Year, Economy, Partner, Flow, Product)

### `unctad.goods_growth`
Year-on-year growth rates derived from `goods_value` (UNCTAD pre-calculated).

**Rows:** ~24.0 M | **Coverage:** same as `goods_value`

### `unctad.services_countries`
Total creative services exports/imports per country per year (aggregate, no sub-category breakdown).

| Column | Type | Description |
|---|---|---|
| Year | BIGINT | Reference year |
| Economy | VARCHAR | ISO 3-digit code |
| Economy Label | VARCHAR | Country name |
| Flow | VARCHAR | '01' = Imports, '02' = Exports |
| Flow Label | VARCHAR | "Imports" / "Exports" |
| US$ at current prices in millions | DOUBLE | Service trade value |
| Growth rate, year-on-year | DOUBLE | YoY % change |
| Percentage of total trade in services | DOUBLE | Share of total services trade |

**Rows:** 5,336 | **Coverage:** ~200 economies, 2005–2024 (incomplete for many small economies)

### `unctad.services_regional`
Same as `services_countries` but at regional aggregate level (LATAM, OECD, etc.), with breakdown by creative service sub-category (CRE, SRND, SSFT, SAUV, SINF, SAMA, SCRH).

| Column | Type | Description |
|---|---|---|
| Year, Economy, Economy Label | — | Same as above (Economy = region code) |
| CreativeService | VARCHAR | Sub-category code (SCRE, SRND, SSFT, SAUV, SINF, SAMA, SCRH) |
| CreativeService Label | VARCHAR | Sub-category name |
| US$ at current prices in millions | DOUBLE | Value |

**Rows:** 945

---

## `atana.ibge_pnadc` — IBGE PNADC Cultural Sector ✅ Live

Source: IBGE *Informações Culturais* (SIIC) 2013–2024.

| Table | Rows | Format | Description |
|---|---:|---|---|
| `tab_6_1a` | 12,166 | long | Trab. culturais por região (geografia em colunas) |
| `tab_6_1b` | 3,047 | long | Trab. culturais por região × raça |
| `tab_6_2` | 10,582 | long | Distribuição etária (geografia em colunas) |
| `tab_6_3` | 671 | wide | Escolaridade no setor cultural |
| `tab_6_4` | 671 | wide | Formalidade por região |
| `tab_6_5` | 693 | wide | Composição racial |
| `tab_6_6` | 704 | wide | Renda média por sexo × raça |
| `tab_6_7` | 671 | wide | Horas trabalhadas por região |
| `tab_6_8` | 671 | wide | Distribuição de horas trabalhadas |
| `tab_6_9` | 1,067 | long | Detalhamento horas (geografia em colunas) |
| `tab_6_10` | 165 | wide | Posição na ocupação |
| `tab_6_11` | 2,475 | long | Idade × posição (geografia em colunas) |
| `tab_6_12` | 363 | wide | Formalidade detalhada |
| `tab_6_13` | 55 | wide | Top 30 atividades culturais |
| `tab_6_14`–`6_17` | 55 + 55 + 55 + 1,430 | wide | Detalhamento de ocupações |

**Format types:**
- **wide**: one row per (year, region), columns `c02, c04, c06...` are values; `c03, c05...` are CVs. Refer to `.claude/skills/ibge-pnadc-cultural/references/column_maps.md` for column meaning per table.
- **long**: one row per (year, row_label, col_index, value). Used for tables 6.1a, 6.1b, 6.2, 6.9, 6.11 where geography is in columns rather than rows.

ETL: `etl/ibge_pnadc__xlsx_to_parquet.py`

---

## `atana.ibge_comex` — IBGE Comércio Exterior Cultural ✅ Live

Source: IBGE *Informações Culturais*, capítulo 10 (SECEX/MDIC for goods, BCB for services).

| Table | Rows | Description |
|---|---:|---|
| `tab_10_1` | 209 | Imp/exp de bens culturais por capítulo NCM × ano (R$ mi FOB) |
| `tab_10_2` | 198 | % de participação por capítulo no total cultural |
| `tab_10_3` | 880 | Top 20 países parceiros × ano × 4 fluxos |
| `tab_10_4` | 11 | Balança de serviços audiovisuais 2014–2024 (BCB/BoP) |

Schema highlights:
- `tab_10_1`: columns include `year, capitulo_ncm, capitulo_label, imp_cultural_brl_mi, exp_cultural_brl_mi, is_pure_cultural` (flag for capítulos 37/46/49/92/97 that are 100% cultural)
- `tab_10_3`: long format with `year, flow, rank, country, share_pct` — easy to filter by flow

ETL: `etl/ibge_comex__xlsx_to_parquet.py`

---

## `atana.salic` — Lei Rouanet (MinC) ✅ Live

Source: API SALIC `api.salic.cultura.gov.br/api/v1`.

| Table | Rows | Description |
|---|---:|---|
| `projetos` | 26,203 | Projetos coletados (2019–2026), com metadados completos |
| `edges_incentivador` | 8,504 | Grafo de incentivadores (PRONAC → incentivador) |
| `propostas_recentes` | 3,000 | Propostas recentes |

ETL: `etl/salic__jsonl_to_parquet.py`

---

## `atana.lexml` — Genealogia Legislativa ✅ Live

Source: LexML (Senado Federal) + complementos.

| Table | Rows | Description |
|---|---:|---|
| `corpus` | 269 | Atos legislativos da economia criativa (corpus completo) |
| `legal` | 237 | Atos com força normativa identificável |
| `biblio` | 32 | Atos administrativos / programáticos |
| `classified` | 217 | Atos com metadados subnacionais |
| `with_ementas` | 217 | Atos com ementas completas |

ETL: `etl/lexml__jsonl_to_parquet.py`

---

## `atana.inegi` — INEGI Cuenta Satélite de la Cultura de México ✅ Live (raw/Parquet; MotherDuck sync pending)

Source: INEGI *Cuenta Satélite de la Cultura de México* (CSCM), base year 2018. Phase 3a of the LATAM expansion — the first non-Brazilian national source in the corpus.

| Table | Rows | Description |
|---|---:|---|
| `csc_comercio` | 5,984 | Cultural imports/exports from the CSCM Cuadros de Oferta y Utilización, by functional area × year × flow × price basis, 2008–2024, MXN million (current + constant 2018) |
| `fx_mxn_usd_annual` | 17 | Reference — annual-average MXN/USD exchange rate (World Bank PA.NUS.FCRF), used to derive the USD column of `csc_comercio` |

Schema highlights:
- `csc_comercio`: grain is `year × area_level × area_general × area_especifica × flow × price_basis`. `area_level` ∈ {`total`, `area_general` (10), `area_especifica` (77)}. `flow` ∈ {`importacion`, `exportacion`}. `price_basis` ∈ {`corriente`, `constante_2018`}. `value_usd_million` is ETL-derived (current-price rows only).
- ⚠️ The CSCM has **no balance-of-payments module**; `csc_comercio` is the import/export columns of the supply-use tables — no bilateral partner detail. Never mix with `unctad` or `ibge_comex` without explicit reconciliation (different methodologies).

ETL: `etl/inegi__csc_xlsx_to_parquet.py` · Methodology: `docs/methodology/inegi_csc.md`

---

## `atana.dane` — DANE Cuenta Satélite de Economía Cultural y Creativa ✅ Live (raw/Parquet; MotherDuck sync pending)

Source: DANE *Cuenta Satélite de Economía Cultural y Creativa* (CSECC), release 2022–2024pr. Phase 3b of the LATAM expansion — second non-Brazilian national source.

| Table | Rows | Description |
|---|---:|---|
| `csecc_comercio` | 484 | Cultural imports/exports from the CSECC product-level supply-use balances, by product × area × year × flow, 2014–2024, COP million (current prices) |
| `fx_cop_usd_annual` | 11 | Reference — annual-average COP/USD exchange rate (World Bank PA.NUS.FCRF), used to derive the USD column of `csecc_comercio` |

Schema highlights:
- `csecc_comercio`: grain is `year × cuadro_num(product) × flow`. `area` ∈ {`Artes y patrimonio`, `Industrias culturales`, `Creaciones funcionales`}. `flow` ∈ {`importacion`, `exportacion`}. 22 of the 35 CSECC product cuadros carry trade; `value_usd_million` is ETL-derived. `source_concept` preserves DANE's verbatim valuation label (imports CIF/precios básicos, exports a precio comprador).
- ⚠️ The CSECC has **no balance-of-payments module** and no bilateral partner detail — same posture as `atana.inegi`. Never mix `dane`, `inegi`, `unctad` or `ibge_comex` in a query without explicit reconciliation (different classifications, valuations, currencies).

ETL: `etl/dane__csecc_xlsx_to_parquet.py` · Methodology: `docs/methodology/dane_csecc.md`

---

## `atana.canonical` — Curated analytical snapshots

Read-only views and tables that power published analyses. **Do not modify directly** — regenerate via build scripts and versioned datasets.

### `canonical.latam_creative_2024`  *(Phase 2)*
The dataset behind Análise 4 / Análise 6 / Atana Index Vol. 1 — 15 LATAM countries × HHI, exposure index, total exports.

Currently lives at `_atana_intel/latam_creative_2024_dataset.json` in the analysis repo; will be promoted to MotherDuck in Phase 2.

### `canonical.brasil_balanca_cultural_2014_2024`  *(Phase 2)*
The dataset behind Análise 10 — Brazilian cultural foreign trade time series.

---

## Update log

| Date | Change |
|---|---|
| 2026-05-16 | Phase 1: schemas created in `md:atana`; 4 UNCTAD tables migrated |
| 2026-05-16 | Phase 2: 18 PNADC + 4 IBGE Comex + 3 SALIC + 5 LexML tables loaded as Parquet and synced to MotherDuck. `gen_latam_fig3_fig9.py` migrated to read from `atana.unctad.*`. |
| 2026-05-22 | Phase 3a: `atana.inegi` schema added — first non-Brazilian national source. `csc_comercio` (5,984 rows) + `fx_mxn_usd_annual` (17 rows) written as Parquet to `raw/inegi/` and synced to MotherDuck. |
| 2026-05-22 | Phase 3b: `atana.dane` schema added — Colombia CSECC. `csecc_comercio` (484 rows) + `fx_cop_usd_annual` (11 rows) written as Parquet to `raw/dane/`. MotherDuck sync pending (not yet pushed). |
