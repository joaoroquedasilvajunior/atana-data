"""Convert Argentina's Cuenta Satélite de Cultura (CSC) — cultural external-trade
module — from the SInCA open-data CSVs to Parquet.

Phase 3c of the Atana Data LATAM expansion. Third national source after
Mexico (`atana.inegi`) and Colombia (`atana.dane`).

WHAT THIS INGESTS
-----------------
The Argentine CSC — produced by SInCA (Sistema de Información Cultural de la
Argentina, Ministerio de Cultura) with INDEC — publishes a `comercio exterior`
dataset on datos.cultura.gob.ar as a set of annual CSV series, 2004–2022:

    csc20-expo-impo-servicios-cult-pesos-k.csv          servicios, constant 2004 pesos
    csc21-expo-impo-bienes-servicios-cult-pesos-c.csv   goods+services, current pesos
    csc22-expo-impo-bienes-servicios-cult-pesos-k.csv   goods+services, constant 2004 pesos
    csc23-participacion-expo-culturales-total-expo-k.csv
    csc24-participacion-impo-culturales-total-impo-k.csv
    csc25-participacion-expo-cult_vbp_cult_pesos_c.csv
    csc26-participacion-expo-cult-vbp-cult-pesos-k.csv

The dataset has no standalone "bienes" (goods) file; goods are recoverable for
the constant series as (goods+services) − services. There is no services file
in current pesos, so for the current basis only the goods+services total exists.

⚠️ CURRENCY CAVEAT. Values are in thousands of Argentine pesos. The current-peso
series (`corriente`) spans two decades of high inflation and is NOT comparable
across years — the constant-2004-peso series is the time-comparable measure.
No USD column is derived: Argentina's official ARS/USD rate diverged sharply
from real value under the multiple-exchange-rate regime (the *brecha cambiaria*),
so any ARS→USD conversion would mislead. Argentina is therefore held in pesos —
the absence of a comparable-USD figure is itself a documented finding.

Output (long format):
    raw/sinca/csc_comercio.parquet         (+ .meta.json)   — trade values
    raw/sinca/csc_participacion.parquet    (+ .meta.json)   — participation ratios

Idempotent. CSV read → list-of-dicts → pandas DataFrame → DuckDB COPY to Parquet
(no pyarrow). MotherDuck push gated behind a token (env var or .motherduck_token).

Usage:
    python etl/sinca__csc_to_parquet.py
"""
import csv
import hashlib
import json
from datetime import date
from pathlib import Path

import duckdb
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parent.parent
OUT = REPO_ROOT / "raw" / "sinca"
SRC = OUT / "_source"
OUT.mkdir(parents=True, exist_ok=True)

# Trade-value source files: filename → (segment, price_basis, value-column prefix)
TRADE_FILES = {
    "csc20-expo-impo-servicios-cult-pesos-k.csv": (
        "servicios_culturales", "constante_2004", "servicios_culturales"),
    "csc21-expo-impo-bienes-servicios-cult-pesos-c.csv": (
        "bienes_y_servicios_culturales", "corriente", "bienes_servicios_culturales"),
    "csc22-expo-impo-bienes-servicios-cult-pesos-k.csv": (
        "bienes_y_servicios_culturales", "constante_2004", "bienes_servicios_culturales"),
}

# Participation source files: filename → (indicator, value-column name)
PARTICIPACION_FILES = {
    "csc23-participacion-expo-culturales-total-expo-k.csv": (
        "expo_cultural_pct_total_expo", "participacion_expo_culturales_total_expo"),
    "csc24-participacion-impo-culturales-total-impo-k.csv": (
        "impo_cultural_pct_total_impo", "part_impo_culturales_total_impo"),
    "csc25-participacion-expo-cult_vbp_cult_pesos_c.csv": (
        "expo_cultural_pct_vbp_cultural_corriente", "part_expo_culturales_vbp_cultural"),
    "csc26-participacion-expo-cult-vbp-cult-pesos-k.csv": (
        "expo_cultural_pct_vbp_cultural_constante", "part_expo_culturales_vbp_cultural"),
}

FLOWS = {"exportacion": "expo", "importacion": "impo", "saldo": "saldo_comercial"}


def _year(indice_tiempo: str) -> int:
    """'2004-01-01' → 2004."""
    return int(str(indice_tiempo).strip()[:4])


def _read_csv(path: Path) -> list:
    with open(path, newline="", encoding="utf-8-sig") as fh:
        return list(csv.DictReader(fh))


def extract_comercio() -> pd.DataFrame:
    """Build the long-format trade table, deriving constant-price goods."""
    rows = []
    # constant-price values keyed (segment, year, flow) → for deriving 'bienes'
    const = {}
    for fname, (segment, basis, prefix) in TRADE_FILES.items():
        for rec in _read_csv(SRC / fname):
            year = _year(rec["indice_tiempo"])
            for flow, colstem in FLOWS.items():
                col = f"{colstem}_{prefix}" if colstem != "saldo_comercial" \
                    else f"saldo_comercial_{prefix}"
                raw = rec.get(col)
                val = float(raw) if raw not in (None, "") else None
                rows.append(dict(
                    year=year, segment=segment, price_basis=basis, flow=flow,
                    value_ars_thousand=val, is_derived=False, source_file=fname))
                if basis == "constante_2004":
                    const[(segment, year, flow)] = val

    # derive goods (bienes) for the constant series: (goods+services) − services
    years = sorted({y for (_, y, _) in const})
    for year in years:
        for flow in FLOWS:
            tot = const.get(("bienes_y_servicios_culturales", year, flow))
            srv = const.get(("servicios_culturales", year, flow))
            val = round(tot - srv, 3) if (tot is not None and srv is not None) else None
            rows.append(dict(
                year=year, segment="bienes_culturales", price_basis="constante_2004",
                flow=flow, value_ars_thousand=val, is_derived=True,
                source_file="derived: csc22 − csc20"))
    return pd.DataFrame(rows).sort_values(
        ["price_basis", "segment", "year", "flow"]).reset_index(drop=True)


