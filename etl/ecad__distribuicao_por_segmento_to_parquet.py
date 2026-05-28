"""ECAD — distribuição by segmento → Parquet.

Phase 4c.3 v2 (2026-05-28). Third of the four tables in the expanded
`atana.ecad` schema. Captures the 2025 segmentation of total distribuição —
how the R$ 1,725 M ECAD paid out broke down across the thirteen channels.

WHY IT MATTERS — THE ARRECADAÇÃO ≠ DISTRIBUIÇÃO GAP
---------------------------------------------------
The arrecadação pie (six segments, see arrecadacao_por_segmento) tells you
where platforms PAY ECAD. The distribuição pie (this table, thirteen
segments) tells you what reaches titulares. They are not the same:
- arrecadação "Serviços Digitais" share 2025 = 33.6 %
- distribuição "pure digital" share 2025 ≈ 24.1 %
  (Streaming de Vídeo 13.43 + Streaming de Audio 10.11 + Serviços Digitais 0.59)
The ≈ 9.5 pp gap is absorbed by ECAD operating cost (9 %, see headline table),
timing lag, and deferred allocation across years. The `is_digital` boolean
here marks the three pure-digital distribution channels — Rádios+DG and
TV aberta+DG are MIXED (part terrestrial, part digital) and stay
is_digital=FALSE; the share inside them isn't separable from the source.

GRAIN
-----
One row per (year, segmento). 2025 only at v2 launch (13 rows).

THE 1.25 % GAP
--------------
The thirteen named segments in the Relatório 2025 p.14 pie sum to 98.75 %.
The remaining 1.25 % is not detailed on the page — likely "outros" or
rounding. NOT silently allocated; flagged in the row's `notes` column and in
the methodology.

SOURCE
------
    ECAD Relatório Anual 2025, p.14 — "Distribuição por segmento" (pie chart).

OUTPUT
------
    raw/ecad/distribuicao_por_segmento.parquet  (+ .meta.json)

Idempotent: inline data → DuckDB COPY to Parquet (no pyarrow); byte-identical
reruns. MotherDuck push gated behind a token (skipped when ATANA_ETL_SKIP_PUSH
is set). Schema: atana.ecad.

Usage:
    python etl/ecad__distribuicao_por_segmento_to_parquet.py
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

SOURCE_PAGE = "ECAD Relatório Anual 2025 p.14"

# 2025 total distribuição from atana.ecad.arrecadacao_distribuicao (Relatório p.13).
TOTAL_2025_BRL = 1_725_497_001.0

# Pure-digital channels (per the corpus convention — see header).
DIGITAL_SEGMENTS = {"Streaming de Vídeo", "Streaming de Audio", "Serviços Digitais"}

COLUMNS = [
    "year",
    "segmento",
    "share_pct",
    "valor_brl",         # derived: TOTAL × share_pct / 100
    "is_digital",        # TRUE only for the three pure-digital channels
    "notes",
    "source_page",
]

# Verbatim from p.14. Order is decreasing share — the pie's natural read.
SEGMENTOS_2025 = [
    ("Rádios + DG",                  18.50),
    ("TV aberta + DG",               15.56),
    ("Shows",                        14.72),
    ("Streaming de Vídeo",           13.43),
    ("TV Fechada",                   11.10),
    ("Streaming de Audio",           10.11),
    ("Sonorização Ambiental",         4.25),
    ("Casas de Festas e Diversão",    3.21),
    ("Música ao Vivo",                3.06),
    ("Carnaval",                      1.92),
    ("Cinema",                        1.80),
    ("Serviços Digitais",             0.59),
    ("Festa Junina",                  0.50),
]

GAP_NOTE = ("Thirteen named segments sum to 98.75 %; the remaining 1.25 % is "
            "not detailed in the Relatório 2025 p.14 pie chart — likely "
            "'outros' or rounding. Documented, not allocated.")


def build() -> pd.DataFrame:
    # Apply the gap note ONLY to the smallest-share row to keep notes sparse
    # but discoverable in any query that filters by segmento (the gap is a
    # property of the chart as a whole, not of any one segment).
    smallest = min(SEGMENTOS_2025, key=lambda x: x[1])[0]
    rows = [
        {
            "year": 2025,
            "segmento": seg,
            "share_pct": share,
            "valor_brl": round(TOTAL_2025_BRL * share / 100.0, 2),
            "is_digital": seg in DIGITAL_SEGMENTS,
            "notes": GAP_NOTE if seg == smallest else None,
            "source_page": SOURCE_PAGE,
        }
        for seg, share in SEGMENTOS_2025
    ]
    df = pd.DataFrame(rows, columns=COLUMNS)
    df = df.sort_values(["year", "share_pct", "segmento"],
                        ascending=[True, False, True]).reset_index(drop=True)
    df["year"] = df["year"].astype("int32")
    return df


def validate(df: pd.DataFrame) -> None:
    print("Validating...")
    assert len(df) == 13, f"expected 13 rows, got {len(df)}"
    print(f"  ✓ 13 rows (2025 × thirteen segments)")

    total = round(df["share_pct"].sum(), 2)
    assert total == 98.75, f"shares must sum to 98.75, got {total}"
    print(f"  ✓ shares sum to 98.75 % — the 1.25 % gap is the documented anomaly")

    digital = df[df["is_digital"]].copy()
    assert len(digital) == 3, f"expected 3 pure-digital rows, got {len(digital)}"
    assert set(digital["segmento"]) == DIGITAL_SEGMENTS, \
        "is_digital flag attached to wrong segments"
    digital_share = round(digital["share_pct"].sum(), 2)
    # Should be 13.43 + 10.11 + 0.59 = 24.13 — matches CLAUDE.md v30 (24.1 %)
    assert abs(digital_share - 24.13) <= 0.01, \
        f"pure-digital share {digital_share} ≠ 24.13"
    print(f"  ✓ pure-digital share = {digital_share} % "
          f"(Streaming Vídeo + Audio + Serviços Digitais)")

    derived_total = df["valor_brl"].sum()
    expected_98_75 = TOTAL_2025_BRL * 0.9875
    # tolerance: rounding adds ≤ R$ 50 drift across 13 rounded values
    assert abs(derived_total - expected_98_75) <= 50.0, \
        f"derived R$ sum {derived_total:,.0f} differs from 98.75 % × total " \
        f"({expected_98_75:,.0f}) by > R$ 50"
    print(f"  ✓ derived R$ {derived_total:,.0f} reconciles with 98.75 % × "
          f"total R$ {TOTAL_2025_BRL:,.0f}")

    # Gap note attached exactly once (on the smallest-share row).
    n_notes = int(df["notes"].notna().sum())
    assert n_notes == 1, f"expected 1 row with the gap note, got {n_notes}"
    print(f"  ✓ 1.25 % gap note attached to the smallest-share row")

    assert df["segmento"].nunique() == 13, "duplicate segments"
    print(f"  ✓ 13 distinct segmentos")


def write_parquet(df: pd.DataFrame) -> Path:
    out_path = OUT / "distribuicao_por_segmento.parquet"
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
        "description": "ECAD distribuição by segmento for 2025 — thirteen-way "
                       "split of R$ 1,725,497,001 paid out across "
                       "Rádios+DG, TV aberta+DG, Shows, the two Streamings, "
                       "TV Fechada, Sonorização Ambiental, etc. share_pct "
                       "verbatim from the Relatório pie chart; valor_brl "
                       "derived (TOTAL × share / 100). is_digital marks the "
                       "three pure-digital channels only (Streaming Vídeo, "
                       "Streaming Audio, Serviços Digitais); Rádios+DG and "
                       "TV aberta+DG are MIXED and stay FALSE.",
        "source": "ECAD Relatório Anual 2025 (PDF, 32 pp.), p.14 — "
                  "'Distribuição por segmento'.",
        "source_pages": [SOURCE_PAGE],
        "fetch_date": "2026-05-28",
        "etl_script": "etl/ecad__distribuicao_por_segmento_to_parquet.py",
        "etl_run_date": str(date.today()),
        "licence": "ECAD published figures — public transparency disclosure",
        "grain": "one row per (year, segmento)",
        "row_count": int(len(df)),
        "notes": "The thirteen named segments sum to 98.75 %; the 1.25 % gap "
                 "is the documented anomaly — not silently allocated. "
                 "Methodology §4 carries the explanation. Pure-digital share "
                 "= 24.13 % (reconciles with CLAUDE.md v30's 24.1 % figure for "
                 "Atana Note context).",
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
    print("Building atana.ecad.distribuicao_por_segmento...")
    df = build()
    validate(df)
    out_path = write_parquet(df)
    write_meta(out_path, df)
    maybe_push(df, "ecad", "distribuicao_por_segmento")
    print("Done.")


if __name__ == "__main__":
    main()
