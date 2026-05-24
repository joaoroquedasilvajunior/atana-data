# Atana Data Manifest

Canonical catalog of every table available in this repository and in `md:atana`. Keep this file synchronized when adding or modifying datasets.

**Last updated:** 2026-05-23

---

## Conventions

- **Schemas** are organized by source: `unctad`, `ibge_pnadc`, `ibge_comex`, `salic`, `lexml`, `inegi`, `dane`, `sinca`, `cr_bccr`, `ibge_estruturais`, `ibge_cempre`, `ibge_tic`, `ibge_turismo`, `bcb`, `canonical`
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

## `atana.inegi` — INEGI Cuenta Satélite de la Cultura de México ✅ Live (GitHub + MotherDuck)

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

## `atana.dane` — DANE Cuenta Satélite de Economía Cultural y Creativa ✅ Live (GitHub + MotherDuck)

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

## `atana.sinca` — Argentina Cuenta Satélite de Cultura ✅ Live (GitHub + MotherDuck)

Source: SInCA (Sistema de Información Cultural de la Argentina) + INDEC — *Cuenta Satélite de Cultura*, foreign-trade module. Phase 3c of the LATAM expansion — third non-Brazilian national source.

| Table | Rows | Description |
|---|---:|---|
| `csc_comercio` | 228 | Cultural goods/services exports, imports and trade balance, 2004–2022, thousands of ARS (current and constant-2004 prices) |
| `csc_participacion` | 76 | Cultural trade as a share of total trade and of cultural gross output, 2004–2022 (ratios) |

Schema highlights:
- `csc_comercio`: grain `year × segment × price_basis × flow`. `segment` ∈ {`servicios_culturales`, `bienes_culturales`, `bienes_y_servicios_culturales`}; `bienes_culturales` is **derived** (`total − services`) and exists for `constante_2004` only. `price_basis` ∈ {`corriente`, `constante_2004`}. `flow` ∈ {`exportacion`, `importacion`, `saldo`}.
- ⚠️ **No `value_usd_million` column** — unlike `atana.inegi`/`atana.dane`. Argentina's multiple-exchange-rate regime makes any ARS→USD conversion misleading; the series is held in pesos and the constant-2004 basis is the time-comparable one. See methodology §4.
- Segment-level only (no product/sector breakdown); series ends 2022. Never mix with `inegi`, `dane`, `unctad` or `ibge_comex` without explicit reconciliation.

ETL: `etl/sinca__csc_to_parquet.py` · Methodology: `docs/methodology/sinca_csc.md`

---

## `atana.cr_bccr` — Cuenta Satélite de Cultura de Costa Rica ✅ Live (GitHub + MotherDuck)

Source: *Cuenta Satélite de Cultura de Costa Rica* (CSCCR) — CICSC consortium (MCJ + BCCR + INEC + PEN + CONARE), hosted by the Banco Central de Costa Rica. Phase 3d of the LATAM expansion — fourth non-Brazilian national source.

| Table | Rows | Description |
|---|---:|---|
| `csc_comercio` | 150 | Cultural exports/imports of 4 sectors (Editorial, Publicidad, Audiovisual, Música), 2010–2024, CRC million (current prices) |
| `fx_crc_usd_annual` | 15 | Reference — annual-average CRC/USD exchange rate, used to derive the USD column |

Schema highlights:
- `csc_comercio`: grain `year × sector × flow`. `sector` ∈ {`Editorial`, `Publicidad`, `Audiovisual`, `Música`, `Total`}; `flow` ∈ {`exportacion`, `importacion`}. `value_usd_million` is ETL-derived.
- ⚠️ **Coverage break:** full 4-sector coverage 2010–2021 only; **2022–2024 is Editorial-only** (other sectors `n.d.`) and the year totals collapse to Editorial. The `full_sector_coverage` boolean flags it. Unlike `inegi`/`dane`, the CSCCR publishes a *dedicated* consolidated trade table. Never mix with other schemas without explicit reconciliation.

ETL: `etl/cr_bccr__csc_to_parquet.py` · Methodology: `docs/methodology/cr_bccr_csc.md`

---

## `atana.ibge_estruturais` — IBGE SIIC ch. 2: structural business surveys 🔜 Built — pending sync

Source: IBGE *Sistema de Informações e Indicadores Culturais* (SIIC), "Informações Culturais" 2024 edition, chapter 2 — structural business surveys (PIA / PAS / PAC). Phase 4a of the Brazil-first transversal-domain expansion — the production-account view that closes the FCS *Cultural and creative goods manufacturing* domain.

| Table | Rows | Description |
|---|---:|---|
| `tab_2_1` … `tab_2_8` | 354 each | One structural-survey variable per table — número de empresas, pessoal ocupado, salários, receita líquida, custos, valor bruto da produção, consumo intermediário, valor adicionado — total economy + cultural sector by domain/activity, ref. 2013 + 2019–2023, with IBGE CV codes |

Long format: grain `table_id × variable × row_label × year → value, cv`. ETL: `etl/ibge_estruturais__siic_ch2_to_parquet.py` · Methodology: `docs/methodology/ibge_estruturais_siic_ch2.md`

