# Methodology — Argentina Cuenta Satélite de Cultura (CSC)

Schema `atana.sinca`. Phase 3c of the Atana Data LATAM expansion — the third non-Brazilian national source, after Mexico (`atana.inegi`) and Colombia (`atana.dane`).

**Source:** SInCA (Sistema de Información Cultural de la Argentina, Ministerio de Cultura) with INDEC — *Cuenta Satélite de Cultura*.
**Portal:** <https://datos.cultura.gob.ar/dataset/cuenta-satelite-de-cultura-comercio-exterior>
**Coverage:** Argentina, national, annual **2004–2022**.
**Licence:** Creative Commons Attribution 4.0 (datos.cultura.gob.ar).
**ETL:** `etl/sinca__csc_to_parquet.py`
**Ingested:** 2026-05-22.

---

## 1. What the CSC is

Argentina's *Cuenta Satélite de Cultura* is a joint product of SInCA and INDEC, built on the Convenio Andrés Bello methodological framework. It produces macroeconomic measures of cultural activity — cultural GVA, employment, foreign trade, public cultural spending. This ingest covers the **foreign-trade module** only, published as an open dataset on the Ministry of Culture's data portal.

## 2. What this ingests

Argentina's CSC foreign-trade module is published as a set of annual CSV series, **2004–2022**. Two `atana.sinca` tables are built from them:

- **`csc_comercio`** — exports, imports and trade balance of cultural goods and services.
- **`csc_participacion`** — cultural trade as a share of total trade and of cultural gross output.

The source dataset's structure is **coarser than Mexico's CSCM or Colombia's CSECC**: it gives a *services* series and a *goods+services total*, but no standalone *goods* file and no product/sector breakdown. Cultural goods (*bienes característicos* — books, discs, works of art, films) are therefore **derived** for the constant-price series as `(goods+services) − services`; they cannot be derived for the current-price series, which publishes only the total.

## 3. The tables

### `sinca.csc_comercio` — 228 rows

One row per **year × segment × price_basis × flow**.

| Column | Type | Description |
|---|---|---|
| `year` | BIGINT | 2004–2022 |
| `segment` | VARCHAR | `servicios_culturales` / `bienes_culturales` / `bienes_y_servicios_culturales` |
| `price_basis` | VARCHAR | `corriente` / `constante_2004` |
| `flow` | VARCHAR | `exportacion` / `importacion` / `saldo` |
| `value_ars_thousand` | DOUBLE | Value in thousands of Argentine pesos |
| `is_derived` | BOOLEAN | TRUE for `bienes_culturales` (derived = total − services) |
| `source_file` | VARCHAR | Originating CSV, or `derived: csc22 − csc20` |

Coverage by combination: the `constante_2004` basis carries all three segments (services, goods, goods+services); the `corriente` basis carries only `bienes_y_servicios_culturales` — the source publishes no current-price services series.

### `sinca.csc_participacion` — 76 rows

One row per **year × indicator**. Four indicators (ratios, 0–1): cultural exports / total exports; cultural imports / total imports; cultural exports / cultural gross output (current and constant bases).

## 4. ⚠️ Currency — and why there is no USD column

Values are in **thousands of Argentine pesos**. Unlike `atana.inegi` and `atana.dane`, **`atana.sinca` carries no `value_usd_million` column.** This is a deliberate, documented decision:

- The **current-peso** series (`corriente`) spans two decades of high inflation — nominal pesos in 2004 and 2022 are not remotely comparable. Only the **`constante_2004`** series is valid for time-series analysis; treat it as primary.
- Converting Argentine pesos to USD would require an ARS/USD rate, and across most of 2004–2022 Argentina ran a **multiple-exchange-rate regime** — the official rate diverged sharply from the parallel ("blue") rate (the *brecha cambiaria*). Any single conversion would materially misstate the figures, in either direction.

