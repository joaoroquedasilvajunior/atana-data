"""rais__bigquery_to_parquet.py — Sprint 1 ETL (3-table model).

basedosdados de-identifies RAIS: no CNPJ in either microdata table, no PIS in
vínculos. Sprint 1 therefore builds three labor-market characterization tables
(not the CNPJ-keyed panel originally planned in roadmap §3.4). The CNPJ join
needed for Phase 3 H1 (causal claim about Rouanet captação → employment) is
deferred to Phase 2b via MTE FTP — scoped in notes/rais_phase2b_mte_ftp_scoping.md.

For each year (2023 → 2014):
  1. Discover schema (fail-fast on critical column drift).
  2. Pull `microdados_estabelecimentos` filtered by direct cultural CNAE.
  3. Pull `microdados_vinculos` filtered by (CNAE direct) OR (CBO family LIKE).
  4. Tag each vínculo with `in_cut_a` (CNAE) / `in_cut_b` (CBO) / `cbo_familia`.
  5. Derive `vinculo_iniciado_no_ano` from mes_admissao.
  6. Attach `siic_dominio` via CNAE lookup; retain `sigla_uf = 'IGNORADO'`.
  7. Build the three tables:
       a. estabelecimentos_culturais   (one row per establishment)
       b. vinculos_culturais           (one row per vínculo, Cut A ∪ Cut B)
       c. panel_cnae_municipio_ano     (derived aggregate)
  8. Write per-year Parquet to `raw/rais/<table>/year=YYYY/part-0.parquet`.
  9. Sync to MotherDuck `md:atana.rais.<table>`.
  10. Per-year QA (row counts, null rates on derived join keys).

The pass is idempotent: years already written are skipped unless `--refresh`.

USAGE
-----
  python rais__bigquery_to_parquet.py --smoke                  # no BigQuery
  python rais__bigquery_to_parquet.py --year 2023 --limit 10000
  python rais__bigquery_to_parquet.py --year 2023
  python rais__bigquery_to_parquet.py                          # all 10 years
  python rais__bigquery_to_parquet.py --year 2022 --refresh

REQUIRED ENV
------------
  GCP_PROJECT_ID
  MOTHERDUCK_TOKEN (optional — Parquets always written locally)

NOTES
-----
  PIS hashing is **not** part of this ETL — basedosdados strips PIS from the
  public vínculos table. The ATANA_PIS_SALT environment variable is therefore
  not required for the basedosdados pipeline. It will become required when
  Phase 2b (MTE FTP) adds the longitudinal worker panel.
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

import pandas as pd
import duckdb

REPO_ROOT = Path(__file__).resolve().parent.parent
REF_DIR = REPO_ROOT / "raw" / "rais" / "_reference"
OUT_BASE = REPO_ROOT / "raw" / "rais"
LOG_PATH = REPO_ROOT / "etl" / "rais__bigquery_to_parquet.log"

YEARS_DEFAULT = list(range(2023, 2013, -1))

CANONICAL_UFS = {
    "AC","AL","AP","AM","BA","CE","DF","ES","GO","MA","MT","MS","MG","PA",
    "PB","PR","PE","PI","RJ","RN","RS","RO","RR","SC","SP","SE","TO",
}

# Columns we pull from basedosdados. Curated subset of the 67 available — we
# drop monthly remuneration columns (12) and obsolete classifications
# (cnae_1, cbo_1994, grau_instrucao_1985_2005) to keep per-vínculo width
# manageable. Storage budget ~10 GB total across all years.
VINCULOS_COLUMNS = [
    "ano", "sigla_uf", "id_municipio", "id_municipio_trabalho",
    "cnae_2_subclasse", "cbo_2002",
    "idade", "sexo", "raca_cor", "grau_instrucao_apos_2005", "nacionalidade",
    "valor_remuneracao_media", "valor_remuneracao_dezembro",
    "valor_salario_contratual", "tipo_salario",
    "quantidade_horas_contratadas",
    "mes_admissao", "tipo_admissao",
    "mes_desligamento", "motivo_desligamento", "causa_desligamento_1",
    "tempo_emprego",
    "tipo_vinculo",
    "indicador_trabalho_intermitente", "indicador_trabalho_parcial",
    "indicador_simples", "indicador_portador_deficiencia",
    "tamanho_estabelecimento", "tipo_estabelecimento", "natureza_juridica",
    "vinculo_ativo_3112",
]

ESTABELECIMENTOS_COLUMNS = [
    "ano", "sigla_uf", "id_municipio",
    "cnae_2_subclasse",
    "tamanho_estabelecimento", "tipo_estabelecimento",
    "natureza_juridica", "natureza_estabelecimento",
    "indicador_simples", "indicador_atividade_ano",
    "indicador_pat", "indicador_rais_negativa",
    "quantidade_vinculos_ativos", "quantidade_vinculos_clt",
    "quantidade_vinculos_estatutarios",
]


# ============================================================================
# Logging
# ============================================================================

def log(msg, also_print=True):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(LOG_PATH, "a") as f:
        f.write(line + "\n")
    if also_print:
        print(line)


# ============================================================================
# Reference table loading
# ============================================================================

def load_references():
    cnae_path = REF_DIR / "cnae_cultural.parquet"
    cbo_path = REF_DIR / "cbo_cultural.parquet"
    if not cnae_path.exists() or not cbo_path.exists():
        sys.exit(
            f"ERROR: reference parquets missing.\n"
            f"  expected: {cnae_path}\n"
            f"  expected: {cbo_path}\n"
            f"Run:  python rais__build_reference_tables.py"
        )
    try:
        cnae = pd.read_parquet(cnae_path)
        cbo = pd.read_parquet(cbo_path)
    except Exception as e:
        sys.exit(
            f"ERROR: reference parquets unreadable by local pyarrow.\n"
            f"  underlying error: {e}\n"
            f"  Fix: regenerate the parquets on this machine:\n"
            f"       python {Path(__file__).parent / 'rais__build_reference_tables.py'}"
        )
    cnae_direct = sorted(cnae[cnae.relacao_cultura == "direct"].cnae_2_subclasse.tolist())
    cbo_families = sorted(cbo.cbo_familia.tolist())
    return {
        "cnae_direct": cnae_direct,
        "cbo_families": cbo_families,
        "cnae_df": cnae,
        "cbo_df": cbo,
    }


# ============================================================================
# Schema discovery
# ============================================================================

def discover_schema(table: str, bid: str, required_cols: list) -> set:
    """Pull a 0-row query to learn actual column names. Fail-fast if any required
    column is missing."""
    import basedosdados as bd
    sql = f"SELECT * FROM `basedosdados.{table}` LIMIT 0"
    try:
        df = bd.read_sql(sql, billing_project_id=bid)
        actual_cols = set(df.columns)
    except Exception as e:
        sys.exit(f"ERROR: schema discovery failed for {table}: {e}")

    missing = [c for c in required_cols if c not in actual_cols]
    if missing:
        log(f"  full column list for {table} ({len(actual_cols)}):")
        for c in sorted(actual_cols):
            log(f"    · {c}")
        sys.exit(
            f"ERROR: required columns missing in {table}: {missing}\n"
            f"  Update VINCULOS_COLUMNS / ESTABELECIMENTOS_COLUMNS in this script,\n"
            f"  then re-run."
        )
    return actual_cols


# ============================================================================
# Output path helpers
# ============================================================================

def year_dir(table: str, year: int) -> Path:
    p = OUT_BASE / table / f"year={year}"
    p.mkdir(parents=True, exist_ok=True)
    return p


def year_parquet(table: str, year: int) -> Path:
    return year_dir(table, year) / "part-0.parquet"


def year_already_done(year: int, refresh: bool) -> bool:
    if refresh:
        return False
    paths = [
        year_parquet("estabelecimentos_culturais", year),
        year_parquet("vinculos_culturais", year),
        year_parquet("panel_cnae_municipio_ano", year),
    ]
    return all(p.exists() for p in paths)


# ============================================================================
# Extract — establishments
# ============================================================================

def pull_estabelecimentos(year: int, cnae_direct: list, bid: str,
                           limit: int = None) -> pd.DataFrame:
    """Pull cultural-CNAE establishments for one year.

    Note: basedosdados stores cnae_2_subclasse as 7-digit (CNAE 5-digit class +
    2-digit subclasse suffix). Our reference parquet stores 5-digit class roots
    per SIIC methodology. Match via SUBSTR(_, 1, 5).
    """
    import basedosdados as bd
    cnae_in = ",".join(f"'{c}'" for c in cnae_direct)
    cols = ", ".join(ESTABELECIMENTOS_COLUMNS)
    limit_clause = f"LIMIT {limit}" if limit else ""
    sql = f"""
    SELECT {cols}
    FROM `basedosdados.br_me_rais.microdados_estabelecimentos`
    WHERE ano = {year}
      AND SUBSTR(cnae_2_subclasse, 1, 5) IN ({cnae_in})
    {limit_clause}
    """
    log(f"  pulling estabelecimentos for {year} (direct CNAEs)...")
    df = bd.read_sql(sql, billing_project_id=bid)
    log(f"    {len(df):,} establishment rows")
    return df


# ============================================================================
# Extract — vínculos (Cut A ∪ Cut B)
# ============================================================================

def pull_vinculos(year: int, cnae_direct: list, cbo_families: list,
                  bid: str, limit: int = None) -> pd.DataFrame:
    """Pull cultural vínculos for one year (CNAE direct OR CBO family match).

    basedosdados stores cnae_2_subclasse as 7-digit; we match first 5 chars
    against our 5-digit reference. CBO is 6-digit, matched via LIKE 'NNNN%'
    against the 4-digit CBO-Domiciliar family roots.
    """
    import basedosdados as bd
    cnae_in = ",".join(f"'{c}'" for c in cnae_direct)
    cbo_likes = " OR ".join(f"cbo_2002 LIKE '{f}%'" for f in cbo_families)
    cols = ", ".join(VINCULOS_COLUMNS)
    limit_clause = f"LIMIT {limit}" if limit else ""
    sql = f"""
    SELECT {cols}
    FROM `basedosdados.br_me_rais.microdados_vinculos`
    WHERE ano = {year}
      AND (SUBSTR(cnae_2_subclasse, 1, 5) IN ({cnae_in}) OR ({cbo_likes}))
    {limit_clause}
    """
    log(f"  pulling vínculos for {year} (Cut A ∪ Cut B)...")
    t0 = time.time()
    df = bd.read_sql(sql, billing_project_id=bid)
    log(f"    {len(df):,} vínculo rows in {time.time()-t0:.1f}s")
    return df


# ============================================================================
# Transform
# ============================================================================

def transform_vinculos(df: pd.DataFrame, refs: dict) -> pd.DataFrame:
    """Tag cuts, derive cbo_familia / cnae_2_classe / cnae_2_divisao /
    siic_dominio / vinculo_iniciado_no_ano.

    basedosdados' cnae_2_subclasse is 7-digit (CNAE class + subclasse suffix).
    We preserve it AND derive cnae_2_classe (5-digit) for joining against the
    SIIC-style reference parquet.
    """
    df = df.copy()

    df["cnae_2_subclasse"] = df["cnae_2_subclasse"].astype(str).str.zfill(7)
    df["cnae_2_classe"] = df["cnae_2_subclasse"].str[:5]
    df["cnae_2_divisao"] = df["cnae_2_subclasse"].str[:2]
    df["cbo_2002"] = df["cbo_2002"].astype(str).str.zfill(6)
    df["cbo_familia"] = df["cbo_2002"].str[:4]

    cnae_direct_set = set(refs["cnae_direct"])
    cbo_families_set = set(refs["cbo_families"])
    df["in_cut_a"] = df["cnae_2_classe"].isin(cnae_direct_set)
    df["in_cut_b"] = df["cbo_familia"].isin(cbo_families_set)

    # mes_admissao = 0 means "already employed pre-reference-year" (methodology §4.6)
    df["mes_admissao"] = pd.to_numeric(df["mes_admissao"], errors="coerce").fillna(-1).astype(int)
    df["vinculo_iniciado_no_ano"] = (df["mes_admissao"] > 0) & (df["mes_admissao"] <= 12)

    cnae_lookup = refs["cnae_df"].set_index("cnae_2_subclasse")["siic_dominio"].to_dict()
    df["siic_dominio"] = df["cnae_2_classe"].map(cnae_lookup)

    for col in ["valor_remuneracao_media", "valor_remuneracao_dezembro",
                "valor_salario_contratual",
                "quantidade_horas_contratadas", "idade", "tempo_emprego"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    return df


def transform_estabelecimentos(df: pd.DataFrame, refs: dict) -> pd.DataFrame:
    df = df.copy()
    df["cnae_2_subclasse"] = df["cnae_2_subclasse"].astype(str).str.zfill(7)
    df["cnae_2_classe"] = df["cnae_2_subclasse"].str[:5]
    df["cnae_2_divisao"] = df["cnae_2_subclasse"].str[:2]
    cnae_lookup = refs["cnae_df"].set_index("cnae_2_subclasse")["siic_dominio"].to_dict()
    df["siic_dominio"] = df["cnae_2_classe"].map(cnae_lookup)
    for col in ["quantidade_vinculos_ativos", "quantidade_vinculos_clt",
                "quantidade_vinculos_estatutarios"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)
    return df


# ============================================================================
# Derive — panel at (CNAE × município × year) grain
# ============================================================================

def _is_female(s):
    return s.dropna().astype(str).isin(["F", "Feminino", "feminino", "2"]).mean() if len(s.dropna()) else None


def _is_preto_pardo(s):
    return s.dropna().astype(str).isin(["preta", "parda", "Preta", "Parda", "2", "4"]).mean() if len(s.dropna()) else None


def _is_clt(s):
    # tipo_vinculo: '10','15','20','25','30','31','35','40','50','55','60','65','70','75','80','90','95','97'
    # CLT-equivalent codes per MTE: 10, 15, 20, 25, 70 (most modal CLT). Conservative use:
    return s.dropna().astype(str).isin(["10", "15", "20", "25"]).mean() if len(s.dropna()) else None


def build_panel_cnae_municipio_ano(vinc: pd.DataFrame, estab: pd.DataFrame, year: int) -> pd.DataFrame:
    """Aggregate Cut A vínculos at (CNAE 5-digit class × município × year) grain.

    Cut A is used as the primary grain (cultural establishments) — same as the
    base for the SALIC-comparison aggregations in Phase 3 H0.

    Aggregation is at the 5-digit CNAE class (cnae_2_classe), not the 7-digit
    subclasse, because the SIIC methodology defines cultural activities at the
    class level. This matches the grain of cross-source joins.
    """
    cut_a = vinc[vinc["in_cut_a"]].copy()
    if len(cut_a) == 0:
        return pd.DataFrame()

    grp = cut_a.groupby(["sigla_uf", "id_municipio", "cnae_2_classe"], dropna=False)

    panel = grp.agg(
        n_vinculos_total=("ano", "size"),
        n_vinculos_cut_b=("in_cut_b", "sum"),
        salario_mediano=("valor_remuneracao_media", "median"),
        salario_dezembro_mediano=("valor_remuneracao_dezembro", "median"),
        horas_medianas=("quantidade_horas_contratadas", "median"),
        idade_mediana=("idade", "median"),
        pct_mulheres=("sexo", _is_female),
        pct_pretos_pardos=("raca_cor", _is_preto_pardo),
        pct_clt=("tipo_vinculo", _is_clt),
        pct_intermitente=("indicador_trabalho_intermitente",
                          lambda s: pd.to_numeric(s, errors="coerce").mean()),
        pct_parcial=("indicador_trabalho_parcial",
                     lambda s: pd.to_numeric(s, errors="coerce").mean()),
    ).reset_index()

    panel["ano"] = year
    panel["cnae_2_divisao"] = panel["cnae_2_classe"].str[:2]
    cnae_lookup = vinc.drop_duplicates("cnae_2_classe").set_index("cnae_2_classe")["siic_dominio"].to_dict()
    panel["siic_dominio"] = panel["cnae_2_classe"].map(cnae_lookup)

    # Join in establishment count by (UF, município, classe) from estab
    if len(estab) > 0:
        estab_counts = (
            estab.groupby(["sigla_uf", "id_municipio", "cnae_2_classe"], dropna=False)
            .size()
            .reset_index(name="n_estabelecimentos")
        )
        panel = panel.merge(estab_counts,
                            on=["sigla_uf", "id_municipio", "cnae_2_classe"], how="left")
        panel["n_estabelecimentos"] = panel["n_estabelecimentos"].fillna(0).astype(int)
    else:
        panel["n_estabelecimentos"] = 0

    col_order = ["ano", "sigla_uf", "id_municipio",
                 "cnae_2_classe", "cnae_2_divisao", "siic_dominio",
                 "n_estabelecimentos", "n_vinculos_total", "n_vinculos_cut_b",
                 "salario_mediano", "salario_dezembro_mediano",
                 "horas_medianas", "idade_mediana",
                 "pct_mulheres", "pct_pretos_pardos",
                 "pct_clt", "pct_intermitente", "pct_parcial"]
    panel = panel[[c for c in col_order if c in panel.columns]]
    return panel


# ============================================================================
# Build the 3 tables for one year
# ============================================================================

def build_tables_for_year(vinculos_raw: pd.DataFrame,
                          estabelecimentos_raw: pd.DataFrame,
                          refs: dict, year: int) -> dict:
    log(f"  transforming {len(vinculos_raw):,} vínculos + {len(estabelecimentos_raw):,} estabelecimentos...")
    vinc = transform_vinculos(vinculos_raw, refs)
    estab = transform_estabelecimentos(estabelecimentos_raw, refs)
    panel = build_panel_cnae_municipio_ano(vinc, estab, year)

    out = {
        "estabelecimentos_culturais": estab,
        "vinculos_culturais": vinc,
        "panel_cnae_municipio_ano": panel,
    }
    for name, df in out.items():
        log(f"    {name}: {len(df):,} rows × {len(df.columns)} cols")
    return out


# ============================================================================
# Write + sync
# ============================================================================

def write_year(tables: dict, year: int):
    for name, df in tables.items():
        path = year_parquet(name, year)
        df.to_parquet(path, index=False, compression="snappy")
        log(f"  wrote {path.relative_to(REPO_ROOT)} ({path.stat().st_size/1e6:.1f} MB)")


def sync_motherduck(tables: dict, year: int):
    """Sync per-year data to MotherDuck. Detects schema drift and recreates
    the cloud table if the column set has changed during active development."""
    token = os.environ.get("MOTHERDUCK_TOKEN")
    if not token:
        log("  MOTHERDUCK_TOKEN not set — skipping md:atana sync")
        return
    con = duckdb.connect(f"md:atana?motherduck_token={token}")
    con.execute("CREATE SCHEMA IF NOT EXISTS atana.rais")
    for name, df in tables.items():
        if len(df) == 0:
            continue
        con.register("df_year", df)

        table_exists = con.execute(f"""
            SELECT COUNT(*) FROM information_schema.tables
            WHERE table_schema = 'rais' AND table_name = '{name}'
        """).fetchone()[0] > 0

        if table_exists:
            existing_cols = set(
                con.execute(f"DESCRIBE atana.rais.{name}").df()["column_name"].tolist()
            )
            new_cols = set(df.columns)
            if existing_cols != new_cols:
                log(f"  schema drift on atana.rais.{name}: "
                    f"existing={len(existing_cols)} cols, new={len(new_cols)} cols — dropping and recreating")
                con.execute(f"DROP TABLE atana.rais.{name}")
                table_exists = False

        if not table_exists:
            con.execute(f"CREATE TABLE atana.rais.{name} AS SELECT * FROM df_year WHERE 1=0")

        con.execute(f"DELETE FROM atana.rais.{name} WHERE ano = {year}")
        con.execute(f"INSERT INTO atana.rais.{name} SELECT * FROM df_year")
        n = con.execute(f"SELECT COUNT(*) FROM atana.rais.{name} WHERE ano = {year}").fetchone()[0]
        log(f"  synced atana.rais.{name} year {year} ({n:,} rows)")
        con.unregister("df_year")
    con.close()


# ============================================================================
# Per-year QA
# ============================================================================

def quick_qa(tables: dict, year: int):
    log(f"  quick QA for {year}:")
    estab = tables["estabelecimentos_culturais"]
    vinc = tables["vinculos_culturais"]
    panel = tables["panel_cnae_municipio_ano"]
    log(f"    estabelecimentos_culturais : {len(estab):,} rows")
    log(f"    vinculos_culturais         : {len(vinc):,} rows")
    log(f"      · Cut A (CNAE direct)    : {vinc['in_cut_a'].sum():,}")
    log(f"      · Cut B (CBO match)      : {vinc['in_cut_b'].sum():,}")
    log(f"      · Cut A ∩ Cut B          : {(vinc['in_cut_a'] & vinc['in_cut_b']).sum():,}")
    log(f"    panel_cnae_municipio_ano   : {len(panel):,} rows")
    log(f"    UFs present (vinculos)     : {sorted(vinc['sigla_uf'].dropna().unique())}")
    null_cnae = vinc["cnae_2_subclasse"].isna().mean() * 100
    null_cbo = vinc["cbo_2002"].isna().mean() * 100
    log(f"    null CNAE rate             : {null_cnae:.2f}%")
    log(f"    null CBO rate              : {null_cbo:.2f}%")
    if null_cnae > 1 or null_cbo > 1:
        log("    ⚠ WARNING: > 1% null on join keys — investigate")


# ============================================================================
# Smoke test
# ============================================================================

def smoke_test():
    log("=" * 70)
    log("SMOKE TEST — synthetic data, no BigQuery")
    log("=" * 70)
    refs = load_references()

    import random
    random.seed(42)
    n = 5000
    # Mimic basedosdados format: 7-digit cnae_2_subclasse (5-digit class + 2-digit suffix)
    cnae_options = [c + "00" for c in refs["cnae_direct"]] + ["0000000"]
    cbo_options = [f + "00" for f in refs["cbo_families"]] + ["999999"]
    uf_options = list(CANONICAL_UFS) + ["IGNORADO"]

    fake_vinc = pd.DataFrame({
        "ano": [2023] * n,
        "sigla_uf": [random.choice(uf_options) for _ in range(n)],
        "id_municipio": [f"{random.randint(1000000, 9999999)}" for _ in range(n)],
        "id_municipio_trabalho": [f"{random.randint(1000000, 9999999)}" for _ in range(n)],
        "cnae_2_subclasse": [random.choice(cnae_options) for _ in range(n)],
        "cbo_2002": [random.choice(cbo_options) for _ in range(n)],
        "idade": [random.randint(18, 65) for _ in range(n)],
        "sexo": [random.choice(["F", "M"]) for _ in range(n)],
        "raca_cor": [random.choice(["branca", "preta", "parda", "amarela", "indigena", "nao_informada"]) for _ in range(n)],
        "grau_instrucao_apos_2005": [str(random.randint(1, 11)) for _ in range(n)],
        "nacionalidade": ["10"] * n,
        "valor_remuneracao_media": [round(random.uniform(1500, 12000), 2) for _ in range(n)],
        "valor_remuneracao_dezembro": [round(random.uniform(1500, 15000), 2) for _ in range(n)],
        "valor_salario_contratual": [round(random.uniform(1500, 12000), 2) for _ in range(n)],
        "tipo_salario": [random.choice(["1", "2", "3"]) for _ in range(n)],
        "quantidade_horas_contratadas": [random.choice([20, 30, 40, 44]) for _ in range(n)],
        "mes_admissao": [random.choice([0]*5 + list(range(1, 13))) for _ in range(n)],
        "tipo_admissao": [random.choice(["1", "2", "3"]) for _ in range(n)],
        "mes_desligamento": [random.choice([0] * 10 + list(range(1, 13))) for _ in range(n)],
        "motivo_desligamento": ["00"] * n,
        "causa_desligamento_1": ["00"] * n,
        "tempo_emprego": [round(random.uniform(0.1, 15.0), 2) for _ in range(n)],
        "tipo_vinculo": [random.choice(["10", "20", "30", "40"]) for _ in range(n)],
        "indicador_trabalho_intermitente": [random.choice([0, 1]) for _ in range(n)],
        "indicador_trabalho_parcial": [random.choice([0, 1]) for _ in range(n)],
        "indicador_simples": [random.choice([0, 1]) for _ in range(n)],
        "indicador_portador_deficiencia": [0] * n,
        "tamanho_estabelecimento": [random.choice(["1", "2", "3", "4"]) for _ in range(n)],
        "tipo_estabelecimento": ["1"] * n,
        "natureza_juridica": [random.choice(["2062", "2305", "3999"]) for _ in range(n)],
        "vinculo_ativo_3112": [random.choice([0, 1]) for _ in range(n)],
    })

    n_estab = 500
    fake_estab = pd.DataFrame({
        "ano": [2023] * n_estab,
        "sigla_uf": [random.choice(uf_options) for _ in range(n_estab)],
        "id_municipio": [f"{random.randint(1000000, 9999999)}" for _ in range(n_estab)],
        "cnae_2_subclasse": [random.choice(refs["cnae_direct"]) + "00" for _ in range(n_estab)],
        "tamanho_estabelecimento": [random.choice(["1", "2", "3", "4"]) for _ in range(n_estab)],
        "tipo_estabelecimento": ["1"] * n_estab,
        "natureza_juridica": [random.choice(["2062", "2305", "3999"]) for _ in range(n_estab)],
        "natureza_estabelecimento": ["1"] * n_estab,
        "indicador_simples": [random.choice([0, 1]) for _ in range(n_estab)],
        "indicador_atividade_ano": [1] * n_estab,
        "indicador_pat": [0] * n_estab,
        "indicador_rais_negativa": [0] * n_estab,
        "quantidade_vinculos_ativos": [random.randint(0, 50) for _ in range(n_estab)],
        "quantidade_vinculos_clt": [random.randint(0, 30) for _ in range(n_estab)],
        "quantidade_vinculos_estatutarios": [random.randint(0, 5) for _ in range(n_estab)],
    })

    tables = build_tables_for_year(fake_vinc, fake_estab, refs, year=2023)
    # Note: smoke test does NOT call write_year() — keeps production parquets clean.
    quick_qa(tables, year=2023)

    log("\n  schema sanity:")
    log(f"    vinculos_culturais columns: {list(tables['vinculos_culturais'].columns)}")
    log(f"    estabelecimentos_culturais columns: {list(tables['estabelecimentos_culturais'].columns)}")
    if len(tables['panel_cnae_municipio_ano']) > 0:
        log(f"    panel columns: {list(tables['panel_cnae_municipio_ano'].columns)}")

    # Confirm no CNPJ/PIS leakage
    forbidden = ["cnpj", "pis", "pis_pasep_hash", "cnpj_estabelecimento", "cnpj_basico"]
    for name, df in tables.items():
        leak = [c for c in forbidden if c in df.columns]
        if leak:
            log(f"    ⚠ {name} leaks forbidden columns: {leak}")
        else:
            log(f"    {name}: no CNPJ/PIS leak ✓")

    log("\n  ✅ Smoke test passed")


# ============================================================================
# Main
# ============================================================================

def process_year(year: int, refs: dict, bid: str, refresh: bool, limit: int):
    if year_already_done(year, refresh) and not limit:
        log(f"year {year}: all 3 parquets exist — skipping (use --refresh to force)")
        return
    log(f"=" * 70)
    log(f"YEAR {year} — starting ETL")
    log(f"=" * 70)

    discover_schema("br_me_rais.microdados_vinculos", bid, VINCULOS_COLUMNS)
    discover_schema("br_me_rais.microdados_estabelecimentos", bid, ESTABELECIMENTOS_COLUMNS)

    estab_raw = pull_estabelecimentos(year, refs["cnae_direct"], bid, limit=limit)
    vinc_raw = pull_vinculos(year, refs["cnae_direct"], refs["cbo_families"], bid, limit=limit)

    tables = build_tables_for_year(vinc_raw, estab_raw, refs, year)
    write_year(tables, year)
    sync_motherduck(tables, year)
    quick_qa(tables, year)
    log(f"YEAR {year} — done\n")


def main():
    ap = argparse.ArgumentParser(description="RAIS Sprint 1 ETL (3-table model)")
    ap.add_argument("--year", type=int, help="single year to process (else all)")
    ap.add_argument("--refresh", action="store_true", help="re-run even if parquets exist")
    ap.add_argument("--smoke", action="store_true", help="run smoke test (no BigQuery)")
    ap.add_argument("--limit", type=int, default=None, help="LIMIT for sanity testing")
    args = ap.parse_args()

    log("=" * 70)
    log("RAIS Sprint 1 ETL — start (3-table basedosdados model)")
    log("=" * 70)

    if args.smoke:
        smoke_test()
        return

    bid = os.environ.get("GCP_PROJECT_ID")
    if not bid:
        sys.exit("ERROR: GCP_PROJECT_ID not set. Run:  export GCP_PROJECT_ID=atana-research")

    refs = load_references()
    log(f"reference tables: {len(refs['cnae_direct'])} CNAE direct, "
        f"{len(refs['cbo_families'])} CBO families")

    years = [args.year] if args.year else YEARS_DEFAULT
    log(f"processing years: {years}")

    for y in years:
        try:
            process_year(y, refs, bid, args.refresh, args.limit)
        except KeyboardInterrupt:
            log("interrupted by user")
            sys.exit(130)
        except Exception as e:
            log(f"ERROR processing {y}: {e}")
            raise

    log("=" * 70)
    log("RAIS Sprint 1 ETL — all years complete")
    log("=" * 70)


if __name__ == "__main__":
    main()
