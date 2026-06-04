"""TCU PNAB audit — deliberations to MinC → Parquet.

Phase 5c. Second of two `atana.tcu` tables. The TCU's recommendations to
the Ministry of Culture flowing from Acórdão 1709/2025 — what MinC must
do to bring PNAB governance up to TCU standards.

These are the action items MinC owes back to TCU and (via the Relatório
de Fiscalizações em Políticas Públicas) to the Comissão Mista de
Orçamento for the next budget cycle.

GRAIN
-----
One row per (audit_year, deliberation_item). 4 deliberations × PNAB × 2025.
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

COLUMNS = ["audit_year", "policy", "deliberation_item",
           "addressee", "verbatim_recommendation",
           "tcu_acordao", "source_url", "notes"]

ROWS = [
    (2025, "PNAB", "Planejamento estratégico formal",
     "MinC",
     "Elaborar e formalizar instrumento de planejamento estratégico para a PNAB, que explicite a teoria da mudança ou modelo lógico de intervenção, documentando a relação entre os problemas identificados, os objetivos da política, as ações planejadas e os resultados e impactos esperados.",
     "1709/2025", SOURCE_PAGE,
     "The TCU asks MinC to make the implicit theory of change explicit and documented."),
    (2025, "PNAB", "Metas de curto/médio/longo prazo",
     "MinC",
     "Estabelecer metas de curto, médio e longo prazo, indo além de objetivos apenas gerenciais ou de governança. Essas metas devem orientar a implementação das ações necessárias para cumprir os objetivos estratégicos da política.",
     "1709/2025", SOURCE_PAGE,
     "Currently goals are managerial only — TCU wants substantive policy targets at multiple horizons."),
    (2025, "PNAB", "Indicadores multidimensionais",
     "MinC",
     "Definir indicadores para a PNAB, com dados disponíveis, prazos e responsáveis pela coleta e aferição, abrangendo eficiência, eficácia, efetividade e equidade.",
     "1709/2025", SOURCE_PAGE,
     "Four-dimensional KPI scheme: efficiency / effectiveness / outcome / equity. Equity dimension is notable — Atana's distributional focus aligns directly."),
    (2025, "PNAB", "Linha de base transparente",
     "MinC",
     "Definir e formalizar uma linha de base para as metas e indicadores, a partir da coleta e análise de dados da PNAB e do setor cultural, garantindo transparência ao processo e ao resultado.",
     "1709/2025", SOURCE_PAGE,
     "The 'transparência' clause is the entry-point for any future Atana auditing role — open baseline data."),
]


def build():
    df = pd.DataFrame([dict(zip(COLUMNS, r)) for r in ROWS], columns=COLUMNS)
    df["audit_year"] = df["audit_year"].astype("int32")
    return df


def validate(df):
    print("Validating...")
    assert len(df) == 4
    assert all(df["addressee"] == "MinC")
    print(f"  ✓ 4 deliberations, all addressed to MinC")
    for _, r in df.iterrows():
        assert isinstance(r["verbatim_recommendation"], str)
        assert len(r["verbatim_recommendation"]) > 80
    print(f"  ✓ verbatim recommendations preserved")
    eq = df[df["verbatim_recommendation"].str.contains("equidade")]
    assert len(eq) == 1
    print(f"  ✓ 'equidade' dimension explicitly mentioned (Atana distributional alignment)")


def write_parquet(df):
    out_path = OUT / "pnab_deliberations.parquet"
    con = duckdb.connect()
    con.register("df_data", df)
    con.execute(f"COPY df_data TO '{out_path}' (FORMAT PARQUET, COMPRESSION ZSTD)")
    print(f"  ✓ {out_path.relative_to(REPO_ROOT)} — {len(df)} rows, "
          f"{out_path.stat().st_size/1024:.1f} KB")
    return out_path


def write_meta(out_path, df):
    meta = {
        "table": out_path.stem, "schema": "tcu",
        "description": "TCU PNAB audit deliberations — 4 actionable "
                       "recommendations to MinC from Acórdão 1709/2025: "
                       "formal strategic planning with theory of change, "
                       "short/medium/long-term targets, multidimensional "
                       "indicators (efficiency/effectiveness/outcome/equity), "
                       "transparent baseline.",
        "source": "TCU - Tribunal de Contas da União, Acórdão 1709/2025.",
        "source_pages": [SOURCE_PAGE], "fetch_date": "2026-06-04",
        "etl_script": "etl/tcu__pnab_deliberations_to_parquet.py",
        "etl_run_date": str(date.today()),
        "licence": "TCU published findings — public release.",
        "grain": "one row per (audit_year, deliberation_item)",
        "row_count": int(len(df)),
        "notes": "These deliberations feed the TCU Relatório de Fiscalizações "
                 "em Políticas Públicas (Comissão Mista de Orçamento), the "
                 "next-cycle budget oversight document. Future TCU follow-ups "
                 "on MinC compliance append by audit_year.",
    }
    out_path.with_suffix(".meta.json").write_text(
        json.dumps(meta, indent=2, ensure_ascii=False))
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
    print("Building atana.tcu.pnab_deliberations...")
    df = build(); validate(df)
    out_path = write_parquet(df); write_meta(out_path, df)
    maybe_push(df, "tcu", "pnab_deliberations")
    print("Done.")


if __name__ == "__main__":
    main()
