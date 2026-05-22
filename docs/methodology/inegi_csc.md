# Methodology — INEGI Cuenta Satélite de la Cultura de México (CSCM)

Schema `atana.inegi`. Phase 3a of the Atana Data LATAM expansion.

**Source:** INEGI — *Cuenta Satélite de la Cultura de México (CSCM)*, part of the Sistema de Cuentas Nacionales de México, base year 2018.
**Portal:** <https://www.inegi.org.mx/programas/cultura/2018/>
**Coverage:** Mexico, national, annual 2008–2024 (2024 preliminary). Latest release 19 Nov 2025.
**Licence:** INEGI — *Términos de Libre Uso de la Información del INEGI* (open, attribution).
**ETL:** `etl/inegi__csc_xlsx_to_parquet.py`
**Ingested:** 2026-05-22.

---

## 1. What the CSCM is

The CSCM is Mexico's cultural satellite account — a structured, National-Accounts-anchored measurement of the cultural sector. It was first published in 2008 and is methodologically built on the *Sistema de Cuentas Nacionales 2008*, the UNESCO Framework for Cultural Statistics (2009), the Convenio Andrés Bello *Guía Metodológica para la implementación de las Cuentas Satélite de Cultura en Iberoamérica* (2015), and the SCIAN 2018 industrial classification. The cultural sector is delimited as 116 economic-activity classes (72 *características* + 44 *conexas*).

The CSCM's thematic coverage is: production accounts, cultural GDP (PIB), employment (*puestos de trabajo*), persons employed by sex, **supply** (*oferta*) and **use** (*utilización*) of cultural goods and services, and household cultural spending — in current and constant (2018) prices.

## 2. ⚠️ The CSCM has no balance-of-payments module — re-scope note

The Phase 3a scoping memo (`_atana_intel/scoping_inegi_csc_2026-05-16.md`) assumed the CSCM publishes a dedicated cultural foreign-trade module (`Cuadro 3/4/5 — Comercio exterior cultural`, in pesos and USD). **Web verification on 2026-05-22 established that no such module exists.** The CSCM is reported entirely in Mexican pesos and has no balance-of-payments cuadro.

Cultural **imports and exports exist only inside the Cuadros de Oferta y Utilización** (supply-use tables): *Importaciones* on the supply side, *Exportaciones* on the use side. The `atana.inegi.csc_comercio` table is built from the import/export columns of those cuadros. There is **no bilateral / by-partner-country detail** — unlike Brazil's `ibge_comex.tab_10_3`, the CSCM cannot answer "which countries does Mexico trade cultural products with."

A Brazil-style bilateral cultural-trade table for Mexico would require a different source — INEGI's general *Balanza Comercial de Mercancías de México* filtered to cultural HS codes, plus Banxico balance-of-payments for services. That is bookmarked as a Phase 3a.2 follow-up (see `publication_pipeline.md`).

## 3. Source files and the `csc_comercio` table

`atana.inegi.csc_comercio` is built from two CSCM *oferta y utilización* cuadros, by áreas generales y específicas:

| Cuadro | File | Price basis |
|---|---|---|
| CSCM_31 | `CSCM_31.xlsx` | Current prices (*valores corrientes*) |
| CSCM_75 | `CSCM_75.xlsx` | Constant 2018 prices (*valores constantes, precios de 2018*) |

Each cuadro is laid out as: column A = the cultural-area hierarchy (Total cultura → 10 áreas generales → 77 áreas específicas); each year (2008–2024) occupies a 10-column block; within a block the trade columns are *Importaciones C.I.F.* (offset +1) and *Exportaciones de bienes FOB* (offset +9).

### Table grain and columns — `inegi.csc_comercio`

One row per **year × area × flow × price_basis**. 5,984 rows (2 price bases × 17 years × 88 areas × 2 flows).