---

## `atana.ibge_cempre` — IBGE SIIC ch. 1: formally constituted activities 🔜 Built — pending sync

Source: SIIC "Informações Culturais" 2024, chapter 1 — CEMPRE (Cadastro Central de Empresas) + company demography + public-register statistics. Phase 4a — the firm-structure complement to `ibge_estruturais`.

23 tables (`tab_1_1_1` … `tab_1_3_4`), **1,202 rows** total. Faithful wide preservation — one Parquet per source sheet, original cells kept as `c01, c02, …` (the 24-sheet workbook's `Quadro 1.1` legend is not ingested). Families: `1.1.x` CEMPRE, `1.2.x` company demography, `1.3.x` public-register statistics; layouts are heterogeneous — see the methodology note. ETL: `etl/ibge_cempre__siic_ch1_to_parquet.py` · Methodology: `docs/methodology/ibge_cempre_siic_ch1.md`

---

## `atana.ibge_tic` — IBGE SIIC ch. 7: internet & television access 🔜 Built — pending sync

Source: SIIC "Informações Culturais" 2024, chapter 7 — PNAD Contínua ICT supplement. Phase 4b — reaches the FCS *Social participation* transversal domain **as a proxy**.

| Table | Rows | Description |
|---|---:|---|
| `tab_7_1` … `tab_7_8` | 5,387 total | Internet / TV / paid-streaming access; year + CV sheets stacked (`is_cv` flag); years vary by table within 2016–2024 |

⚠️ **Proxy domain** — digital-access data, an *approximate* proxy for FCS Social participation; Brazil has no continuous cultural-practices survey. Faithful wide format (`c02…` preserve the IBGE column structure). ETL: `etl/ibge_tic__siic_ch7_to_parquet.py` · Methodology: `docs/methodology/ibge_tic_siic_ch7.md`

---

## `atana.ibge_turismo` — IBGE SIIC ch. 9: leisure, culture & nature tourism 🔜 Built — pending sync

Source: SIIC "Informações Culturais" 2024, chapter 9 — PNAD Contínua leisure-tourism supplement. Phase 4b — reaches FCS *Social participation* **as a proxy**.

| Table | Rows | Description |
|---|---:|---|
| `tab_9_1` … `tab_9_5` | 891 total | Leisure travel by type incl. "Cultura e gastronomia"; year + CV sheets stacked; ref. 2021 / 2023 / 2024 |

⚠️ **Proxy domain** — see `ibge_tic`. Faithful wide format. ETL: `etl/ibge_turismo__siic_ch9_to_parquet.py` · Methodology: `docs/methodology/ibge_turismo_siic_ch9.md`

---

## `atana.bcb` — BCB intellectual-property-services balance of payments ✅ Live (GitHub `e435a1e`)

Source: Banco Central do Brasil — SGS series 22777 (receita) / 22778 (despesa), *Serviços de propriedade intelectual* (BPM6). Phase 4c.1 — reaches the FCS *Intellectual property* transversal domain (the cross-border IP-royalty flow).

| Table | Rows | Description |
|---|---:|---|
| `ip_services_bop` | 750 | IP-services BoP flow, monthly 1995–2026, long format — `series_code × date → value_usd_million`, `flow` ∈ {receita, despesa} |

⚠️ **All-economy, not cultural-only** — the macro IP-royalty flow; a cultural cut needs INPI (Phase 4c.2) + ECAD (Phase 4c.3). The ETL `etl/bcb__sgs_ip_services_to_parquet.py` pulls the BCB SGS API live and caches the JSON under `raw/bcb/_source/` (gitignored); rerun with `--refresh` for a new vintage. ETL: `etl/bcb__sgs_ip_services_to_parquet.py` · Methodology: `docs/methodology/bcb_sgs_ip_services.md`

---

## `atana.canonical` — Curated analytical snapshots

Read-only views and tables that power published analyses. **Do not modify directly** — regenerate via build scripts and versioned datasets.

### `canonical.domain_crosswalk` ✅ Live (Phase 3) · 🔜 extended for Phase 4 — pending re-sync

The Atana harmonisation crosswalk — maps every cultural-statistics classification in the corpus onto one common spine. **83 rows**, one per classification code (Phase 3 built 72; Phase 4 added 10 `ibge_siic` rows and 1 `bcb` row).

| Column | Type | Description |
|---|---|---|
| `source_schema` | VARCHAR | `fcs2025` / `inegi` / `dane` / `sinca` / `cr_bccr` / `unctad` / `ibge_comex` / `ibge_siic` / `bcb` |
| `source_system` | VARCHAR | Human-readable classification name |
| `source_code` | VARCHAR | Code within that classification |
| `source_label` | VARCHAR | Label within that classification |
| `fcs2025_domain` | VARCHAR | The spine — a 2025 UNESCO FCS domain, a bundle, or NULL |
| `fcs2025_domain_type` | VARCHAR | `cultural` / `transversal` (or a verbatim bundle / NULL) |
| `unctad_cer` | VARCHAR | Nearest UNCTAD CER / service code; NULL if none |
| `ibge_ncm_chapter` | VARCHAR | Nearest IBGE NCM chapter(s); NULL if not a traded good |
| `mapping_confidence` | VARCHAR | `exact` / `good` / `approximate` / `no-equivalent` |
| `notes` | VARCHAR | The definitional gap, stated explicitly (`★` flags a finding) |

Row composition: `fcs2025` 14 (the spine — 7 cultural + 7 transversal) · `inegi` 10 · `dane` 22 · `sinca` 2 · `cr_bccr` 4 · `unctad` 15 · `ibge_comex` 5 · `ibge_siic` 10 · `bcb` 1. It turns the isolated national schemas into a cross-queryable layer — a query joins any national CSC, the IBGE SIIC or the BCB account to the FCS spine through this one table. Definitional gaps are kept visible (`mapping_confidence`, `notes`), never silently reconciled. The build script's coverage meter now reaches **13/14** FCS domains (Phase 4 added *Cultural and creative goods manufacturing*, *Social participation* as a proxy, and *Intellectual property* via the BCB row; only *Intangible cultural heritage* remains, out of scope by decision). Stored un-timestamped — a living reference table, not a versioned snapshot.

ETL: `etl/canonical__build_domain_crosswalk.py` · Methodology: `docs/methodology/canonical_domain_crosswalk.md`

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
| 2026-05-22 | Phase 3b: `atana.dane` schema added — Colombia CSECC. `csecc_comercio` (484 rows) + `fx_cop_usd_annual` (11 rows) written as Parquet to `raw/dane/`, pushed to GitHub (`617ff7d`) and synced to MotherDuck. |
| 2026-05-22 | ETL hardening: `inegi__*` and `dane__*` now read the MotherDuck token from a gitignored `.motherduck_token` file and validate it is a JWT before connecting. |
| 2026-05-22 | Phase 3c: `atana.sinca` schema added — Argentina CSC. `csc_comercio` (228 rows) + `csc_participacion` (76 rows) written as Parquet to `raw/sinca/`, pushed to GitHub (`d137218`) and synced to MotherDuck. |
| 2026-05-22 | Phase 3d: `atana.cr_bccr` schema added — Costa Rica CSCCR. `csc_comercio` (150 rows) + `fx_crc_usd_annual` (15 rows) written as Parquet to `raw/cr_bccr/`, pushed to GitHub (`3d9d3e7`) and synced to MotherDuck. The LATAM ingest order (Mexico → Colombia → Argentina → Costa Rica) is complete. |
| 2026-05-23 | Phase 3 (Part C): `canonical.domain_crosswalk` materialised — the harmonisation table (72 rows) mapping all six corpus classifications onto the 2025 UNESCO FCS spine. Written to `curated/domain_crosswalk.parquet`, pushed to GitHub (`94166a2`) and synced to MotherDuck. Build script `etl/canonical__build_domain_crosswalk.py`; methodology `docs/methodology/canonical_domain_crosswalk.md`. |
| 2026-05-23 | Phase 4a: schemas `atana.ibge_estruturais` (8 tables, 2,832 rows — SIIC ch. 2 structural surveys) and `atana.ibge_cempre` (23 tables, 1,202 rows — SIIC ch. 1 CEMPRE) added. Closes the FCS *Cultural and creative goods manufacturing* transversal domain. Parquet written to `raw/ibge_estruturais/` and `raw/ibge_cempre/`. **Built locally — pending GitHub push + MotherDuck sync (João).** |
| 2026-05-23 | Phase 4b: schemas `atana.ibge_tic` (8 tables, 5,387 rows — SIIC ch. 7 ICT access) and `atana.ibge_turismo` (5 tables, 891 rows — SIIC ch. 9 leisure tourism) added. Reaches the FCS *Social participation* transversal domain as a proxy. Parquet written to `raw/ibge_tic/` and `raw/ibge_turismo/`. **Built locally — pending GitHub push + MotherDuck sync (João).** |
| 2026-05-23 | Phase 4 crosswalk extension: `canonical.domain_crosswalk` rebuilt 72 → 82 rows (10 new `ibge_siic` rows — the IBGE SIIC cultural-domain classification). Coverage meter 10/14 → **12/14** FCS domains. **Built locally — pending re-sync (João).** |
| 2026-05-23 | Phase 4c.1: schema `atana.bcb` added — BCB SGS IP-services BoP (series 22777/22778), table `ip_services_bop` (750 rows, monthly 1995–2026). ETL `etl/bcb__sgs_ip_services_to_parquet.py`; João ran the ETL and pushed to GitHub (`e435a1e`). Reaches the FCS Intellectual property domain. Methodology `docs/methodology/bcb_sgs_ip_services.md`. |
| 2026-05-23 | Phase 4c.1 crosswalk extension: `canonical.domain_crosswalk` rebuilt 82 → 83 rows (1 new `bcb` row). Coverage meter **12/14 → 13/14** FCS domains — only *Intangible cultural heritage* unreached (out of scope by decision). Built locally — **pending re-sync (João).** |
