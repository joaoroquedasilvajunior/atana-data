# Atana Data Manifest

Canonical catalog of every table available in this repository and in `md:atana`. Keep this file synchronized when adding or modifying datasets.

**Last updated:** 2026-06-04

---

## Conventions

- **Schemas** are organized by source: `unctad`, `ibge_pnadc`, `ibge_comex`, `salic`, `lexml`, `rais`, `inegi`, `dane`, `sinca`, `cr_bccr`, `ibge_estruturais`, `ibge_cempre`, `ibge_tic`, `ibge_turismo`, `bcb`, `inpi`, `ecad`, `cisac`, `ifpi`, `canonical`
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

## `atana.rais` — RAIS formal cultural employment ✅ Live (GitHub `8d874f5`, extended to 2014–2025 in `48996a7`)

Source: RAIS/MTE via Base dos Dados (`br_me_rais`, pulled through BigQuery). Sprint 1 of the RAIS phase — the administrative-register view of formal cultural employment, complementary to the survey-based `ibge_pnadc`. Base dos Dados de-identifies RAIS (no CNPJ, no PIS), so this is a three-table labour-market characterisation, not a firm- or worker-level panel.

| Table | Rows | Description |
|---|---:|---|
| `vinculos_culturais` | ~14 M | One row per cultural employment relationship (vínculo), Cut A ∪ Cut B; flags `in_cut_a` (cultural CNAE) / `in_cut_b` (cultural CBO family), plus derived `cnae_2_classe`, `cbo_familia`, `siic_dominio`, `vinculo_iniciado_no_ano` |
| `estabelecimentos_culturais` | ~2.4 M | One row per cultural establishment (cultural CNAE), with active-link counts |
| `panel_cnae_municipio_ano` | ~120 k | Derived aggregate — Cut A vínculos at `cnae_2_classe × município × ano` grain (median pay, hours, demographic shares) |

**Coverage:** 2014–2025 (vínculos + panel) / 2014–2024 (establecimientos), one `year=YYYY` Parquet partition per table. ⚠️ The 2025 partition of `estabelecimentos_culturais` is present but **0 rows** — Base dos Dados' 2025 establishments partition has `cnae_2_subclasse` NULL across all 13.5 M rows (verified 2026-06-04), so the cultural-CNAE filter returns nothing. Re-pull with `--year 2025 --refresh` when BdD fills the column. **Convention:** active links on 31 Dec; the monetary columns of `vinculos_culturais` and `panel_cnae_municipio_ano` carry `_ipca` deflated twins in base-2024 BRL (IPCA from BCB SGS series 433, cached in `raw/rais/_reference/`). **Cuts:** A = cultural-CNAE employer (33 CNAE classes), B = cultural-CBO-family occupation (62 CBO families); A∪B = formal cultural workforce, A∩B = specialised core.

⚠️ **De-identified** — no CNPJ/PIS; firm- and worker-level linkage (Phase 2b) was cancelled because the MTE FTP is also de-identified. The BigQuery pull needs a billed GCP project (`atana-research`) and credentials — it is a local/credentialed step, never a sandbox one (see `etl/RAIS_2024_INGEST_RUNBOOK.md`).

ETL: `etl/rais__bigquery_to_parquet.py` + `rais__deflate_ipca.py` (both `--staging`-aware, skip MotherDuck under `ATANA_ETL_SKIP_PUSH`) + `rais__build_reference_tables.py` · Methodology: `docs/rais_methodology.md` · Runbooks: `etl/RAIS_SPRINT1_RUNBOOK.md`, `etl/RAIS_2024_INGEST_RUNBOOK.md`

---

## `atana.inegi` — INEGI Cuenta Satélite de la Cultura de México ✅ Live (trade); 🔜 non-trade built locally — pending sync

Source: INEGI *Cuenta Satélite de la Cultura de México* (CSCM), base year 2018. Phase 3a (trade module) + **Phase 5b (non-trade modules, 2026-06-01)** — the first LATAM non-Brazilian production-account + employment view the corpus carries, anchored on the just-released CSCM 2024 boletín (Comunicado 144/25, 19 Nov 2025).

| Table | Rows | Phase | Description |
|---|---:|---|---|
| `csc_comercio` | 5,984 | 3a | Cultural imports/exports from the CSCM Cuadros de Oferta y Utilización, by functional area × year × flow × price basis, 2008–2024, MXN million (current + constant 2018) |
| `fx_mxn_usd_annual` | 17 | 3a | Reference — annual-average MXN/USD exchange rate (World Bank PA.NUS.FCRF), used to derive the USD column of `csc_comercio` |
| `cscm_2024_pib_headline` | 1 | 5b | Cultural PIB MXN 865,682 mi (2.8 % of total economy); empleo 1,430,528 puestos (3.5 %); real growth 2024 +1.2 % vs total +1.3 %; empleo YoY −0.2 % |
| `cscm_2024_pib_by_origin` | 3 | 5b | PIB by institutional origin: actividades de mercado 2.21 % / hogares 0.38 % / gestión pública 0.17 % |
| `cscm_2024_pib_by_area` | 10 | 5b | Cultural PIB by clasificación funcional — sums to 100 %, growth for 5 named (top-3 + bottom-2) |
| `cscm_2024_pib_growth_series` | 16 | 5b | Annual real growth 2009–2024, cultural sector vs total economy (Gráfica 1) |

