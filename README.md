# atana-data

Open data repository for the **Atana** research practice — evidence-based AI policy for creative economies in Latin America.

This repository hosts curated, versioned datasets in Apache Parquet format covering the cultural and creative economies of Brazil and Latin America. It is the upstream source of truth for the analyses published in [atana.studio](https://atana.studio) and the Atana Index series.

---

## What's here

| Folder | Content |
|---|---|
| `raw/` | Source data, lightly normalized into Parquet (one folder per source) |
| `curated/` | Derived datasets used directly by published analyses (a.k.a. analytical snapshots) |
| `etl/` | Scripts that produce the Parquet files from the original sources (xlsx, API, JSONL) |
| `docs/` | Manifest of all tables, naming conventions, methodology notes |

---

## Quick start

### Querying with DuckDB (local, no install beyond DuckDB)

```bash
# Install duckdb cli (one-time)
brew install duckdb

# Query a Parquet file directly
duckdb -c "
SELECT \"Economy Label\", \"US\$ at current prices in millions\"
FROM 'https://github.com/joaoroquer/atana-data/raw/main/raw/unctad/services_countries.parquet'
WHERE Year=2024 AND Flow='02' AND \"Economy Label\"='Brazil'
"
```

### Querying via MotherDuck (cloud, faster, joinable across sources)

All datasets are mirrored to the `md:atana` MotherDuck database, organized into schemas matching the folder structure:

```sql
-- Connect: duckdb md:atana?motherduck_token=YOUR_TOKEN
SELECT * FROM atana.unctad.services_countries WHERE Year=2024 LIMIT 10;
SELECT * FROM atana.ibge_comex.tab_10_1 WHERE year=2024;        -- coming in Phase 2
SELECT * FROM atana.ibge_pnadc.tab_6_10 WHERE year=2024;        -- coming in Phase 2
```

To request access to the read-only token for `md:atana`, see the [data access policy](docs/data_access.md) (coming soon).

### From Python

```python
import duckdb
con = duckdb.connect()

# Option A — read Parquet directly from GitHub
df = con.execute("""
    SELECT * FROM 'https://github.com/joaoroquer/atana-data/raw/main/raw/unctad/goods_value.parquet'
    WHERE Year=2024 AND Product='CER024'
""").df()

# Option B — query MotherDuck
con = duckdb.connect("md:atana?motherduck_token=...")
df = con.execute("SELECT * FROM atana.unctad.goods_value WHERE Year=2024").df()
```

---

## What's in `raw/`

| Source | Tables | Coverage | Status |
|---|---|---|---|
| `unctad/` | 4 tables (goods_value, goods_growth, services_countries, services_regional) | Global, 1995–2024 (services since 2005) | ✅ Live in MotherDuck |
| `ibge_pnadc/` | 15 tables (Tabela 6.1a – 6.17) | Brazil, 2014–2024 (annual) | 🚧 Phase 2 |
| `ibge_comex/` | 4 tables (Tabela 10.1–10.4) | Brazil cultural foreign trade, 2014–2024 | 🚧 Phase 2 |
| `salic/` | Projects + edges (Lei Rouanet) | Brazil, 2019–2026, 26 k projects | 🚧 Phase 2 |
| `lexml/` | Legislative corpus (creative economy) | Brazil, 1998–2026, 269 acts | 🚧 Phase 2 |

See [`docs/manifest.md`](docs/manifest.md) for the complete catalog of tables, columns, and provenance.

---

## License

Data is licensed under [Creative Commons Attribution 4.0 International (CC BY 4.0)](https://creativecommons.org/licenses/by/4.0/) — you may share and adapt, with attribution.

Underlying source data carries its own licenses:
- UNCTADstat — open data, citation requested
- IBGE *Informações Culturais* (SIIC) — open data, public domain
- MinC SALIC API — public, open
- Senado Federal LexML — public, open

Code (ETL scripts) is licensed under MIT.

---

## Provenance & citation

If you use these datasets in a publication, cite:

> Roquer, J. (2026). *atana-data: Open data on creative economies in Latin America*. Atana Research. https://github.com/joaoroquer/atana-data

The original sources should also be cited individually. See [`docs/citations.md`](docs/citations.md) for boilerplate citation strings for each source.

---

## Contact

- João Roquer — joaoroquer@gmail.com
- Atana — [atana.studio](https://atana.studio) (under construction)
