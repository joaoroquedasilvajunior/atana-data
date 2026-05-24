"""ECAD — headline arrecadação / distribuição series → Parquet.

Phase 4c.3 of the Atana Data expansion. The third lens on the FCS *Intellectual
property* domain: cultural-IP *income* actually collected and distributed —
music public-performance royalties. (BCB 4c.1 = the IP-royalty flow; INPI
4c.2 = the IP registration stock; ECAD 4c.3 = IP income.)

⚠️ WHY THIS IS A HAND-TRANSCRIBED HEADLINE SERIES, NOT A DATA INGEST
--------------------------------------------------------------------
ECAD publishes **no machine-readable dataset.** Its Transparência pages carry
the headline figures as page text; the segment-by-segment breakdown is
published only as PNG chart images; the deeper data sits in annual-report PDFs.
There is no CSV/XLSX equivalent of the BCB API or the INPI/SIIC spreadsheets.

So this ETL ingests the **headline series only** — total arrecadação and
distribuição per year — transcribed verbatim from the ECAD Transparência pages
(the inline ROWS below). These are the *rounded* headline values ECAD
publishes (R$ X.X billion); precise-to-the-real figures live in the annual
Balanço Patrimonial PDFs and are out of scope for this headline ingest.
Segment splits are NOT included — they are image-only at source.

SOURCE PAGES (verbatim — the inline data is transcribed from):
    2023: https://www4.ecad.org.br/transparencia-2023/
    2024: https://www4.ecad.org.br/transparencia-2024/
    2025: https://www4.ecad.org.br/transparencia/

OUTPUT:
    raw/ecad/arrecadacao_distribuicao.parquet  (+ .meta.json)
    grain: one row per reference year

Idempotent: inline data → DuckDB COPY to Parquet (no pyarrow); byte-identical
reruns. MotherDuck push gated behind a token (skipped when ATANA_ETL_SKIP_PUSH
is set). Schema: atana.ecad.

Usage:
    python etl/ecad__headline_series_to_parquet.py
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

COLUMNS = [
    "year",
    "arrecadacao_brl_billion",          # total collected — rounded headline figure
    "arrecadacao_yoy_pct",              # stated year-on-year growth
    "distribuicao_brl_billion",         # total distributed — rounded headline figure
    "distribuicao_yoy_pct",             # stated year-on-year growth
    "titulares_contemplados_mil",       # rights-holders paid, thousands
    "digital_services_arrec_share_pct", # Serviços Digitais share of arrecadação
    "source_page",
]

# Transcribed verbatim from the ECAD Transparência pages (see header).
# digital-services share is NULL for 2023 — the 2023 page does not state it as
# a clean % of arrecadação (only streaming growth rates, in text).
ROWS = [
    (2023, 1.6, 17, 1.3, 13, 323, None,
     "https://www4.ecad.org.br/transparencia-2023/"),
    (2024, 1.8, 12, 1.5, 12, 345, 26.0,
     "https://www4.ecad.org.br/transparencia-2024/"),
    (2025, 2.1, 15, 1.7, 10, 345, 33.6,
     "https://www4.ecad.org.br/transparencia/"),
]


def build() -> pd.DataFrame:
    return pd.DataFrame(ROWS, columns=COLUMNS)


def validate(df: pd.DataFrame) -> None:
    print("Validating...")
    assert len(df) == 3, f"expected 3 year rows, got {len(df)}"
    assert list(df["year"]) == [2023, 2024, 2025], "unexpected years"
    # arrecadação ≥ distribuição every year (ECAD keeps 9%, associations 6%)
    assert (df["arrecadacao_brl_billion"] >= df["distribuicao_brl_billion"]).all(), \
        "distribuição exceeds arrecadação — check the figures"
    # monotone-ish growth sanity: both series rise across the 3 years
    assert df["arrecadacao_brl_billion"].is_monotonic_increasing
    assert df["distribuicao_brl_billion"].is_monotonic_increasing
    print(f"  ✓ 3 rows, 2023-2025; arrecadação ≥ distribuição each year; "
          f"both series rising")


def write_parquet(df: pd.DataFrame) -> Path:
    out_path = OUT / "arrecadacao_distribuicao.parquet"
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
        "description": "ECAD music public-performance royalties — headline "
                       "annual series: total arrecadação and distribuição, "
                       "2023-2025. Rounded headline figures transcribed from "
                       "the ECAD Transparência pages (ECAD publishes no "
                       "machine-readable dataset). Segment splits are "
                       "image-only at source and not included.",
        "source": "ECAD — Escritório Central de Arrecadação e Distribuição, "
                  "Transparência pages",
        "source_pages": sorted(df["source_page"].unique().tolist()),
        "fetch_date": "2026-05-23",
        "etl_script": "etl/ecad__headline_series_to_parquet.py",
        "etl_run_date": str(date.today()),
        "licence": "ECAD published figures — public transparency disclosure",
        "grain": "one row per reference year",
        "row_count": int(len(df)),
        "notes": "Values are ECAD's ROUNDED headline figures (R$ X.X billion) "
                 "as published on the Transparência pages — not precise to the "
                 "real. Precise figures are in the annual Balanço Patrimonial "
                 "PDFs. yoy_pct columns are the growth rates ECAD states for "
                 "each year. digital_services share is NULL for 2023 (not "
                 "stated as a clean %). See docs/methodology/ecad_headline.md.",
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
    print("Building atana.ecad.arrecadacao_distribuicao (headline series)...")
    df = build()
    validate(df)
    out_path = write_parquet(df)
    write_meta(out_path, df)
    maybe_push(df, "ecad", "arrecadacao_distribuicao")
    print("Done.")


if __name__ == "__main__":
    main()
