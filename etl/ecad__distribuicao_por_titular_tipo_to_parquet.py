"""ECAD — distribuição by titular type (national vs foreign) → Parquet.

Phase 4c.3 of the Atana Data expansion. Fourth of the four `atana.ecad`
tables. The 2016–2025 split of distribuição between **nacional** (titulares
cadastrados no Brasil) and **estrangeiro**, separately for the **autoral**
part (composers, lyricists) and the **conexa** part (performers, phonogram
producers).

v3 (2026-05-29): extended back from 2021–2025 to **2016–2025** using the
autoral/conexa nacional series in the ECAD Relatório Anual 2020 (which carries
2016–2020). 20 rows = 10 years × 2 partes.

WHY IT MATTERS
--------------
The headline "≈ 78 % nacional" published by ECAD splits into a four-corner
story and, importantly, is NOT stable over time:
- Autoral nacional drifts up: 68 % (2016) → 76 % (2019–2022) → 77 % (2025).
- Conexa nacional is volatile: 79 % (2016) → 89 % (2018, peak) → 75 % (2020,
  pandemic trough) → 82 % (2023) → 79 % (2025).

The *overall* (not autoral/conexa) repertoire nacional share rose 65 % (2023,
Transparência) → ≈ 78 % (2025) — a +13 pp move in two years. That overall
figure is a different aggregate and is documented in the methodology, not in
this table (which is split by parte).

⚠️ "Nacional" is a CADASTRAL category — a titular registered in Brazil — and
includes the Brazilian editoras/gravadoras that are subsidiaries of foreign
majors (Universal/Sony/Warner Music Brasil), which redistribute upstream. So
"77 % nacional" ≠ "77 % of royalties reach Brazilian creators". See Análise 21.

GRAIN
-----
One row per (year, parte). 2016–2025 × {autoral, conexa} = 20 rows.

SOURCE
------
    2016–2020: ECAD Relatório Anual 2020 (autoral/conexa nacional series).
    2021–2025: ECAD Relatório Anual 2025, pp.13–14 (stacked-bar charts).

OUTPUT
------
    raw/ecad/distribuicao_por_titular_tipo.parquet  (+ .meta.json)

Idempotent: inline data → DuckDB COPY to Parquet (no pyarrow); byte-identical
reruns. MotherDuck push gated behind a token (skipped when ATANA_ETL_SKIP_PUSH
is set). Schema: atana.ecad.

Usage:
    python etl/ecad__distribuicao_por_titular_tipo_to_parquet.py
"""
import hashlib
import json
import os
from datetime import date
from pathlib import Path

import duckdb
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parent.parent
OUT = REPO_ROOT / "raw" / "ecad"
OUT.mkdir(parents=True, exist_ok=True)

R2020 = "ECAD Relatório Anual 2020"
R2025 = "ECAD Relatório Anual 2025 pp.13–14"

COLUMNS = [
    "year",
    "parte",                 # "autoral" / "conexa"
    "nacional_pct",
    "estrangeiro_pct",
    "source_page",
]

# nacional_pct per (parte, year). estrangeiro = 100 - nacional.
# 2016–2020 from Relatório 2020; 2021–2025 from Relatório 2025.
AUTORAL_NACIONAL = {2016: 68, 2017: 74, 2018: 75, 2019: 76, 2020: 76,
                    2021: 76, 2022: 76, 2023: 75, 2024: 75, 2025: 77}
CONEXA_NACIONAL = {2016: 79, 2017: 86, 2018: 89, 2019: 80, 2020: 75,
                   2021: 79, 2022: 78, 2023: 82, 2024: 80, 2025: 79}


def _src(year: int) -> str:
    return R2020 if year <= 2020 else R2025


def build() -> pd.DataFrame:
    rows = []
    for parte, series in (("autoral", AUTORAL_NACIONAL), ("conexa", CONEXA_NACIONAL)):
        for year, nac in series.items():
            rows.append({
                "year": year,
                "parte": parte,
                "nacional_pct": float(nac),
                "estrangeiro_pct": float(100 - nac),
                "source_page": _src(year),
            })
    df = pd.DataFrame(rows, columns=COLUMNS)
    df = df.sort_values(["year", "parte"]).reset_index(drop=True)
    df["year"] = df["year"].astype("int32")
    return df


