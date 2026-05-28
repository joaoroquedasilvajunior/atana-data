"""ECAD — arrecadação / distribuição headline series → Parquet.

Phase 4c.3 of the Atana Data expansion (v2 — re-ingest 2026-05-28). The third
lens on the FCS *Intellectual property* domain: cultural-IP *income* actually
collected and distributed — music public-performance royalties. (BCB 4c.1 =
the IP-royalty flow; INPI 4c.2 = the IP registration stock; ECAD 4c.3 = IP
income, in four tables.)

v2 EXPANSION — what changed
---------------------------
v1 (2026-05-23) carried 3 rows (2023–2025) transcribed from the ECAD
Transparência pages. v2 extends the headline series to **8 rows (2018–2025)**
sourced from the 2025 ECAD Annual Report (PDF, 32 pp.), and ships three new
sibling tables that v1 omitted (segment breakdowns, national-vs-foreign
distribution mix). See:
    etl/ecad__arrecadacao_por_segmento_to_parquet.py
    etl/ecad__distribuicao_por_segmento_to_parquet.py
    etl/ecad__distribuicao_por_titular_tipo_to_parquet.py

This file owns the headline series only.

⚠️ WHY STILL HAND-TRANSCRIBED
-----------------------------
ECAD publishes no machine-readable dataset. The Annual Report data sits inside
a 32-page PDF (converted via markitdown for transcription). Charts are PNG
images; tables are reconstructable but not directly exported. So this ETL
inlines values verbatim from the PDF and the Transparência pages.

SCHEMA BREAK FROM v1
--------------------
v1 used `arrecadacao_brl_billion` / `distribuicao_brl_billion` (rounded R$ bi).
v2 uses `arrecadacao_brl_mi` (R$ mi from p.12) and `distribuicao_brl` (exact
R$ from p.13). YoY columns are now *computed in-script* from the values
themselves (v1 carried the headline-stated YoY); see §1.2 of the
expansion prompt for why — the markitdown conversion scrambled YoY labels
in the source PDF table, so deriving from values is more reliable.

CENTRAL CAVEATS (documented in docs/methodology/ecad_relatorio_anual.md)
----------------------------------------------------------------------
- Distribuição values for 2018–2020 are NULL (not in source).
- 2022 distribuição of R$ 901,588,853 implies a −26.8% YoY versus 2021,
  which contradicts the arrecadação pattern (+24% in 2022). The 2021
  caption "+36.66% vs 2020" implies 2020 ≈ R$ 901.6 mi — equal to the value
  labelled "2022". So either (a) the figure is correct and ECAD had a one-off
  distribution drop in 2022 (pandemic reprocessing), or (b) markitdown
  swapped the 2020 and 2022 labels and 2022 is missing from the chart. v2
  preserves the value as transcribed and flags it in `notes`. Verify against
  the PDF when feasible.
- `custo_operacional_pct` = 9.0 is stated for 2025 only; the report calls
  the rate "estável" but does not give per-year figures, so other years are
  NULL.

SOURCE PAGES
------------
    Arrecadação 2018–2025:   ECAD Relatório Anual 2025, p.12 (verbatim)
    Distribuição 2021–2025:  ECAD Relatório Anual 2025, p.13 (verbatim)
    Titulares 2023–2025:     ECAD Transparência pages + Relatório 2025
    Digital share 2024–2025: ECAD Relatório 2025, segment breakdown p.10
    Custo operacional 2025:  ECAD Relatório 2025, p.18

OUTPUT
------
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

SOURCE_REPORT = "ECAD Relatório Anual 2025"
SOURCE_TRANSP = "https://www4.ecad.org.br/transparencia/"

COLUMNS = [
    "year",
    "arrecadacao_brl_mi",                   # R$ mi correntes — Relatório 2025 p.12
    "arrecadacao_yoy_pct",                  # computed from arrecadacao values
    "distribuicao_brl",                     # R$ correntes exato — Relatório 2025 p.13
    "distribuicao_yoy_pct",                 # computed from distribuicao values
    "titulares_contemplados_mil",           # rights-holders paid, thousands
    "digital_services_arrec_share_pct",     # Serviços Digitais share of arrecadação
    "custo_operacional_pct",                # ECAD operating cost as % of arrecadação
    "notes",                                # caveats per-row
    "source_page",
]

# Verbatim from the ECAD Relatório Anual 2025 (PDF, 32 pp.) — see header.
# Tuple order: (year, arrecadacao_brl_mi, distribuicao_brl, titulares_contemplados_mil,
#               digital_services_arrec_share_pct, custo_operacional_pct, notes, source_page)
# arrecadacao_yoy_pct and distribuicao_yoy_pct are computed in build().
ROWS = [
    (2018,  905.81,           None, None, None, None,
     None,                                              f"{SOURCE_REPORT} p.12"),
    (2019, 1106.0,             None, None, None, None,
     None,                                              f"{SOURCE_REPORT} p.12"),
    (2020, 1086.0,             None, None, None, None,
     "distribuicao for 2020 not in source chart; the 2021 caption implies "
     "≈ R$ 901.6 mi — see notes column for 2022 and methodology §3.",
                                                        f"{SOURCE_REPORT} p.12"),
    (2021, 1121.0,    1_232_071_471.0, None, None, None,
     "Relatório caption notes +36.66% vs 2020 — implied 2020 ≈ R$ 901.6 mi.",
                                                        f"{SOURCE_REPORT} pp.12–13"),
    (2022, 1394.0,      901_588_853.0, None, None, None,
     "⚠ 2022 distribuição value transcribed verbatim implies a −26.8% YoY "
     "vs 2021, contradicting the +24.4% arrecadação growth. Two explanations: "
     "(a) genuine one-off 2022 distribution drop (post-pandemic reprocessing) — "
     "the report itself does not annotate it as such; (b) markitdown swap of "
     "the 2020 and 2022 labels in the PDF table — the figure 901,588,853 "
     "matches the implied 2020 baseline from the 2021 +36.66% caption almost "
     "exactly. NEEDS PDF VERIFICATION before downstream use.",
                                                        f"{SOURCE_REPORT} pp.12–13"),
    (2023, 1631.0,    1_390_932_884.0,  323, None, None,
     None,                                              f"{SOURCE_REPORT} pp.12–13"),
    (2024, 1831.0,    1_569_374_513.0,  345, 26.0, None,
     None,                                              f"{SOURCE_REPORT} pp.12–13"),
    (2025, 2105.0,    1_725_497_001.0,  345, 33.6,  9.0,
     "9% custo operacional figure stated as 'estável' in the report; the "
     "earlier years are NULL because per-year custo is not given.",
                                                        f"{SOURCE_REPORT} pp.12–13"),
]


def build() -> pd.DataFrame:
    # ROWS shape: (year, arrec, distrib, titulares, digi, custo, notes, source_page)
    df = pd.DataFrame(
        [{
            "year": r[0],
            "arrecadacao_brl_mi": r[1],
            "arrecadacao_yoy_pct": None,
            "distribuicao_brl": r[2],
            "distribuicao_yoy_pct": None,
            "titulares_contemplados_mil": r[3],
            "digital_services_arrec_share_pct": r[4],
            "custo_operacional_pct": r[5],
            "notes": r[6],
            "source_page": r[7],
        } for r in ROWS],
        columns=COLUMNS,
    ).sort_values("year").reset_index(drop=True)

    # YoY computed in-script — preserves data integrity given v1's transcribed
    # YoY labels were scrambled by markitdown (see header).
    df["arrecadacao_yoy_pct"] = (
        df["arrecadacao_brl_mi"].pct_change() * 100
    ).round(2)
    df["distribuicao_yoy_pct"] = (
        df["distribuicao_brl"].pct_change() * 100
    ).round(2)

    # Cast columns to clean nullable types for the Parquet
    df["year"] = df["year"].astype("int32")
    df["titulares_contemplados_mil"] = df["titulares_contemplados_mil"].astype("Int32")
    return df


def validate(df: pd.DataFrame) -> None:
    print("Validating...")
    assert len(df) == 8, f"expected 8 year rows, got {len(df)}"
    years = list(df["year"])
    assert years == list(range(2018, 2026)), f"unexpected year sequence: {years}"
    print(f"  ✓ 8 rows, 2018–2025 contiguous")

    # Arrecadação YoY matches the prompt's transcribed labels (sanity)
    expected_arrec_yoy = {
        2019:  22.1,   # 1106/905.81 - 1
        2020:  -1.8,
        2021:   3.2,
        2022:  24.4,
        2023:  17.0,
        2024:  12.3,
        2025:  15.0,
    }
    for y, exp in expected_arrec_yoy.items():
        got = float(df.loc[df["year"] == y, "arrecadacao_yoy_pct"].iloc[0])
        # tolerance 0.2 pp — rounded headline values produce small drift
        assert abs(got - exp) <= 0.2, \
            f"arrecadação YoY {y}: computed {got:.2f} vs expected {exp:.2f}"
    print(f"  ✓ arrecadação YoYs (computed) reconcile with PDF caption labels within ±0.2 pp")

    # Distribuição values: 5 rows non-null (2021–2025), 3 NULL (2018–2020)
    nn = df["distribuicao_brl"].notna()
    assert int(nn.sum()) == 5, f"expected 5 distribuicao rows, got {int(nn.sum())}"
    assert list(df.loc[nn, "year"]) == [2021, 2022, 2023, 2024, 2025], \
        "distribuicao non-null years not 2021–2025"
    print(f"  ✓ distribuição present for 2021–2025; 2018–2020 NULL (not in source)")

    # The 2022 anomaly is preserved with the documented caveat in notes
    assert "⚠ 2022" in (df.loc[df["year"] == 2022, "notes"].iloc[0] or ""), \
        "2022 row must carry the verification caveat in notes"
    print(f"  ✓ 2022 anomaly flagged in notes")

    # arrecadação vs distribuição ratio — NOT a strict ≥ invariant. ECAD's
    # distribution of year N draws on arrecadação of N-1 and N-2 via the
    # processing lag, so distrib_N can exceed arrec_N (and does in 2021, when
    # the pandemic-depressed 2020 arrec was followed by a delayed catch-up
    # distribution in 2021). We just check the ratio band looks sane and
    # surface it so an outlier becomes visible.
    both = df[df["distribuicao_brl"].notna()].copy()
    both["arrec_brl"] = both["arrecadacao_brl_mi"] * 1_000_000
    both["ratio_dist_over_arrec"] = (
        both["distribuicao_brl"] / both["arrec_brl"]).round(3)
    band_min, band_max = 0.50, 1.20
    out_of_band = both[(both["ratio_dist_over_arrec"] < band_min) |
                       (both["ratio_dist_over_arrec"] > band_max)]
    if not out_of_band.empty:
        print(f"  ⚠ distribuição/arrecadação outside [{band_min}, {band_max}]:")
        for _, row in out_of_band.iterrows():
            print(f"      {int(row['year'])}: ratio "
                  f"{row['ratio_dist_over_arrec']:.3f}  "
                  f"(distrib R$ {row['distribuicao_brl']/1e6:.1f} mi, "
                  f"arrec R$ {row['arrecadacao_brl_mi']:.0f} mi)")
        print(f"      → expected for 2022 (the documented anomaly); "
              f"investigate any others.")
    ratios = both.set_index("year")["ratio_dist_over_arrec"].to_dict()
    print(f"  ✓ distrib/arrec ratios: "
          + ", ".join(f"{y} {r:.2f}" for y, r in ratios.items()))

    # custo_operacional_pct is 9.0 in 2025, NULL elsewhere (per source caveat)
    custo = df.set_index("year")["custo_operacional_pct"].to_dict()
    assert custo[2025] == 9.0, "2025 custo_operacional_pct must be 9.0"
    for y in [2018, 2019, 2020, 2021, 2022, 2023, 2024]:
        assert pd.isna(custo[y]), f"custo_operacional_pct {y} must be NULL"
    print(f"  ✓ custo_operacional_pct = 9.0 in 2025 only (other years NULL)")


def write_parquet(df: pd.DataFrame) -> Path:
    out_path = OUT / "arrecadacao_distribuicao.parquet"
    con = duckdb.connect()
    con.register("df_data", df)
    con.execute(
        f"COPY df_data TO '{out_path}' (FORMAT PARQUET, COMPRESSION ZSTD)")
    size_kb = out_path.stat().st_size / 1024
    print(f"  ✓ {out_path.relative_to(REPO_ROOT)} — {len(df)} rows, {size_kb:.1f} KB")
    return out_path


def write_meta(out_path: Path, df: pd.DataFrame) -> None:
    meta = {
        "table": out_path.stem,
        "schema": "ecad",
        "description": "ECAD music public-performance royalties — headline "
                       "annual series 2018–2025: arrecadação (R$ mi) and "
                       "distribuição (R$ exact). v2 (2026-05-28) — extended "
                       "from 3 rows to 8 using the ECAD 2025 Annual Report. "
                       "YoY columns are computed from values (not transcribed) "
                       "because the source PDF labels were scrambled by the "
                       "markitdown conversion. Segment breakdowns and the "
                       "national-vs-foreign distribution mix live in three "
                       "sibling tables.",
        "source": "ECAD Relatório Anual 2025 (PDF, 32 pp.) — pages 12 (arrec.), "
                  "13 (distrib.), 10 (digital share), 18 (custo); "
                  "Transparência pages for titulares counts.",
        "source_pages": sorted(set(df["source_page"].dropna().tolist())),
        "fetch_date": "2026-05-28",
        "etl_script": "etl/ecad__headline_series_to_parquet.py",
        "etl_run_date": str(date.today()),
        "licence": "ECAD published figures — public transparency disclosure",
        "grain": "one row per reference year",
        "row_count": int(len(df)),
        "notes": "v2 schema break vs v1: column rename "
                 "arrecadacao_brl_billion → arrecadacao_brl_mi (R$ mi), "
                 "distribuicao_brl_billion → distribuicao_brl (R$ exato). "
                 "2022 distribuição flagged with a verification caveat in the "
                 "row's `notes` column — see docs/methodology/ecad_relatorio_anual.md "
                 "§3 for the two competing explanations and the verification path.",
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
    print("Building atana.ecad.arrecadacao_distribuicao (v2 — 2018–2025)...")
    df = build()
    validate(df)
    out_path = write_parquet(df)
    write_meta(out_path, df)
    maybe_push(df, "ecad", "arrecadacao_distribuicao")
    print("Done.")


if __name__ == "__main__":
    main()
