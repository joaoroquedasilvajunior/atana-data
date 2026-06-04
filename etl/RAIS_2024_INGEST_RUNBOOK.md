# RAIS 2024 + 2025 — Ingest Runbook

> Turnkey sequence to extend the `atana.rais` corpus from **2014–2023 → 2014–2025**.
> Triggered by the DB-updater run of 2026-05-25 (RAIS 2024 vintage detected) and
> **verified 2026-06-04 against the Base dos Dados portal: temporal coverage now
> reads `1985 – 2025`** — i.e. the 2025 vintage has also landed (unusually early
> against RAIS's typical ~N+1 lag). Both years are pulled here.
>
> **Why this is a local step:** the pull runs a billed BigQuery job through
> `basedosdados` and needs the `atana-research` GCP project + Application
> Default Credentials. The Atana sandbox has neither — same hand-off pattern
> as every prior RAIS / BCB pull. Run this on João's Mac.
>
> **Estimated time:** ~60–120 min wall-clock for both years (mostly BigQuery I/O).
> **BigQuery budget:** ~40–80 GB scanned for the two years — well inside the
> 1 TB/month free tier.
> **Prereqs:** Sprint 0 reference parquets present; `basedosdados` installed;
> `gcloud` auth or a service-account key for project `atana-research`.

---

## 0. The hardening is already done

Flags 1 and 3 from the DB-updater proposal are resolved (2026-05-25):

- `rais__bigquery_to_parquet.py` and `rais__deflate_ipca.py` now accept
  `--staging` (writes to `raw/rais/_staging/`) and honour `ATANA_ETL_SKIP_PUSH`
  (skips the MotherDuck sync). `.gitignore` excludes `raw/*/_staging/`.
- `rais__deflate_ipca.py`'s docstring was reconciled (the *runtime* targets
  were already the correct Sprint 1 names).

You do **not** need to edit the ETL scripts. Just run the steps below.

> **Flag 2 (MTE renamed dissemination variables) is handled automatically.**
> Both pull queries call `discover_schema()` first — a `LIMIT 0` probe that
> fail-fasts and prints the full actual column list if any expected column is
> missing. Base dos Dados normally harmonises column names across years, so
> the existing SQL most likely still works; if it does not, the ETL stops
> cleanly before pulling any data — see Troubleshooting.

---

## 1. Setup (2 min)

```bash
cd "/Users/joaoroque/Documents/Cultural production - book/Dados da Economia Cultural no Brasil/atana-data"

export GCP_PROJECT_ID=atana-research
export MOTHERDUCK_TOKEN=$(cat .motherduck_token)     # used only in step 5
```

Confirm the reference parquets exist (Sprint 0 output):

```bash
ls raw/rais/_reference/        # cnae_cultural.parquet, cbo_cultural.parquet, ipca_annual_mean.parquet
```

---

## 2. Smoke test — free, ~30 s

```bash
python3 etl/rais__bigquery_to_parquet.py --smoke
```

Expect `✅ Smoke test passed`. This validates the transform pipeline (cut
tagging, panel aggregation) without touching BigQuery.

> Optional dry-run: `python3 etl/rais__bigquery_to_parquet.py --year 2024 --staging`
> writes 2024 to `raw/rais/_staging/` and never syncs MotherDuck — useful to
> eyeball the year in isolation. It is a separate BigQuery scan of similar cost;
> delete `raw/rais/_staging/` afterwards (`rm -rf raw/rais/_staging`).

---

## 3. Pull 2024 — local Parquet only (BigQuery, ~20–40 min)

**Run the pull with `ATANA_ETL_SKIP_PUSH=1`.** This writes the three 2024
Parquet partitions locally but does **not** sync MotherDuck — deliberate; see
the box below.

```bash
ATANA_ETL_SKIP_PUSH=1 python3 etl/rais__bigquery_to_parquet.py --year 2024
ATANA_ETL_SKIP_PUSH=1 python3 etl/rais__bigquery_to_parquet.py --year 2025
```

Writes (six new partitions — three tables × two years):

```
raw/rais/estabelecimentos_culturais/year=2024/part-0.parquet
raw/rais/estabelecimentos_culturais/year=2025/part-0.parquet
raw/rais/vinculos_culturais/year=2024/part-0.parquet
raw/rais/vinculos_culturais/year=2025/part-0.parquet
raw/rais/panel_cnae_municipio_ano/year=2024/part-0.parquet
raw/rais/panel_cnae_municipio_ano/year=2025/part-0.parquet
```

Expect the log to end with `YEAR 2024 — done`. Watch it live if you like:
`tail -f etl/rais__bigquery_to_parquet.log`.

> ### ⚠️ Why skip the inline MotherDuck sync here
> `sync_motherduck()` recreates a cloud table whenever the column set drifts.
> The 2024 pull produces vínculos/panel rows **without** the `_ipca` columns;
> the live `md:atana.rais.vinculos_culturais` and `panel_cnae_municipio_ano`
> tables **have** `_ipca` columns (added by the Sprint 1 deflation). Syncing
> the pull directly would be read as a drift and **drop 2014–2023** from those
> two cloud tables. So: pull skips the sync, the deflation (step 4) produces
> the `_ipca` columns, and step 5 syncs the deflated, schema-matching 2024 rows.