def validate(df: pd.DataFrame) -> None:
    print("Validating...")
    assert len(df) == 20, f"expected 20 rows (10 years × 2 partes), got {len(df)}"
    years = sorted(df["year"].unique().tolist())
    assert years == list(range(2016, 2026)), f"unexpected years: {years}"
    print(f"  ✓ 20 rows — 2016–2025 × {{autoral, conexa}}")

    partes = sorted(df["parte"].unique().tolist())
    assert partes == ["autoral", "conexa"], f"unexpected partes: {partes}"
    print(f"  ✓ partes ∈ {{autoral, conexa}}")

    s = df["nacional_pct"] + df["estrangeiro_pct"]
    assert (s == 100.0).all(), "nacional + estrangeiro ≠ 100 in some row"
    print(f"  ✓ nacional_pct + estrangeiro_pct = 100 for all 20 rows")

    # boundary sanity: 2020 from Relatório 2020 and 2021 from Relatório 2025
    a2020 = df[(df.year == 2020) & (df.parte == "autoral")]["nacional_pct"].iloc[0]
    a2021 = df[(df.year == 2021) & (df.parte == "autoral")]["nacional_pct"].iloc[0]
    assert a2020 == 76 and a2021 == 76, "autoral nacional 2020/2021 should both be 76"
    print(f"  ✓ source boundary consistent (autoral nacional 2020=76 [R.2020], 2021=76 [R.2025])")

    assert (df.groupby(["year", "parte"]).size() == 1).all(), "duplicate (year, parte)"
    print(f"  ✓ (year, parte) unique")


def write_parquet(df: pd.DataFrame) -> Path:
    out_path = OUT / "distribuicao_por_titular_tipo.parquet"
    con = duckdb.connect()
    con.register("df_data", df)
    con.execute(f"COPY df_data TO '{out_path}' (FORMAT PARQUET, COMPRESSION ZSTD)")
    size_kb = out_path.stat().st_size / 1024
    print(f"  ✓ {out_path.relative_to(REPO_ROOT)} — {len(df)} rows, {size_kb:.1f} KB")
    return out_path


def write_meta(out_path: Path, df: pd.DataFrame) -> None:
    meta = {
        "table": out_path.stem,
        "schema": "ecad",
        "description": "ECAD distribuição by titular type — annual split of "
                       "distribuição between titulares cadastrados no Brasil "
                       "('nacional') and 'estrangeiro', 2016–2025, for the "
                       "autoral and conexa partes separately. 20 rows = 10 "
                       "years × 2 partes. v3 extended back to 2016 using "
                       "Relatório 2020.",
        "source": "ECAD Relatório Anual 2020 (2016–2020) + Relatório Anual "
                  "2025 pp.13–14 (2021–2025).",
        "source_pages": sorted(set(df["source_page"].tolist())),
        "fetch_date": "2026-05-29",
        "etl_script": "etl/ecad__distribuicao_por_titular_tipo_to_parquet.py",
        "etl_run_date": str(date.today()),
        "licence": "ECAD published figures — public transparency disclosure",
        "grain": "one row per (year, parte)",
        "row_count": int(len(df)),
        "notes": "'nacional' is a CADASTRAL category — includes Brazilian "
                 "subsidiaries of foreign majors — so it is not equivalent to "
                 "'royalties reaching Brazilian creators'. The overall (not "
                 "autoral/conexa) repertoire nacional share rose 65% (2023, "
                 "Transparência) → ≈78% (2025); that aggregate is documented in "
                 "the methodology, not tabled here. See Análise 21 and "
                 "docs/methodology/ecad_relatorio_anual.md §3.",
    }
    out_path.with_suffix(".meta.json").write_text(
        json.dumps(meta, indent=2, ensure_ascii=False))
    print(f"  ✓ {out_path.with_suffix('.meta.json').relative_to(REPO_ROOT)}")


def maybe_push(df: pd.DataFrame, schema: str, table: str) -> None:
    """Push to MotherDuck if a valid JWT token is available.

    Skipped entirely when ATANA_ETL_SKIP_PUSH is set — for build-only / sandbox
    runs where the Parquet is produced but the sync stays with João.
    """
    if os.environ.get("ATANA_ETL_SKIP_PUSH"):
        print(f"  · push skipped for atana.{schema}.{table} (ATANA_ETL_SKIP_PUSH)")
        return

    def _jwt(t) -> str:
        t = (t or "").strip()
        return t if (t.startswith("eyJ") and t.count(".") == 2) else ""
    token = _jwt(os.environ.get("MOTHERDUCK_TOKEN"))
    if not token:
        tf = REPO_ROOT / ".motherduck_token"
        token = _jwt(tf.read_text()) if tf.exists() else ""
    if not token:
        print(f"  · MotherDuck push skipped for atana.{schema}.{table} — no "
              f"valid token.")
        return
    con = duckdb.connect(f"md:atana?motherduck_token={token}")
    con.execute(f"CREATE SCHEMA IF NOT EXISTS atana.{schema}")
    con.register("df_data", df)
    con.execute(
        f"CREATE OR REPLACE TABLE atana.{schema}.{table} AS SELECT * FROM df_data")
    n = con.execute(f"SELECT COUNT(*) FROM atana.{schema}.{table}").fetchone()[0]
    print(f"  ✓ Synced atana.{schema}.{table} ({n} rows)")


def main() -> None:
    print("Building atana.ecad.distribuicao_por_titular_tipo (v3 — 2016–2025)...")
    df = build()
    validate(df)
    out_path = write_parquet(df)
    write_meta(out_path, df)
    maybe_push(df, "ecad", "distribuicao_por_titular_tipo")
    print("Done.")


if __name__ == "__main__":
    main()
