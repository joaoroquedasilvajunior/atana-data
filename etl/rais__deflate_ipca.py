"""rais__deflate_ipca.py — post-ETL pass: add IPCA-deflated remuneração.

Run this AFTER `rais__bigquery_to_parquet.py` has completed all years. It:

  1. Pulls annual IPCA index from `basedosdados.br_ipea_indices.ipca`
  2. Computes the deflator factor against a base year (default 2024)
  3. For each year's parquet of `vinculos_em_*` and `cnpj_cultural_employer_panel`,
     adds columns:
       - `valor_remuneracao_media_ipca`   (base-year BRL)
       - `valor_remuneracao_dezembro_ipca` (base-year BRL)
       - `salario_mediano_total_ipca`     (panel only)
       - `salario_mediano_cultural_ipca`  (panel only)
  4. Re-syncs to MotherDuck if MOTHERDUCK_TOKEN is set.

The deflation is separated from the main ETL so the base-year choice and
the deflator semantics (annual mean vs December-only) can be revisited
without re-running the BigQuery extraction.

Default: base year = 2024 (most recent complete year at ETL time);
deflator basis = annual mean IPCA accumulated.

USAGE
-----
  python rais__deflate_ipca.py
  python rais__deflate_ipca.py --base 2023      # different base year
  python rais__deflate_ipca.py --year 2023      # just one year

REQUIRED ENV
------------
  GCP_PROJECT_ID
  MOTHERDUCK_TOKEN (optional)
"""

import argparse
import os
import sys
from pathlib import Path
from datetime import datetime

import pandas as pd
import duckdb

REPO_ROOT = Path(__file__).resolve().parent.parent
OUT_BASE = REPO_ROOT / "raw" / "rais"
LOG_PATH = REPO_ROOT / "etl" / "rais__deflate_ipca.log"
DEFLATOR_CACHE = REPO_ROOT / "raw" / "rais" / "_reference" / "ipca_annual_mean.parquet"


def log(msg):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(LOG_PATH, "a") as f:
        f.write(line + "\n")
    print(line)


def pull_ipca_annual(bid: str) -> pd.DataFrame:
    """Pull IPCA monthly variation from BCB SGS API (series 433), compound
    to a cumulative index (base = Jan 2014 = 100), return annual mean.

    BCB SGS is public, no auth needed. The basedosdados br_ipea_indices.ipca
    table that an earlier version used turned out to be unavailable / renamed,
    so we go to the primary source directly.
    """
    if DEFLATOR_CACHE.exists():
        log(f"using cached IPCA from {DEFLATOR_CACHE.name}")
        return pd.read_parquet(DEFLATOR_CACHE)

    import urllib.request
    import json
    url = (
        "https://api.bcb.gov.br/dados/serie/bcdata.sgs.433/dados"
        "?formato=json&dataInicial=01/01/2014&dataFinal=31/12/2024"
    )
    log(f"pulling IPCA monthly from BCB SGS series 433...")
    with urllib.request.urlopen(url, timeout=30) as resp:
        raw = json.loads(resp.read().decode("utf-8"))

    monthly = pd.DataFrame(raw)
    monthly["data"] = pd.to_datetime(monthly["data"], format="%d/%m/%Y")
    monthly["valor"] = monthly["valor"].astype(float)   # % variation that month
    monthly["ano"] = monthly["data"].dt.year
    monthly = monthly.sort_values("data").reset_index(drop=True)

    # Compound monthly variations into cumulative index, base = Jan 2014 = 100
    monthly["fator"] = 1 + monthly["valor"] / 100.0
    monthly["indice"] = 100.0 * monthly["fator"].cumprod()

    df = (
        monthly.groupby("ano")["indice"]
        .mean()
        .reset_index()
        .rename(columns={"indice": "ipca_annual_mean"})
    )
    DEFLATOR_CACHE.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(DEFLATOR_CACHE, index=False)
    log(f"  cached {len(df)} years to {DEFLATOR_CACHE.name}")
    return df


