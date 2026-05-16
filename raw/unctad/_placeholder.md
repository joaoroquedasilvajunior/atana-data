# UNCTAD raw exports — Phase 2

This folder will host Parquet exports of the four UNCTAD tables currently live in `md:atana.unctad`:

- `goods_value.parquet`   (~25 M rows)
- `goods_growth.parquet`  (~24 M rows)
- `services_countries.parquet` (5,336 rows)
- `services_regional.parquet`  (945 rows)

Export will be done in Phase 2 (next session) via:

```python
import duckdb, os
con = duckdb.connect(f"md:atana?motherduck_token={os.environ['MOTHERDUCK_TOKEN']}")
for t in ['goods_value','goods_growth','services_countries','services_regional']:
    con.execute(f"COPY atana.unctad.{t} TO 'raw/unctad/{t}.parquet' (FORMAT PARQUET, COMPRESSION SNAPPY)")
```

Until then, query via MotherDuck.
