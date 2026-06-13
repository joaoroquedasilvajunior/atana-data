"""INEGI CSCM 2024 — PIB by clasificación funcional (10 áreas) → Parquet.

Phase 5b. Third of four `atana.inegi` non-trade tables. Mexico's 10-area
cultural PIB split for 2024, with the five named growth rates (3 fastest +
2 declining) attached. Five other areas have growth NULL — the boletín only
names the top-3 and bottom-2.

THE ARTESANÍAS PARADOX — the corpus's headline INEGI cell
----------------------------------------------------------
Artesanías is the LARGEST area by PIB share (18.4 %) AND the LARGEST
decliner (−3.8 %) in 2024. It is also Mexico's biggest cultural employer
(per the CSCM boletines historically ≈ 30 % of cultural employment) yet
contributes only 18.4 % of cultural PIB — a productivity (value-per-
worker) trough. Atana Index Vol. 1 §6 quadrant cited 'Mexico — gigante
dormente'; CSCM 2024 says the giant is shrinking specifically on the
artesanías face.

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

COLUMNS = ["year", "area", "share_pib_cultural_pct",
           "real_growth_yoy_pct", "notes", "source_page"]

# Verbatim from the boletín. Growth NULL where not stated (5 of 10 areas).
ROWS = [
    (2024, "Artesanías",                       18.4, -3.8,
     "Largest area by PIB share and largest decliner in 2024 — the artesanías "
     "paradox: highest employment share, lowest VA-per-worker, falling.",
     SOURCE_PAGE),
    (2024, "Contenidos digitales e internet",  18.1, None,
     "Acceso y transmisión de contenidos digitales. Growth not stated in the boletín.",
     SOURCE_PAGE),
    (2024, "Medios audiovisuales",             17.2, -3.6,
     "Televisión, cine. Second-largest decliner in 2024.",
     SOURCE_PAGE),
    (2024, "Diseño y servicios creativos",     14.5,  7.7,
     "Second-fastest grower in 2024 — pairs with Brazil's Design/software boom "
     "story across atana.inpi / atana.rais / atana.ibge_cempre / atana.ibge_estruturais.",
     SOURCE_PAGE),
    (2024, "Artes escénicas y espectáculos",    7.0, None,
     "Performing arts. Growth not stated.", SOURCE_PAGE),
    (2024, "Patrimonio cultural y natural",     6.1, None,
     "Heritage. Growth not stated.", SOURCE_PAGE),
    (2024, "Libros, impresiones y prensa",      5.8, None,
     "Books, print, press. Growth not stated.", SOURCE_PAGE),
    (2024, "Formación y difusión cultural",     5.6, None,
     "Cultural training & dissemination. Growth not stated.", SOURCE_PAGE),
    (2024, "Artes visuales y plásticas",        4.5,  5.3,
     "Third-fastest grower in 2024.", SOURCE_PAGE),
    (2024, "Música y conciertos",               2.8, 14.9,
     "FASTEST-growing area in 2024. Pairs with IFPI GMR 2026 Mexico +13.3 % "
     "(#10 globally) and atana.cisac Mexico 65.1 % digital share — three "
     "independent music-Mexico signals in 2025.",
     SOURCE_PAGE),
]


def build():
    df = pd.DataFrame([dict(zip(COLUMNS, r)) for r in ROWS], columns=COLUMNS)
    df = df.sort_values(["year", "share_pib_cultural_pct"],
                        ascending=[True, False]).reset_index(drop=True)
    df["year"] = df["year"].astype("int32")
    return df


def validate(df):
    print("Validating...")
    assert len(df) == 10, f"expected 10 áreas, got {len(df)}"
    s = round(df["share_pib_cultural_pct"].sum(), 1)
    assert s == 100.0, f"10 áreas sum {s} ≠ 100.0 %"
    print(f"  ✓ 10 áreas sum to 100.0 % of cultural PIB")
    growth = df["real_growth_yoy_pct"].dropna().tolist()
    assert len(growth) == 5, f"5 áreas should have stated growth, got {len(growth)}"
    print(f"  ✓ 5 áreas with stated growth (top-3 + bottom-2), 5 NULL")
    fastest = df.sort_values("real_growth_yoy_pct", ascending=False, na_position="last").iloc[0]
    assert fastest["area"] == "Música y conciertos" and fastest["real_growth_yoy_pct"] == 14.9
    print(f"  ✓ fastest: Música y conciertos +14.9 % (cross-confirms IFPI Mexico +13.3 %)")
    largest = df.iloc[0]
    decliner = df.sort_values("real_growth_yoy_pct").iloc[0]
    assert largest["area"] == "Artesanías" and decliner["area"] == "Artesanías"
    print(f"  ✓ Artesanías paradox: largest area (18.4 %) and largest decliner (−3.8 %)")


def write_parquet(df):
    out_path = OUT / "cscm_2024_pib_by_area.parquet"
    con = duckdb.connect(); con.register("df_data", df)
    con.execute(f"COPY df_data TO '{out_path}' (FORMAT PARQUET, COMPRESSION ZSTD)")
    print(f"  ✓ {out_path.relative_to(REPO_ROOT)} — {len(df)} rows, "
          f"{out_path.stat().st_size/1024:.1f} KB")
    return out_path


def write_meta(out_path, df):
    meta = {
        "table": out_path.stem, "schema": "inegi",
        "description": "INEGI CSCM 2024 — cultural PIB by clasificación "
                       "funcional (10 áreas), share + growth. Artesanías "
                       "paradox highlighted (largest + largest decliner); "
                       "Música y conciertos fastest grower at +14.9 %.",
        "source": "INEGI Comunicado 144/25 (CSCM 2024).",
        "source_pages": [SOURCE_PAGE], "fetch_date": "2026-06-01",
        "etl_script": "etl/inegi__cscm_2024_pib_by_area_to_parquet.py",
        "etl_run_date": str(date.today()),
        "licence": "INEGI public data — open licence",
        "grain": "one row per (year, area)", "row_count": int(len(df)),
        "notes": "10 áreas sum to 100.0 % of cultural PIB. Growth NULL for 5 "
                 "áreas — the boletín only names the top-3 and bottom-2.",
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
    print("Building atana.inegi.cscm_2024_pib_by_area...")
    df = build(); validate(df)
    out_path = write_parquet(df); write_meta(out_path, df)
    maybe_push(df, "inegi", "cscm_2024_pib_by_area")
    print("Done.")


if __name__ == "__main__":
    main()
