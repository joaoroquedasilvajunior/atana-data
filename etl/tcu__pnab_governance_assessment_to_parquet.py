"""TCU PNAB audit — governance maturity assessment → Parquet.

Phase 5c. First of two `atana.tcu` tables — the **first governance/audit lens**
in the Atana corpus. The TCU (*Tribunal de Contas da União*) audited Brazil's
*Política Nacional Aldir Blanc de Fomento à Cultura* (PNAB) under the
*Referencial de Controle de Políticas Públicas* (Acórdão 1709/2025 - Plenário,
sessão 30/07/2025, relator Augusto Nardes).

The corpus already holds the dispenser-side microdata of Brazilian public
cultural funding (SALIC/Rouanet, Análises 5/7/8). This schema is the
**accountability counterpart** — what the audit court said about the
maturity of the same fomento system, with verbatim governance ratings.

THE PLURALISM CUT
-----------------
"What got funded" (SALIC) **vs.** "what was held to account" (TCU). Same
fomento policy, two institutional standpoints. This pairs directly with:
- Análise 8's bimodality (65 % of approved projects captured 0 %, R$ 35.1 bn
  over 33 years), and
- the briefing's accompanying R$ 22 bn / ~29.7k projects pending PC at
  MinC + Ancine (stored separately in `tcu__pendings_to_parquet.py`, TBD).

GRAIN
-----
One row per (audit_year, governance_dimension). 4 rows × 2025 at v1 launch.
Future TCU PNAB audits append by year.

SOURCE
------
    https://portal.tcu.gov.br/imprensa/noticias/politica-nacional-de-cultura-e-auditada-pelo-tribunal-de-contas-da-uniao
    Acórdão 1709/2025 - Plenário, processo TC 025.939/2024-6, sessão 30/07/2025.
"""
import hashlib, json, os
from datetime import date
from pathlib import Path
import duckdb, pandas as pd

REPO_ROOT = Path(__file__).resolve().parent.parent
OUT = REPO_ROOT / "raw" / "tcu"
OUT.mkdir(parents=True, exist_ok=True)
SOURCE_PAGE = ("https://portal.tcu.gov.br/imprensa/noticias/"
               "politica-nacional-de-cultura-e-auditada-pelo-tribunal-de-contas-da-uniao")

COLUMNS = ["audit_year", "policy", "governance_dimension",
           "maturity_level", "maturity_ordinal", "verbatim_finding",
           "tcu_acordao", "tcu_processo", "tcu_session_date",
           "source_url", "notes"]

# Ordinal scale of governance maturity (per TCU Referencial):
# 1 = "não institucionalizada"
# 2 = "parcialmente institucionalizada"
# 3 = "institucionalizada"
ROWS = [
    (2025, "PNAB", "Formulação dos objetivos",
     "parcialmente institucionalizada", 2,
     "Objetivos claros, logicamente coerentes, apropriados e realistas, mas NÃO específicos, mensuráveis e delimitados em recorte temporal.",
     "1709/2025", "TC 025.939/2024-6", "2025-07-30", SOURCE_PAGE,
     "TCU notes the policy has clear normative intent but lacks SMART-style operational specification."),
    (2025, "PNAB", "Indicadores de desempenho",
     "parcialmente institucionalizada", 2,
     "Alguns indicadores, mas insuficientes para contemplar as dimensões de eficiência, eficácia e efetividade da política.",
     "1709/2025", "TC 025.939/2024-6", "2025-07-30", SOURCE_PAGE,
     "Insufficient KPIs across the 3+1 dimensions (efficiency / effectiveness / outcome / equity)."),
    (2025, "PNAB", "Gestão de riscos e controles internos",
     "não institucionalizada", 1,
     "As estruturas de gestão de riscos e controles internos NÃO estão institucionalizadas.",
     "1709/2025", "TC 025.939/2024-6", "2025-07-30", SOURCE_PAGE,
     "The lowest rating on the TCU scale — direct accountability concern for an R$ 15 bn / R$ 3 bn-per-year policy."),
    (2025, "PNAB", "Monitoramento e avaliação",
     "parcialmente institucionalizada", 2,
     "As estruturas de monitoramento e avaliação já estão PARCIALMENTE institucionalizadas. Resultados das avaliações de desempenho parcialmente reportados e utilizados.",
     "1709/2025", "TC 025.939/2024-6", "2025-07-30", SOURCE_PAGE,
     "M&E half-built. 'Avaliação dos resultados esperados ainda não se aplica' because PNAB is in early execution phase."),
]


