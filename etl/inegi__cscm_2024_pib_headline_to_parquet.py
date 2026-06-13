"""INEGI CSCM 2024 — PIB & empleo headline → Parquet.

Phase 5b. First of four `atana.inegi` *non-trade* tables (siblings to the
existing csc_comercio). Extends the corpus's only LATAM non-Brazilian
production+employment view: Mexico's CSCM 2024, just released by INEGI
(19 November 2025).

KEY CORPUS NUMBER
-----------------
- Cultural PIB 2024: **MXN 865,682 mi = 2.8 %** of total Mexican economy
- Real growth 2024: **+1.2 %** (total economy +1.3 % — cultural lagged by 0.1 pp)
- Cultural empleo: **1,430,528 puestos = 3.5 %** of total
- Empleo YoY 2024: **−0.2 %** (−2,852 puestos) — VA grew while empleo shrank

This is Mexico's counterpart to Brazil's `atana.ibge_estruturais` value-added
series. The natural input for a LATAM-comparative read of Análise 14.

SOURCE
------
    https://www.inegi.org.mx/contenidos/saladeprensa/boletines/2025/cultura/CSCM2024_CP.pdf
    INEGI Comunicado de Prensa 144/25, 19 November 2025 (public PDF).

OUTPUT
------
    raw/inegi/cscm_2024_pib_headline.parquet  (+ .meta.json)

Idempotent; ATANA_ETL_SKIP_PUSH guard. Schema: atana.inegi.
"""
import hashlib, json, os
from datetime import date
from pathlib import Path
import duckdb, pandas as pd

REPO_ROOT = Path(__file__).resolve().parent.parent
OUT = REPO_ROOT / "raw" / "inegi"
OUT.mkdir(parents=True, exist_ok=True)
SOURCE_PAGE = ("https://www.inegi.org.mx/contenidos/saladeprensa/boletines/2025/"
               "cultura/CSCM2024_CP.pdf")

COLUMNS = ["year", "pib_cultural_mxn_mi", "share_total_pib_pct",
           "real_growth_yoy_pct", "total_eco_real_growth_yoy_pct",
           "puestos_trabajo", "share_total_empleo_pct",
           "empleo_yoy_pct", "notes", "source_page"]

ROWS = [
    (2024, 865682, 2.8, 1.2, 1.3, 1430528, 3.5, -0.2,
     "Cultural sector contributed MXN 865,682 mi (2.8 %) to total Mexican PIB "
     "in 2024. Real growth +1.2 % (total economy +1.3 %; 0.1 pp gap). 1,430,528 "
     "puestos de trabajo = 3.5 % of total. Empleo dropped 2,852 puestos (−0.2 %) "
     "while VA grew — the productivity-up / headcount-down pattern.",
     SOURCE_PAGE),
]


def build():
    df = pd.DataFrame(
        [dict(zip(COLUMNS, r)) for r in ROWS], columns=COLUMNS)
    df["year"] = df["year"].astype("int32")
    df["pib_cultural_mxn_mi"] = df["pib_cultural_mxn_mi"].astype("Int64")
    df["puestos_trabajo"] = df["puestos_trabajo"].astype("Int64")
    return df


def validate(df):
    print("Validating...")
    assert len(df) == 1
    r = df.iloc[0]
    assert int(r["pib_cultural_mxn_mi"]) == 865682
    assert r["share_total_pib_pct"] == 2.8
    assert int(r["puestos_trabajo"]) == 1430528
    print(f"  ✓ 2024 headline: PIB MXN {r['pib_cultural_mxn_mi']:,} mi ({r['share_total_pib_pct']}%), "
          f"{r['puestos_trabajo']:,} puestos ({r['share_total_empleo_pct']}%); "
          f"real +{r['real_growth_yoy_pct']}% PIB / {r['empleo_yoy_pct']}% empleo")


def write_parquet(df):
    out_path = OUT / "cscm_2024_pib_headline.parquet"
    con = duckdb.connect()
    con.register("df_data", df)
    con.execute(f"COPY df_data TO '{out_path}' (FORMAT PARQUET, COMPRESSION ZSTD)")
    print(f"  ✓ {out_path.relative_to(REPO_ROOT)} — {len(df)} rows, "
          f"{out_path.stat().st_size/1024:.1f} KB")
    return out_path


def write_meta(out_path, df):
    meta = {
        "table": out_path.stem, "schema": "inegi",
        "description": "INEGI Cuenta Satélite de la Cultura de México (CSCM) "
                       "2024 — headline PIB + empleo for the cultural sector. "
                       "MXN 865,682 mi (2.8 % of total economy), 1.43 mi "
                       "puestos (3.5 %), real growth +1.2 % vs total economy "
                       "+1.3 %. Phase 5b of the corpus expansion — sibling to "
                       "csc_comercio (the trade module already ingested).",
        "source": "INEGI Comunicado de Prensa 144/25, 19 November 2025 (CSCM 2024).",
        "source_pages": [SOURCE_PAGE], "fetch_date": "2026-06-01",
        "etl_script": "etl/inegi__cscm_2024_pib_headline_to_parquet.py",
        "etl_run_date": str(date.today()),
        "licence": "INEGI public data — open licence",
        "grain": "one row per reference year", "row_count": int(len(df)),
        "notes": "Reference year 2018 for real-value series. Atana corpus's "
                 "first LATAM non-Brazilian PIB/empleo cell. See "
                 "docs/methodology/inegi_csc.md §6 for the non-trade module update.",
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
    print("Building atana.inegi.cscm_2024_pib_headline...")
    df = build(); validate(df)
    out_path = write_parquet(df); write_meta(out_path, df)
    maybe_push(df, "inegi", "cscm_2024_pib_headline")
    print("Done.")


if __name__ == "__main__":
    main()
