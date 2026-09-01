"""PNAB beneficiary microdata → table atana.pnab.beneficiarios (Phase 10a).

The MinC 'dados abertos completo' export: one row per (beneficiary × ente) of the
PNAB Ciclo 1 direct transfer, the beneficiary document MASKED (LGPD), joined by MinC
to BB-Ágil (payment), Receita CPF (sex/age/occupation/MEI), Receita CNPJ (CNAE/porte),
RAIS (race/schooling/PCD/CBO/wage band), INSS, CNEFE, CadÚnico (poverty/PBF/BPC), BPC
and IBGE (population/region). 167,817 rows × 59 cols, R$ 2.87 bn — reconciles to the
Ciclo 1 aggregate already in atana.pnab.execucao_financeira.

Design (matches pnab__to_parquet.py):
  - Source lives in raw/pnab/_source/ (gitignored, 125 MB). Only the Parquet is committed.
  - Column names kept with their SOURCE suffix (_bbagil / _receita_cpf / _rais …) as
    provenance. One typed column added: valor_brl (DOUBLE) from valor_transacao_total_bbagil.
  - BRL NOMINAL (PNAB convention, §4 of the methodology). Ciclo 1 only.
  - Idempotent: read_csv (all_varchar) → DuckDB COPY (ZSTD), ORDER BY ALL → byte-identical
    reruns. MotherDuck sync is a MANUAL checkpoint (new table) — see the handoff.
"""
import hashlib
import json
from datetime import date
from pathlib import Path

import duckdb

REPO = Path(__file__).resolve().parent.parent
SRC = REPO / "raw" / "pnab" / "_source" / "pnab_dados_abertos_completo.csv"
OUT = REPO / "curated" / "pnab"
OUT.mkdir(parents=True, exist_ok=True)
TABLE = "beneficiarios"


def header_names(path):
    with open(path, encoding="utf-8-sig") as fh:
        return fh.readline().rstrip("\n").split(";")


def build():
    names = header_names(SRC)
    assert len(names) == 59, f"expected 59 cols, got {len(names)}"
    con = duckdb.connect()
    con.execute("PRAGMA threads=4")
    reader = (
        f"read_csv('{SRC}', delim=';', header=true, names={names!r}, "
        f"all_varchar=true, ignore_errors=true)"
    )
    # typed money col + everything else preserved as provenance-suffixed strings
    con.execute(f"""
        CREATE TABLE t AS
        SELECT *, TRY_CAST(valor_transacao_total_bbagil AS DOUBLE) AS valor_brl
        FROM {reader}
    """)
    p = OUT / f"{TABLE}.parquet"
    con.execute(f"COPY (SELECT * FROM t ORDER BY ALL NULLS LAST) "
                f"TO '{p}' (FORMAT PARQUET, COMPRESSION ZSTD)")
    n = con.execute("SELECT count(*) FROM t").fetchone()[0]
    total = con.execute("SELECT sum(valor_brl) FROM t").fetchone()[0]
    con.close()
    (OUT / f"{TABLE}.meta.json").write_text(json.dumps({
        "table": f"pnab.{TABLE}", "rows": n,
        "value_total_brl": round(total, 2), "currency": "BRL nominal (Ciclo 1)",
        "source": "MinC Portal de Dados da Cultura — 'PNAB dados abertos completo' "
                  "(BB-Ágil × Receita CPF/CNPJ × RAIS × INSS × CNEFE × CadÚnico × BPC × IBGE)",
        "note": "beneficiary document masked (LGPD); demographic joins cover the formal "
                "subset only (majority NULL). See docs/methodology/pnab_beneficiarios.md",
        "etl_script": "etl/pnab__beneficiarios_to_parquet.py", "etl_run_date": str(date.today()),
        "licence": "CC BY 4.0 (Portal de Dados da Cultura)",
    }, indent=2, ensure_ascii=False))
    return p, n, total


def validate(p):
    con = duckdb.connect()
    R = f"read_parquet('{p}')"
    n = con.execute(f"SELECT count(*) FROM {R}").fetchone()[0]
    tot = con.execute(f"SELECT sum(valor_brl)/1e9 FROM {R}").fetchone()[0]
    cpf, cnpj = con.execute(f"""SELECT
        sum(valor_brl) FILTER(WHERE tipo_documento_bbagil='CPF'),
        sum(valor_brl) FILTER(WHERE tipo_documento_bbagil='CNPJ') FROM {R}""").fetchone()
    m, fem = con.execute(f"""SELECT
        sum(valor_brl) FILTER(WHERE sexo_receita_cpf='Masculino'),
        sum(valor_brl) FILTER(WHERE sexo_receita_cpf='Feminino') FROM {R}""").fetchone()
    ne, se = con.execute(f"""SELECT
        count(*) FILTER(WHERE nome_macrorregiao_ibge='Nordeste'),
        count(*) FILTER(WHERE nome_macrorregiao_ibge='Sudeste') FROM {R}""").fetchone()
    mun, est = con.execute(f"""SELECT
        count(*) FILTER(WHERE tipo_ente_bbagil='MUNICIPIO'),
        count(*) FILTER(WHERE tipo_ente_bbagil='ESTADO') FROM {R}""").fetchone()
    con.close()
    checks = [
        ("rows = 167,817", n == 167817),
        ("total ~R$2.87bn (reconciles Ciclo 1)", 2.7 < tot < 3.0),
        ("CNPJ money > CPF money", cnpj > cpf),
        ("Masculino > Feminino (CPF)", m > fem),
        ("Nordeste more beneficiaries than Sudeste", ne > se),
        ("municipal=145,235 + estadual=22,582 (SNIIC seminar identity)",
         mun == 145235 and est == 22582),
    ]
    for name, ok in checks:
        print(f"  [{'OK' if ok else 'XX'}] {name}")
    assert all(ok for _, ok in checks), "validation failed"
    print(f"  {sum(ok for _, ok in checks)}/{len(checks)} passed")


if __name__ == "__main__":
    p, n, total = build()
    print(f"✓ wrote {p.relative_to(REPO)} — {n:,} rows, R$ {total/1e9:.2f} bn")
    validate(p)
    print(f"  md5 {hashlib.md5(p.read_bytes()).hexdigest()}")
    print("\nMotherDuck sync is MANUAL (new table). See the Phase 10a handoff.")
