"""ECAD — arrecadação by segmento → Parquet.

Phase 4c.3 v2 (2026-05-28). Second of the four tables in the expanded
`atana.ecad` schema. Captures the 2025 segmentation of total arrecadação —
where the money comes from across the six channels ECAD collects from.

WHAT IT IS
----------
For 2025, ECAD reports a six-way split of total arrecadação (R$ 2,105 mi):
Serviços Digitais, Televisão, Show e Eventos, Usuários Gerais, Rádio,
Cinema. The Relatório Anual 2025 p.10 publishes this as a single pie chart;
this ETL captures the six shares and the implied R$ value per segment.

The 2025 digital share (33.6%) is the headline figure that the corpus's
existing `arrecadacao_distribuicao.digital_services_arrec_share_pct` column
also carries — they reconcile by design.

GRAIN
-----
One row per (year, segmento). 2025 only at v2 launch (6 rows). Future
annual reports can be appended without schema change.

SOURCE
------
    ECAD Relatório Anual 2025, p.10 — "Participação dos segmentos na
    arrecadação de 2025" (pie chart).

OUTPUT
------
    raw/ecad/arrecadacao_por_segmento.parquet  (+ .meta.json)

Idempotent: inline data → DuckDB COPY to Parquet (no pyarrow); byte-identical
reruns. MotherDuck push gated behind a token (skipped when ATANA_ETL_SKIP_PUSH
is set). Schema: atana.ecad.

Usage:
    python etl/ecad__arrecadacao_por_segmento_to_parquet.py
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

SOURCE_PAGE = "ECAD Relatório Anual 2025 p.10"

# 2025 total arrecadação from atana.ecad.arrecadacao_distribuicao (Relatório p.12).
TOTAL_2025_BRL_MI = 2105.0

COLUMNS = [
    "year",
    "segmento",
    "share_pct",
    "valor_brl_mi",       # derived: TOTAL × share_pct / 100
    "source_page",
]

# Verbatim from p.10. Order is the pie's clockwise order (digital first),
# preserved for reading convenience; the ETL sorts deterministically.
SEGMENTOS_2025 = [
    ("Serviços Digitais", 33.6),
    ("Televisão",         20.4),
    ("Show e Eventos",    19.5),
    ("Usuários Gerais",   18.1),
    ("Rádio",              7.1),
    ("Cinema",             1.3),
]


def build() -> pd.DataFrame:
    rows = [
        {
            "year": 2025,
            "segmento": seg,
            "share_pct": share,
            "valor_brl_mi": round(TOTAL_2025_BRL_MI * share / 100.0, 2),
            "source_page": SOURCE_PAGE,
        }
        for seg, share in SEGMENTOS_2025
    ]
    df = pd.DataFrame(rows, columns=COLUMNS)
    # Deterministic order: share_pct desc, then segmento alpha to break ties.
    df = df.sort_values(["year", "share_pct", "segmento"],
                        ascending=[True, False, True]).reset_index(drop=True)
    df["year"] = df["year"].astype("int32")
    return df


def validate(df: pd.DataFrame) -> None:
    print("Validating...")
    assert len(df) == 6, f"expected 6 rows, got {len(df)}"
    print(f"  ✓ 6 rows (2025 × six segments)")

    total = round(df["share_pct"].sum(), 2)
    assert total == 100.0, f"shares must sum to 100.00, got {total}"
    print(f"  ✓ shares sum to 100.00 %")

    derived_total = round(df["valor_brl_mi"].sum(), 0)
    # tolerance: rounding adds ≤ 1 R$ mi drift
    assert abs(derived_total - TOTAL_2025_BRL_MI) <= 1.0, \
        f"derived total R$ mi {derived_total} differs from " \
        f"corpus total {TOTAL_2025_BRL_MI} by > 1"
    print(f"  ✓ derived R$ {derived_total:,.0f} mi reconciles with corpus "
          f"total R$ {TOTAL_2025_BRL_MI:,.0f} mi")

    assert df["segmento"].nunique() == 6, "duplicate segments"
    print(f"  ✓ 6 distinct segmentos")


def write_parquet(df: pd.DataFrame) -> Path:
    out_path = OUT / "arrecadacao_por_segmento.parquet"
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
        "description": "ECAD arrecadação by segmento for 2025 — six-way split "
                       "(Serviços Digitais, Televisão, Show e Eventos, "
                       "Usuários Gerais, Rádio, Cinema) of the R$ 2,105 mi "
                       "total ECAD collected in 2025. share_pct is verbatim "
                       "from the Relatório pie chart; valor_brl_mi is derived "
                       "(TOTAL × share / 100). 2025 only at v2 launch.",
        "source": "ECAD Relatório Anual 2025 (PDF, 32 pp.), p.10 — "
                  "'Participação dos segmentos na arrecadação de 2025'.",
        "source_pages": [SOURCE_PAGE],
        "fetch_date": "2026-05-28",
        "etl_script": "etl/ecad__arrecadacao_por_segmento_to_parquet.py",
        "etl_run_date": str(date.today()),
        "licence": "ECAD published figures — public transparency disclosure",
        "grain": "one row per (year, segmento)",
        "row_count": int(len(df)),
        "notes": "Digital share 33.6 % matches the headline-series column "
                 "`digital_services_arrec_share_pct` for 2025 by design.",
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
    print("Building atana.ecad.arrecadacao_por_segmento...")
    df = build()
    validate(df)
    out_path = write_parquet(df)
    write_meta(out_path, df)
    maybe_push(df, "ecad", "arrecadacao_por_segmento")
    print("Done.")


if __name__ == "__main__":
    main()