def compute_deflator(ipca: pd.DataFrame, base_year: int) -> dict:
    """Return {year: deflator_to_base} dict.

    deflator(year) = ipca(base_year) / ipca(year)
    So:  value_in_base_year_BRL = value_in_year_BRL * deflator(year)
    """
    ipca = ipca.set_index("ano")
    if base_year not in ipca.index:
        sys.exit(f"ERROR: base year {base_year} not in IPCA series. Available: {sorted(ipca.index)}")
    base_idx = ipca.loc[base_year, "ipca_annual_mean"]
    return {y: float(base_idx / row["ipca_annual_mean"]) for y, row in ipca.iterrows()}


def deflate_parquet(path: Path, year: int, deflator: float, cols_to_deflate: list):
    df = pd.read_parquet(path)
    for col in cols_to_deflate:
        if col in df.columns:
            df[f"{col}_ipca"] = df[col] * deflator
    df.to_parquet(path, index=False, compression="snappy")
    log(f"  deflated {path.relative_to(REPO_ROOT)} ({len(df):,} rows, factor={deflator:.4f})")


def sync_motherduck_year(table: str, year: int, df: pd.DataFrame):
    """Sync per-year data to MotherDuck with schema-drift auto-recovery.

    The deflator adds _ipca columns that don't exist in the cloud table on
    first run; detect the mismatch and recreate the cloud table.
    """
    token = os.environ.get("MOTHERDUCK_TOKEN")
    if not token:
        return
    con = duckdb.connect(f"md:atana?motherduck_token={token}")
    con.register("df_year", df)

    existing_cols = set(
        con.execute(f"DESCRIBE atana.rais.{table}").df()["column_name"].tolist()
    )
    new_cols = set(df.columns)
    if existing_cols != new_cols:
        log(f"  schema drift on atana.rais.{table}: "
            f"existing={len(existing_cols)} cols, new={len(new_cols)} cols — dropping and recreating")
        con.execute(f"DROP TABLE atana.rais.{table}")
        con.execute(f"CREATE TABLE atana.rais.{table} AS SELECT * FROM df_year WHERE 1=0")

    con.execute(f"DELETE FROM atana.rais.{table} WHERE ano = {year}")
    con.execute(f"INSERT INTO atana.rais.{table} SELECT * FROM df_year")
    con.unregister("df_year")
    con.close()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", type=int, default=2024, help="base year for deflator (default 2024)")
    ap.add_argument("--year", type=int, help="just deflate one year")
    args = ap.parse_args()

    bid = os.environ.get("GCP_PROJECT_ID")
    if not bid:
        sys.exit("ERROR: GCP_PROJECT_ID not set.")

    log("=" * 70)
    log(f"IPCA deflation — base year {args.base}")
    log("=" * 70)

    ipca = pull_ipca_annual(bid)
    deflator_map = compute_deflator(ipca, args.base)
    log(f"deflator factors (base={args.base}):")
    for y, f in sorted(deflator_map.items()):
        log(f"  {y}: {f:.4f}")

    years = [args.year] if args.year else sorted(deflator_map.keys())

    vinculos_cols = ["valor_remuneracao_media", "valor_remuneracao_dezembro",
                     "valor_salario_contratual"]
    panel_cols = ["salario_mediano", "salario_dezembro_mediano"]

    for y in years:
        if y not in deflator_map:
            log(f"  year {y}: no deflator available, skipping")
            continue
        d = deflator_map[y]
        log(f"\nyear {y} (deflator {d:.4f}):")

        for table, cols in [
            ("vinculos_culturais", vinculos_cols),
            ("panel_cnae_municipio_ano", panel_cols),
        ]:
            path = OUT_BASE / table / f"year={y}" / "part-0.parquet"
            if not path.exists():
                log(f"  {table}: MISSING — run rais__bigquery_to_parquet.py first")
                continue
            deflate_parquet(path, y, d, cols)
            df = pd.read_parquet(path)
            sync_motherduck_year(table, y, df)

    log("\nIPCA deflation complete.")


if __name__ == "__main__":
    main()