def extract_participacion() -> pd.DataFrame:
    rows = []
    for fname, (indicator, col) in PARTICIPACION_FILES.items():
        for rec in _read_csv(SRC / fname):
            raw = rec.get(col)
            rows.append(dict(
                year=_year(rec["indice_tiempo"]),
                indicator=indicator,
                value_ratio=float(raw) if raw not in (None, "") else None,
                source_file=fname))
    return pd.DataFrame(rows).sort_values(
        ["indicator", "year"]).reset_index(drop=True)


def write_parquet(df: pd.DataFrame, table_name: str) -> Path:
    out_path = OUT / f"{table_name}.parquet"
    con = duckdb.connect()
    con.register("df_data", df)
    con.execute(f"COPY df_data TO '{out_path}' (FORMAT PARQUET, COMPRESSION ZSTD)")
    size_kb = out_path.stat().st_size / 1024
    print(f"  ✓ {out_path.relative_to(REPO_ROOT)} — {len(df):,} rows, {size_kb:.1f} KB")
    return out_path


def write_meta(out_path: Path, source_files: list, description: str,
               extra: dict | None = None) -> None:
    srcs = []
    for sf in source_files:
        p = Path(sf)
        h = hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else None
        srcs.append({"file": p.name, "sha256": h})
    meta = {
        "table": out_path.stem,
        "description": description,
        "source": "SInCA (Sistema de Información Cultural de la Argentina, "
                   "Ministerio de Cultura) + INDEC — Cuenta Satélite de Cultura",
        "source_url": "https://datos.cultura.gob.ar/dataset/"
                      "cuenta-satelite-de-cultura-comercio-exterior",
        "source_files": srcs,
        "fetch_date": "2026-05-22",
        "etl_script": "etl/sinca__csc_to_parquet.py",
        "etl_run_date": str(date.today()),
        "licence": "Creative Commons Attribution 4.0 (datos.cultura.gob.ar)",
    }
    if extra:
        meta.update(extra)
    out_path.with_suffix(".meta.json").write_text(
        json.dumps(meta, indent=2, ensure_ascii=False))
    print(f"  ✓ {out_path.with_suffix('.meta.json').relative_to(REPO_ROOT)}")


def maybe_push(df: pd.DataFrame, schema: str, table: str) -> None:
    """Push to MotherDuck if a valid token is available. The token is read from
    the MOTHERDUCK_TOKEN env var, or from a gitignored `.motherduck_token` file
    in the repo root. A MotherDuck token is a JWT — it starts with 'eyJ' and has
    exactly two dots; anything else is rejected so it fails fast. Off by default."""
    import os

    def _jwt(t) -> str:
        t = (t or "").strip()
        return t if (t.startswith("eyJ") and t.count(".") == 2) else ""
    token = _jwt(os.environ.get("MOTHERDUCK_TOKEN"))
    if not token:
        tf = REPO_ROOT / ".motherduck_token"
        token = _jwt(tf.read_text()) if tf.exists() else ""
    if not token:
        print(f"  · MotherDuck push skipped for atana.{schema}.{table} — no valid "
              f"token. Put a real MotherDuck token (a JWT: starts 'eyJ', two dots) "
              f"in {REPO_ROOT}/.motherduck_token, then re-run.")
        return
    con = duckdb.connect(f"md:atana?motherduck_token={token}")
    con.execute(f"CREATE SCHEMA IF NOT EXISTS atana.{schema}")
    con.register("df_data", df)
    con.execute(
        f"CREATE OR REPLACE TABLE atana.{schema}.{table} AS SELECT * FROM df_data")
    n = con.execute(f"SELECT COUNT(*) FROM atana.{schema}.{table}").fetchone()[0]
    print(f"  ✓ Synced atana.{schema}.{table} ({n:,} rows)")


def main() -> None:
    if not SRC.exists():
        raise SystemExit(f"Source folder not found: {SRC}")

    print("Extracting CSC trade values...")
    com = extract_comercio()
    com_path = write_parquet(com, "csc_comercio")
    write_meta(com_path, [SRC / f for f in TRADE_FILES],
               "Argentine cultural foreign trade — exports, imports and trade "
               "balance of cultural goods and services, 2004–2022, in thousands "
               "of pesos (current and constant-2004 prices). Goods (bienes) for "
               "the constant series are derived as (goods+services) − services.",
               extra={"grain": "year × segment × price_basis × flow",
                      "currency": "thousands of Argentine pesos (miles de pesos); "
                                  "no USD column — see currency caveat",
                      "currency_caveat": "Current-peso series is not comparable "
                      "across years (high inflation); use constante_2004. No "
                      "ARS/USD conversion is provided — the official rate diverged "
                      "from real value under the multiple-exchange-rate regime."})

    print("Extracting CSC participation ratios...")
    par = extract_participacion()
    par_path = write_parquet(par, "csc_participacion")
    write_meta(par_path, [SRC / f for f in PARTICIPACION_FILES],
               "Argentine cultural trade as a share of total trade and of "
               "cultural gross output (VBP), 2004–2022. Ratios (0–1).",
               extra={"grain": "year × indicator"})

    maybe_push(com, "sinca", "csc_comercio")
    maybe_push(par, "sinca", "csc_participacion")
    print("Done.")


if __name__ == "__main__":
    main()
