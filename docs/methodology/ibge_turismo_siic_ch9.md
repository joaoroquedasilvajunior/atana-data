# Methodology — IBGE SIIC chapter 9: leisure, culture and nature tourism

Schema `atana.ibge_turismo`. Phase 4b of the Atana Data expansion — the second
of the two ingests that reach the FCS transversal domain *Social participation*
**as a proxy** (see §3).

**Source:** IBGE — *Sistema de Informações e Indicadores Culturais* (SIIC),
"Informações Culturais" 2024 edition, **chapter 9 — Turismo de lazer, cultura e
natureza**.
**Underlying survey:** PNAD Contínua — leisure-tourism supplement.
**Portal:** <https://www.ibge.gov.br/estatisticas/sociais/cultura.html>
**Coverage:** Brazil, national/region/UF; reference years **2021, 2023, 2024**.
**Licence:** open data — IBGE official statistics.
**ETL:** `etl/ibge_turismo__siic_ch9_to_parquet.py`
**Ingested:** 2026-05-23.

---

## 1. Why this source

Chapter 9 records **leisure travel by type** — and one of its leisure-type
categories is **"Cultura e gastronomia"**. Cultural tourism is a form of
cultural participation a foreign-trade module cannot see; this chapter is the
travel-side complement to chapter 7's digital-access measure.

## 2. The five tables

One Parquet per source table file, `tab_9_1` … `tab_9_5`. Each xlsx has a sheet
per reference year (2021, 2023, 2024) plus a paired `<year> (CV)` sheet; the ETL
stacks them with an `is_cv` flag.

| Column | Type | Description |
|---|---|---|
| `table_id` | VARCHAR | `9.1` … `9.5` |
| `year` | BIGINT | 2021, 2023, 2024 |
| `is_cv` | BOOLEAN | FALSE = value row; TRUE = the matching IBGE CV reliability code |
| `row_index` | BIGINT | source spreadsheet row — preserves order |
| `row_label` | VARCHAR | the breakdown label (region/UF, income class, trip-type…) |
| `c02`, `c03`, … | mixed | the original value columns, left-to-right |

As with chapter 7, the IBGE multi-row header is **not flattened** — `c02…` are
raw spreadsheet columns and their meaning (trip motive, leisure type, the
"Cultura e gastronomia" sub-column) is read from the source header. One IBGE
stub-header row per sheet is also captured — identify it by `row_index`.

## 3. ⚠️ Proxy, not full measurement — the central caveat

Chapter 9 is **leisure-travel data**. It is an *approximate proxy* for the FCS
*Social participation* domain, not a cultural-practices survey — see
`ibge_tic_siic_ch7.md` §3 for the full statement of this caveat (Brazil has no
continuous national cultural-practices survey). The `canonical.domain_crosswalk`
rows for this domain carry `mapping_confidence = 'approximate'` and a proxy note.
The "Cultura e gastronomia" leisure-type column is the closest cultural slice;
even it bundles culture with gastronomy.

## 4. Limitations and caveats

- **Proxy domain** — see §3. Cultural tourism ≠ cultural participation in full.
- **Three reference years only** — 2021, 2023, 2024; no continuous series.
- **"Cultura e gastronomia" is a bundle** — the source does not separate
  cultural travel from gastronomic travel.
- **Column meaning is in the source header, not the data** — consult the IBGE
  workbook before interpreting `c02…`.
- **CV rows** (`is_cv = TRUE`) mirror the value rows — filter on reliability;
  suppress `E`-coded cells.

## 5. Domain mapping → 2025 UNESCO FCS

`canonical.domain_crosswalk` (`source_schema = 'ibge_siic'`) maps the PNADC
leisure-tourism supplement to *Social participation*, transversal,
**`approximate`** — the proxy is explicit in the row's note.

## 6. Validation (2026-05-23)

- **Coverage** — 5 Parquet tables, 891 rows; years 2021/2023/2024.
- **Spot value** — `tab_9_1`, 2024, `Brasil`, resident-population column
  (`c02`) = 211 852.978 (1 000 persons) — matches the source workbook; the
  "Cultura e gastronomia" leisure-trip column for `Brasil` 2024 = 1 708.31
  (1 000 trips).
- **Idempotency** — re-running the ETL produces byte-identical Parquet.

## 7. Citation

> IBGE (2024). *Sistema de Informações e Indicadores Culturais — Informações
> Culturais, capítulo 9: Turismo de lazer, cultura e natureza*. Instituto
> Brasileiro de Geografia e Estatística.

---

*Methodology note for `atana.ibge_turismo`. Prepared 2026-05-23. Pairs with
`ibge_tic_siic_ch7.md` (Phase 4b) and `_atana_intel/phase4_scoping.md` §A.4.*
