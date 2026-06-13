"""INEGI CSCM 2024 — PIB cultural real growth 2009–2024 → Parquet.

Phase 5b. Fourth of four `atana.inegi` non-trade tables. Annual real-growth
series 2009–2024 (16 rows) — cultural sector vs. total economy. Lifted from
CSCM 2024 boletín Gráfica 1 (verbatim values; reference year 2018).

Tells the most important macro story of Mexican cultural value: a sector
more VOLATILE than the total economy (much sharper pandemic drop 2020:
−20.3 % vs −8.0 % total) but capable of stronger rebounds (2021: +9.0 % vs
+5.8 %; 2022: +9.3 % vs +3.6 %). 2024 is a normalisation year — cultural
+1.2 % vs total +1.3 %, near-converged for the first time since the
pandemic.

SOURCE
------
    INEGI Comunicado 144/25 (CSCM 2024) — Gráfica 1.
"""
import hashlib, json, os
from datetime import date
from pathlib import Path
import duckdb, pandas as pd

REPO_ROOT = Path(__file__).resolve().parent.parent
OUT = REPO_ROOT / "raw" / "inegi"
OUT.mkdir(parents=True, exist_ok=True)
SOURCE_PAGE = ("https://www.inegi.org.mx/contenidos/saladeprensa/boletines/2025/"
               "cultura/CSCM2024_CP.pdf")

COLUMNS = ["year", "sector_cultura_real_yoy_pct",
           "total_economia_real_yoy_pct", "source_page"]

# Verbatim from Gráfica 1 — series at 2018 reference prices.
SERIES = [
    (2009,  -5.3,  -5.9), (2010, -0.2,  5.3), (2011,  4.7,  3.6),
    (2012,   1.0,   3.7), (2013, -1.7,  0.9), (2014,  5.5,  2.5),
    (2015,   7.7,   2.6), (2016, -0.9,  1.7), (2017,  2.0,  1.9),
    (2018,   0.3,   1.9), (2019,  0.4, -0.4), (2020, -20.3, -8.0),
    (2021,   9.0,   5.8), (2022,  9.3,  3.6), (2023,  2.5,  3.0),
    (2024,   1.2,   1.3),
]


def build():
    df = pd.DataFrame(
        [{"year": y, "sector_cultura_real_yoy_pct": c,
          "total_economia_real_yoy_pct": t, "source_page": SOURCE_PAGE}
         for y, c, t in SERIES], columns=COLUMNS)
    df = df.sort_values("year").reset_index(drop=True)
    df["year"] = df["year"].astype("int32")
    return df


def validate(df):
    print("Validating...")
    assert len(df) == 16
    assert list(df["year"]) == list(range(2009, 2025))
    print(f"  ✓ 16 rows, 2009–2024 contiguous")
    pandemic = df[df["year"] == 2020].iloc[0]
    assert pandemic["sector_cultura_real_yoy_pct"] == -20.3
    print(f"  ✓ 2020 pandemic shock: cultural −20.3 % vs total −8.0 % (2.5× deeper)")
    avg_culture = df["sector_cultura_real_yoy_pct"].mean()
    avg_total = df["total_economia_real_yoy_pct"].mean()
    print(f"  · 2009–2024 mean YoY: cultural {avg_culture:.2f} % vs total "
          f"{avg_total:.2f} % (cultural underperforms by {avg_total - avg_culture:.2f} pp)")
    last = df[df["year"] == 2024].iloc[0]
    assert abs(last["sector_cultura_real_yoy_pct"] - 1.2) < 0.05
    assert abs(last["total_economia_real_yoy_pct"] - 1.3) < 0.05
    print(f"  ✓ 2024 cultural +1.2 % vs total +1.3 % — near-converged after pandemic divergence")


def write_parquet(df):
    out_path = OUT / "cscm_2024_pib_growth_series.parquet"
    con = duckdb.connect(); con.register("df_data", df)
    con.execute(f"COPY df_data TO '{out_path}' (FORMAT PARQUET, COMPRESSION ZSTD)")
    print(f"  ✓ {out_path.relative_to(REPO_ROOT)} — {len(df)} rows, "
          f"{out_path.stat().st_size/1024:.1f} KB")
    return out_path


def write_meta(out_path, df):
    meta = {
        "table": out_path.stem, "schema": "inegi",
        "description": "INEGI CSCM 2024 — annual real-growth series 2009–2024 "
                       "(cultural sector vs total economy, 16 rows × 2 series). "
                       "Reference prices = 2018. Shows the cultural sector's "
                       "higher volatility (2020 pandemic 2.5× deeper than "
                       "total economy) and 2021–2022 sharp rebound.",
        "source": "INEGI Comunicado 144/25 (CSCM 2024) — Gráfica 1.",
        "source_pages": [SOURCE_PAGE], "fetch_date": "2026-06-01",
        "etl_script": "etl/inegi__cscm_2024_pib_growth_series_to_parquet.py",
        "etl_run_date": str(date.today()),
        "licence": "INEGI public data — open licence",
        "grain": "one row per reference year", "row_count": int(len(df)),
        "notes": "Cumulative ≈ 2009–2024 — derive in-query, not stored. The "
                 "INEGI Gráfica 1 reads as a bar chart; values transcribed verbatim.",
    }
    out_path.with_suffix(".meta.json").write_text(
        json.dumps(meta, indent=2, ensure_ascii=False))
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
    print("Building atana.inegi.cscm_2024_pib_growth_series...")
    df = build(); validate(df)
    out_path = write_parquet(df); write_meta(out_path, df)
    maybe_push(df, "inegi", "cscm_2024_pib_growth_series")
    print("Done.")


if __name__ == "__main__":
    main()