| Column | Type | Description |
|---|---|---|
| `year` | BIGINT | 2008–2024 |
| `area_level` | VARCHAR | `total` / `area_general` / `area_especifica` |
| `area_general` | VARCHAR | One of the 10 functional areas (`Total cultura` for the total row) |
| `area_especifica` | VARCHAR | Specific area; NULL unless `area_level='area_especifica'` |
| `flow` | VARCHAR | `importacion` / `exportacion` |
| `price_basis` | VARCHAR | `corriente` / `constante_2018` |
| `value_mxn_million` | DOUBLE | Trade value, million MXN. NULL where INEGI reports `NA` (*no aplica*) |
| `value_usd_million` | DOUBLE | **ETL-derived** — `value_mxn_million ÷ fx_rate`. Populated for `corriente` only |
| `fx_rate_mxn_per_usd` | DOUBLE | Annual-average FX used (traceability); `corriente` only |
| `is_preliminary` | BOOLEAN | TRUE for 2024 (INEGI flags it `2024P`) |
| `source_cuadro` | VARCHAR | `CSCM_31` / `CSCM_75` |

### What the trade columns actually cover

Although labelled with merchandise-valuation terms (*C.I.F.* for imports, *FOB* for exports), the columns empirically carry **both cultural goods and cultural services** — service areas such as *Acceso a internet*, *Televisión*, *Publicidad*, *Arquitectónico* and *Conciertos* all carry non-zero export values. The columns should be read as total cultural exports/imports (goods + services combined), not as merchandise-only.

## 4. The 10 functional areas (áreas generales)

| # | Área general | Scope (abridged from CSCM Cuadro 1) |
|--:|---|---|
| 1 | Artes visuales y plásticas | Drawing, photography, painting, sculpture, engraving, galleries |
| 2 | Artes escénicas y espectáculos | Theatre, dance, opera, live artistic and sporting spectacles, venue rental, festivals |
| 3 | Música y conciertos | Recorded and live music, composition, instruments, audio equipment, royalties |
| 4 | Libros, impresiones y prensa | Books, newspapers, magazines, periodicals, printing, news agencies, bookshops |
| 5 | Medios audiovisuales | Film, radio, television, video clips, video games, AV equipment, distribution |
| 6 | Artesanías | Crafts — pottery, textiles, woodwork, metalwork, jewellery, typical foods |
| 7 | Diseño y servicios creativos | Industrial/graphic/interior/fashion/architectural design, advertising, IP in design |
| 8 | Patrimonio cultural y natural | Material/intangible heritage, museums, libraries, protected natural sites |
| 9 | Formación y difusión cultural | Cultural education and dissemination in public/private institutions |
| 10 | Contenidos digitales e internet | Internet TV/radio, streaming, app development, internet access services |

## 5. Domain-mapping table — CSCM → 2025 UNESCO FCS → UNCTAD CER → IBGE NCM

This is the Mexico section of the harmonisation crosswalk designed in `_atana_intel/phase3_schema_design.md` (`canonical.domain_crosswalk`). It lets `atana.inegi` join to `atana.unctad` and `atana.ibge_comex` **while keeping the definitional gaps visible** — never silently reconciled.

| CSCM área general | 2025 FCS domain | FCS type | UNCTAD CER | IBGE NCM ch. | Confidence |
|---|---|---|---|---|---|
| Artes visuales y plásticas | Visual arts and crafts | cultural | CER040 | 97 | approximate |
| Artes escénicas y espectáculos | Performing arts | cultural | CER040 | — | approximate |
| Música y conciertos | Music | cultural | CER040 | 92 | approximate |
| Libros, impresiones y prensa | Books and press | cultural | CER030 | 49 | good |
| Medios audiovisuales | Audiovisual | cultural | CER010 + CER060 | 37 | good |
| Artesanías | Visual arts and crafts | cultural | CER020 | 46, 67, 69, 71 | approximate |
| Diseño y servicios creativos | Design | cultural | CER020 + CER050 | 94 | approximate |
| Patrimonio cultural y natural | Cultural and natural heritage | cultural | CER070 | — | good |
| Formación y difusión cultural | Education in culture | transversal | — | — | good |
| Contenidos digitales e internet | ICT and digital infrastructure | transversal | CER060 (partial) | — | approximate |

Three definitional gaps are findings, not noise (full discussion in `phase3_schema_design.md` §C.4.3): **artesanías** (mostly informal household production — see §7 below), **contenidos digitales** (straddles a cultural and a transversal FCS domain), and **diseño/architecture** (a three-way many-to-many between CSCM, UNCTAD and FCS).

## 6. Currency conversion

