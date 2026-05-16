# Naming conventions

Stable rules for naming schemas, tables, columns, and files in this repository and in `md:atana`. Keep these consistent — they are part of the public contract.

## Schemas

One schema per data source. Lowercase, underscores, no hyphens.

| Schema | Source | Notes |
|---|---|---|
| `unctad` | UNCTADstat (Creative Economy) | International benchmarks |
| `ibge_pnadc` | IBGE PNADC Cultural | Continuous workforce survey, annual |
| `ibge_comex` | IBGE Comércio Exterior Cultural | Cultural foreign trade |
| `salic` | MinC SALIC API | Lei Rouanet projects |
| `lexml` | Senado Federal LexML | Legislative corpus |
| `canonical` | Curated analytical snapshots | Used by published analyses |

## Tables

- **Lowercase + snake_case** (e.g., `goods_value`, `services_countries`)
- **For IBGE tables**: prefixed by `tab_` and table number (e.g., `tab_6_10`, `tab_10_1`)
- **Single noun + qualifier**: `projetos`, `incentivadores_edges`, `corpus_completo`
- **No table number from analysis numbering** — refer to source numbering only

## Columns

- **Original columns preserved as-is when from a structured source** (UNCTAD column names use spaces and `$` because that's how UNCTAD provides them — preserved for traceability)
- **New columns added in ETL** use lowercase snake_case
- **Time**: always `year` (BIGINT) or `date` (DATE) — never `Year` or `Ano` in newly-created columns
- **Country**: prefer ISO 3-digit codes in `country_code` column; full names in `country_label`
- **Currency suffix**: when value is in non-default currency, suffix the column: `value_usd_million`, `value_brl_million`, `value_brl_fob_million`

## File names

Inside `raw/<source>/`:

- One Parquet file per table: `<table_name>.parquet`
- For multi-year sources stored as one file: `<table_name>.parquet`
- For multi-year sources stored separately: `<table_name>__<year>.parquet`

ETL scripts in `etl/`:

- `<source>__<action>.py` — e.g., `ibge_pnadc__xlsx_to_parquet.py`, `salic__refresh.py`, `motherduck__sync.py`

## Versioning

- **Source data versioning**: each ETL writes a `<table_name>.parquet` and a sidecar `<table_name>.meta.json` with source URL, fetch date, file hash
- **Analytical snapshots in `canonical/`**: timestamped — `latam_creative_2024__2026-05-14.parquet` — allowing prior versions to remain accessible

## Languages

- **Code, schemas, table names**: English
- **Column names from IBGE/SALIC**: Portuguese (original) — preserved verbatim for traceability
- **Manifest, README, ETL comments**: English
- **Atana analyses themselves**: bilingual (PT primary, EN/ES as needed)

This split is deliberate: the data layer is internationally consumable; the analytical layer can be localized.
