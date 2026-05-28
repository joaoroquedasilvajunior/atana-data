"""ECAD — arrecadação / distribuição headline series → Parquet.

Phase 4c.3 of the Atana Data expansion. The third lens on the FCS *Intellectual
property* domain: cultural-IP **income** actually collected and distributed —
music public-performance royalties. (BCB 4c.1 = the IP-royalty flow; INPI
4c.2 = the IP registration stock; ECAD 4c.3 = IP income, in four tables.)

v3 CORRECTION + ENRICHMENT (2026-05-29)
---------------------------------------
v2 (2026-05-28) ingested 8 rows (2018–2025) transcribed from the ECAD
Relatório Anual 2025's historical chart. That chart's year labels turned out
to be **scrambled by the markitdown conversion** — the value set was right but
the years 2018–2021 were permuted, and (critically) the stated YoY labels were
permuted *with* the values, so the scramble was self-consistent and passed
v2's internal YoY validation. It is only detectable against contemporary
reports.

The cross-source reference (built 2026-05-29 from the Relatório Anual 2020 and
2022) corrects it:

    Relatório 2020:  2019 = R$ 1,121 mi → 2020 = R$ 905.8 mi (−19.2%)
    Relatório 2022:  2021 = R$ 1,086,436,152 → 2022 = R$ 1,393,765,668 (+28.3%)

Corrected arrecadação series (this file):
    2019 1,121 · 2020 905.8 · 2021 1,086 · 2022 1,394 · 2023 1,631 ·
    2024 1,831 · 2025 2,105   (R$ mi)

2018 itself is not in any available report — the leftover scrambled value
R$ 1,106 mi may belong to 2018 but is unverified; 2018 is dropped (the series
now starts 2019). The mis-yeared v2 row for 2018 (905.81, the pandemic low) is
the iconic 2020 figure; "905.8" appears in every contemporary report as the
2020 pandemic drop.

v3 also backfills, from the same multi-report reference:
    - digital_services_arrec_share_pct: 2020 18 · 2021 23 · 2022 22.8
      (alongside the v2 figures 2024 26 · 2025 33.6) — the "digital headline
      series" Análise 23 was after.
    - custo_operacional_pct: 2020 15.0 (10% ECAD + 5% associações, Relatório
      2020) alongside 2025 9.0 — a documented efficiency reduction (⚠ the two
      may have different perimeters — verify).
    - titulares_contemplados_mil: 2020 263 (alongside 2023 323, 2024/2025 345).

DISTRIBUIÇÃO — STILL SUSPECT FOR 2021/2022
------------------------------------------
The reference corrects ARRECADAÇÃO only; it provides no contemporary
distribuição series. The distribuição values are unchanged from v2, BUT the
confirmed arrecadação scramble raises the probability that the distribuição
chart (Relatório 2025 p.13) was scrambled the same way. The clean
reconstruction — distribuição 2021 ≈ R$ 901.6 mi (tracking the 2020 pandemic
arrecadação with lag), 2022 ≈ R$ 1,232 mi — would remove the −26.8 % 2022
anomaly and restore a monotonic series. This is *inference*, not a contemporary
source, so the values are NOT reordered here; the 2021 and 2022 rows carry the
hypothesis in `notes`, flagged for verification against the printed PDF p.13.

⚠️ WHY STILL HAND-TRANSCRIBED
-----------------------------
ECAD publishes no machine-readable dataset. Values are inlined verbatim from
the PDFs and Transparência pages. Charts are PNG/JPEG images read by eye.

SOURCE REPORTS
--------------
    Relatório Anual 2020 — arrecadação 2019/2020, custo 15%, titulares 263k,
                           digital 18%, autoral/conexa nacional 2016–2020.
    Relatório Anual 2022 — arrecadação 2021/2022 (exact), segment absolutes.
    Transparência 2023   — arrecadação ~R$ 1.6 bi, titulares 323k, 65% nacional.
    Relatório Anual 2024 (versão-mercado) — arrecadação 2024, digital 26% (#1).
    Relatório Anual 2025 — arrecadação/distribuição 2025, custo 9%, all splits.

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

COLUMNS = [
    "year",
    "arrecadacao_brl_mi",                   # R$ mi correntes — contemporary reports (corrected)
    "arrecadacao_yoy_pct",                  # computed from arrecadacao values
    "distribuicao_brl",                     # R$ correntes — Relatório 2025 p.13 (2021/2022 suspect)
    "distribuicao_yoy_pct",                 # computed from distribuicao values
    "titulares_contemplados_mil",           # rights-holders paid, thousands
    "digital_services_arrec_share_pct",     # Serviços Digitais share of arrecadação
    "custo_operacional_pct",                # ECAD(+assoc.) operating cost as % of arrecadação
    "notes",
    "source_page",
]

R2020 = "ECAD Relatório Anual 2020"
R2022 = "ECAD Relatório Anual 2022"
T2023 = "ECAD Transparência 2023"
R2024 = "ECAD Relatório Anual 2024 (versão-mercado)"
R2025 = "ECAD Relatório Anual 2025"

# Tuple: (year, arrec_brl_mi, distribuicao_brl, titulares_mil, digital_share,
#         custo_pct, notes, source_page). YoY computed in build().
ROWS = [
    (2019, 1121.0, None, None, None, None,
     "Arrecadação corrected 2026-05-29 — verified against the contemporary "
     "Relatório 2020 (2019 = R$ 1,121 mi). 2018 is not in any available "
     "report; the leftover scrambled value R$ 1,106 mi may belong to 2018 but "
     "is unverified and dropped.",
     R2020),
    (2020, 905.8, None, 263, 18.0, 15.0,
     "Arrecadação corrected — R$ 905.8 mi is the iconic pandemic low "
     "(−19.2% YoY), verified against Relatório 2020. custo operacional 15% "
     "(10% ECAD + 5% associações) — ⚠ perimeter may differ from the 2025 9% "
     "figure. digital share 18% (digital +41.2% in 2020). titulares 263 mil.",
     R2020),
    (2021, 1086.0, 1_232_071_471.0, None, 23.0, None,
     "Arrecadação corrected — R$ 1,086 mi verified against Relatório 2022 "
     "(2021 = R$ 1,086,436,152). ⚠ distribuição R$ 1,232 mi exceeds "
     "arrecadação; given the confirmed arrecadação-chart scramble, this is "
     "suspected to be a 2021↔2022 distribuição label swap — the clean "
     "reconstruction is 2021 distribuição ≈ R$ 901.6 mi (tracking the 2020 "
     "pandemic arrecadação with lag). NOT reordered (inference only); verify "
     "against the printed Relatório 2025 p.13.",
     f"{R2022} / {R2025}"),
    (2022, 1394.0, 901_588_853.0, None, 22.8, None,
     "Arrecadação R$ 1,394 mi verified (Relatório 2022: R$ 1,393,765,668, "
     "+28.3%). ⚠ distribuição R$ 901.6 mi implies −26.8% YoY — implausible "
     "against +28.3% arrecadação growth; see the 2021 note. Clean "
     "reconstruction puts 2022 distribuição ≈ R$ 1,232 mi. Verify against PDF. "
     "digital share dip to 22.8% (Shows recover post-pandemic and dilute it).",
     f"{R2022} / {R2025}"),
    (2023, 1631.0, 1_390_932_884.0, 323, None, None,
     "Arrecadação R$ 1,631 mi (rounded headline R$ 1.6 bi; +17% vs 2022). "
     "digital share image-only (JPEG) at source — estimated ~24–25%, left "
     "NULL. titulares 323 mil. Transparência 2023 also states 65% repertório "
     "nacional overall (see methodology — the nacional share rose 65%→78% by "
     "2025).",
     f"{T2023} / {R2025}"),
    (2024, 1831.0, 1_569_374_513.0, 345, 26.0, None,
     "digital share 26% — FIRST year Serviços Digitais was the #1 arrecadação "
     "segment (Relatório 2024: 'pela primeira vez').",
     R2024),
    (2025, 2105.0, 1_725_497_001.0, 345, 33.6, 9.0,
     "9% custo operacional stated as 'estável' in the 2025 report (down from "
     "15% in 2020 — ⚠ perimeters may differ).",
     R2025),
]


def build() -> pd.DataFrame:
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

    df["arrecadacao_yoy_pct"] = (df["arrecadacao_brl_mi"].pct_change() * 100).round(2)
    df["distribuicao_yoy_pct"] = (df["distribuicao_brl"].pct_change() * 100).round(2)

    df["year"] = df["year"].astype("int32")
    df["titulares_contemplados_mil"] = df["titulares_contemplados_mil"].astype("Int32")
    return df


def validate(df: pd.DataFrame) -> None:
    print("Validating...")
    assert len(df) == 7, f"expected 7 year rows, got {len(df)}"
    years = list(df["year"])
    assert years == list(range(2019, 2026)), f"unexpected year sequence: {years}"
    print(f"  ✓ 7 rows, 2019–2025 contiguous (2018 dropped — not in any report)")

    # Corrected arrecadação YoYs must match CONTEMPORARY-report figures.
    def yoy(y):
        return float(df.loc[df["year"] == y, "arrecadacao_yoy_pct"].iloc[0])
    checks = {2020: -19.2, 2022: 28.3, 2023: 17.0}  # Relatório 2020 / 2022 / Transparência
    for y, exp in checks.items():
        got = yoy(y)
        assert abs(got - exp) <= 0.6, \
            f"arrecadação YoY {y}: computed {got:.2f} vs contemporary report {exp:.2f}"
    print(f"  ✓ corrected arrecadação YoYs match contemporary reports: "
          f"2020 {yoy(2020):.1f}% (−19.2 expected), 2022 +{yoy(2022):.1f}% "
          f"(+28.3 expected), 2023 +{yoy(2023):.1f}%")

    # 905.8 (the pandemic low) must now sit on 2020, NOT 2018.
    assert float(df.loc[df["year"] == 2020, "arrecadacao_brl_mi"].iloc[0]) == 905.8, \
        "the R$ 905.8 mi pandemic low must be on 2020"
    print(f"  ✓ R$ 905.8 mi pandemic low correctly on 2020 (was mis-yeared 2018 in v2)")

    # Distribuição present 2021–2025
    nn = df["distribuicao_brl"].notna()
    assert list(df.loc[nn, "year"]) == [2021, 2022, 2023, 2024, 2025], \
        "distribuicao non-null years not 2021–2025"
    print(f"  ✓ distribuição present 2021–2025; 2019–2020 NULL")

    # The 2021 + 2022 distribuição suspicion is documented
    for y in (2021, 2022):
        assert "⚠ distribuição" in (df.loc[df["year"] == y, "notes"].iloc[0] or ""), \
            f"{y} row must carry the distribuição scramble caveat"
    print(f"  ✓ 2021/2022 distribuição scramble hypothesis flagged in notes")

    # digital share backfilled
    dig = df.set_index("year")["digital_services_arrec_share_pct"].to_dict()
    for y, exp in {2020: 18.0, 2021: 23.0, 2022: 22.8, 2024: 26.0, 2025: 33.6}.items():
        assert dig[y] == exp, f"digital share {y}: {dig[y]} ≠ {exp}"
    print(f"  ✓ digital-share series backfilled: 2020 18 · 2021 23 · 2022 22.8 "
          f"· 2024 26 · 2025 33.6 (2019, 2023 NULL)")

    # custo backfilled
    custo = df.set_index("year")["custo_operacional_pct"].to_dict()
    assert custo[2020] == 15.0 and custo[2025] == 9.0, "custo 2020=15 / 2025=9 expected"
    print(f"  ✓ custo operacional: 2020 15% · 2025 9%")

    # ratio band surface (not strict)
    both = df[df["distribuicao_brl"].notna()].copy()
    both["ratio"] = (both["distribuicao_brl"] / (both["arrecadacao_brl_mi"] * 1e6)).round(3)
    ratios = both.set_index("year")["ratio"].to_dict()
    print(f"  · distrib/arrec ratios: "
          + ", ".join(f"{y} {r:.2f}" for y, r in ratios.items())
          + "  (2021 > 1 and 2022 ≈ 0.65 are the suspected-scramble rows)")


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
                       "annual series 2019–2025. v3 (2026-05-29): arrecadação "
                       "years corrected (the v2 ingest from the Relatório 2025 "
                       "chart was year-scrambled 2018–2021; corrected against "
                       "the contemporary Relatório 2020 and 2022); "
                       "digital-share, custo operacional and titulares "
                       "backfilled from the multi-report cross-source. "
                       "Distribuição values unchanged but 2021/2022 flagged as "
                       "likely-scrambled (inference; not reordered).",
        "source": "ECAD Relatório Anual 2020 / 2022 / 2024 / 2025 + "
                  "Transparência 2023. Hand-transcribed (ECAD publishes no "
                  "machine-readable data).",
        "source_pages": sorted(set(df["source_page"].dropna().tolist())),
        "fetch_date": "2026-05-29",
        "etl_script": "etl/ecad__headline_series_to_parquet.py",
        "etl_run_date": str(date.today()),
        "licence": "ECAD published figures — public transparency disclosure",
        "grain": "one row per reference year",
        "row_count": int(len(df)),
        "notes": "v3 corrects the v2 arrecadação scramble (2018–2021). 2018 "
                 "dropped (not in any available report). Distribuição 2021/2022 "
                 "carry a scramble-hypothesis caveat in their `notes`, pending "
                 "PDF p.13 verification. See docs/methodology/ecad_relatorio_anual.md §3.",
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
    print("Building atana.ecad.arrecadacao_distribuicao (v3 — corrected 2019–2025)...")
    df = build()
    validate(df)
    out_path = write_parquet(df)
    write_meta(out_path, df)
    maybe_push(df, "ecad", "arrecadacao_distribuicao")
    print("Done.")


if __name__ == "__main__":
    main()
