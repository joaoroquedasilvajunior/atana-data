# SALIC year-slice refresh runbook — targeted 2025–2026 backlog

> **Purpose.** The SALIC API returned after a ~5-week blackout reporting a new
> universe total of **59,642** (+1,499 vs the 29/06 baseline of 58,143). Our
> canonical ingest `atana.salic.projetos` is at **48,189** → a corpus lag of
> **~11,453 PRONACs** and coverage of **80.8%** (not the ~85% we cite — the
> universe grew under us). This runbook refreshes ONLY the years where the gap
> lives (expected 2025–2026, the blackout backlog) rather than a 6-hour full
> bulk run.
>
> **Discipline.** Propose-and-approve. Do NOT run the write step (Step 2) until
> the reconciliation diff (Step 0) has been reviewed and confirms the gap is
> concentrated in the year(s) you're about to slice. The downloader upserts to
> **live MotherDuck**, so Step 0.5 (pre-slice snapshot) is mandatory rollback
> insurance.
>
> **Machine.** João-side only. `api.salic.cultura.gov.br` is Cloudflare-Turnstile-gated;
> the sandbox cannot reach it. Requires the Bright Data residential proxy +
> FlareSolverr stack the bulk downloader already uses, and `MOTHERDUCK_TOKEN`.

---

## Environment

```bash
cd atana-data
export MOTHERDUCK_TOKEN="<full JWT — not a placeholder>"
# Bright Data + FlareSolverr must be up (same stack as the 13/06 refresh).
# The downloader throttles to 1 req/sec; a 2-year slice is a small fraction of
# the ~6h full run (order of tens of minutes to ~1–2h incl. WAF retries).
```

---

## Step 0 — Reconcile FIRST (gates everything below)

Produce a light **index pass** from the downloader (id-level only: PRONAC +
ano_projeto + situacao — no full payloads), then diff it against the canonical
parquet. This is what tells you which years to slice.

```bash
# (a) produce the fresh universe index however the downloader exposes it
#     (paginate every year, keep only PRONAC/ano_projeto/situacao). Save as
#     e.g. raw/salic/_staging/salic_index_2026-08-10.parquet

# (b) diff it against the canonical ingest (propose-only, writes nothing to DB)
python3 ../_atana_intel/phase9b_salic_delta_reconcile.py \
  --fresh   raw/salic/_staging/salic_index_2026-08-10.parquet \
  --ingest  raw/salic/projetos.parquet \
  [--snap0629 raw/salic/_staging/pronac_ids_2026-06-29.txt]   # if you kept it
```

Read `_atana_intel/salic_delta_reconcile_<date>.md`:

- **§2 (new PRONACs by ano_projeto)** is the decision. Set the `--years` list in
  Step 2 to exactly the years that carry a material gap.
  - Gap concentrated in **2025–2026** → `--years 2025,2026` (the default case).
  - Material rows in **2023/2024** → add them (`--years 2023,2024,2025,2026`);
    investigate whether they're late registrations or an API-scope change.
- **§3 (new by situacao)** — if the new rows cluster in a status our ingest
  window excludes, part of the "gap" is scope, not lag: adjust the coverage
  claim instead of pulling. Don't refresh phantom rows.
- **§1 dropped PRONACs** — if non-zero, sample them before the run (status flips
  vs genuine removals). Discovery-mode insert never deletes, so drops are safe
  to defer, but note them.

**Gate:** proceed only if §2 confirms the slice years. Otherwise stop and
re-scope.

---

## Step 0.5 — Pre-slice snapshot (rollback insurance)

```bash
python3 - <<'PY'
import os, duckdb, datetime as dt
con = duckdb.connect(f"md:atana?motherduck_token={os.environ['MOTHERDUCK_TOKEN']}")
snap = f"raw/salic/projetos_pre_slice_{dt.date.today().isoformat()}.parquet"
con.execute(f"COPY (SELECT * FROM atana.salic.projetos) TO '{snap}' (FORMAT PARQUET)")
n = con.execute("SELECT COUNT(*) FROM atana.salic.projetos").fetchone()[0]
print(f"snapshot {snap}  ({n:,} rows)")
PY
# keep this file until the refresh is validated + pushed; gitignore it (large).
```

Also record the **pre-slice year distribution** so Step 4 can prove the
untouched years didn't move:

```bash
python3 -c "import os,duckdb; c=duckdb.connect(f\"md:atana?motherduck_token={os.environ['MOTHERDUCK_TOKEN']}\"); print(c.execute('SELECT ano_projeto, COUNT(*) FROM atana.salic.projetos GROUP BY 1 ORDER BY 1').fetchall())"
```

---

## Step 1 — (optional) dry read-only sanity

`--dry-run` only affects *refresh* mode, not discovery, so there is no dry-run
for the insert path — **idempotency is the safety**: discovery skips every
PRONAC already cached, so a slice run inserts only novel rows and touches no
existing row. If you want a no-write preview of the open-cycle refresh path:

```bash
python etl/salic__bulk_download.py --refresh-only --dry-run --years 2025,2026
```

---

## Step 2 — Run the targeted slice (the write step; needs approval)

```bash
# discovery only (insert novel 2025–2026 PRONACs; other years untouched):
python etl/salic__bulk_download.py --years 2025,2026

# OR discovery + refresh open-cycle cycle-state (valor_captado / situacao) too:
python etl/salic__bulk_download.py --refresh-existing --years 2025,2026
```

