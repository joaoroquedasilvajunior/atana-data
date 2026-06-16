# `atana.ibge_pnadc` — IBGE PNADC Cultural Sector (SIIC Ch. 6)

> **Status (2026-06-14):** GitHub ✅ `411644f` on origin/main · MotherDuck ✅ live · 18 tables / 35,596 rows in `raw/ibge_pnadc/`

> Methodology note. Phase 1 (foundational corpus). ETL: `etl/ibge_pnadc__xlsx_to_parquet.py`.
> **Consumed by:** Análises 1, 2, 3 (the original opening trilogy of the book) · Análise 17 (música) · Análise 18 (cinco portas) · Atana Note #06 (Funk).

## 1. What the source is

The **IBGE PNADC** is the *Pesquisa Nacional por Amostra de Domicílios Contínua*, Brazil's quarterly household labour-force survey. Once a year, IBGE publishes a special publication called **"Informações Culturais"** (SIIC) that re-cuts the PNADC microdata through a fixed list of cultural CNAEs + CBOs and releases summary tables for the cultural sector. Chapter 6 of SIIC — *Ocupação no setor cultural* — is the source for `atana.ibge_pnadc`.

This is **the only continuous, nationally representative measure of the Brazilian cultural workforce**: ~5.86 M people in 2024, 5.79 % of the active labour force. It catches both formal and informal workers (unlike `atana.rais`, which is formal-only).

The series runs 2014–2024 (annual, single-cut per year). Sample design is household-based, two-stage; variance estimation by linearisation. IBGE publishes coefficient-of-variation (CV) bands per cell — A (≤5 %), B (5–10 %), C (10–20 %), D (20–30 %), E (>30 %). Cells with CV grade E are suppressed in the published tables.

## 2. Tables (18 tables in the schema)

The xlsx workbook ships 18 sheets, one per analytical cut. Naming convention: `tab_6_<n>` where `n` is the IBGE table number.

| Family | Tables | What they cut |
|---|---|---|
| Headline | `tab_6_1a`, `tab_6_1b` | National + per-region trajectories. Note the geography lives in **columns**, not rows (W1 caveat — see below). |
| Domain × geography | `tab_6_3`, `tab_6_4`, `tab_6_5` | Cultural-sector share by sex × region; race × region; race × sex (proxy only — see W2). |
| Income | `tab_6_6` | Income by sex, race (cells), region. The race × sex cross is NOT in the table — Note 6 mathematical workaround uses single-axis cuts as proxy (W2). |
| Formality | `tab_6_7`, `tab_6_8` | Formality rate by attribute and by region. |
| Position in occupation | `tab_6_10` | The "great inversion" — CLT 46 % → 34 %, conta-própria 31 % → 43 % (2014–2024). The empirical engine of Análise 2. |
| Hours | `tab_6_11`, `tab_6_12` | Hours-worked distributions. |
| Top occupations | `tab_6_13`, `tab_6_14` | Top 25 cultural CBO codes — the "where the workers actually are" tables; basis of Análise 1 + 2. **Row 8 is the Brazil total; individual rows start at row 9** (W5). |
| Activities | `tab_6_15`, `tab_6_16`, `tab_6_17` | Cultural CNAE activity breakdowns. |

Each table preserves the published structure verbatim (wide format, one Parquet per sheet). No row-level reshape — the published tables already carry CVs in the column adjacent to every value.

## 3. Methodology / ingest notes

- **ETL is openpyxl → DuckDB COPY → Parquet (ZSTD).** Idempotent; byte-identical reruns.
- **Source xlsx files** are checked into `raw/ibge_pnadc/_source/` and gitignored from `raw/ibge_pnadc/`.
- **CV column convention:** the column immediately to the right of every value column carries the CV letter (A–E). The ETL preserves this — readers join `c<n>` with `c<n+1>` for confidence.
- **No deflation** — most cuts are share or count; income cells are nominal BRL of the published vintage, deflate downstream with `atana.macro.ipca` if comparing across years.

## 4. Caveats (W1–W7)

| # | Alert |
|---|---|
| W1 | **Tables 6.1a and 6.1b put geography in columns, not rows.** Searching by `row[0]=='Brasil'` will return nothing. The Brazil column is column 1. |
| W2 | **Table 6.6 has no race × sex cross.** Income figures for "mulheres brancas" / "homens pretos" cited in Análise 3 are mathematical projections from single-axis cuts, not direct measurements. Flag this when publishing. |
| W3 | **Tables 6.13 / 6.14** — the "Total" row is row 8; individual top-25 occupations start at row 9. Off-by-one is the common bug. |
| W4 | **Table 6.10** — Brazil row index may shift by year; validate by the expected value (~43 % conta-própria in 2024) rather than positional indexing. |
| W5 | Cells with **CV = B (5–10 %)** are publishable but should carry a "high confidence" footnote, not "A-grade". CV = C is indicative only. |
| W6 | **PNADC is a household survey, not an administrative register.** It catches informal workers (the conta-própria + autônomo population) that `atana.rais` cannot see — this is the central reason the corpus carries both. |
| W7 | The cultural-sector cut is a fixed IBGE codelist of cultural CNAEs + CBOs; activities can shift over time as classifications update. Document any specific CNAE list when comparing across years. |

## 5. References

- The **Data Context Skill** for this schema lives at `.claude/skills/ibge-pnadc-cultural/` and contains column maps, key 2024 metrics, recipes, and the warnings reference.
- Original publication: **IBGE — Informações Culturais 2024**, capítulo 6.
- CLAUDE.md §2, §6, §8 (the book's analytical anchor for this schema).