---

## 4. Deflate 2024 + 2025 — local Parquet only (~2 min)

> ### ⚠️ IPCA cache needs to be extended for 2025
> The existing cached IPCA series at
> `raw/rais/_reference/ipca_annual_mean.parquet` was built from a BCB pull
> with `dataFinal=31/12/2024` — i.e. it covers **2014–2024 only**. Deflating
> the 2025 RAIS vintage to base-2024 BRL requires the IPCA index for 2025
> (`deflator_2025 = ipca(2024) / ipca(2025)`), which the cache does not have.
>
> Two one-time prep steps before running the deflate for 2025:
>
> 1. **Edit** `etl/rais__deflate_ipca.py` — in `pull_ipca_annual()`, change
>    the hardcoded `dataFinal=31/12/2024` in the BCB SGS URL to `31/12/2025`
>    (or just to the current end-of-year for future-proofing).
> 2. **Delete the cache** so it re-pulls:
>    `rm raw/rais/_reference/ipca_annual_mean.parquet`
>
> The next `rais__deflate_ipca.py` invocation re-pulls the full IPCA series
> from BCB SGS (no auth needed) and writes the extended cache. After that
> the 2025 deflation runs cleanly.

```bash
# After the IPCA cache prep above:
ATANA_ETL_SKIP_PUSH=1 python3 etl/rais__deflate_ipca.py --year 2024
ATANA_ETL_SKIP_PUSH=1 python3 etl/rais__deflate_ipca.py --year 2025
```

Adds the IPCA-deflated `_ipca` columns to the vínculos and panel parquets.
Base year is 2024, so the 2024 `_ipca` values equal the nominal values
(deflator = 1.0). The 2025 `_ipca` values will be slightly below nominal
(2025 BRL is worth less than 2024 BRL).

After this step all three 2024 parquets are final and schema-consistent with
2014–2023. Nothing has touched MotherDuck yet.

---

## 5. QA — before committing

```bash
duckdb -c "
SELECT ano,
       COUNT(*)                       AS n_vinculos,
       SUM(CAST(in_cut_a AS INT))      AS cut_a,
       SUM(CAST(in_cut_b AS INT))      AS cut_b,
       COUNT(DISTINCT sigla_uf)        AS n_uf
FROM read_parquet('raw/rais/vinculos_culturais/year=2023/part-0.parquet')
GROUP BY ano
UNION ALL
SELECT ano, COUNT(*), SUM(CAST(in_cut_a AS INT)), SUM(CAST(in_cut_b AS INT)),
       COUNT(DISTINCT sigla_uf)
FROM read_parquet('raw/rais/vinculos_culturais/year=2024/part-0.parquet')
GROUP BY ano
ORDER BY ano;
"
```

Check:

- [ ] 2024 row count is the same order of magnitude as 2023 (2023 grew +7.2 % YoY;
      expect modest 2024 movement, not a 2× jump or collapse).
- [ ] `n_uf` is 27 (or 27 + `IGNORADO` — the `IGNORADO` UF convention is documented
      in `docs/rais_methodology.md` §4.5).
- [ ] `_ipca` columns present: `duckdb -c "DESCRIBE SELECT * FROM read_parquet('raw/rais/vinculos_culturais/year=2024/part-0.parquet')" | grep ipca`
- [ ] No errors in `etl/rais__bigquery_to_parquet.log`.

If a year looks wrong, re-run the pull with `--year 2024 --refresh`.

---

## 6. Commit the new partitions (GitHub)

`git add` **only** the RAIS paths and the hardening files — do not `git add -A`,
the working tree has unrelated changes from earlier sessions.

```bash
# ETL hardening + docs (this can also be its own earlier commit)
git add etl/rais__bigquery_to_parquet.py etl/rais__deflate_ipca.py \
        etl/RAIS_2024_INGEST_RUNBOOK.md .gitignore docs/manifest.md
git commit -m "RAIS ETL: --staging + skip-push hardening; 2024 ingest runbook; manifest atana.rais section"

# the 2024 data
git add raw/rais/vinculos_culturais/year=2024 \
        raw/rais/vinculos_culturais/year=2025 \
        raw/rais/estabelecimentos_culturais/year=2024 \
        raw/rais/estabelecimentos_culturais/year=2025 \
        raw/rais/panel_cnae_municipio_ano/year=2024 \
        raw/rais/panel_cnae_municipio_ano/year=2025 \
        raw/rais/_reference/ipca_annual_mean.parquet \
        etl/rais__deflate_ipca.py
git commit -m "RAIS: ingest ano-base 2024 + 2025 (corpus now 2014-2025); extend IPCA cache to 2025"

git push
```

---

## 7. Sync 2024 to MotherDuck — safe, explicit

Do **not** re-run the ETLs to sync. Run this snippet — it column-aligns the
INSERT and **refuses** to proceed on a schema mismatch (never drops a table):

