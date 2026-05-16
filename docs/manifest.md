# Atana Data Manifest

Canonical catalog of every table available in this repository and in `md:atana`. Keep this file synchronized when adding or modifying datasets.

**Last updated:** 2026-05-16

---

## Conventions

- **Schemas** are organized by source: `unctad`, `ibge_pnadc`, `ibge_comex`, `salic`, `lexml`, `canonical`
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

## `atana.ibge_pnadc` — IBGE PNADC Cultural Sector  *(Phase 2, planned)*

Source: IBGE *Informações Culturais* (SIIC) 2013–2024.

Planned tables (one per IBGE Tabela 6.x):

| Table | Description |
|---|---|
| `tab_6_1a`, `tab_6_1b` | Trabalhadores culturais por região (sex/race) |
| `tab_6_3` | Trabalhadores culturais por escolaridade |
| `tab_6_4` | Trabalhadores culturais por sexo × idade |
| `tab_6_5` | Trabalhadores culturais por sexo × raça |
| `tab_6_6` | Renda média no setor cultural por sexo × raça |
| `tab_6_7` | Horas trabalhadas no setor cultural |
| `tab_6_8` | Horas trabalhadas — distribuição |
| `tab_6_10` | Posição na ocupação no setor cultural |
| `tab_6_12` | Formalidade no setor cultural |
| `tab_6_13` | Top 30 atividades culturais |
| `tab_6_14`, `tab_6_15`, `tab_6_16`, `tab_6_17` | Detalhamento de ocupações |

All tables will be reshaped to **long format** (one row per country × year × dimension × value) for easy aggregation. CV columns will be preserved as a separate column.

ETL: `etl/ibge_pnadc_xlsx_to_parquet.py`

---

## `atana.ibge_comex` — IBGE Comércio Exterior Cultural  *(Phase 2, planned)*

Source: IBGE *Informações Culturais*, capítulo 10.

| Table | Description |
|---|---|
| `tab_10_1` | Importação/exportação de bens culturais por capítulo NCM (R$ FOB, 2014–2024) |
| `tab_10_2` | % de participação por capítulo no total cultural |
| `tab_10_3` | Top 20 países parceiros (cultural vs total) |
| `tab_10_4` | Balança de serviços audiovisuais (BCB/BoP, R$) |

ETL: `etl/ibge_comex_xlsx_to_parquet.py`

---

## `atana.salic` — Lei Rouanet (MinC)  *(Phase 2, planned)*

Source: API SALIC `api.salic.cultura.gov.br/api/v1`.

| Table | Description |
|---|---|
| `projetos` | 26.203 projetos coletados (2019–2026), com metadados completos |
| `incentivadores_edges` | Grafo de incentivadores (8.504 edges PRONAC → incentivador) |

ETL: `etl/salic_jsonl_to_parquet.py`

---

## `atana.lexml` — Genealogia Legislativa  *(Phase 2, planned)*

Source: LexML (Senado Federal) + complementos.

| Table | Description |
|---|---|
| `corpus_completo` | 269 atos legislativos (creative economy vocabulary) |
| `corpus_legal` | 237 atos com força normativa identificável |
| `corpus_biblio` | 32 atos administrativos / programáticos |

ETL: `etl/lexml_jsonl_to_parquet.py`

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
| — | Phase 2: planned for next session — IBGE PNADC + ibge_comex + SALIC + LexML to Parquet |
