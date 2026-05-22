# Methodology — DANE Cuenta Satélite de Economía Cultural y Creativa (CSECC)

Schema `atana.dane`. Phase 3b of the Atana Data LATAM expansion — the second non-Brazilian national source, after Mexico's INEGI CSCM (`atana.inegi`).

**Source:** DANE — *Cuenta Satélite de Economía Cultural y Creativa (CSECC)*, an extension of Colombia's Sistema de Cuentas Nacionales.
**Portal:** <https://www.dane.gov.co/index.php/estadisticas-por-tema/cuentas-nacionales/cuentas-satelite/cuenta-satelite-de-cultura-en-colombia>
**Coverage:** Colombia, national, annual 2014–2024 (2023 provisional `p`, 2024 preliminary `pr`). Release: *CSECC 2022–2024pr*, boletín técnico 30 Jul 2025.
**Licence:** DANE — open data (Colombian official statistics).
**ETL:** `etl/dane__csecc_xlsx_to_parquet.py`
**Ingested:** 2026-05-22.

---

## 1. What the CSECC is

The CSECC is Colombia's cultural satellite account. Colombia has run a cultural satellite account since 2002 — it was the pilot for the Convenio Andrés Bello *Guía Metodológica para la implementación de las Cuentas Satélite de Cultura en Iberoamérica* — making it one of the most mature in the region. *Ley 2319 de 2023* renamed it from *Cuenta Satélite de Cultura y Economía Naranja* (CSCEN) to its current name.

The CSECC groups cultural and creative activities into **three areas**: *Artes y patrimonio*, *Industrias culturales*, and *Creaciones funcionales*. In 2024pr the cultural and creative economy's gross value added reached 44,321 thousand-million pesos, ≈ 2.9% of national GVA.

## 2. What this ingests — the supply-use balances (no BoP module)

Like Mexico's CSCM, the CSECC has **no dedicated balance-of-payments module** and **no bilateral / by-partner-country detail**. Cultural imports and exports appear as rows *inside the product-level supply-use balances* — *Importaciones* on the supply side, *Exportaciones a precio comprador* on the use side.

`atana.dane.csecc_comercio` is built from one DANE anexo — `anex-CSECC-balanceOferUtilizacion-2024pr.xlsx`, *"Balances oferta utilización de productos a precios corrientes 2014–2024pr"*. The anexo has **35 cuadros, one cultural product per cuadro**, grouped into the three areas:

| Area | Cuadros | Trade-bearing cuadros |
|---|---|---|
| Artes y patrimonio | 1–13 | 6 |
| Industrias culturales | 14–29 | 12 |
| Creaciones funcionales | 30–35 | 4 |

Of the 35 product cuadros, **22 carry import/export rows**; the other 13 (e.g. *Artes visuales*, *Creación musical*, *Servicios especializados de diseño*) record no cross-border trade in the CSECC balance and contribute no rows.

## 3. The `csecc_comercio` table

One row per **year × product (cuadro) × flow**. **484 rows** (22 trade cuadros × 11 years × 2 flows).

