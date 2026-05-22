# Methodology — Cuenta Satélite de Cultura de Costa Rica (CSCCR)

Schema `atana.cr_bccr`. Phase 3d of the Atana Data LATAM expansion — the fourth non-Brazilian national source, after Mexico (`atana.inegi`), Colombia (`atana.dane`) and Argentina (`atana.sinca`).

**Source:** *Cuenta Satélite de Cultura de Costa Rica* (CSCCR), built by the CICSC consortium — Ministerio de Cultura y Juventud, Banco Central de Costa Rica, INEC, Programa Estado de la Nación, CONARE. Data hosted by the BCCR.
**Portal:** <https://www.bccr.fi.cr/indicadores-economicos/cuentas-tematicas/cuenta-satelite-de-cultura>
**Coverage:** Costa Rica, national, annual **2010–2024**.
**Licence:** open data — Costa Rican official statistics (BCCR / MCJ).
**ETL:** `etl/cr_bccr__csc_to_parquet.py`
**Ingested:** 2026-05-22.

---

## 1. What the CSCCR is

The CSCCR is Costa Rica's cultural satellite account — an extension of the national accounts that measures cultural GDP, employment, production, financing and **foreign trade**. It is governed by an inter-institutional commission (CICSC) and follows the Convenio Andrés Bello methodological framework.

Unlike Mexico's CSCM and Colombia's CSECC — where cultural trade had to be extracted from the supply-use tables — the CSCCR publishes a **dedicated, consolidated foreign-trade table**. This ingest takes that table directly.

## 2. The `csc_comercio` table

Built from one sheet — `Comercio exterior cultural` — of the BCCR workbook `Resumen de indicadores.xlsx`. Exports and imports of **four cultural sectors**, 2010–2024, in **millions of colones (CRC)**.

One row per **year × sector × flow**. **150 rows** (15 years × 5 sectors-incl-Total × 2 flows).

| Column | Type | Description |
|---|---|---|
| `year` | BIGINT | 2010–2024 |
| `sector` | VARCHAR | `Editorial` / `Publicidad` / `Audiovisual` / `Música` / `Total` |
| `flow` | VARCHAR | `exportacion` / `importacion` |
| `value_crc_million` | DOUBLE | Trade value, million CRC. NULL where the source reports `n.d.` |
| `value_usd_million` | DOUBLE | **ETL-derived** — `value_crc_million ÷ fx_rate` |
| `fx_rate_crc_per_usd` | DOUBLE | Annual-average FX used (traceability) |
| `full_sector_coverage` | BOOLEAN | TRUE for 2010–2021, FALSE for 2022–2024 — see §3 |

A companion reference table, `cr_bccr.fx_crc_usd_annual` (15 rows), holds the colón/USD series.

## 3. ⚠️ Coverage break at 2022

The CSCCR trade table covers all four cultural sectors only for **2010–2021**. From **2022 onward only the Editorial sector is reported** — Publicidad, Audiovisual and Música show `n.d.` (no disponible) — and the published year **totals collapse to Editorial-only**.

This is captured explicitly:
- `full_sector_coverage` = TRUE for 2010–2021, FALSE for 2022–2024.
- The 18 NULL `value_crc_million` cells are exactly the three non-Editorial sectors × 2022–2024 × 2 flows.
- The `Total` rows for 2022–2024 equal the Editorial figure and are **not comparable** with the 4-sector totals of 2010–2021.

Any time-series analysis of Costa Rican cultural trade should either stop at 2021 or restrict to the Editorial sector — never compare a 2022–2024 total with a pre-2022 total. The break is a finding, surfaced rather than smoothed over.

## 4. Currency conversion

CSCCR trade values are **millions of colones**, current prices. `value_usd_million` is an **Atana ETL derivation** — `value_crc_million ÷ annual-average CRC/USD`. The FX series (`cr_bccr.fx_crc_usd_annual`) is sourced in two parts:

- **2010–2021** — from the CSCCR's own `TC` sheet (Banco Central de Costa Rica annual average). Best provenance: the rate is published inside the same source workbook.
- **2022–2024** — supplemented from World Bank / CEIC annual averages (the CSCCR `TC` sheet stops at 2021). The 2023 value is transcribed approximate. **Re-verify the 2022–2024 rates against the live BCCR / World Bank series before any publication relies on the USD figures.**

Costa Rica's colón is a normally-functioning currency, so the USD conversion is meaningful — unlike Argentina, where the multiple-exchange-rate regime ruled a USD column out.

## 5. Domain mapping — CSCCR sectors → 2025 UNESCO FCS

The CSCCR trade table is sector-level (four sectors). The crosswalk to the 2025 UNESCO FCS:

| CSCCR sector | 2025 FCS domain | FCS type | UNCTAD CER | IBGE NCM |
|---|---|---|---|---|
| Editorial | Books and press | cultural | CER030 | 49 |
| Audiovisual | Audiovisual | cultural | CER010 + CER060 | 37 |
| Publicidad | Design (advertising) | cultural | CER050-adjacent / SAMA service | — |
| Música | Music | cultural | CER040 | 92 |

The mapping is good for Editorial/Audiovisual/Música; Publicidad (advertising) is the usual approximate case — FCS routes advertising under Design while UNCTAD treats it as a service (SAMA). From 2022 only Editorial → *Books and press* has data.

## 6. Coverage limitations and comparability caveats

- **2022–2024 is Editorial-only** (see §3) — the single most important caveat.
- **Sector-level, current prices** — four sectors, no finer product detail; no constant-price trade series.
- **Comparability vs CSCM / CSECC / SInCA / Brazilian SIIC** — four different national systems, four classifications, different currencies and price bases. The CSCCR is the only one of the four LATAM sources with a *dedicated* consolidated trade table (Mexico and Colombia embed trade in supply-use tables; Argentina splits goods/services). Never mix `cr_bccr` with `inegi`, `dane`, `sinca`, `unctad` or `ibge_comex` in a query without explicit reconciliation.
- The other CSCCR workbooks (`Sector_Editorial.xlsx`, `Sector_Audiovisual.xlsx`, the `Estadisticas_*` files, etc.) carry richer sector detail — production accounts, employment, supply-use balances — and remain available for a future ingest beyond the trade module.

## 7. Validation (2026-05-22)

- **Row count** — 150 rows = 15 years × 5 sectors (4 + Total) × 2 flows. 18 NULL values = the three non-Editorial sectors × 2022–2024 × 2 flows (the `n.d.` cells).
- **Hierarchy identity** — for 2010–2021 (full coverage), `Total` = sum of the four sectors for every year × flow; maximum discrepancy **0.0 CRC mn**. For 2022–2024, `Total` = Editorial exactly (confirmed).
- **Spot values** — exports 2010 total 12,185.05; imports 2017 total 170,842.29; Editorial exports 2024 4,379.35 CRC mn — all match source (full float precision preserved).
- **FX** — 2010 525.83, 2021 620.78 (from the `TC` sheet); 2022 646.899, 2024 515.561 (supplement).
- **Idempotency** — re-running the ETL produces byte-identical Parquet.

## 8. Citation

> CICSC (2025). *Cuenta Satélite de Cultura de Costa Rica — Resumen de indicadores, 2010–2024*. Comisión Interinstitucional de la Cuenta Satélite de Cultura (MCJ, BCCR, INEC, PEN, CONARE).

---

*Methodology note for `atana.cr_bccr`. Prepared 2026-05-22. Pairs with `inegi_csc.md`, `dane_csecc.md`, `sinca_csc.md`, `_atana_intel/phase3_schema_design.md` and `_atana_intel/latam_cultural_sources_inventory.md`.*
