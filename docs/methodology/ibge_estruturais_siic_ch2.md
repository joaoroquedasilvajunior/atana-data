# Methodology — IBGE SIIC chapter 2: structural business surveys

Schema `atana.ibge_estruturais`. Phase 4a of the Atana Data expansion — the
first of the Brazil-first non-trade ingests that close the FCS transversal
blind spots surfaced by the `canonical.domain_crosswalk` build.

**Source:** IBGE — *Sistema de Informações e Indicadores Culturais* (SIIC),
"Informações Culturais" 2024 edition, **chapter 2 — Pesquisas estruturais em
empresas**.
**Underlying surveys:** PIA (Pesquisa Industrial Anual), PAS (Pesquisa Anual de
Serviços), PAC (Pesquisa Anual de Comércio).
**Portal:** <https://www.ibge.gov.br/estatisticas/sociais/cultura.html>
**Coverage:** Brazil, national, reference years **2013 + 2019–2023**.
**Licence:** open data — IBGE official statistics.
**ETL:** `etl/ibge_estruturais__siic_ch2_to_parquet.py`
**Ingested:** 2026-05-23.

---

## 1. Why this source

A foreign-trade module (the corpus's `ibge_comex`) sees imports and exports of
cultural goods; it cannot see **domestic production**. The FCS transversal
domain *Cultural and creative goods manufacturing* is a production domain.
Chapter 2 carries the production accounts — gross output, intermediate
consumption and **value added** — for the cultural sector, broken down by
cultural domain and by activity. It is the measure that lights up that domain.

## 2. The eight tables

One Parquet per source sheet, `tab_2_1` … `tab_2_8`. Each holds one
structural-survey variable:

| Table | Variable (`variable` column) |
|---|---|
| `tab_2_1` | Número de empresas |
| `tab_2_2` | Pessoal ocupado |
| `tab_2_3` | Salários e outras remunerações |
| `tab_2_4` | Receita líquida |
| `tab_2_5` | Custos e despesas |
| `tab_2_6` | Valor bruto da produção |
| `tab_2_7` | Consumo intermediário |
| `tab_2_8` | Valor adicionado |

The exact caption is in each table's `variable` column. Monetary tables are in
**R$ 1 000** (per the IBGE header); read the caption before interpreting units.

## 3. Table structure (long format)

Each table is **354 rows** — 59 row labels × 6 reference years.

| Column | Type | Description |
|---|---|---|
| `table_id` | VARCHAR | `2.1` … `2.8` |
| `variable` | VARCHAR | the structural-survey variable (sheet caption) |
| `row_index` | BIGINT | source spreadsheet row — preserves the domain hierarchy order |
| `row_label` | VARCHAR | the cultural domain / activity label |
| `year` | BIGINT | 2013, 2019, 2020, 2021, 2022, 2023 |
| `value` | DOUBLE | the figure; NULL where the cell is blank |
| `cv` | VARCHAR | IBGE CV reliability code — `A` best … `E` suppress; `Z` = rounds to zero |

## 4. The SIIC cultural-domain hierarchy

`row_label` carries IBGE's nested cultural-domain structure:

```
Total geral (*)
└─ Total dos domínios culturais
   ├─ Total das atividades culturais centrais
   │  ├─ B. Apresentações artísticas e celebrações   (+ activity rows)
   │  ├─ C. Artes visuais e artesanato
   │  ├─ D. Livros e imprensa
   │  ├─ E. Mídias audiovisuais e interativas
   │  ├─ F. Design e serviços criativos
   │  └─ H. Esportes e recreação
   └─ Total das atividades culturais periféricas      (+ activity rows)
      └─ equipment, telecom, software and the "Fabricação de …" rows
```

The domain headers (`B.` … `H.`) and the "Total …" rows are aggregates; the
remaining rows are CNAE activity classes. The **`Fabricação de …` rows inside
"atividades culturais periféricas"** are the manufacturing of cultural and
creative goods — this is the slice that reaches the FCS *Cultural and creative
goods manufacturing* domain in `canonical.domain_crosswalk`.

## 5. Limitations and caveats

- **Reference years are not continuous** — 2013, then a gap, then 2019–2023.
  There is no 2014–2018 series; do not interpolate.
- **CV codes matter.** Many activity-level rows carry `D`/`E`. Filter on `cv`
  before publishing an activity-level figure; `E` rows should be suppressed.
- **`Z`** is a distinct code — the value rounds to zero, it is not missing.
- **Not RAIS.** `atana.rais` already covers formal cultural *employment*
  (incl. the manufacturing CNAEs). What chapter 2 newly adds is **value added,
  gross output and the firm/revenue accounts** — the production-account view
  RAIS does not provide. The two are complementary, not interchangeable.
- **Brazil only.** The LATAM CSC production modules are a later phase.

## 6. Domain mapping → 2025 UNESCO FCS

The SIIC cultural-domain classification is crosswalked to the FCS in
`canonical.domain_crosswalk` (`source_schema = 'ibge_siic'`). Chapter 2's
production accounts are the evidence behind the *Cultural and creative goods
manufacturing* crosswalk row.

## 7. Validation (2026-05-23)

- **Row count** — all 8 tables: 354 rows = 59 labels × 6 years.
- **CV vocabulary** — `{A, B, C, D, E, Z}` only.
- **Accounting identity** — for every year, `Total dos domínios culturais` =
  `atividades culturais centrais` + `atividades culturais periféricas`;
  maximum discrepancy **0.0%** (2013: −5e-7%, IBGE rounding).
- **Spot value** — `tab_2_8` (valor adicionado) `Total geral` 2023 =
  4 645 645 431.287 (R$ 1 000) — matches the source workbook.
- **Idempotency** — re-running the ETL produces byte-identical Parquet.

## 8. Citation

> IBGE (2024). *Sistema de Informações e Indicadores Culturais — Informações
> Culturais, capítulo 2: Pesquisas estruturais em empresas*. Instituto
> Brasileiro de Geografia e Estatística.

---

*Methodology note for `atana.ibge_estruturais`. Prepared 2026-05-23. Pairs with
`ibge_cempre_siic_ch1.md` (Phase 4a) and `_atana_intel/phase4_scoping.md`.*
