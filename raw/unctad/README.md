# UNCTAD — Raw Parquet exports

Snapshot of the four UNCTAD tables from `md:atana.unctad.*` as Parquet files.

## Files

| File / Folder | Rows | Size | Notes |
|---|---:|---:|---|
| `services_countries.parquet` | 5,336 | ~70 KB | Total creative services by country × year × flow |
| `services_regional.parquet` | 945 | ~20 KB | Regional aggregates with sub-category breakdown |
| `goods_growth.parquet` | 23,953,295 | ~32 MB | YoY growth rates of creative goods trade |
| `goods_value/goods_value_<YYYY>.parquet` | ~1.1 M × 23 years | ~13 MB each | Bilateral creative goods trade, partitioned by year |

`goods_value` is partitioned because the single-file export is ~310 MB (above GitHub's 100 MB per-file limit). All 23 year files together total ~310 MB.

## Querying

### Single file
```sql
SELECT * FROM 'raw/unctad/services_countries.parquet' WHERE Year=2024;
```

### Partitioned `goods_value` — glob pattern reads all years at once
```sql
SELECT * FROM read_parquet('raw/unctad/goods_value/goods_value_*.parquet')
WHERE Year=2024 AND Product='CER023';
```

### One specific year (faster — only reads that file)
```sql
SELECT * FROM 'raw/unctad/goods_value/goods_value_2024.parquet'
WHERE Product='CER023';
```

### Over HTTP from GitHub
```sql
SELECT * FROM read_parquet('https://github.com/joaoroquedasilvajunior/atana-data/raw/main/raw/unctad/goods_value/goods_value_2024.parquet');
```

## Regenerating

```bash
export MOTHERDUCK_TOKEN="..."
python etl/unctad__export_parquet.py
```

Idempotent — skips files that already exist.
