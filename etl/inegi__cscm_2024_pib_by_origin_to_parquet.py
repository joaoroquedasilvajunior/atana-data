"""INEGI CSCM 2024 — PIB by origin (mercado / hogares / gestión pública) → Parquet.

Phase 5b. Second of four `atana.inegi` non-trade tables. The 2024 cultural PIB
disaggregated by the three institutional origin categories the CSCM tracks:

- **Actividades de mercado** (2.21 %): private cultural production for profit
- **Hogares** (0.38 %): household-level cultural activity (volunteer work,
  street vendors, etc.)
- **Gestión pública** (0.17 %): public-sector cultural activities

Sum = 2.76 ≈ 2.8 (the headline total) within rounding.

The hogares category is the structural piece worth flagging: 0.38 / 2.76 =
13.8 % of cultural PIB comes from household activity that the corpus has no
Brazilian counterpart for — the CSC methodology captures something the IBGE
SIIC does not.

SOURCE
------
    INEGI Comunicado 144/25 (CSCM 2024).
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

COLUMNS = ["year", "origen", "share_total_pib_pct", "notes", "source_page"]

ROWS = [
    (2024, "Actividades de mercado", 2.21,
     "Agentes privados que generan bienes y servicios culturales con fines de lucro.",
     SOURCE_PAGE),
    (2024, "Hogares",                0.38,
     "Trabajo voluntario en actividades culturales, comercio de productos "
     "culturales en la vía pública. NB: the IBGE SIIC does not measure a "
     "comparable Brazilian aggregate.",
     SOURCE_PAGE),
    (2024, "Gestión pública",        0.17,
     "Actividades de unidades de gobierno (acceso, difusión, desarrollo, "
     "fortalecimiento cultural).",
     SOURCE_PAGE),
]


def build():
    df = pd.DataFrame([dict(zip(COLUMNS, r)) for r in ROWS], columns=COLUMNS)
    df = df.sort_values(["year", "share_total_pib_pct"],
                        ascending=[True, False]).reset_index(drop=True)
    df["year"] = df["year"].astype("int32")
    return df


def validate(df):
    print("Validating...")
    assert len(df) == 3
    expected = {"Actividades de mercado", "Hogares", "Gestión pública"}
    assert set(df["origen"]) == expected
    total = df["share_total_pib_pct"].sum()
    assert abs(total - 2.76) < 0.01, f"three origins sum {total} ≠ 2.76"
    print(f"  ✓ 3 origins, sum {total:.2f} % ≈ 2.8 % headline (rounding)")
    hogares_pct = df.loc[df["origen"] == "Hogares", "share_total_pib_pct"].iloc[0] / total * 100
    print(f"  · 'Hogares' = {hogares_pct:.1f} % of cultural PIB — methodological "
          f"gap that IBGE SIIC does not measure")


def write_parquet(df):
    out_path = OUT / "cscm_2024_pib_by_origin.parquet"
    con = duckdb.connect(); con.register("df_data", df)
    con.execute(f"COPY df_data TO '{out_path}' (FORMAT PARQUET, COMPRESSION ZSTD)")
    print(f"  ✓ {out_path.relative_to(REPO_ROOT)} — {len(df)} rows, "
          f"{out_path.stat().st_size/1024:.1f} KB")
    return out_path


def write_meta(out_path, df):
    meta = {
        "table": out_path.stem, "schema": "inegi",
        "description": "INEGI CSCM 2024 — cultural PIB by institutional origin "
                       "(mercado / hogares / gestión pública). 3 rows × 2024. "
                       "'Hogares' (0.38 %) is the structural piece the IBGE "
                       "SIIC does not measure — a methodological-pluralism "
                       "data point.",
        "source": "INEGI Comunicado 144/25 (CSCM 2024).",
        "source_pages": [SOURCE_PAGE], "fetch_date": "2026-06-01",
        "etl_script": "etl/inegi__cscm_2024_pib_by_origin_to_parquet.py",
        "etl_run_date": str(date.today()),
        "licence": "INEGI public data — open licence",
        "grain": "one row per (year, origen)", "row_count": int(len(df)),
        "notes": "Three origins sum to 2.76 % vs the 2.8 % headline (rounding).",
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
    print("Building atana.inegi.cscm_2024_pib_by_origin...")
    df = build(); validate(df)
    out_path = write_parquet(df); write_meta(out_path, df)
    maybe_push(df, "inegi", "cscm_2024_pib_by_origin")
    print("Done.")


if __name__ == "__main__":
    main()
