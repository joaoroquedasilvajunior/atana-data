# Methodology — IBGE SIIC chapter 7: internet and television access

> **Status (2026-06-14):** GitHub ✅ `5fa9c34` on origin/main · MotherDuck ✅ live · 8 tables / 5,387 rows in `raw/ibge_tic/`

Schema `atana.ibge_tic`. Phase 4b of the Atana Data expansion — one of the two
ingests that reach the FCS transversal domain *Social participation* **as a
proxy** (see §3).

**Source:** IBGE — *Sistema de Informações e Indicadores Culturais* (SIIC),
"Informações Culturais" 2024 edition, **chapter 7 — Acesso à Internet e à
televisão**.
**Underlying survey:** PNAD Contínua — ICT supplement (TIC).
**Portal:** <https://www.ibge.gov.br/estatisticas/sociais/cultura.html>
**Coverage:** Brazil, national/region/UF; reference years vary by table within
**2016–2024** (no 2015, no 2020; tables 7.7–7.8 also lack 2021).
**Licence:** open data — IBGE official statistics.
**ETL:** `etl/ibge_tic__siic_ch7_to_parquet.py`
**Ingested:** 2026-05-23.

---

## 1. Why this source

The 2025 UNESCO FCS introduces *Social participation* through a praxeological
lens — cultural practice, not industrial output. A foreign-trade module cannot
see it. Chapter 7 measures **cultural access**: internet use, purpose of access,
devices, mobile-phone and television ownership, and **paid streaming-service
access** (tables 7.7–7.8). It is the closest continuous national series the
Brazilian corpus has for the access side of participation.

## 2. The eight tables

One Parquet per source table file, `tab_7_1` … `tab_7_8`. Each xlsx has a sheet
per reference year plus a paired `<year> (CV)` sheet of reliability codes; the
ETL stacks them into one table with an `is_cv` flag.

| Column | Type | Description |
|---|---|---|
| `table_id` | VARCHAR | `7.1` … `7.8` |
| `year` | BIGINT | reference year (per-table list in `.meta.json`) |
| `is_cv` | BOOLEAN | FALSE = value row; TRUE = the matching IBGE CV reliability code |
| `row_index` | BIGINT | source spreadsheet row — preserves order |
| `row_label` | VARCHAR | the breakdown label (Total, sex, colour/race, age, education, region…) |
| `c02`, `c03`, … | mixed | the original value columns, left-to-right |

The chapter's tables carry a deep multi-row IBGE header. Per the `ibge_pnadc`
precedent the ETL **preserves the column structure faithfully** rather than
flattening it: `c02…` are the spreadsheet columns; their meaning (which
indicator, which sub-column) is read from the source header and is **not**
encoded in the data. One IBGE stub-header row per sheet (the one carrying a
label in column 1) is also captured — identify it by `row_index`.

## 3. ⚠️ Proxy, not full measurement — the central caveat

Chapter 7 is **digital-access data**. It is an *approximate proxy* for the FCS
*Social participation* domain, **not** a cultural-practices survey. Brazil has
no continuous national survey of cultural practice — museum, theatre and cinema
attendance, reading, live-event attendance — comparable to Colombia's *Encuesta
de Consumo Cultural* or Argentina's *Encuesta Nacional de Consumos Culturales*.

That gap is itself a finding: **Brazil under-measures cultural participation**
relative to the FCS praxeological lens. Accordingly, the `canonical.domain_
crosswalk` rows for this domain carry `mapping_confidence = 'approximate'` and a
note marking the proxy. The methodological-pluralism rule applies — surface the
limitation, do not imply full measurement.

## 4. Limitations and caveats

- **Proxy domain** — see §3. Streaming access (tables 7.7–7.8) is the closest
  cultural slice; the rest is general ICT access.
- **Discontinuous years** — no 2015, no 2020; tables 7.7–7.8 also lack 2021.
  Years differ by table — use the `years` list in each `.meta.json`.
- **Column meaning is in the source header, not the data** — `c02…` are raw
  spreadsheet columns. Consult the IBGE workbook header before interpreting.
- **CV rows** (`is_cv = TRUE`) mirror the value rows — filter on reliability
  before publishing; `E`-coded cells should be suppressed.

## 5. Domain mapping → 2025 UNESCO FCS

`canonical.domain_crosswalk` (`source_schema = 'ibge_siic'`) maps the PNADC ICT
supplement to *Social participation*, transversal, **`approximate`** — the proxy
is explicit in the row's note.

## 6. Validation (2026-05-23; column map corrected 2026-05-24)

- **Coverage** — 8 Parquet tables, 5 387 rows; years per table recorded in meta.
- **Tables 7.7 / 7.8 column map** (`is_cv = FALSE` rows, % of household
  residents): `c02` total residents (1 000 persons) · `c04` household has a
  television · `c06` has a flat-screen television · **`c08` has access to
  pay-TV by subscription (*serviço de televisão por assinatura*)** ·
  **`c10` has access to a paid video-streaming service (Netflix, Prime Video,
  Disney+, Globoplay…)**.
- **Spot values** — `tab_7_7`, 2024, `Total`: pay-TV (`c08`) = 24.46 % and
  paid streaming (`c10`) = 11.39 % — both match the source workbook.
  ⚠️ **Correction (2026-05-24):** an earlier version of this note labelled
  `c08` (24.46 %) as the paid-streaming column. That was wrong — `c08` is
  pay-TV by subscription; the paid-streaming column is `c10`. Any analysis of
  streaming access must use `c10`.
- **Streaming is a short series** — the paid-streaming question (`c10`) was
  added to the supplement only in 2022; for 2016–2019 the column reads 0.0,
  which is *not a real zero* — the question did not yet exist. The same holds
  for the music, reading and gaming purpose columns in tables 7.3 / 7.4.
- **Idempotency** — re-running the ETL produces byte-identical Parquet.

## 7. Citation

> IBGE (2024). *Sistema de Informações e Indicadores Culturais — Informações
> Culturais, capítulo 7: Acesso à Internet e à televisão*. Instituto Brasileiro
> de Geografia e Estatística.

---

*Methodology note for `atana.ibge_tic`. Prepared 2026-05-23. Pairs with
`ibge_turismo_siic_ch9.md` (Phase 4b) and `_atana_intel/phase4_scoping.md` §A.4.*
