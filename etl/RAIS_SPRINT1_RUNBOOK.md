# RAIS Sprint 1 — Operational Runbook

> Step-by-step guide to run the Sprint 1 ETL locally.
>
> **Prerequisites:** Sprint 0 complete (reference parquets + methodology + Check 1 GREEN).
> **Estimated time:** 6–10 hours of wall-clock, mostly BigQuery I/O.
> **BigQuery budget:** ~200–400 GB total scanned, well inside the 1 TB/month free tier.

---

## 0. Before you start (5 minutes)

```bash
cd "/Users/joaoroque/Documents/Cultural production - book/Dados da Economia Cultural no Brasil"
```

Verify Sprint 0 prerequisites exist:

```bash
ls atana-data/raw/rais/_reference/         # should show cnae_cultural.parquet + cbo_cultural.parquet
cat rais_sprint0_check1_findings.md | head -5   # verdict should be GREEN
```

Set required environment variables:

```bash
export GCP_PROJECT_ID=atana-research
# MOTHERDUCK_TOKEN is optional — without it, the ETL skips cloud sync
# (Parquets still get written locally)
```

---

## 1. PIS hashing salt — NOT required for Sprint 1 (basedosdados has no PIS)

The basedosdados public RAIS strips PIS for LGPD compliance, so the Sprint 1 ETL does not need `ATANA_PIS_SALT`. The salt becomes required only for **Phase 2b** (MTE FTP pipeline; see `notes/rais_phase2b_mte_ftp_scoping.md`).

If you've already generated and exported the salt, that's fine — leave it. If not, skip this step entirely.

---

## 2. Smoke test (no BigQuery, ~30 seconds)

Validates the transform pipeline before burning any quota.

```bash
python3 atana-data/etl/rais__bigquery_to_parquet.py --smoke
```

Expected output ends with `✅ Smoke test passed`. The test exercises PIS hashing, cut tagging, dual-measure aggregation, and IGNORADO handling on synthetic data.

---

## 3. Dry run — one year, sample (3 minutes)

Pull a 10k-row sample of 2023 to test the BigQuery path with real data.

```bash
python3 atana-data/etl/rais__bigquery_to_parquet.py --year 2023 --limit 10000
```

Expected output ends with `YEAR 2023 — done`. Inspect outputs:

```bash
ls atana-data/raw/rais/                                                 # 4 table folders + _reference
ls atana-data/raw/rais/cnpj_cultural_employer_panel/year=2023/          # part-0.parquet
duckdb -c "SELECT COUNT(*), AVG(n_vinculos_total) FROM 'atana-data/raw/rais/cnpj_cultural_employer_panel/year=2023/part-0.parquet'"
```

If anything looks wrong, fix and re-run with `--refresh`. Delete the sample outputs before the full run:

```bash
rm -rf atana-data/raw/rais/{estabelecimentos_culturais,vinculos_em_*,cnpj_cultural_employer_panel}/year=2023
```

---

## 4. Full year — 2023 production run (30–60 minutes)

```bash
python3 atana-data/etl/rais__bigquery_to_parquet.py --year 2023
```

Watch the log file in another terminal:

```bash
tail -f atana-data/etl/rais__bigquery_to_parquet.log
```

Expected output magnitudes (from Check 1):

| Table | Rows |
|---|---:|
| estabelecimentos_culturais | ~700,000 |
| vinculos_culturais (Cut A ∪ Cut B) | ~2,000,000 |
| panel_cnae_municipio_ano (derived) | ~100,000–300,000 |

If MOTHERDUCK_TOKEN is set, the script also pushes to `md:atana.rais.*`.

---

## 5. Full panel — 2014 to 2023 (overnight, ~6–10 hours)

Once 2023 looks healthy, run the rest:

```bash
nohup python3 atana-data/etl/rais__bigquery_to_parquet.py > rais_etl_overnight.out 2>&1 &
disown
```