CSCM values are **million Mexican pesos** — current prices (`corriente`) or constant 2018 prices (`constante_2018`). The CSCM publishes **no USD figures**.

The `value_usd_million` column is an **Atana ETL derivation**: `value_mxn_million ÷ annual-average MXN/USD`. The FX series lives in `atana.inegi.fx_mxn_usd_annual` (also `raw/inegi/_reference/fx_mxn_usd_annual.parquet`), sourced from World Bank Open Data indicator **PA.NUS.FCRF** (*Official exchange rate, LCU per US$, period average*; underlying source IMF International Financial Statistics).

USD is derived for current-price (`corriente`) rows only — converting constant-2018-peso flows by a current-year rate is not meaningful. **The FX values were transcribed 2026-05-22 and should be re-verified against the live World Bank / Banxico series before any publication relies on the USD figures.**

## 7. Coverage limitations and comparability caveats

**Artesanías carry no recorded trade.** In `csc_comercio`, the *Artesanías* área general is `NA` (NULL) for both imports and exports across all years. Mexican crafts are the single largest cultural-GDP area (18.4% in 2024) and employer (30.2%), but the CSCM captures most of them as *producción cultural de los hogares* — informal household production outside the trade-recorded frame. Any Mexico cultural-trade total therefore **excludes the country's largest cultural domain**. This is the Mexican parallel of the informal-workforce invisibility documented for Brazil.

**No bilateral detail.** `csc_comercio` has no partner-country dimension (see §2).

**Comparability vs Brazilian SIIC / IBGE Comex.** The two systems are not directly comparable and must not be mixed in a query without explicit reconciliation:

- IBGE Comex (`ibge_comex.tab_10_*`) classifies cultural trade by **NCM chapter** with a *pure* vs *partial* cultural split, separates goods (SECEX/MDIC) from audiovisual services (BCB), and reports bilateral partner detail. CSCM classifies by **10 functional areas / SCIAN 2018**, combines goods and services in single COU columns, and has no partner detail.
- IBGE Comex goods are reported in R$ FOB; CSCM trade is in MXN within a supply-use balance.
- The two answer different questions. As with the UNCTAD-vs-IBGE "55.6% vs 5.0%" gap (Atana Note #03), divergence is treated as a finding, never averaged away.

**Base-year / vintage.** This ingest is the base-2018 CSCM. Earlier CSCM vintages used base year 2013 and are not comparable line-for-line.

## 8. Validation (2026-05-22)

The ingest passed every check in the verification pass:

- **Row count** — 5,984 rows: 2 price bases × (17 years × 88 areas × 2 flows). 10 áreas generales + 77 áreas específicas + 1 total confirmed.
- **Hierarchy identity** — Σ(áreas específicas) = their área general, and Σ(áreas generales) = Total cultura, for every year × flow × price basis. Maximum absolute discrepancy **0.0 MXN mn**.
- **Supply-use accounting identity** — in the source cuadros, *Producción + Importaciones + Márgenes* = *Demanda intermedia + Consumo + FBKF + Variación de existencias + Exportaciones* for Total cultura, all 17 years; maximum residual **0.011 MXN mn** (rounding).
- **Spot values** — 2008 Total cultura: imports 82,785.125 / exports 41,085.127 MXN mn. 2024 Total cultura: imports 159,354.092 / exports 103,649.894 MXN mn — a cultural-trade deficit of ≈ 55,704 MXN mn (≈ US$ 3.0 bn at the 2024 average rate).

Note: a web snippet citing "5.6% import share of cultural supply in 2019" does **not** reconcile with the base-2018 CSCM (the 2019 import share of total *oferta* is ≈ 10.3%); the snippet appears to refer to an earlier vintage or a differently-constructed ratio and was not treated as an authoritative validation target.

## 9. Citation

> INEGI (2025). *Cuenta Satélite de la Cultura de México (CSCM), base 2018*. Instituto Nacional de Estadística y Geografía. <https://www.inegi.org.mx/programas/cultura/2018/>

---

*Methodology note for `atana.inegi`. Prepared 2026-05-22. Pairs with `_atana_intel/phase3_schema_design.md` and `_atana_intel/latam_cultural_sources_inventory.md`.*
