# Methodology — INPI Indicadores de Propriedade Industrial

Schema `atana.inpi`. Phase 4c.2 of the Atana Data expansion — the cultural-IP
*stock* (registration counts), enriching the FCS *Intellectual property* domain
that Phase 4c.1 (BCB) reached as a *flow*.

**Source:** INPI — *Instituto Nacional da Propriedade Industrial*, *Tabelas
Completas dos Indicadores de Propriedade Industrial* (Anuário Estatístico),
**2024 edition**.
**Portal:** <https://www.gov.br/inpi/pt-br/inpi-data/dados-e-series-temporais/tabelas-completas-dos-indicadores-de-pi>
**Coverage:** Brazil, national + sub-national, annual series **2000–2024**.
**Licence:** open data — INPI official statistics.
**ETL:** `etl/inpi__indicadores_to_parquet.py`
**Ingested:** 2026-05-23.

---

## 1. Why this source

BCB's IP-services account (`atana.bcb`, 4c.1) measures the cross-border IP
*royalty flow*. INPI measures the *stock* — how much intellectual property is
applied for and granted in Brazil each year. Together they give the FCS
*Intellectual property* transversal domain two lenses: money (BCB) and
registrations (INPI).

## 2. The cultural cut

INPI registers all industrial property. The cultural cut is taken **at the file
level** — the ETL ingests the four cultural IP-type workbooks and skips the
rest:

| Ingested (`iptype`) | What | |
|---|---|---|
| `prg` | Computer programs (registros de programa de computador) | software & games — creative by nature |
| `di` | Industrial designs (desenhos industriais) | the FCS *Design* domain |
| `ig` | Geographical indications | artisanal / cultural-product protection |
| `mrc` | Trademarks (marcas), incl. Nice-class breakdowns | the cultural-class slice |

**Skipped:** patents (PTN), technology-transfer contracts (CTT/CON), IC
topographies (TCI) and the gender cut (PI_Genero) — not cultural IP.

**Trademark Nice-class filter.** `prg`, `di`, `ig` are taken whole. For `mrc`,
the *cultural* slice is a Nice-class filter applied **downstream**, not in the
ETL — the class dimension is preserved in the `mrc_*_classe*` tables so the cut
is a revisable view, not a destructive filter:

- **Tight cut (recommended default):** Nice class **41** (entertainment &
  cultural activities) + **16** (printed matter / publishing).
- **Wide cut:** also class **9** (recorded media / downloadable content) +
  **28** (games & toys).

Which classes count as "cultural" is a genuine scoping choice — stated here so
it can be argued with (the methodological-pluralism discipline), not buried.

## 3. The tables

68 Parquet tables — one per source sheet of the four cultural workbooks
(`prg` 7 · `di` 18 · `ig` 10 · `mrc` 33; the `Sumário` index sheets skipped).
Faithful wide preservation, the `ibge_cempre` precedent.

| Column | Type | Description |
|---|---|---|
| `iptype` | VARCHAR | `prg` / `di` / `ig` / `mrc` |
| `source_sheet` | VARCHAR | the source workbook sheet name |
| `row_index` | BIGINT | source spreadsheet row — preserves order |
| `c01`, `c02`, … | VARCHAR | the original cells, left-to-right, as text |

**Every `c…` cell is stored as text** — uniform `VARCHAR` columns, cast
downstream as needed. (Mixing typed and string cells in one column otherwise
trips DuckDB's type inference — a header label in a column of integer counts.)
All-empty trailing columns may type as `INTEGER`; they carry no data.

Two sheet layouts appear, both preserved as-is: **year-in-rows** series
(`c01` = year, `c02…` = values; data from row ~8) and **class-in-rows /
year-in-columns** breakdowns (the `*_classe*` sheets — `c01` = class code,
`c02` = class label, `c03…` = years). Banner and `Fonte`/`Nota` lines are
dropped; title and header rows are kept (use `row_index`).

## 4. Limitations and caveats

- **Registration ≠ cultural value.** A count of computer-program or trademark
  registrations is an activity proxy, not an economic-value measure. INPI
  carries no creative/non-creative split *within* an IP type — `prg` is *all*
  software registrations, the cultural reading is by inference.
- **2024 edition only.** The annual indicator tables are 2000–2024 series, so
  the 2024 edition carries the full history. The older editions (2018, 2019,
  2020, 2023) remain in `raw/inpi/` for cross-checking but are not ingested.
- **Faithful image, not a tidy model** — header rows are preserved; column
  meaning is sheet-specific (read the source). Select by `source_sheet` /
  `row_index` for the rows you need.
- **Sub-national depth varies** — many sheets are by-country / by-city
  cross-tabs; the headline series are the `*_total*` / `deposito_*` /
  `registro_*` sheets.

## 5. Domain mapping → 2025 UNESCO FCS

`canonical.domain_crosswalk` (`source_schema = 'inpi'`) maps the cultural INPI
registration series to *Intellectual property* (transversal, `good`). The
coverage meter stays 13/14 — INPI deepens a domain BCB already reached.

## 6. Validation (2026-05-23)

- **Coverage** — 68 tables, 15,321 rows; `prg` 7 · `di` 18 · `ig` 10 · `mrc` 33.
- **Spot values** — `prg_total_geral` 2000 deposits = 661; `di_deposito_di`
  2000 = 3,563; `mrc_registro_mrc_contagem_classes` 2000 (direto) = 18,689;
  `ig_1_total_geral` 2000 = 2 — all match the source workbook.
- **Idempotency** — re-running the ETL produces byte-identical Parquet (68/68).

## 7. Citation

> INPI (2024). *Tabelas Completas dos Indicadores de Propriedade Industrial —
> Anuário Estatístico, 2000–2024*. Instituto Nacional da Propriedade Industrial.

---

*Methodology note for `atana.inpi`. Prepared 2026-05-23. Phase 4c.2. Pairs with
`bcb_sgs_ip_services.md` (4c.1) and `_atana_intel/phase4c_inpi_ecad_spec.md`.*