The script skips 2023 (already done) and iterates 2022 → 2014. If interrupted, re-running picks up where it stopped (already-written years are skipped).

Monitor:

```bash
tail -f atana-data/etl/rais__bigquery_to_parquet.log
ls atana-data/raw/rais/cnpj_cultural_employer_panel/        # should grow: year=2023, year=2022, ...
```

---

## 6. IPCA deflation (10 minutes)

Once all 10 years are written:

```bash
python3 atana-data/etl/rais__deflate_ipca.py
```

Adds `_ipca` columns to vínculos and panel parquets (base year = 2024). Re-syncs to MotherDuck.

To use a different base year:

```bash
python3 atana-data/etl/rais__deflate_ipca.py --base 2014   # base year of the panel start
```

---

## 7. Sanity checks before Sprint 2 validation

```bash
# Per-year row counts via DuckDB
duckdb -c "
SELECT
    year,
    SUM(n_vinculos_total) AS total_workforce
FROM read_parquet('atana-data/raw/rais/cnpj_cultural_employer_panel/year=*/part-0.parquet', hive_partitioning=1)
GROUP BY year ORDER BY year
"
```

Expected pattern (per Check 1):

- 2020: ~1.05M
- 2021: ~1.20M (+13.7%)
- 2022: ~1.44M (+20.1%)
- 2023: ~1.54M (+7.2%)
- 2014–2019: growth trajectory before the pandemic dip

If any year is anomalously low (< 0.5 × neighbors), check the log for that year and consider `--refresh`.

---

## 8. What "done" looks like

Sprint 1 is done when:

- [ ] All 10 years × 3 tables = 30 parquets exist under `atana-data/raw/rais/`
- [ ] `_reference/ipca_annual_mean.parquet` cached
- [ ] `md:atana.rais.*` has 3 tables (`estabelecimentos_culturais`, `vinculos_culturais`, `panel_cnae_municipio_ano`), each with rows for 2014–2023
- [ ] Per-year row counts roughly track Check 1 expectations
- [ ] No errors in `rais__bigquery_to_parquet.log`

**Phase 3 enablement note:** Sprint 1 unlocks the **H0 paper** ("most Rouanet proponentes operate outside the formal employment frame"). It does *not* unlock the H1 causal paper — that needs CNPJ-level linkage which basedosdados strips. The H1 path is bookmarked as **Phase 2b** (MTE FTP pipeline); see `notes/rais_phase2b_mte_ftp_scoping.md`.

At that point, open the Sprint 2 conversation. The kickoff message is in `notes/rais_sprint0_completion.md` (it points to here).

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| `ERROR: ATANA_PIS_SALT not set` | Salt env var missing | Re-run step 1, then `source ~/.zshrc` |
| `ERROR: GCP_PROJECT_ID not set` | env var missing | `export GCP_PROJECT_ID=atana-research` |
| `schema discovery failed` | basedosdados table renamed | Update `COL_ALIASES` in main ETL script |
| BigQuery quota error | Free tier exhausted | Wait for monthly reset, or supply billing card |
| One year missing in output | Interrupted mid-run | Just re-run; idempotent |
| Want to redo a year | Schema drift, transform fix | `--year YYYY --refresh` |
| Hash determinism check fails | Salt changed between runs | Restore the original salt from 1Password |

---

## What this delivers

- **`atana-data/raw/rais/<table>/year=YYYY/part-0.parquet`** — 40 partitioned Parquet files
- **`atana-data/raw/rais/_reference/ipca_annual_mean.parquet`** — cached deflator
- **`md:atana.rais.{estabelecimentos_culturais, vinculos_em_estabelecimentos_culturais, vinculos_em_ocupacoes_culturais, cnpj_cultural_employer_panel}`** — 4 cloud-queryable tables, 2014–2023
- **`atana-data/etl/rais__bigquery_to_parquet.log`** — full audit trail

Sprint 2 (validation against SIIC) and Phase 3 (SALIC × RAIS paper) build on top of this.