So Argentina is held in pesos. The **absence of a comparable-USD figure is itself the finding** — the methodological-pluralism principle (cf. Atana Note #03): rather than manufacture a misleading USD number for cross-country charts, the gap is surfaced. Mexico and Colombia have USD columns; Argentina does not, and that asymmetry is documented rather than papered over.

## 5. Domain mapping

The Argentine CSC trade dataset has **no product or sector breakdown** — only the goods/services split. A fine-grained crosswalk to the 2025 UNESCO FCS domains (as built for Mexico's 10 areas and Colombia's 22 products) is therefore **not possible at the trade-module level**. The mapping is necessarily coarse:

| CSC segment | 2025 FCS coverage | UNCTAD analogue |
|---|---|---|
| `bienes_culturales` | Spans *Books and press*, *Audiovisual*, *Visual arts and crafts*, *Music* (characteristic cultural goods: books, discs, art, films) — not separable in this dataset | UNCTAD creative goods (CER000), aggregate |
| `servicios_culturales` | Spans audiovisual, information, cultural/recreational services | UNCTAD creative services (SCRE), aggregate |

For finer FCS alignment, Argentina's CSC sector-level GVA tables (a separate dataset, not ingested here) would be needed.

## 6. Coverage limitations and comparability caveats

- **Series ends 2022** — Argentina's cultural-trade data is one to two years shorter than Mexico's CSCM (2024) and Colombia's CSECC (2024). The Milei administration (from December 2023) post-dates the series entirely; the relevant caveat for this data is inflation/FX distortion, not a Milei-era disruption.
- **No product/sector detail** — segment-level only (see §5).
- **Goods are derived, not published** — `bienes_culturales` exists only for `constante_2004` and is `(goods+services) − services`.
- **Source rounding** — SInCA publishes `exportacion`, `importacion` and `saldo` as independently rounded integers; the published `saldo` differs from `exportacion − importacion` by up to 1 thousand pesos in the source files (≤ 2 for the derived `bienes` series, which compounds two roundings). The published values are reproduced **as-is** — `saldo` is not recomputed — so this small inconsistency is faithful to the source.
- **Comparability vs CSCM / CSECC / Brazilian SIIC** — Argentina is the coarsest of the three national trade modules (segment-level), is peso-only with no USD, uses base year 2004 (vs INEGI 2018, DANE current-price), and ends in 2022. Never mix `sinca` with `inegi`, `dane`, `unctad` or `ibge_comex` in a query without explicit reconciliation.

## 7. Validation (2026-05-22)

- **Row counts** — `csc_comercio` 228 rows (constant: 3 segments × 19 years × 3 flows = 171; current: 1 segment × 19 × 3 = 57). `csc_participacion` 76 rows (4 indicators × 19 years). No null values.
- **Accounting identity** — `saldo ≈ exportacion − importacion` holds within source rounding: ≤ 1 thousand pesos in the three source-derived segments, ≤ 2 in the derived `bienes` series. Confirmed to originate in the source CSVs (9/18, 3/18, 7/18 rows respectively carry a ≤1 rounding gap).
- **Spot values** — services constant 2022 `saldo` −986,208; goods+services current 2004 exports 685,133; goods+services constant 2008 exports 1,602,960 — all match source.
- **Derived goods** — 2004 constant goods exports = 685,133 − 417,851 = 267,282, confirmed.
- **Idempotency** — re-running the ETL produces byte-identical Parquet.

## 8. Citation

> SInCA / INDEC. *Cuenta Satélite de Cultura — comercio exterior, 2004–2022*. Sistema de Información Cultural de la Argentina, Ministerio de Cultura. datos.cultura.gob.ar, CC BY 4.0.

---

*Methodology note for `atana.sinca`. Prepared 2026-05-22. Pairs with `inegi_csc.md`, `dane_csecc.md`, `_atana_intel/phase3_schema_design.md` and `_atana_intel/latam_cultural_sources_inventory.md`.*