| Column | Type | Description |
|---|---|---|
| `year` | BIGINT | 2014–2024 |
| `area` | VARCHAR | `Artes y patrimonio` / `Industrias culturales` / `Creaciones funcionales` |
| `cuadro_num` | BIGINT | Source cuadro number, 1–35 |
| `producto` | VARCHAR | Product name (the cuadro's title) |
| `flow` | VARCHAR | `importacion` / `exportacion` |
| `value_cop_million` | DOUBLE | Trade value, current prices, million COP |
| `value_usd_million` | DOUBLE | **ETL-derived** — `value_cop_million ÷ fx_rate` |
| `fx_rate_cop_per_usd` | DOUBLE | Annual-average FX used (traceability) |
| `year_status` | VARCHAR | `definitivo` / `provisional` (2023) / `preliminar` (2024) |
| `source_concept` | VARCHAR | Verbatim DANE row label — preserves the valuation basis |

**Valuation basis.** DANE values imports and exports on *different* bases — imports CIF / *precios básicos*, exports *a precio comprador*. The `source_concept` column preserves the exact DANE label so the asymmetry stays visible rather than being silently flattened. (Mexico's CSCM uses C.I.F. imports / FOB exports — a third convention. Cross-country trade comparisons must account for this.)

## 4. Domain mapping — CSECC → 2025 UNESCO FCS → UNCTAD CER → IBGE NCM

DANE's three areas are the *Economía Naranja* taxonomy, not the FCS structure — so the mapping is done at the **product (cuadro) level**. The 22 trade-bearing cuadros map as follows (the Mexico section of the same crosswalk is in `inegi_csc.md` §5; the design is in `_atana_intel/phase3_schema_design.md`).

| Cuadro | Product | 2025 FCS domain | FCS type | UNCTAD CER | IBGE NCM |
|--:|---|---|---|---|---|
| 4 | Producción/presentación artes escénicas | Performing arts | cultural | CER040 | — |
| 7 | Bibliotecas y archivos | Archives | transversal | — | — |
| 8 | Preservación y museos | Cultural and natural heritage | cultural | CER070 | — |
| 10 | Parques de atracciones | *(recreation — no clean FCS equivalent)* | — | — | — |
| 11 | Educación cultural preescolar–media | Education in culture | transversal | — | — |
| 13 | Educación cultural para el trabajo | Education in culture | transversal | — | — |
| 15 | Edición de libros | Books and press | cultural | CER030 | 49 |
| 16 | Diarios, revistas y publicaciones | Books and press | cultural | CER030 | 49 |
| 17 | Otros trabajos de edición | Books and press | cultural | CER030 | 49 |
| 20 | Impresión y reproducción | Books and press | cultural | CER030 | 49 |
| 21 | Producción de películas/video/TV | Audiovisual | cultural | CER010 + CER060 | 37 |
| 22 | Postproducción de audiovisuales | Audiovisual | cultural | CER010 | 37 |
| 23 | Distribución de programas TV/cine | Audiovisual | cultural | CER060 | — |
| 24 | Proyección de películas | Audiovisual | cultural | CER010 | — |
| 25 | Transmisión y programación de radio | Audiovisual | cultural | CER060 | — |
| 26 | Transmisión y programación de TV | Audiovisual | cultural | CER060 | — |
| 27 | Distribución de programas de pago | Audiovisual | cultural | CER060 | — |
| 29 | Agencias de noticias | Books and press | cultural | — | — |
| 31 | Joyas y artículos conexos | Visual arts and crafts | cultural | CER024 | 71 |
| 32 | Instrumentos musicales | Music | cultural | CER040 | 92 |
| 33 | Juegos y juguetes | Design / CC goods manufacturing | cultural / transversal | CER025 | 95 |
| 35 | Servicios publicitarios | Design | cultural | CER050-adjacent | — |

Mapping confidence is *approximate* throughout — the CSECC's product granularity is finer than the FCS domains, and several products (e.g. *Parques de atracciones*, *Juegos y juguetes*) straddle FCS boundaries. As with Mexico, the gaps are documented rather than reconciled away.

## 5. Currency conversion

CSECC values are **million Colombian pesos**, current prices. The CSECC publishes no USD figures. `value_usd_million` is an **Atana ETL derivation** — `value_cop_million ÷ annual-average COP/USD` — using `atana.dane.fx_cop_usd_annual` (World Bank Open Data indicator **PA.NUS.FCRF**, period average; underlying source IMF IFS). **The FX values were transcribed 2026-05-22 and should be re-verified against the live World Bank / Banco de la República series before any publication relies on the USD figures.**

## 6. Coverage limitations and comparability caveats

**Current prices only.** The DANE balance anexo is current-price COP; there is no constant-price trade series (unlike Mexico's CSCM, which has both). Colombia's chained-volume series exist for the *production account* (`anex-CSECC-ConsolidadSegmento`, not ingested here), not for the trade balances.

**No bilateral detail.** `csecc_comercio` has no partner-country dimension.

**13 of 35 products have no recorded trade** — services such as *Artes visuales*, *Creación musical*, *Creación literaria* and *Servicios especializados de diseño* show no cross-border flows in the CSECC balances.

**Comparability vs Mexico's CSCM and Brazilian SIIC.** The three national systems must not be mixed in a query without explicit reconciliation:
- Classifications differ — DANE's 3 *Economía Naranja* areas vs INEGI's 10 functional areas vs IBGE's NCM chapters.
- Valuation differs — DANE imports CIF/básicos & exports a precio comprador; INEGI imports C.I.F. & exports FOB; IBGE Comex goods in R$ FOB.
- Currency and price basis differ — COP current prices (DANE) vs MXN current + constant-2018 (INEGI) vs R$ FOB (IBGE).
This is the methodological-pluralism principle: divergence is a finding, not a defect (cf. Atana Note #03).

## 7. Validation (2026-05-22)

- **Row count** — 484 rows = 22 trade-bearing cuadros × 11 years × 2 flows. By area: Artes y patrimonio 6 cuadros / 132 rows, Industrias culturales 12 / 264, Creaciones funcionales 4 / 88. No null values.
- **Supply-use accounting identity** — *Total oferta* = *Total utilización* checked across all 35 cuadros × 11 years (385 cells); maximum residual **1.7 × 10⁻¹⁰** (floating-point only).
- **Spot values** — Cuadro 31 (*Joyas*): 2014 imports 48,301 / exports 3,065 COP mn; 2024 imports 130,030 / exports 16,780 COP mn — match the source exactly.
- **2024 totals** — cultural imports 2,327,848 COP mn, exports 1,079,802 COP mn — a cultural-trade deficit of ≈ 1,248,046 COP mn (≈ US$ 307 mn at the 2024 average rate).
- **Idempotency** — re-running the ETL produces byte-identical Parquet.

## 8. Citation

> DANE (2025). *Cuenta Satélite de Economía Cultural y Creativa (CSECC), 2022–2024pr*. Departamento Administrativo Nacional de Estadística, Colombia.

---

*Methodology note for `atana.dane`. Prepared 2026-05-22. Pairs with `inegi_csc.md`, `_atana_intel/phase3_schema_design.md` and `_atana_intel/latam_cultural_sources_inventory.md`.*
