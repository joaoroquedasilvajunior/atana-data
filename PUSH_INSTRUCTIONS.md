# Pushing this repo to GitHub

The local repository in this folder is fully initialized with one commit. Follow these steps to publish it to GitHub.

## Step 1 — Create the empty repo on GitHub

Go to **https://github.com/new** and create a new repository with these exact settings:

| Field | Value |
|---|---|
| **Repository name** | `atana-data` |
| **Owner** | `joaoroquer` |
| **Visibility** | Public |
| **Initialize this repository with** | leave everything UNCHECKED (no README, no .gitignore, no license) — we already have those locally |

Click **Create repository**.

## Step 2 — Add the remote and push

Open Terminal and run:

```bash
cd "/Users/joaoroque/Documents/Cultural production - book/Dados da Economia Cultural no Brasil/atana-data"

# Add the GitHub remote
git remote add origin https://github.com/joaoroquedasilvajunior/atana-data.git

# Push the main branch
git push -u origin main
```

If prompted for authentication, you'll need either:
- A **Personal Access Token** (PAT) with `repo` scope — generate at https://github.com/settings/tokens
- Or **GitHub CLI** (`gh auth login` first), then push as above

## Step 3 — Verify

After pushing, visit https://github.com/joaoroquedasilvajunior/atana-data — you should see:

- 1 commit on `main`
- README rendered on the landing page
- License badge auto-detected as CC BY 4.0
- 5 folders: `curated/`, `docs/`, `etl/`, `raw/`, plus root files

## Step 4 — Add repository description and topics on GitHub

In the GitHub UI, click the gear icon next to "About" on the right sidebar and set:

**Description:**
> Open data on creative economies in Latin America — UNCTAD, IBGE, MinC SALIC, LexML. Used by Atana Research.

**Topics:**
```
creative-economy  cultural-policy  open-data  latin-america  brazil
unctad  ibge  duckdb  motherduck  cultural-statistics
```

**Website:**
```
https://atana.studio
```

## Step 5 (optional) — Pin the repo on your GitHub profile

Once it's pinned, visitors to your profile will see it immediately. From your profile page → Customize your pins → select `atana-data`.

---

## After pushing

The repository will be ready for Phase 2 (next session), in which we'll:

1. Export the 4 UNCTAD tables from MotherDuck → Parquet → commit to `raw/unctad/`
2. Run `etl/ibge_pnadc__xlsx_to_parquet.py` (to be written) for the 15 PNADC tables
3. Run `etl/ibge_comex__xlsx_to_parquet.py` for the 4 comex tables
4. Run `etl/salic__jsonl_to_parquet.py` for the 26 k Rouanet projects
5. Run `etl/lexml__jsonl_to_parquet.py` for the 269 legislative acts
6. Sync everything to `md:atana` (matching schemas)
7. Update `docs/manifest.md` row counts

After Phase 2, each analysis script (`gen_latam_fig3_fig9.py`, `gen_t10_charts.py`, etc.) can be rewritten to use atana-data as its single source of truth — no more `openpyxl.load_workbook(...)`.

## Setting up your MotherDuck token as an environment variable

The ETL scripts in Phase 2 read the token from `$MOTHERDUCK_TOKEN`. Set it permanently:

```bash
# Add to your ~/.zshrc or ~/.bash_profile
export MOTHERDUCK_TOKEN="eyJhbGciOi..."   # the full token

# Reload
source ~/.zshrc
```

Then any script in `etl/` connects automatically:
```python
import duckdb, os
con = duckdb.connect(f"md:atana?motherduck_token={os.environ['MOTHERDUCK_TOKEN']}")
```

**Never commit the token.** It's already in `.gitignore`.