```python
import duckdb
from pathlib import Path

REPO = Path.cwd()      # run from the atana-data/ directory
token = (REPO / ".motherduck_token").read_text().strip()
con = duckdb.connect(f"md:atana?motherduck_token={token}")

YEARS = [2024, 2025]   # both new vintages from the runbook
TABLES = ["estabelecimentos_culturais", "vinculos_culturais",
          "panel_cnae_municipio_ano"]

for t in TABLES:
    cloud = [r[0] for r in con.execute(f"DESCRIBE atana.rais.{t}").fetchall()]
    cols = ", ".join(f'"{c}"' for c in cloud)
    for year in YEARS:
        pq = REPO / "raw" / "rais" / t / f"year={year}" / "part-0.parquet"
        assert pq.exists(), f"missing {pq}"
        new = [r[0] for r in con.execute(
            f"DESCRIBE SELECT * FROM read_parquet('{pq}', hive_partitioning=0)").fetchall()]
        if set(cloud) != set(new):
            print(f"  STOP {t} year={year}: column mismatch — do NOT sync, investigate.")
            print(f"    only in cloud      : {sorted(set(cloud) - set(new))}")
            print(f"    only in {year} pq  : {sorted(set(new) - set(cloud))}")
            continue
        con.execute(f"DELETE FROM atana.rais.{t} WHERE ano = {year}")
        con.execute(f"INSERT INTO atana.rais.{t} ({cols}) "
                    f"SELECT {cols} FROM read_parquet('{pq}', hive_partitioning=0)")
        n = con.execute(
            f"SELECT COUNT(*) FROM atana.rais.{t} WHERE ano = {year}"
        ).fetchone()[0]
        print(f"  OK  {t} year={year}: {n:,} rows synced")
con.close()
```

If any (table, year) prints `STOP`, the schema diverged (most likely MTE / Base
dos Dados renamed a column and `VINCULOS_COLUMNS` / `ESTABELECIMENTOS_COLUMNS`
were edited for the pull). Reconcile before syncing — do not let a table be
dropped. **The same column set must hold for both years**; if 2024 syncs cleanly
but 2025 prints STOP, that's still a hard stop on 2025.

Verify per-table year coverage:

```python
# atana.rais.* should now span 2014..2025
con.execute("""
    SELECT MIN(ano), MAX(ano), COUNT(DISTINCT ano)
    FROM atana.rais.vinculos_culturais
""").fetchall()
```

---

## 8. Docs update (after the pull succeeds)

**`docs/manifest.md`** — in the `atana.rais` section, change the coverage line
from `2014–2023` to `2014–2025`, and add to the Update log table:

```
| 2026-06-04 | RAIS: ano-base 2024 + 2025 ingested — `atana.rais.{vinculos_culturais, estabelecimentos_culturais, panel_cnae_municipio_ano}` extended to 2014–2025 (six new year-partitions, 3 tables × 2 years). IPCA cache extended through 2025. ETL hardened with `--staging` + `ATANA_ETL_SKIP_PUSH`. Pushed to GitHub; MotherDuck synced. |
```

**`CLAUDE.md`** — add a version note in your usual style, e.g.:

> 2026-05-25 (vNN RAIS 2024) — DB-updater detected the `br_me_rais` 2024 vintage;
> `atana.rais.*` extended 2014–2023 → **2014–2025** via `etl/RAIS_2024_INGEST_RUNBOOK.md` (the BdD portal showed `1985–2025` on 2026-06-04, so both new vintages were pulled together).
> RAIS ETL hardened (`--staging` + `ATANA_ETL_SKIP_PUSH`). Análise 11 (RAIS) can now
> be refreshed with the 2024 year.

**`_atana_intel/db_update_log.md`** — append a one-line resolution under the
2026-05-25 proposal (+ 2026-06-04 verification of the 2025 vintage): ingest completed, corpus 2014–2025, commits `<hash>`.

---

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `ModuleNotFoundError: basedosdados` | package not installed | `pip install basedosdados` |
| `GCP_PROJECT_ID not set` | env var missing | `export GCP_PROJECT_ID=atana-research` |
| `DefaultCredentialsError` | no GCP auth | `gcloud auth application-default login`, or set a service-account key |
| `ERROR: required columns missing in br_me_rais...` | Base dos Dados renamed a column (flag 2) | the log prints the full actual column list — map old→new in `VINCULOS_COLUMNS` / `ESTABELECIMENTOS_COLUMNS`, re-run with `--year 2024 --refresh` |
| step 7 prints `STOP ... column mismatch` | 2024 schema diverged from 2014–2023 | reconcile columns; never let the table drop |
| BigQuery quota error | free tier exhausted | wait for monthly reset, or attach billing |
| want to redo 2024 | transform fix / schema drift | `--year 2024 --refresh` |

---

## What this delivers

- `raw/rais/{vinculos_culturais, estabelecimentos_culturais, panel_cnae_municipio_ano}/year=2024/part-0.parquet`
- `md:atana.rais.*` extended to 2014–2024
- `atana.rais` corpus ready for an Análise 11 refresh and the H0 paper's
  formal-employment baseline
