"""ECAD — arrecadação by segmento → Parquet.

Phase 4c.3 of the Atana Data expansion. Second of the four `atana.ecad`
tables: the segmentation of total arrecadação — where the money comes from
across ECAD's collection channels.

v3 (2026-05-29): extended from 2025-only (6 rows) to a **2020–2025 series**
(30 rows; 2023 omitted), sourced from the ECAD Relatórios Anuais 2020 / 2021 /
2022 / 2024 / 2025. Each report carries its own year's six-way split. This is
the series behind the "digital headline" Análise 23 was after — the Serviços
Digitais share runs 18 % (2020) → 23 (2021) → 22.8 (2022) → [~24–25 est. 2023]
→ 26 (2024, first year as the #1 segment) → 33.6 (2025).

WHY 2023 IS MISSING
-------------------
The 2023 arrecadação pie is published only as a JPEG (`Arreacadacao2023.jpeg`)
on the Transparência page — not text-extractable. Only the digital share is
estimable (~24–25 %, bracketed by 22.8 % in 2022 and 26 % in 2024; audio
streaming +57.85 % and video +23.16 % in 2023). 2023 is omitted here rather
than filled with a partial/estimated column; acquiring the 2023 report or the
JPEG would close the one-year gap.

2020 UG / RÁDIO CAVEAT
----------------------
For 2020 the markitdown reading of the pie does not preserve the label↔value
pairing with confidence for Usuários Gerais (12 %) and Rádio (20 %). The
text-confirmed 2020 shares are Televisão 44 %, Shows 5 %, Cinema 1 %, Serviços
Digitais ~18 %. The 2021 structure (UG 20 %, Rádio 11 %) suggests the pairing
may be UG ≈ 20 / Rádio ≈ 12 instead. The values are stored AS READ (UG 12 /
Rádio 20) with the doubt flagged in `notes`; both pairings sum to 100 %.

GRAIN
-----
One row per (year, segmento). 5 years × 6 segments = 30 rows.

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

# Corrected per-year total arrecadação (R$ mi) — from the headline series
# (atana.ecad.arrecadacao_distribuicao, v3 corrected). 2023 omitted.
TOTALS_BRL_MI = {2020: 905.8, 2021: 1086.0, 2022: 1394.0, 2024: 1831.0, 2025: 2105.0}

SRC = {
    2020: "ECAD Relatório Anual 2020",
    2021: "ECAD Relatório Anual 2021/2022",
    2022: "ECAD Relatório Anual 2022",
    2024: "ECAD Relatório Anual 2024 (versão-mercado)",
    2025: "ECAD Relatório Anual 2025 p.10",
}

COLUMNS = [
    "year",
    "segmento",
    "share_pct",
    "valor_brl_mi",       # derived: year total × share / 100
    "notes",
    "source_page",
]

# Shares (%) per (year, segmento), verbatim from each Relatório. Canonical
# segment names match the rest of the corpus ("Show e Eventos", not "Shows").
# year -> {segmento: share_pct}
SHARES = {
    2020: {"Televisão": 44.0, "Serviços Digitais": 18.0, "Usuários Gerais": 12.0,
           "Show e Eventos": 5.0, "Rádio": 20.0, "Cinema": 1.0},
    2021: {"Televisão": 41.0, "Serviços Digitais": 23.0, "Usuários Gerais": 20.0,
           "Show e Eventos": 4.0, "Rádio": 11.0, "Cinema": 1.0},
    2022: {"Televisão": 32.5, "Serviços Digitais": 22.8, "Usuários Gerais": 20.5,
           "Show e Eventos": 13.4, "Rádio": 9.5, "Cinema": 1.3},
    2024: {"Televisão": 25.0, "Serviços Digitais": 26.0, "Usuários Gerais": 19.0,
           "Show e Eventos": 20.0, "Rádio": 8.0, "Cinema": 2.0},
    2025: {"Televisão": 20.4, "Serviços Digitais": 33.6, "Usuários Gerais": 18.1,
           "Show e Eventos": 19.5, "Rádio": 7.1, "Cinema": 1.3},
}

UG_RADIO_2020_NOTE = (
    "2020 markitdown label↔value pairing uncertain for Usuários Gerais / Rádio; "
    "the 2021 structure (UG 20 / Rádio 11) suggests this may be UG≈20 / "
    "Rádio≈12. Stored as read; verify against the printed Relatório 2020 pie.")


def build() -> pd.DataFrame:
    rows = []
    for year, segs in SHARES.items():
        total = TOTALS_BRL_MI[year]
        for seg, share in segs.items():
            note = UG_RADIO_2020_NOTE if (year == 2020 and seg in
                                          ("Usuários Gerais", "Rádio")) else None
            rows.append({
                "year": year,
                "segmento": seg,
                "share_pct": share,
                "valor_brl_mi": round(total * share / 100.0, 2),
                "notes": note,
                "source_page": SRC[year],
            })
    df = pd.DataFrame(rows, columns=COLUMNS)
    df = df.sort_values(["year", "share_pct", "segmento"],
                        ascending=[True, False, True]).reset_index(drop=True)
    df["year"] = df["year"].astype("int32")
    return df


def validate(df: pd.DataFrame) -> None:
    print("Validating...")
    assert len(df) == 30, f"expected 30 rows (5 years × 6), got {len(df)}"
    years = sorted(df["year"].unique().tolist())
    assert years == [2020, 2021, 2022, 2024, 2025], f"unexpected years: {years}"
    print(f"  ✓ 30 rows — 2020, 2021, 2022, 2024, 2025 × six segments (2023 omitted, JPEG-only)")

    for y in years:
        s = round(df.loc[df["year"] == y, "share_pct"].sum(), 2)
        assert s == 100.0, f"{y} shares sum to {s}, not 100.00"
    print(f"  ✓ every year's shares sum to 100.00 %")

    for y in years:
        derived = round(df.loc[df["year"] == y, "valor_brl_mi"].sum(), 0)
        total = round(TOTALS_BRL_MI[y], 0)
        assert abs(derived - total) <= 1.0, \
            f"{y} derived R$ {derived} mi ≠ total R$ {total} mi"
    print(f"  ✓ derived valor_brl_mi reconciles with each year's corrected total")

    # digital-share trajectory must read 18 → 23 → 22.8 → 26 → 33.6
    dig = (df[df["segmento"] == "Serviços Digitais"]
           .set_index("year")["share_pct"].to_dict())
    assert dig == {2020: 18.0, 2021: 23.0, 2022: 22.8, 2024: 26.0, 2025: 33.6}, \
        f"digital trajectory off: {dig}"
    print(f"  ✓ Serviços Digitais trajectory: 18 → 23 → 22.8 → [2023 gap] → 26 → 33.6")

    # 2020 UG/Rádio caveat present
    n = int(df[(df["year"] == 2020) & (df["notes"].notna())].shape[0])
    assert n == 2, f"expected 2 flagged 2020 rows (UG + Rádio), got {n}"
    print(f"  ✓ 2020 UG/Rádio label-pairing caveat flagged (2 rows)")

    assert (df.groupby(["year", "segmento"]).size() == 1).all(), "duplicate (year, segmento)"
    print(f"  ✓ (year, segmento) unique")


def write_parquet(df: pd.DataFrame) -> Path:
    out_path = OUT / "arrecadacao_por_segmento.parquet"
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
        "description": "ECAD arrecadação by segmento, 2020–2025 (2023 omitted — "
                       "JPEG-only at source). Six-way split per year "
                       "(Televisão, Serviços Digitais, Usuários Gerais, Show e "
                       "Eventos, Rádio, Cinema). share_pct verbatim from each "
                       "Relatório Anual; valor_brl_mi derived from the "
                       "corrected per-year total. The digital trajectory "
                       "18→23→22.8→26→33.6 % is the headline series for "
                       "Análise 23.",
        "source": "ECAD Relatórios Anuais 2020 / 2021 / 2022 / 2024 / 2025. "
                  "Hand-transcribed (charts are images at source).",
        "source_pages": sorted(set(df["source_page"].tolist())),
        "fetch_date": "2026-05-29",
        "etl_script": "etl/ecad__arrecadacao_por_segmento_to_parquet.py",
        "etl_run_date": str(date.today()),
        "licence": "ECAD published figures — public transparency disclosure",
        "grain": "one row per (year, segmento)",
        "row_count": int(len(df)),
        "notes": "2023 omitted — the 2023 pie is a JPEG at source; only the "
                 "digital share (~24–25 %, estimated) is recoverable. 2020 UG "
                 "and Rádio shares flagged (label-pairing uncertainty). "
                 "Exact 2021/2022 per-segment R$ absolutes (Relatório 2022) "
                 "reconcile with these shares to within rounding — see "
                 "docs/methodology/ecad_relatorio_anual.md §4.",
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
    print("Building atana.ecad.arrecadacao_por_segmento (v3 — 2020–2025)...")
    df = build()
    validate(df)
    out_path = write_parquet(df)
    write_meta(out_path, df)
    maybe_push(df, "ecad", "arrecadacao_por_segmento")
    print("Done.")


if __name__ == "__main__":
    main()
