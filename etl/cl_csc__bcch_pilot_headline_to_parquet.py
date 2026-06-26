"""Chile CSC pilot — BCCh household cultural consumption headline → Parquet.

Phase 7a.0. First of the planned tables in the new `atana.cl_csc` schema —
the **fifth LATAM country** to enter the corpus (after BR, MX, CO, CR, AR).

The Cuenta Satélite de Cultura de Chile launched its **first results in
2024**, jointly developed by:
- MINCAP (Ministerio de las Culturas, las Artes y el Patrimonio)
- Banco Central de Chile (BCCh) — anchor in the Cuentas Nacionales system
- CEPAL — technical methodological support

This single-table ingest captures the publicly stated **headline indicator** of
the CSC pilot — *consumo efectivo de los hogares en productos culturales*
(% del consumo total efectivo de los hogares) — for the three explicitly stated
years in MINCAP's *Informe Final Cuenta Pública Participativa 2025* (published
early 2026): 2018 (pre-pandemic baseline), pandemic low, and 2022 (last year
with BCCh data available at time of report).

Tier-1 ingest pattern, sibling to `atana.tcu`, `atana.luminate`,
`atana.ifpi` — inline data, idempotent, byte-identical reruns. Phase 7a.1
(the deeper INE Estadísticas Culturales Informe Anual 2024 ingest) is
separately scoped.

PROVENANCE
----------
Verbatim from MINCAP cuenta pública 2025 (PDF; the corpus stores the relevant
extract in `_atana_intel/phase7_chile_uruguay_scoping.md` §9.1):

> "el consumo efectivo de los hogares en productos culturales disminuyo desde
> el 2018 hasta la pandemia, de 1,7% a 1,4%; mientras que luego de la pandemia,
> se ha mantenido en un 1,4% hasta el 2022 (último año con datos del Banco
> Central de Chile disponibles)."

The intermediate years 2019/2021 are NOT explicitly stated by MINCAP and are
therefore NOT included here. Phase 7a.1 may recover the full series from the
underlying BCCh release.

SOURCE
------
    https://www.cultura.gob.cl/cuentapublica/wp-content/uploads/sites/28/2026/01/informe-final-convencion-cuenta-publica-2025.pdf
"""
import hashlib, json, os
from datetime import date
from pathlib import Path
import duckdb, pandas as pd

REPO_ROOT = Path(__file__).resolve().parent.parent
OUT = REPO_ROOT / "raw" / "cl_csc"
OUT.mkdir(parents=True, exist_ok=True)

SOURCE_URL = ("https://www.cultura.gob.cl/cuentapublica/wp-content/uploads/"
              "sites/28/2026/01/informe-final-convencion-cuenta-publica-2025.pdf")
ATTRIB = "MINCAP — Informe Final Cuenta Pública Participativa 2025 (Chile)"

COLUMNS = ["year", "year_label", "indicator_key", "indicator_label",
           "indicator_value", "indicator_unit",
           "csc_status", "data_owner", "anchor_source",
           "verbatim_quote_source", "attribution", "source_url", "notes"]

ROWS = [
    (2018, "2018 (pre-pandemia, baseline)",
     "household_effective_cultural_consumption_share",
     "Consumo efectivo de los hogares en productos culturales, % del consumo efectivo total de los hogares",
     1.7, "percent",
     "pilot_first_results_2024", "BCCh + MINCAP + CEPAL",
     "Banco Central de Chile — Cuentas Nacionales",
     "MINCAP cuenta pública 2025 §reporting on CSC primeros resultados 2024",
     ATTRIB, SOURCE_URL,
     "Pre-pandemic baseline. The peak of the published 3-point series."),
    (2020, "≈2020 (pandemic low)",
     "household_effective_cultural_consumption_share",
     "Consumo efectivo de los hogares en productos culturales, % del consumo efectivo total de los hogares",
     1.4, "percent",
     "pilot_first_results_2024", "BCCh + MINCAP + CEPAL",
     "Banco Central de Chile — Cuentas Nacionales",
     "MINCAP cuenta pública 2025 §reporting on CSC primeros resultados 2024",
     ATTRIB, SOURCE_URL,
     "MINCAP prose states 'disminuyó desde el 2018 hasta la pandemia, de 1,7% a 1,4%'. "
     "The specific pandemic year is not nominated explicitly; we use 2020 as the conventional pandemic-trough year. "
     "Phase 7a.1 (INE/BCCh release) should resolve to the exact year."),
    (2022, "2022 (last year with BCCh data)",
     "household_effective_cultural_consumption_share",
     "Consumo efectivo de los hogares en productos culturales, % del consumo efectivo total de los hogares",
     1.4, "percent",
     "pilot_first_results_2024", "BCCh + MINCAP + CEPAL",
     "Banco Central de Chile — Cuentas Nacionales",
     "MINCAP cuenta pública 2025 §reporting on CSC primeros resultados 2024",
     ATTRIB, SOURCE_URL,
     "Most recent published point. 'Último año con datos del Banco Central de Chile disponibles' per MINCAP."),
]


