# Phase 2 — Finalization steps (run these in Terminal)

All Phase 2 ETL work is complete inside the sandbox:

- ✅ 5 ETL scripts written to `etl/`
- ✅ 35 Parquet files written to `raw/` across 5 schemas
- ✅ All tables synced to `md:atana.{unctad,ibge_pnadc,ibge_comex,salic,lexml}.*`
- ✅ `docs/manifest.md` updated with row counts
- ✅ Files staged with `git add -A`
- ❌ Commit blocked by stale lockfile in sandbox

Run these commands locally to finish the push:

```bash
cd "/Users/joaoroque/Documents/Cultural production - book/Dados da Economia Cultural no Brasil/atana-data"

# 1. Clear stale git locks from sandbox
rm -f .git/index.lock .git/HEAD.lock

# 2. Delete the obsolete 321 MB single-file goods_value.parquet
#    (replaced by partitioned raw/unctad/goods_value/goods_value_<YYYY>.parquet)
#    Also delete the leftover placeholder file
rm -f raw/unctad/goods_value.parquet raw/unctad/_placeholder.md

# 3. Commit
git commit -m "Phase 2: Load IBGE PNADC + Comex + SALIC + LexML + UNCTAD partitioned

- 18 IBGE PNADC tables (Tabela 6.1a–6.17) as wide/long Parquet
- 4 IBGE Comex tables (Tabela 10.1–10.4)
- 3 SALIC tables (projetos, edges_incentivador, propostas_recentes)
- 5 LexML tables (corpus, legal, biblio, classified, with_ementas)
- UNCTAD goods_value partitioned by year (23 files of ~14MB)
- All tables synced to md:atana.<schema>.<table> on MotherDuck
- gen_latam_fig3_fig9.py migrated to use atana.unctad.* schema
- 5 ETL scripts in etl/ — idempotent, MOTHERDUCK_TOKEN-driven"

# 4. Push
git push
```

## Sanity-check: what was loaded

Open https://github.com/joaoroquedasilvajunior/atana-data after pushing — `raw/` should now have 4 new folders alongside `unctad/`:

- `raw/ibge_comex/` — 4 Parquet files
- `raw/ibge_pnadc/` — 18 Parquet files
- `raw/salic/` — 3 Parquet files (largest: propostas_recentes ~13 MB)
- `raw/lexml/` — 5 Parquet files
- `raw/unctad/goods_value/` — 23 yearly Parquet files (~14 MB each)

`docs/manifest.md` should render with the updated catalog showing row counts.

## Verifying MotherDuck

To confirm everything is live in the cloud DB:

```bash
duckdb "md:atana?motherduck_token=$MOTHERDUCK_TOKEN" <<'SQL'
SELECT schema_name, table_name, estimated_size
FROM duckdb_tables()
WHERE database_name='atana' AND schema_name NOT IN ('information_schema','main')
ORDER BY 1, 2;
SQL
```

Expected output: 35 tables across 5 schemas.

## Once pushed, what to delete from the analysis project

These are now redundant — the data lives in `atana-data/` + MotherDuck:

```bash
# Optional — only if you want to free disk space; the originals are still useful as backup
# rm -rf "../6_ocupacao_no_setor_cultural"   # IBGE PNADC xlsx (≈40 MB)
# rm -rf "../10_comercio_exterior_de_bens_e_servicos_culturais"  # IBGE Comex xlsx (≈200 KB)
# rm -rf "../salic_api_data"                  # SALIC JSONL (~70 MB)
# rm -rf "../a9_data"                          # LexML JSONL (~5 MB)
```

**Don't delete** these — they're still needed:
- `analise_*.md` (the published analyses)
- `Graficos produzidos/`
- `_atana_intel/`
- `gen_latam_fig3_fig9.py` and other generation scripts
- `.claude/skills/`

## Migrating other scripts

`gen_latam_fig3_fig9.py` is the template. To migrate any other analysis script:

1. Find the line that opens a MotherDuck connection (usually `duckdb.connect("md:unctad_culture?...")` or similar)
2. Replace `md:unctad_culture` → `md:atana`
3. Prefix table names with their schema (`creative_goods_value` → `atana.unctad.goods_value`)
4. For IBGE scripts that read xlsx via openpyxl: replace with SQL against `atana.ibge_pnadc.tab_*` or `atana.ibge_comex.tab_*`

Scripts to migrate (recommended priority order):
- `gen_t10_charts.py` → use `atana.ibge_comex.tab_10_*`
- `gen_gastos_charts.py` → still uses local xlsx for now; can wait
- Other analysis scripts → migrate when next touching them