def build():
    df = pd.DataFrame([dict(zip(COLUMNS, r)) for r in ROWS], columns=COLUMNS)
    df["audit_year"] = df["audit_year"].astype("int32")
    df["maturity_ordinal"] = df["maturity_ordinal"].astype("int32")
    df["tcu_session_date"] = pd.to_datetime(df["tcu_session_date"]).dt.date
    return df


def validate(df):
    print("Validating...")
    assert len(df) == 4
    print(f"  ✓ 4 rows — 4 governance dimensions × PNAB × 2025")
    levels = set(df["maturity_level"])
    expected = {"não institucionalizada", "parcialmente institucionalizada"}
    assert levels == expected, f"unexpected maturity levels: {levels}"
    print(f"  ✓ maturity levels ∈ {{não institucionalizada, parcialmente institucionalizada}} — no dimension rated 'institucionalizada'")
    ordinals = df["maturity_ordinal"].tolist()
    assert all(1 <= o <= 3 for o in ordinals)
    avg = sum(ordinals) / len(ordinals)
    print(f"  · mean governance maturity = {avg:.2f} on 1-3 scale (full institutionalisation = 3)")
    riscos = df[df["governance_dimension"].str.contains("riscos")]
    assert riscos["maturity_ordinal"].iloc[0] == 1
    print(f"  ✓ Gestão de riscos / controles internos = 1 (lowest), the TCU's flagged concern")


def write_parquet(df):
    out_path = OUT / "pnab_governance_assessment.parquet"
    con = duckdb.connect()
    con.register("df_data", df)
    con.execute(f"COPY df_data TO '{out_path}' (FORMAT PARQUET, COMPRESSION ZSTD)")
    print(f"  ✓ {out_path.relative_to(REPO_ROOT)} — {len(df)} rows, "
          f"{out_path.stat().st_size/1024:.1f} KB")
    return out_path


def write_meta(out_path, df):
    meta = {
        "table": out_path.stem, "schema": "tcu",
        "description": "TCU PNAB governance-maturity assessment, Acórdão "
                       "1709/2025 (sessão 30/07/2025, relator Augusto Nardes). "
                       "4 governance dimensions × 2025 (Formulação, "
                       "Indicadores, Gestão de riscos e controles, M&E) with "
                       "TCU verbatim ratings and ordinal scoring 1-3.",
        "source": "TCU - Tribunal de Contas da União, Acórdão 1709/2025.",
        "source_pages": [SOURCE_PAGE], "fetch_date": "2026-06-04",
        "etl_script": "etl/tcu__pnab_governance_assessment_to_parquet.py",
        "etl_run_date": str(date.today()),
        "licence": "TCU published findings — public release.",
        "grain": "one row per (audit_year, policy, governance_dimension)",
        "row_count": int(len(df)),
        "notes": "Maturity scale per TCU Referencial de Controle: "
                 "1 = não institucionalizada, "
                 "2 = parcialmente institucionalizada, "
                 "3 = institucionalizada. None of the 4 dimensions reached 3.",
    }
    out_path.with_suffix(".meta.json").write_text(
        json.dumps(meta, indent=2, ensure_ascii=False, default=str))
    print(f"  ✓ {out_path.with_suffix('.meta.json').relative_to(REPO_ROOT)}")


def maybe_push(df, schema, table):
    if os.environ.get("ATANA_ETL_SKIP_PUSH"):
        print(f"  · push skipped for atana.{schema}.{table} (ATANA_ETL_SKIP_PUSH)")
        return
    def _jwt(t):
        t = (t or "").strip()
        return t if (t.startswith("eyJ") and t.count(".") == 2) else ""
    token = _jwt(os.environ.get("MOTHERDUCK_TOKEN"))
    if not token:
        tf = REPO_ROOT / ".motherduck_token"
        token = _jwt(tf.read_text()) if tf.exists() else ""
    if not token:
        print(f"  · MotherDuck push skipped for atana.{schema}.{table} — no valid token.")
        return
    con = duckdb.connect(f"md:atana?motherduck_token={token}")
    con.execute(f"CREATE SCHEMA IF NOT EXISTS atana.{schema}")
    con.register("df_data", df)
    con.execute(f"CREATE OR REPLACE TABLE atana.{schema}.{table} AS SELECT * FROM df_data")
    n = con.execute(f"SELECT COUNT(*) FROM atana.{schema}.{table}").fetchone()[0]
    print(f"  ✓ Synced atana.{schema}.{table} ({n} rows)")


def main():
    print("Building atana.tcu.pnab_governance_assessment...")
    df = build(); validate(df)
    out_path = write_parquet(df); write_meta(out_path, df)
    maybe_push(df, "tcu", "pnab_governance_assessment")
    print("Done.")


if __name__ == "__main__":
    main()