Notes:
- `--years` (added 2026-08-10) restricts the **discovery** loop to the listed
  years; the default without it is the full `YEARS_TO_BACKFILL`. Discovery stays
  idempotent — reruns are safe and resume after any WAF interruption.
- **Caveat:** `--refresh-existing` refreshes open-cycle PRONACs for `ano ≥ 2020`
  regardless of `--years` (refresh mode is not year-sliced). For a pure
  additive slice, use plain discovery (first command).
- A partial-year interruption is fine — the script saves what it got and the
  next run resumes (already-cached PRONACs are skipped).
- On completion the script **auto-exports** `raw/salic/projetos.parquet` and
  `raw/salic/refresh_log.parquet` from MotherDuck (single source of truth = MD;
  parquet is a derived export).

---

## Step 3 — Validate (must pass before commit)

```bash
python3 ../_atana_intel/phase9b_salic_delta_reconcile.py \
  --fresh  raw/salic/_staging/salic_index_2026-08-10.parquet \
  --ingest raw/salic/projetos.parquet
```

Expect:
- **gap** collapsed to ~0 for the sliced years (residual = scope-only rows, §3).
- **new** ≈ 0 for the sliced years; **coverage** recomputed upward.

Then the invariants:

```bash
python3 - <<'PY'
import duckdb
c = duckdb.connect()
p = "raw/salic/projetos.parquet"
n, d = c.execute(f"SELECT COUNT(*), COUNT(DISTINCT PRONAC) FROM read_parquet('{p}')").fetchone()
print("rows", n, "distinct_PRONAC", d, "->", "OK no dup" if n==d else "⚠ DUPLICATES")
print("year dist:", c.execute(f"SELECT ano_projeto, COUNT(*) FROM read_parquet('{p}') GROUP BY 1 ORDER BY 1").fetchall())
PY
```

Checks:
1. `rows == distinct PRONAC` (no dup key).
2. **Untouched years unchanged** — compare the year-dist against the Step 0.5
   pre-slice figures; 2019–2024 counts (if not sliced) must be identical.
3. Sliced-year counts rose by the number of inserted rows Step 2 reported.
4. `situacao` distribution is sane (no flood of a single sentinel/null status).

---

## Step 4 — Commit + push (GitHub side of the write)

```bash
git add raw/salic/projetos.parquet raw/salic/refresh_log.parquet
git commit -m "SALIC year-slice refresh 2025–2026 — coverage <old%>→<new%> (+<N> PRONACs)

Targeted discovery slice after the ~5-week API blackout. Universe 59,642;
ingest <old>→<new>. Only 2025–2026 discovered; 2019–2024 untouched (verified
against pre-slice snapshot). MotherDuck already updated by the upsert."
git push
```

`projetos_v2.parquet` (legacy 26,203 GitHub compat) is **not** touched — leave it.

---

## Step 5 — Update the documentation surfaces

- `docs/methodology/salic_api.md` §1 + §1.1 — new canonical count, coverage %,
  and refreshed **year distribution** (replace the 48,189 line + the year list).
  Add a dated refresh bullet in §3.
- `docs/manifest.md` — `atana.salic` row count + year-dist.
- `atana_site/data.yaml` — SALIC card count (PT/EN/ES) + meta line, then
  `python3 atana_site/build_site.py` (+ `--publish` if the /data/ page is live).
- `_atana_intel/db_update_log.md` — one entry: blackout delta, slice decision,
  before/after counts, commit hash.
- `CLAUDE.md` — next session-update line (coverage reframed to <new%>).

Note: published Notes/Análises citing 48,189 / 85% remain correct at their
publication date — no retroactive rewrite; new work uses the refreshed figure.

---

## Rollback

If Step 3 fails or the situacao distribution looks wrong:

```bash
python3 - <<'PY'
import os, duckdb, glob
con = duckdb.connect(f"md:atana?motherduck_token={os.environ['MOTHERDUCK_TOKEN']}")
snap = sorted(glob.glob("raw/salic/projetos_pre_slice_*.parquet"))[-1]
con.execute(f"CREATE OR REPLACE TABLE atana.salic.projetos AS SELECT * FROM read_parquet('{snap}')")
con.execute(f"COPY (SELECT * FROM atana.salic.projetos) TO 'raw/salic/projetos.parquet' (FORMAT PARQUET)")
print("rolled back from", snap)
PY
# then `git checkout -- raw/salic/projetos.parquet` if already staged.
```

---

## Gotchas / guardrails

- **WAF flakiness** — the run may interrupt mid-year; just rerun the same
  command. Idempotent discovery resumes; no dup risk (distinct-PRONAC check).
- **2026 is a partial year** — it will keep growing; don't read 2026 counts as a
  full-year comparison (same caveat as methodology W7).
- **`--refresh-existing` is not year-sliced** — it touches open-cycle PRONACs
  `ano ≥ 2020`. Use plain discovery for a strictly additive slice.
- **Donor graph unaffected** — this slice only inserts into `projetos`. The
  `edges_*` / `corporate_canon` tables are not refreshed here; if a new top-100
  donor appears, `corporate_canon` needs its own manual review pass (out of
  scope for a year slice).
- **projetos vs projetos_v2 divergence** — query `projetos` everywhere; leave
  the legacy `projetos_v2.parquet` on GitHub alone.
- **The write is the approval point** — nothing here runs unattended; the
  reconcile diff (Step 0) is reviewed by João before Step 2.
```
