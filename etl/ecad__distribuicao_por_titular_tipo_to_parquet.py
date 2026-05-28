"""ECAD — distribuição by titular type (national vs foreign) → Parquet.

Phase 4c.3 v2 (2026-05-28). Fourth of the four tables in the expanded
`atana.ecad` schema. Captures the 2021–2025 split of distribuição between
**nacional** (titulares cadastrados no Brasil) and **estrangeiro** (foreign
titulares), separately for the **autoral** part (composers, lyricists) and
the **conexa** part (performers, phonogram producers).

WHY IT MATTERS
--------------
The headline reading "≈ 78 % nacional / 22 % estrangeiro" published by ECAD
splits into a more nuanced four-corner story:
- Autoral (composers): 2021 76/24 → 2025 77/23 — very stable, slight tilt
  upward in 2025.
- Conexa (performers + phonogram producers): more volatile, 2021 79/21 →
  2023 82/18 (a peak in national share) → 2025 79/21 (settled back).

Crucially, "nacional" here is a *cadastral* notion — a titular registered
in Brazil. This includes the Brazilian *editoras* / *gravadoras* that are
subsidiaries of foreign majors (Universal Music Brasil, Sony Music Brasil,
Warner Music Brasil etc.) — they redistribute upstream to their parent
companies. The 77 % "nacional" share therefore does NOT equal "77 % of
royalties go to Brazilian creators"; that interpretation requires further
analysis of the cadastral composition, scoped in Análise 21.

GRAIN
-----
One row per (year, parte). 2021–2025 × {autoral, conexa} = 10 rows.

SOURCE
------
    ECAD Relatório Anual 2025, pp.13–14 — the two stacked-bar charts.

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

SOURCE_PAGES = "ECAD Relatório Anual 2025 pp.13–14"

COLUMNS = [
    "year",
    "parte",                 # "autoral" / "conexa"
    "nacional_pct",
    "estrangeiro_pct",
    "source_page",
]

# Verbatim from pp.13–14 (the two stacked-bar charts).
AUTORAL = [    # (year, nacional, estrangeiro)
    (2021, 76, 24),
    (2022, 76, 24),
    (2023, 75, 25),
    (2024, 75, 25),
    (2025, 77, 23),
]
CONEXA = [
    (2021, 79, 21),
    (2022, 78, 22),
    (2023, 82, 18),
    (2024, 80, 20),
    (2025, 79, 21),
]


def build() -> pd.DataFrame:
    rows = []
    for y, nac, est in AUTORAL:
        rows.append({"year": y, "parte": "autoral",
                     "nacional_pct": float(nac), "estrangeiro_pct": float(est),
                     "source_page": SOURCE_PAGES})
    for y, nac, est in CONEXA:
        rows.append({"year": y, "parte": "conexa",
                     "nacional_pct": float(nac), "estrangeiro_pct": float(est),
                     "source_page": SOURCE_PAGES})
    df = pd.DataFrame(rows, columns=COLUMNS)
    df = df.sort_values(["year", "parte"]).reset_index(drop=True)
    df["year"] = df["year"].astype("int32")
    return df


def validate(df: pd.DataFrame) -> None:
    print("Validating...")
    assert len(df) == 10, f"expected 10 rows, got {len(df)}"
    print(f"  ✓ 10 rows (5 years × 2 partes)")

    years = sorted(df["year"].unique().tolist())
    assert years == [2021, 2022, 2023, 2024, 2025], f"unexpected years: {years}"
    print(f"  ✓ years 2021–2025")

    partes = sorted(df["parte"].unique().tolist())
    assert partes == ["autoral", "conexa"], f"unexpected partes: {partes}"
    print(f"  ✓ partes ∈ {{autoral, conexa}}")

    # Identity: nacional + estrangeiro = 100 for every (year, parte)
    df["sum"] = df["nacional_pct"] + df["estrangeiro_pct"]
    off = df[df["sum"] != 100.0]
    assert off.empty, \
        f"nacional + estrangeiro ≠ 100 for: " \
        f"{off[['year','parte','sum']].to_dict('records')}"
    print(f"  ✓ nacional_pct + estrangeiro_pct = 100 for all 10 rows")

    # Each (year, parte) appears exactly once
    dup = df.groupby(["year", "parte"]).size()
    assert (dup == 1).all(), "duplicate (year, parte) rows"
    print(f"  ✓ (year, parte) is unique")


def write_parquet(df: pd.DataFrame) -> Path:
    df = df.drop(columns=["sum"], errors="ignore")
    out_path = OUT / "distribuicao_por_titular_tipo.parquet"
    con = duckdb.connect()
    con.register("df_data", df)
    con.execute(
        f"COPY df_data TO '{out_path}' (FORMAT PARQUET, COMPRESSION ZSTD)")
    size_kb = out_path.stat().st_size / 1024
    print(f"  ✓ {out_path.relative_to(REPO_ROOT)} — {len(df)} rows, "
          f"{size_kb:.1f} KB")
    return out_path


def write_meta(out_path: Path, df: pd.DataFrame) -> None:
    meta = {
        "table": out_path.stem,
        "schema": "ecad",
        "description": "ECAD distribuição by titular type — annual split of "
                       "distribuição between titulares cadastrados no Brasil "
                       "('nacional') and 'estrangeiro', 2021–2025, for the "
                       "autoral and conexa partes separately. 10 rows = 5 "
                       "years × 2 partes. Source: Relatório Anual 2025, "
                       "pp.13–14 (two stacked-bar charts).",
        "source": "ECAD Relatório Anual 2025 (PDF, 32 pp.), pp.13–14.",
        "source_pages": [SOURCE_PAGES],
        "fetch_date": "2026-05-28",
        "etl_script": "etl/ecad__distribuicao_por_titular_tipo_to_parquet.py",
        "etl_run_date": str(date.today()),
        "licence": "ECAD published figures — public transparency disclosure",
        "grain": "one row per (year, parte)",
        "row_count": int(len(df.drop(columns=['sum'], errors='ignore'))),
        "notes": "'nacional' is a CADASTRAL category — a titular registered "
                 "in Brazil — and therefore includes editoras/gravadoras that "
                 "are Brazilian subsidiaries of foreign majors (Universal "
                 "Music Brasil, Sony Music Brasil, Warner Music Brasil, etc.) "
                 "which redistribute upstream. The 77 % 'nacional' share is "
                 "not equivalent to '77 % of royalties go to Brazilian "
                 "creators'. See Análise 21 for the geography drilldown and "
                 "methodology §3 for the caveat.",
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
    df = df.drop(columns=["sum"], errors="ignore")
    con = duckdb.connect(f"md:atana?motherduck_token={token}")
    con.execute(f"CREATE SCHEMA IF NOT EXISTS atana.{schema}")
    con.register("df_data", df)
    con.execute(
        f"CREATE OR REPLACE TABLE atana.{schema}.{table} AS SELECT * FROM df_data")
    n = con.execute(f"SELECT COUNT(*) FROM atana.{schema}.{table}").fetchone()[0]
    print(f"  ✓ Synced atana.{schema}.{table} ({n} rows)")


def main() -> None:
    print("Building atana.ecad.distribuicao_por_titular_tipo...")
    df = build()
    validate(df)
    out_path = write_parquet(df)
    write_meta(out_path, df)
    maybe_push(df, "ecad", "distribuicao_por_titular_tipo")
    print("Done.")


if __name__ == "__main__":
    main()