Schema highlights:
- `csc_comercio`: grain `year × area_level × area_general × area_especifica × flow × price_basis`. `area_level` ∈ {`total`, `area_general` (10), `area_especifica` (77)}. `flow` ∈ {`importacion`, `exportacion`}. `price_basis` ∈ {`corriente`, `constante_2018`}. `value_usd_million` is ETL-derived (current-price rows only).
- ⚠️ The CSCM has **no balance-of-payments module**; `csc_comercio` is the import/export columns of the supply-use tables — no bilateral partner detail. Never mix with `unctad` or `ibge_comex` without explicit reconciliation.
- **Phase 5b caveats** (`docs/methodology/inegi_csc.md` §10): (1) **the artesanías paradox** — Artesanías is the largest cultural PIB area (18.4 %) AND the largest 2024 decliner (−3.8 %); already trade-invisible in `csc_comercio`. (2) **productivity-up / headcount-down 2024** — cultural PIB +1.2 % while empleo −0.2 %, the first CSCM year of this pattern. (3) **three independent music-Mexico signals** — INEGI Música +14.9 %, IFPI Mexico +13.3 % (#10), CISAC Mexico 65.1 % digital share. (4) "Hogares" 0.38 % of PIB ≈ 13.8 % of cultural PIB is **household cultural activity the IBGE SIIC does not measure** — methodological gap on any direct Mexico vs Brazil comparison.

ETLs: `etl/inegi__csc_xlsx_to_parquet.py` (3a) · `etl/inegi__cscm_2024_pib_headline_to_parquet.py` (5b) · `etl/inegi__cscm_2024_pib_by_origin_to_parquet.py` (5b) · `etl/inegi__cscm_2024_pib_by_area_to_parquet.py` (5b) · `etl/inegi__cscm_2024_pib_growth_series_to_parquet.py` (5b) · Methodology: `docs/methodology/inegi_csc.md`

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

## `atana.inpi` — INPI industrial-property register (cultural IP) 🔜 Built — pending sync

Source: INPI — *Tabelas Completas dos Indicadores de Propriedade Industrial* (Anuário Estatístico), 2024 edition. Phase 4c.2 — the cultural-IP *stock* (registration counts), deepening the FCS *Intellectual property* domain that BCB (4c.1) reached as a flow.

**68 tables, ~15,321 rows** — one Parquet per source sheet of the four cultural IP-type workbooks: `prg_*` computer programs (7 tables) · `di_*` industrial designs (18) · `ig_*` geographical indications (10) · `mrc_*` trademarks (33). Annual series 2000–2024. Patents, technology-transfer contracts and IC topographies are not ingested — not cultural IP.

Faithful wide preservation — original cells kept as `c01…` (all VARCHAR). The trademark cultural cut is a Nice-class filter — 41+16 (tight) / +9+28 (wide) — applied downstream on the `mrc_*classe*` tables, not in the ETL. ⚠️ The 5 source `.zip` editions sit in `raw/inpi/_source/` (gitignored — `.gitignore` already excludes `raw/*/_source/`); only the Parquet is committed. ETL: `etl/inpi__indicadores_to_parquet.py` · Methodology: `docs/methodology/inpi_indicadores.md`

---

## `atana.ecad` — ECAD music public-performance royalties ✅ Live v2 · 🔜 v3 built locally — pending re-sync

Source: ECAD — *Escritório Central de Arrecadação e Distribuição*. Phase 4c.3 — the cultural-IP *income* lens; the third reach into the FCS *Intellectual property* domain. **v3 (2026-05-29)** corrects a v2 year-scramble and adds multi-year series, sourced from the ECAD Relatórios Anuais **2020 / 2021 / 2022 / 2024 / 2025** (markitdown-converted) + Transparência 2023. **4 tables, 70 rows.**

| Table | Rows | Years | Description |
|---|---:|---|---|
| `arrecadacao_distribuicao` | 7 | 2019–2025 | Headline series — arrecadação (R$ mi, **years corrected** vs v2), distribuição (R$ exact, 2021–2025; 2021/2022 flagged), titulares, digital share (backfilled 2020–2022), custo operacional (2020 15 % · 2025 9 %), computed YoY |
| `arrecadacao_por_segmento` | 30 | 2020–2025 | Six-way arrecadação split per year (2023 omitted — JPEG-only). The digital trajectory 18→23→22.8→26→33.6 % |
| `distribuicao_por_segmento` | 13 | 2025 | 2025 distribuição thirteen-channel split with `is_digital`; sums to 98.75 % (1.25 % gap documented) |
| `distribuicao_por_titular_tipo` | 20 | 2016–2025 | Nacional vs estrangeiro, autoral + conexa parts, back to 2016 |

⚠️ **Hand-transcribed.** ECAD publishes no machine-readable dataset. Central caveats — `docs/methodology/ecad_relatorio_anual.md` §3 — (1) **arrecadação 2018–2021 was year-scrambled in v2 by the markitdown conversion of the Relatório 2025 chart; v3 corrects it against the contemporary Relatório 2020/2022** (R$ 905.8 mi is the 2020 pandemic low, not 2018; 2018 dropped — not in any report); (2) the structural ≈ 9.5 pp arrecadação-vs-distribuição digital gap; (3) **distribuição 2021/2022 are now suspected to be scrambled too** (2022 implies −26.8 % YoY against +28.3 % arrecadação growth) — *not reordered* (inference), flagged for PDF verification; (4) the 1.25 % distribution-by-segment gap; (5) "nacional" is a *cadastral* category (includes Brazilian subsidiaries of foreign majors) and is **not stable** — overall nacional rose 65 % (2023) → ≈78 % (2025). Multi-year operational metrics (titulares, obras cadastradas, custo, executions) are documented in the methodology §5, not tabled.

ETLs: `etl/ecad__headline_series_to_parquet.py` · `etl/ecad__arrecadacao_por_segmento_to_parquet.py` · `etl/ecad__distribuicao_por_segmento_to_parquet.py` · `etl/ecad__distribuicao_por_titular_tipo_to_parquet.py` · Methodology: `docs/methodology/ecad_relatorio_anual.md` (v1's `ecad_headline.md` is a redirect stub)

---

## `atana.cisac` — CISAC Global Collections Report (global creator-royalty headlines) 🔜 Built locally — pending sync

Source: **CISAC Global Collections Report 2025** (covering 2024 royalty data; published ~November 2025), via the public landing page. Phase 5a of the Atana Data expansion — the global counterpart to `atana.ecad`. CISAC is the global federation of authors' and composers' collective-management societies (228 members across 111 countries; ALCAM is its LATAM bloc — see `canonical.cmo_directory_alcam`).

| Table | Rows | Years | Description |
|---|---:|---|---|
| `gcr_2025_global_by_stream` | 4 | 2024 | Headline by income stream — Digital €5.14 bn / Live & background €3.60 bn / Broadcast €3.94 bn / Total €13.97 bn (+6.6 %) |
| `gcr_2025_global_by_repertoire` | 5 | 2024 | By repertoire — Music €12.59 bn (+7.2 %) · AV €727 mi · Visual arts €219 mi · Drama €208 mi (−3.4 %) · Literature €231 mi |
| `gcr_2025_global_by_region` | 6 | 2024 | By region — West Europe €7.09 bn · Canada/USA €3.52 bn · Asia-Pacific €1.92 bn · **Latin America €786 mi (−0.6 %)** · East Europe €566 mi · Africa €90 mi |
| `gcr_2025_leading_smaller_markets_digital_share` | 10 | 2024 | Top-10 by 2024 digital share + 2015–2024 growth — Mali 89.9 % through Ukraine 63.3 %; **Mexico 65.1 % is the only LATAM cell**; Mali growth NULL (no 2015 baseline) |

⚠️ **Public-landing-page ingest only (Tier 1).** The full GCR PDF (auth-walled at `members.cisac.org`) carries per-country tables and the 2015–2024 historical series; that is **Tier 2** (~1 day, deferred — access routes in `_atana_intel/scoping_cisac_gcr_2025_2026-05-29.md` §5). Caveats — readable in `docs/methodology/cisac_gcr.md` §3 — (1) the **named-streams gap**: Digital + Live & background + Broadcast sum to €12.68 bn vs Total €13.97 bn; the €1.29 bn residual (~9.2 %) = physical formats + private copying (documented, not allocated); (2) **LATAM is the only declining region in 2024** (−0.6 %); (3) **Music = ~90 % of global** — scale context for the corpus's music-heavy Brazilian work; (4) currency is **EUR** while `atana.ecad` is **BRL** — any direct ECAD ↔ GCR-LATAM reconciliation needs an EUR/BRL FX series (not yet in corpus); (5) the GCR text gives large-market digital-share comparators in prose (USA 27.1 % · France 13.9 % · UK 11.4 %) — kept in methodology §4, not in the table (which stays strictly to CISAC's "leading smaller markets" framing).

ETLs: `etl/cisac__gcr_2025_global_by_stream_to_parquet.py` · `etl/cisac__gcr_2025_global_by_repertoire_to_parquet.py` · `etl/cisac__gcr_2025_global_by_region_to_parquet.py` · `etl/cisac__gcr_2025_leading_smaller_markets_to_parquet.py` · Methodology: `docs/methodology/cisac_gcr.md` · Scoping: `_atana_intel/scoping_cisac_gcr_2025_2026-05-29.md`

---

## `atana.ifpi` — IFPI Global Music Report (global recorded-music revenue) 🔜 Built locally — pending sync

Source: **IFPI Global Music Report 2026** (covering 2025 recorded-music revenue; press release 18 March 2026). Phase 5b of the Atana Data expansion — the *recorded-music* (record-label / master-recording) lens, structurally distinct from the *author-royalty* (CMO) lens carried by `atana.ecad` (Brazil) and `atana.cisac` (global). Three music-money lenses now in the corpus.

| Table | Rows | Years | Description |
|---|---:|---|---|
| `gmr_2026_global_headline` | 1 | 2025 | Global recorded-music revenue US$ 31.7 bn (+6.4 %), 11th consecutive year of growth, 837 mi paid streaming users |
| `gmr_2026_global_by_format` | 5 | 2025 | Streaming (total) 69.6 %, Paid sub-stream (subset) 52.4 % / +8.8 %, Physical +8.0 %, Performance rights US$ 2.9 bn / +0.3 %, Total |
| `gmr_2026_global_by_region` | 7 | 2025 | USA & Canada +3.5 % / Europe +5.6 % / Asia +10.9 % / **LATAM +17.1 %** (fastest, streaming 88.1 %) / Australasia +1.5 % / MENA +15.2 % / Sub-Saharan Africa +15.2 % |
| `gmr_2026_top_markets` | 12 | 2025 | 12 countries named in press release; 7 with global rank — USA #1, Japan #2, China #4, **Brazil #8 (+14.1 %)**, Canada #9, **Mexico #10 (+13.3 %)**, Australia #13 |

⚠️ **Tier 1 public-press-release ingest only.** The GMR 2026 Premium Edition holds the full top-200 country list, 2015-onwards historical series, and format-by-region cross-tabs — paywalled, Tier 2 deferred. Caveats — `docs/methodology/ifpi_gmr.md` §3 — (1) **the IFPI ↔ CISAC LATAM divergence**: IFPI 2025 LATAM +17.1 % recorded-music vs CISAC 2025 LATAM −0.6 % author-royalties (a +17.7 pp gap on the same region/period = recorded-music label revenue vs CMO author royalties = different value-chain layers); (2) named-format coverage ≈ 79 % of total (Streaming 69.6 % + Performance rights 9.1 %); the ~21 % residual is Physical + downloads/sync, not separately stated in the press release; (3) USD figures restated annually by IFPI on revised FX, so historical values can change retrospectively; (4) the top-markets table is the press-release SUBSET, not the GMR's full ranking. Brazil + Mexico both top-10 is the LATAM corpus headline.

ETLs: `etl/ifpi__gmr_2026_global_headline_to_parquet.py` · `etl/ifpi__gmr_2026_global_by_format_to_parquet.py` · `etl/ifpi__gmr_2026_global_by_region_to_parquet.py` · `etl/ifpi__gmr_2026_top_markets_to_parquet.py` · Methodology: `docs/methodology/ifpi_gmr.md`

---

## `atana.luminate` — Luminate Year-End Music Industry Report ✅ Live (GitHub `9f8611b` + MotherDuck)

Source: **Luminate Year-End 2025 Music Industry Report** (released January 2026), via the public landing page; figures verified against Music Business Worldwide coverage (22 Jan 2026). Phase 5c — the *consumer / catalog-supply* lens at global scale. **Fourth music-money lens** in the corpus after `atana.ecad` (BR author payout), `atana.cisac` (global CMO collection) and `atana.ifpi` (global label revenue) — each at a different stage of the value chain.

| Table | Rows | Years | Description |
|---|---:|---|---|
| `ye2025_global_headline` | 1 | 2025 | 5.1 tn global ondemand audio streams (+9.6 %), ex-US 3.7 tn (+11.6 %), US 1.4 tn (+4.6 %); 253 mi tracks on streaming year-end; **47.6 % of catalog under 10 streams** (long-tail saturation) |
| `ye2025_top_markets_paid_share` | 4 | 2025 | The 4-country half-of-global-paid cell — USA (31 % share), Mexico (+50.9 bn YoY), Brazil (+38.6 bn YoY), Germany |
| `ye2025_us_genre_share` | 5 | 2025 | US-only genre split — R&B/Hip-Hop 25.5 % (−0.8 pp), Rock 15.3 % (flat), Pop 12.6 % (+0.3), **Latin 8.0 % (+0.6 pp = largest gainer)**, Christian/Gospel 3.5 % (+0.4) |
| `ye2025_most_local_markets` | 4 | 2025 | Most-local repertoire markets — India 79.2 %, **Brazil 75.2 %**, Turkey 69.9 %, Nigeria 62.2 % |

⚠️ **Tier 1 — public headlines only.** Per-track and per-artist Luminate Connect data are paywalled (Tier 2 deferred). Central caveats — `docs/methodology/luminate_ye.md` §6 — (1) "local repertoire" measured by *language*, not rights-ownership country (a Brazilian Portuguese song owned by Universal Music Brasil still counts as local — that's exactly the gap that drives the Authenticity Paradox); (2) Luminate excludes some platforms (e.g., specific China-based services) — residual offset for IFPI / CISAC cross-reads; (3) free vs paid stream split partial in public summary. **The cross-lens reading is the value:** Brazil 75.2 % local consumption × +38.6 bn paid-stream growth × IFPI LATAM +17.1 % × CISAC LATAM −0.6 % = the **Authenticity Paradox in stereo** — value flows to platform + label, not to creator + CMO. Mexico is the convergence-pole (IFPI México +13.3 % × INEGI Música y conciertos +14.9 % × Luminate +50.9 bn); Brazil is the divergence-pole.

ETLs: `etl/luminate__ye2025_global_headline_to_parquet.py` · `etl/luminate__ye2025_top_markets_paid_share_to_parquet.py` · `etl/luminate__ye2025_us_genre_share_to_parquet.py` · `etl/luminate__ye2025_most_local_markets_to_parquet.py` · Methodology: `docs/methodology/luminate_ye.md`

---

## `atana.tcu` — TCU PNAB audit (governance & accountability lens) ✅ Live (GitHub `9f8611b` + MotherDuck)

Source: **Tribunal de Contas da União**, *Acórdão 1709/2025 - Plenário* (sessão 30/07/2025, relator Augusto Nardes, processo TC 025.939/2024-6). Phase 5c — the corpus's **first governance/audit lens**. Pairs SALIC (what got funded) with TCU (what was held to account) over the same fomento system — the *Política Nacional Aldir Blanc* (PNAB), R$ 15 bn / R$ 3 bn-per-year.

| Table | Rows | Years | Description |
|---|---:|---|---|
| `pnab_governance_assessment` | 4 | 2025 | 4 governance dimensions × PNAB × 2025, with TCU verbatim ratings and ordinal scoring 1-3. **Mean maturity 1.75 / 3**; no dimension reached "institucionalizada" (3); **Gestão de riscos = 1** (the lowest TCU rating, the flagged concern) |
| `pnab_deliberations` | 4 | 2025 | The TCU's recommendations to **MinC** — formal strategic planning with theory of change, short/medium/long-term targets, multidimensional indicators (eficiência / eficácia / efetividade / **equidade**), transparent baseline |

⚠️ TCU PNAB audits are **episodic, not annual** — cadence depends on TCU's *Relatório de Fiscalizações em Políticas Públicas* priority. Central caveats — `docs/methodology/tcu_pnab.md` §6 — (1) the **equidade** deliberation dimension is the direct policy entry-point for Atana's distributional decomposition (Análises 1-3, 12, 17-20); (2) the R$ 22 bn / ~29.7 k projects pending PC at MinC + Ancine is a SEPARATE TCU finding (likely a future `pnab_pendings` table in Tier 2); (3) verbatim recommendations transcribed; full Acórdão PDF available but not extracted in this v1; (4) maturity scale is TCU's own (per the Referencial de Controle de Políticas Públicas) — not internationally comparable without caveats. The FCS has no "cultural-policy governance" domain — fomento crosses all 7 cultural domains by design; this is why the crosswalk row is `approximate` with a bundle value.

ETLs: `etl/tcu__pnab_governance_assessment_to_parquet.py` · `etl/tcu__pnab_deliberations_to_parquet.py` · Methodology: `docs/methodology/tcu_pnab.md`

---

## `atana.oecd_ai` — OECD AI Papers (methodological frame for the Atana AI Exposure Index) ✅ Live (GitHub `9f8611b` + MotherDuck)

Source: **OECD Artificial Intelligence Papers** series (OECD-OPSI), **No. 59** *The OECD AI exposure measure: Mapping the OECD AI Capability Indicators to occupations* (May 2026, 58 pp) and **No. 60** *Benefits of AI Openness* (3 Jun 2026, 46 pp; G7 discussion paper at the French presidency's request). Phase 5c — methodological-frame source for the Atana AI Exposure Index (Vol. 1) and Vol. 2.

| Table | Rows | Years | Description |
|---|---:|---|---|
| `papers_headline` | 2 | 2026 | One row per paper, with 3 headline findings each + `atana_relevance`. No. 59 builds the AI Capability Gap Index across OECD-member labour markets (incl. **creativity** as one of 10 domains); No. 60 finds open models ≈ 90 % of closed performance, positive significant correlation between open-source AI activity and growth across 33 countries, and that **AI openness shifts value capture downstream** — to SMEs, public institutions, and creators |
| `ai_capability_domains` | 10 | — | The 10 OECD AI capability domains (language, social interaction, problem solving, **creativity ★**, metacognition, knowledge, learning/memory, vision, manipulation, robotic intelligence) with cultural-occupation entry-points |

⚠️ **Methodological-frame source — NOT a cultural classification.** Central caveats — `docs/methodology/oecd_ai_papers.md` §6 — (1) the papers measure OECD labour markets directly; LATAM not in analytical scope; (2) the OECD's `creativity` domain is functional ("production of novel and valuable outputs") and is *not* the same construct as the FCS creative-domain spine — mapping is methodological-frame, not classification-equivalence; (3) Tier 1 captures headline findings; full-PDF datasets (capability score tables, 33-country growth-correlation panel) are Tier 2 / not scheduled; (4) AI capability scoring updates annually — schema rotates when No. 59's successor drops. **Cross-lens role:** with Stanford HAI's Foundation Model Transparency Index (58 → 40 between editions), forms a three-corner methodological frame for Atana Index Vol. 2 — **exposure × openness × transparency**.

ETLs: `etl/oecd_ai__papers_headline_to_parquet.py` · `etl/oecd_ai__ai_capability_domains_to_parquet.py` · Methodology: `docs/methodology/oecd_ai_papers.md`

---

## `atana.macro` — Macro reference series (FX, deflators) 🔜 Built locally — pending first sync (NEW schema)

Cross-cutting convenience reference series used to derive comparable views of BRL-denominated corpus tables. **Not cultural statistics** — documented derivation inputs, in the convention of the per-country `fx_*_usd_annual` tables.

| Table | Rows | Years | Description |
|---|---:|---|---|
| `fx_brl_usd_annual` | 32 | 1994–2025 | Annual-average BRL/USD. Primary: World Bank PA.NUS.FCRF (same indicator as the MX/CO/CR FX tables); 2025 from BCB SGS 3698 (monthly mean, annualised), flagged in `source`. Build-time WB×BCB cross-check ≤2 % on all overlapping years. |
| `fx_brl_eur_annual` | 27 | 1999–2025 | Annual-average BRL/EUR from BCB SGS 21619 (daily, annualised; <200-obs years dropped). Unblocks the A24 EUR/BRL precision caveat (ECAD R$ × CISAC €: 2025 = 6.3095 measured vs ~6.03 eyeballed). |

`raw/macro/ipca.parquet` (BCB SGS 433, the RAIS deflator reference) logically belongs to this schema and should be registered here at the next RAIS touch.

**Validation:** byte-identical reruns; external benchmark — `ibge_comex.tab_10_1` 2024 cultural exports convert to **US$ 747.6 mi** vs the independently derived US$ 746 mi published in Análise 10 figT8 (0.2 %). **Unlocks:** Brazil's row in the cross-LATAM FCS-domain trade comparison (`phase6_corpus_criterion_and_vol2_scoping.md` §2). ⚠️ Flow-vs-stock conversion rules in the methodology note.

ETL: `etl/macro__fx_brl_annual_to_parquet.py` (API fetch + cache in `raw/macro/_source/`, `--refresh` for new vintages — a DB-updater job once live) · Methodology: `docs/methodology/macro_fx_brl.md`

---

## `atana.canonical` — Curated analytical snapshots

Read-only views and tables that power published analyses. **Do not modify directly** — regenerate via build scripts and versioned datasets.

### `canonical.domain_crosswalk` ✅ Live at 90 rows (`9f8611b` + MotherDuck synced)

The Atana harmonisation crosswalk — maps every cultural-statistics classification in the corpus onto one common spine. **90 rows**, one per classification code (Phase 3 built 72; Phase 4 added 10 `ibge_siic` rows and the `bcb` / `inpi` / `ecad` rows; Phase 5 added `cisac` / `ifpi` and most recently `luminate` / `tcu` / `oecd_ai`).

| Column | Type | Description |
|---|---|---|
| `source_schema` | VARCHAR | `fcs2025` / `inegi` / `dane` / `sinca` / `cr_bccr` / `unctad` / `ibge_comex` / `ibge_siic` / `bcb` / `inpi` / `ecad` / `cisac` / `ifpi` / `luminate` / `tcu` / `oecd_ai` |
| `source_system` | VARCHAR | Human-readable classification name |
| `source_code` | VARCHAR | Code within that classification |
| `source_label` | VARCHAR | Label within that classification |
| `fcs2025_domain` | VARCHAR | The spine — a 2025 UNESCO FCS domain, a bundle, or NULL |
| `fcs2025_domain_type` | VARCHAR | `cultural` / `transversal` (or a verbatim bundle / NULL) |
| `unctad_cer` | VARCHAR | Nearest UNCTAD CER / service code; NULL if none |
| `ibge_ncm_chapter` | VARCHAR | Nearest IBGE NCM chapter(s); NULL if not a traded good |
| `mapping_confidence` | VARCHAR | `exact` / `good` / `approximate` / `no-equivalent` |
| `notes` | VARCHAR | The definitional gap, stated explicitly (`★` flags a finding) |

Row composition: `fcs2025` 14 (the spine — 7 cultural + 7 transversal) · `inegi` 10 · `dane` 22 · `sinca` 2 · `cr_bccr` 4 · `unctad` 15 · `ibge_comex` 5 · `ibge_siic` 10 · `bcb` 1 · `inpi` 1 · `ecad` 1 · `cisac` 1 · `ifpi` 1 · `luminate` 1 · `tcu` 1 · `oecd_ai` 1. It turns the isolated national schemas into a cross-queryable layer — a query joins any national CSC, the IBGE SIIC, the BCB account, the INPI register, the ECAD/CISAC/IFPI/Luminate music series, the TCU governance assessment or the OECD AI methodological frame to the FCS spine through this one table. Definitional gaps are kept visible (`mapping_confidence`, `notes`), never silently reconciled. The build script's coverage meter still reaches **13/14** FCS domains (only *Intangible cultural heritage* remains, out of scope by decision). Stored un-timestamped — a living reference table, not a versioned snapshot.

ETL: `etl/canonical__build_domain_crosswalk.py` · Methodology: `docs/methodology/canonical_domain_crosswalk.md`

### `canonical.cmo_directory_alcam` ✅ Live locally — pending push + sync

The LATAM music-CMO reference directory. **13 rows**, one per member society of ALCAM (*Alianza Latinoamericana de Autores y Compositores de Música*, alcammusica.org), across 12 countries (Brazil has two: ABRAMUS + UBC).

| Column | Type | Description |
|---|---|---|
| `country` | VARCHAR | English country name |
| `country_iso3` | VARCHAR | ISO 3166-1 alpha-3 |
| `society_acronym` | VARCHAR | Short name as used by ALCAM (e.g. `SADAIC`, `SCD`) |
| `society_name` | VARCHAR | Best-known full Spanish/Portuguese form of the society's name; the URL remains authoritative |
| `url` | VARCHAR | Official society URL |
| `in_atana_corpus` | BOOLEAN | `true` iff the society's data is reachable via an existing corpus schema |
| `linked_atana_schema` | VARCHAR | The corpus schema the society is reachable through; `'ecad'` for the Brazilian pair, `NULL` otherwise |
| `source_url` | VARCHAR | The ALCAM /sociedades page captured |
| `as_of` | DATE | Capture date (2026-05-25) |

A join key for any future per-society data across the 11 non-Brazilian ALCAM countries. **Not** a classification crosswalk (it is a directory of entities, not codes) — it does not extend `canonical.domain_crosswalk`. The Brazilian pair ABRAMUS + UBC carries `linked_atana_schema = 'ecad'`, tying the creator-side societies to the existing collection-side data; the other 11 carry `NULL` until per-society data is ingested (Tier 2 / Phase 5 candidate; see `_atana_intel/scoping_alcammusica_2026-05-25.md` §4).

⚠️ `society_name` is best-known canonical form, not source-captured — the ALCAM /sociedades page only prints acronyms + country names. The URL of each society is the authoritative source for the official name. For `AEI` (Guatemala) the official expansion was not separately verified — see methodology §3.

ETL: `etl/canonical__build_cmo_directory_alcam.py` (inline data → DuckDB COPY → Parquet, idempotent, byte-identical reruns) · Methodology: `docs/methodology/cmo_directory_alcam.md`

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
| 2026-05-23 | Phase 4c.1 crosswalk extension: `canonical.domain_crosswalk` rebuilt 82 → 83 rows (1 new `bcb` row). Coverage meter **12/14 → 13/14** FCS domains — only *Intangible cultural heritage* unreached (out of scope by decision). Synced — GitHub (`ce72a56`) + MotherDuck `atana.canonical.domain_crosswalk` (83 rows). |
| 2026-05-23 | Phase 4c.2: `atana.inpi` schema added — INPI Tabelas Completas / Anuário 2024, the cultural-IP register. 68 tables (~15,321 rows) from the four cultural IP-type workbooks (computer programs, industrial designs, geographical indications, trademarks), annual series 2000–2024. ETL `etl/inpi__indicadores_to_parquet.py`; methodology `docs/methodology/inpi_indicadores.md`. **Built locally — pending GitHub push + MotherDuck sync (João).** |
| 2026-05-23 | Phase 4c.2 crosswalk extension: `canonical.domain_crosswalk` rebuilt 83 → 84 rows (1 new `inpi` row). Coverage meter unchanged at **13/14** — INPI deepens *Intellectual property*, already reached by BCB. **Built locally — pending re-sync (João).** |
| 2026-05-23 | Phase 4c.3: `atana.ecad` schema added — ECAD music public-performance royalties, headline series `arrecadacao_distribuicao` (3 rows, 2023–2025). ECAD publishes no machine-readable data — figures transcribed from the Transparência pages. ETL `etl/ecad__headline_series_to_parquet.py`; methodology `docs/methodology/ecad_headline.md`. **Built locally — pending GitHub push + MotherDuck sync (João).** |
| 2026-05-23 | Phase 4c.3 crosswalk extension: `canonical.domain_crosswalk` rebuilt 84 → 85 rows (1 new `ecad` row). Coverage unchanged at **13/14** — ECAD is the third lens on *Intellectual property*. **Phase 4 complete:** 10/14 → 13/14 FCS domains; only *Intangible cultural heritage* unreached (out of scope by decision). **Built locally — pending re-sync (João).** |
| 2026-05-25 | Documentation: `atana.rais` section added to this manifest. The schema has been live since Sprint 1 (GitHub `8d874f5`, 3 tables, 2014–2023) but was undocumented here. |
| 2026-05-25 | ETL hardening: `rais__bigquery_to_parquet.py` and `rais__deflate_ipca.py` gained a `--staging` flag (output → `raw/rais/_staging/`) and an `ATANA_ETL_SKIP_PUSH` guard on the MotherDuck sync; `.gitignore` now excludes `raw/*/_staging/`. Enables the DB-updater to stage a RAIS refresh safely. |
| 2026-05-25 | `canonical.cmo_directory_alcam` added — Tier 1 of the ALCAM Música scoping. **13 rows** (12 LATAM countries × music creator-side CMO members of ALCAM, Brazil ×2), with a `linked_atana_schema` pointer that ties ABRAMUS/UBC to `atana.ecad`. Build script `etl/canonical__build_cmo_directory_alcam.py`; methodology `docs/methodology/cmo_directory_alcam.md`; output `curated/cmo_directory_alcam.parquet` + `.meta.json`. **Built locally — pending GitHub push + MotherDuck sync (João).** |
| 2026-05-28 | `atana.ecad` v2 expansion — 1 table → **4 tables**, sourced from the ECAD *Relatório Anual 2025* PDF (markitdown-converted). `arrecadacao_distribuicao` extended 3 → 8 rows (2018–2025) with schema break (`_brl_billion` → `_brl_mi`/`_brl`); three new sibling tables — `arrecadacao_por_segmento` (6 rows), `distribuicao_por_segmento` (13 rows), `distribuicao_por_titular_tipo` (10 rows). 4 central caveats foregrounded in row `notes` + methodology §3, notably a flagged 2022 distribuição anomaly that needs PDF re-verification. New methodology doc `docs/methodology/ecad_relatorio_anual.md`; v1's `ecad_headline.md` reduced to a redirect stub. **Built locally — pending GitHub push + MotherDuck re-sync (João).** |
| 2026-05-28 | `canonical.domain_crosswalk` refreshed — descriptive note on the `ecad` row updated to reflect the v2 4-table scope; `derived_from` meta repoints to `ecad_relatorio_anual.md`. Row count unchanged (still 85; coverage 13/14). **Built locally — pending re-sync.** |
| 2026-05-29 | `atana.ecad` **v3 — correction + multi-year** from a cross-source of the ECAD Relatórios 2020/2021/2022/2024 + Transparência 2023. (a) **Corrected a v2 arrecadação year-scramble** (2018–2021 were permuted by markitdown; R$ 905.8 mi pandemic low was mis-yeared 2018 → 2020) — verified against contemporary reports; 2018 dropped; `arrecadacao_distribuicao` now 7 rows (2019–2025) with digital share + custo + titulares backfilled. (b) **`arrecadacao_por_segmento` extended 6 → 30 rows** (2020–2025 ex-2023). (c) **`distribuicao_por_titular_tipo` extended 10 → 20 rows** (back to 2016). `distribuicao_por_segmento` unchanged (13). atana.ecad total 37 → **70 rows**. Distribuição 2021/2022 flagged as likely-scrambled (not reordered). Crosswalk `ecad` note refreshed (still 85 rows). **Built locally — pending GitHub push + MotherDuck re-sync (João).** |
| 2026-05-29 | **Phase 5a — `atana.cisac` schema added** (CISAC Global Collections Report 2025 → public landing page, Tier 1 ingest). **4 tables, 25 rows** — `gcr_2025_global_by_stream` (4 rows × 2024), `gcr_2025_global_by_repertoire` (5), `gcr_2025_global_by_region` (6), `gcr_2025_leading_smaller_markets_digital_share` (10). EUR millions, 2024 reference year. The first global creator-royalty frame the corpus carries; LATAM €786 mi (−0.6 %) is the comparable-aggregate row that ties `atana.ecad` (Brazil) and `canonical.cmo_directory_alcam` (LATAM CMO directory) into a global structure. `canonical.domain_crosswalk` extended 85 → **86 rows** (1 new `cisac` row → *Intellectual property*); coverage 13/14 unchanged. Tier 2 (full PDF, country-level + 2015–2024 historical series) deferred — PDF auth-walled. **Built locally — pending GitHub push + MotherDuck sync (João).** |
| 2026-06-01 | **Phase 5b — `atana.ifpi` schema added** (IFPI Global Music Report 2026 → public press release, Tier 1 ingest, 2025 data). **4 tables, 25 rows** — `gmr_2026_global_headline` (1), `gmr_2026_global_by_format` (5), `gmr_2026_global_by_region` (7), `gmr_2026_top_markets` (12 countries). USD billions/millions. The **recorded-music** lens; third music-money lens in the corpus after `atana.ecad` (BR author royalties) and `atana.cisac` (global author royalties). **Headline cross-source finding:** LATAM +17.1 % in IFPI vs −0.6 % in CISAC = the value-chain gap between recorded-music revenue (label side) and author-royalty collection (CMO side). Brazil + Mexico both in IFPI top-10. `canonical.domain_crosswalk` extended 86 → **87 rows** (1 new `ifpi` row → *Intellectual property*); coverage 13/14 unchanged. Tier 2 (Premium Edition: top-200 countries, 2015–2024 historical, format-by-region cross-tabs) deferred — paywalled. **Built locally — pending GitHub push + MotherDuck sync (João).** |
| 2026-06-01 | **Phase 5b — `atana.inegi` extended with non-trade modules** from the CSCM 2024 boletín (Comunicado 144/25, INEGI, 19 Nov 2025). 4 new tables × 30 new rows: `cscm_2024_pib_headline` (1), `cscm_2024_pib_by_origin` (3), `cscm_2024_pib_by_area` (10), `cscm_2024_pib_growth_series` (16). First LATAM non-Brazilian production-account + employment cells in the corpus. **Headline findings:** Mexican cultural PIB 2.8 % of total economy (MXN 865,682 mi), real growth +1.2 %; the **artesanías paradox** (largest area + largest decliner); **productivity-up / headcount-down** in 2024 (PIB +1.2 % / empleo −0.2 %, first such year); Música y conciertos +14.9 % (fastest grower) — cross-confirms IFPI Mexico +13.3 % (#10) and CISAC Mexico 65.1 % digital share. Crosswalk inherits the 10 existing `inegi` áreas rows — no new rows; coverage unchanged. **Built locally — pending GitHub push + MotherDuck sync (João).** |
| 2026-06-04 | **RAIS 2024 + 2025 ingested** ✅ Live on GitHub `48996a7` + MotherDuck. `atana.rais.*` extended **2014–2023 → 2014–2025** (vínculos + panel) and 2014–2024 for establecimientos. 6 new year-partitions across 3 tables, **~3.2 M new vínculos rows** (2024: 1.57 M, 2025: 1.62 M). IPCA cache extended to 12 years (2014–2025); deflate script's `dataFinal` updated. ⚠️ **2025 establishments came back at 0 rows** — Base dos Dados' 2025 establishments partition has `cnae_2_subclasse` NULL across all 13.5 M rows (verified 2026-06-04 via direct BdD probe); the 2025 vínculos table is unaffected (its own per-relationship CNAE column is populated). Re-pull 2025 establishments via `--year 2025 --refresh` when BdD fills the column. **Headline finding from the new data:** real cultural wages dropped from R$ 3,549 (2022) → R$ 3,002 (2025) in 2024 BRL — **−15.4 % real over three years** even while vínculos grew +12.3 % — extends Análise 11 by two years and confirms a continued real-terms decline. |
| 2026-06-04 | **Phase 5c — three new schemas added** ✅ Live (GitHub `9f8611b` + MotherDuck), acting on the W23 Atana Monday Briefing's four recommendations (option D). (1) **`atana.luminate`** (4 tables, 14 rows × 2025) — fourth music-money lens closing the value-chain frame, headline figures from the Luminate Year-End 2025 Music Industry Report verified against MBW coverage; key cell is Brazil 75.2 % local repertoire × +38.6 bn paid-stream growth, the **Authenticity Paradox in stereo** when cross-read with IFPI LATAM +17.1 % and CISAC LATAM −0.6 %. (2) **`atana.tcu`** (2 tables, 8 rows × 2025) — first governance/audit lens in the corpus, transcribing TCU Acórdão 1709/2025 on PNAB; mean governance maturity 1.75 / 3, **Gestão de riscos = 1** (TCU's flagged concern), and the **equidade** deliberation aligns directly with Atana's distributional decomposition. (3) **`atana.oecd_ai`** (2 tables, 12 rows) — methodological-frame source for the Atana AI Exposure Index (Paper No. 59 May 2026 with `creativity` as one of 10 explicit AI capability domains; Paper No. 60 Jun 2026 on AI openness shifting value capture downstream); with HAI's Foundation Model Transparency Index gives Vol. 2 a three-corner frame (exposure × openness × transparency). `canonical.domain_crosswalk` extended **87 → 90 rows** (3 new rows, one per new schema), all ★-flagged as approximate/good methodological-or-frame mappings; coverage 13/14 unchanged. Three methodology docs written. Same commit also batched the previously-pending Phase 5b items (IFPI + INEGI CSCM 2024 + federal/SALIC additions). |
| 2026-06-10 | **Phase 6a (first item) — `atana.macro` schema added (NEW)** — BRL annual FX reference series: `fx_brl_usd_annual` (32 rows, 1994–2025; World Bank PA.NUS.FCRF primary + BCB SGS 3698 for 2025, WB×BCB cross-check ≤2 %) and `fx_brl_eur_annual` (27 rows, 1999–2025; BCB SGS 21619 daily annualised). Closes the "Brazil can't join the cross-LATAM USD comparison" gap (phase6 scoping §2.2) and the A24 EUR/BRL caveat (2025 = 6.3095 measured). External benchmark: ibge_comex 2024 cultural exports → US$ 747.6 mi vs A10 figT8's independently derived US$ 746 mi (0.2 %). ETL `etl/macro__fx_brl_annual_to_parquet.py` (API cache in `raw/macro/_source/`); methodology `docs/methodology/macro_fx_brl.md`. Same date: `sinca_csc.md` §8 added — Argentina's USD incommensurability documented as a Vol 2 finding, not an ingest gap. **Built locally — pending GitHub push + first MotherDuck sync of the new schema (João).** |
