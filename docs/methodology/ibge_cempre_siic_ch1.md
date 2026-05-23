# Methodology — IBGE SIIC chapter 1: formally constituted activities

Schema `atana.ibge_cempre`. Phase 4a of the Atana Data expansion — the
firm-structure complement to `atana.ibge_estruturais` (chapter 2).

**Source:** IBGE — *Sistema de Informações e Indicadores Culturais* (SIIC),
"Informações Culturais" 2024 edition, **chapter 1 — Atividades formalmente
constituídas**.
**Underlying registers:** CEMPRE (Cadastro Central de Empresas), the
company-demography statistics, and the public-register statistics.
**Portal:** <https://www.ibge.gov.br/estatisticas/sociais/cultura.html>
**Coverage:** Brazil, national/UF, reference **2022** (demography 2015–2022).
**Licence:** open data — IBGE official statistics.
**ETL:** `etl/ibge_cempre__siic_ch1_to_parquet.py`
**Ingested:** 2026-05-23.

---

## 1. Why this source

Chapter 1 is the **registered-business** view of the cultural economy: how many
firms and local units exist, how many people they employ, what they pay, and
the demography of firm births, deaths, survival and high-growth. It complements
chapter 2's production accounts and `atana.rais`'s employment-link records with
the firm-count and firm-demography dimension neither of those carries.

## 2. The 23 tables

One Parquet per source sheet. The workbook has 24 sheets; `Quadro 1.1` is a
structure legend and is **not ingested**. The 23 data sheets fall in three
families (per the legend):

| Family | Sheets | Source register | Scope |
|---|---|---|---|
| `1.1.x` | `tab_1_1_1` … `tab_1_1_9` | CEMPRE statistics | all legal natures |
| `1.2.x` | `tab_1_2_1` … `tab_1_2_8` | company demography | legal nature 2 (companies) |
| `1.3.x` | `tab_1_3_1` … `tab_1_3_4` | public-register statistics | legal nature 213-5 etc. |

`.a`-suffixed sheets (`tab_1_1_6_a`, `tab_1_2_1_a`, `tab_1_2_2_a`) are IBGE's
provisional support tables.

## 3. Table structure — faithful wide preservation

The 23 sheets do **not** share one layout: some are single-year, some are
multi-block, and column 1 is a reference year in some tables and a label in
others. Rather than 23 bespoke parsers, the ETL preserves each sheet faithfully
(the `ibge_pnadc` precedent — "preserve IBGE's column structure"):

| Column | Type | Description |
|---|---|---|
| `table_id` | VARCHAR | the SIIC sheet id, e.g. `1.1.1`, `1.2.1.a` |
| `row_index` | BIGINT | the source spreadsheet row number — preserves order |
| `c01`, `c02`, … | mixed | the original cells, left-to-right, over the sheet's real used range |

Each table keeps only its own real used column range, so widths differ table to
table. **`c01` is a reference year in some tables and a label in others** — read
the table before querying. The title row and `Fonte:` lines are dropped; header
rows are kept (identifiable by `row_index`); a small number of footnote rows
beginning `(1)`, `(2)` … may also appear and are likewise identifiable by their
long text in `c01` with empty remaining cells.

The per-table `.meta.json` records the table title and used-column count.

## 4. Limitations and caveats

- **Heterogeneous layout** — there is no single grain across the 23 tables;
  `c0n` column meaning is table-specific. Treat each `tab_1_x_y` on its own
  terms; the source title is in the meta sidecar.
- **Single reference year for most CEMPRE tables** (2022); the `1.2.x`
  demography tables span 2015–2022.
- **Faithful image, not a tidy model** — header rows and the occasional
  footnote row are preserved. This is deliberate: it keeps the ingest lossless
  and low-judgment. Downstream analysis should select by `row_index` /
  `row_label` for the rows it needs.
- **Legal-nature scope differs by family** — `1.1.x` (all natures), `1.2.x`
  (companies), `1.3.x` (public register). Do not pool across families without
  reading the legend.

## 5. Domain mapping → 2025 UNESCO FCS

Chapter 1, with chapter 2, is the firm/production evidence behind the *Cultural
and creative goods manufacturing* row of `canonical.domain_crosswalk`
(`source_schema = 'ibge_siic'`).

## 6. Validation (2026-05-23)

- **Coverage** — 23 Parquet tables written (24 sheets minus the `Quadro 1.1`
  legend); 1 202 rows total.
- **Spot value** — `tab_1_1_1` carries one CEMPRE data row (`row_index` 7,
  `c01` = 2022); `tab_1_2_1` carries the two demography blocks (cultural sector
  and CEMPRE total), years 2017–2022 — both match the source workbook.
- **Idempotency** — re-running the ETL produces byte-identical Parquet.

## 7. Citation

> IBGE (2024). *Sistema de Informações e Indicadores Culturais — Informações
> Culturais, capítulo 1: Atividades formalmente constituídas*. Instituto
> Brasileiro de Geografia e Estatística.

---

*Methodology note for `atana.ibge_cempre`. Prepared 2026-05-23. Pairs with
`ibge_estruturais_siic_ch2.md` (Phase 4a) and `_atana_intel/phase4_scoping.md`.*