def build():
    df = pd.DataFrame([dict(zip(COLUMNS, r)) for r in ROWS], columns=COLUMNS)
    df["year"] = df["year"].astype("int32")
    df["indicator_value"] = df["indicator_value"].astype("float64")
    return df


def validate(df):
    print("Validating...")
    assert len(df) == 3, f"expected 3 rows, got {len(df)}"
    print(f"  ✓ 3 rows — 3 explicitly-stated points in MINCAP cuenta pública prose")
    years = set(df["year"])
    assert years == {2018, 2020, 2022}, f"unexpected years: {years}"
    print(f"  ✓ years = {{2018, 2020, 2022}} (intermediate 2019/2021 deliberately omitted)")
    assert df.loc[df["year"] == 2018, "indicator_value"].iloc[0] == 1.7
    assert df.loc[df["year"] == 2020, "indicator_value"].iloc[0] == 1.4
    assert df.loc[df["year"] == 2022, "indicator_value"].iloc[0] == 1.4
    print(f"  ✓ headline values: 2018=1.7% · 2020=1.4% · 2022=1.4% (verbatim MINCAP)")
    indicators = set(df["indicator_key"])
    assert indicators == {"household_effective_cultural_consumption_share"}
    print(f"  ✓ single indicator across all 3 rows — household cultural consumption share")


def write_parquet(df):
    out_path = OUT / "bcch_pilot_headline_consumption.parquet"
    con = duckdb.connect()
    con.register("df_data", df)
    con.execute(f"COPY df_data TO '{out_path}' (FORMAT PARQUET, COMPRESSION ZSTD)")
    print(f"  ✓ {out_path.relative_to(REPO_ROOT)} — {len(df)} rows, "
          f"{out_path.stat().st_size/1024:.1f} KB")
    return out_path


def write_meta(out_path, df):
    meta = {
        "table": out_path.stem, "schema": "cl_csc",
        "description": (
            "Chile Cuenta Satélite de Cultura pilot — household effective "
            "cultural consumption share, 3-point series (2018, ≈2020, 2022) "
            "as published in the MINCAP Informe Final Cuenta Pública "
            "Participativa 2025. First results of the BCCh+MINCAP+CEPAL CSC "
            "launched 2024. Tier 1 — single headline indicator transcribed "
            "from the cuenta pública prose, not the underlying BCCh release."
        ),
        "source": ATTRIB,
        "source_pages": [SOURCE_URL],
        "fetch_date": "2026-06-16",
        "etl_script": "etl/cl_csc__bcch_pilot_headline_to_parquet.py",
        "etl_run_date": str(date.today()),
        "licence": "MINCAP cuenta pública — public release.",
        "grain": "one row per (year, indicator)",
        "row_count": int(len(df)),
        "notes": (
            "Intermediate years 2019 and 2021 are not explicitly stated in the "
            "cuenta pública and are deliberately omitted. The pandemic-low "
            "year is conventionally 2020 (not explicitly nominated). The "
            "underlying BCCh CSC release (Phase 7a.1) should resolve to the "
            "full annual series 2018-2022 with 5 rows."
        ),
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
    print("Building atana.cl_csc.bcch_pilot_headline_consumption...")
    df = build(); validate(df)
    out_path = write_parquet(df); write_meta(out_path, df)
    maybe_push(df, "cl_csc", "bcch_pilot_headline_consumption")
    print("Done.")


if __name__ == "__main__":
    main()
