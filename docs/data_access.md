# Data access

## Public — via GitHub (Parquet over HTTP)

All Parquet files in `raw/` and `curated/` are queryable directly from the GitHub raw URLs. No authentication required.

```bash
duckdb -c "
SELECT * FROM 'https://github.com/joaoroquer/atana-data/raw/main/raw/unctad/services_countries.parquet'
WHERE Year=2024 LIMIT 10
"
```

## Cloud query layer — `md:atana` on MotherDuck

For interactive / faster queries (and joins across sources), the same data is mirrored to a MotherDuck cloud database.

### Read-only access

Currently the database is provisioned with the maintainer's personal token. To request a public read-only access token, contact joaoroquer@gmail.com or open an issue.

Read-only requests are typically granted within 48h for:
- Academic research
- Journalism
- Civil society organizations working on cultural policy

### Connection example

```python
import duckdb
con = duckdb.connect(f"md:atana?motherduck_token={READ_ONLY_TOKEN}")
df = con.execute("""
    SELECT "Economy Label", "US$ at current prices in millions"
    FROM atana.unctad.services_countries
    WHERE Year=2024 AND Flow='02'
    ORDER BY 2 DESC LIMIT 20
""").df()
```

## Reproducing locally

If you want a fully local setup that mirrors the cloud database:

```bash
# Clone the repo
git clone https://github.com/joaoroquer/atana-data.git
cd atana-data

# Create a local DuckDB from the Parquet files
duckdb local.duckdb <<'SQL'
CREATE SCHEMA unctad;
CREATE TABLE unctad.goods_value AS SELECT * FROM 'raw/unctad/goods_value.parquet';
CREATE TABLE unctad.services_countries AS SELECT * FROM 'raw/unctad/services_countries.parquet';
-- ...repeat for other tables
SQL

# Query
duckdb local.duckdb "SELECT * FROM unctad.services_countries LIMIT 5"
```
