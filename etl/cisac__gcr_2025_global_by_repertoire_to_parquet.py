"""CISAC GCR 2025 — global collections by repertoire → Parquet.

Phase 5a of the Atana Data expansion — second of four tables in
`atana.cisac` (Tier 1 of the CISAC scoping). The 2024 split of global
royalty collections across CISAC's five creative repertoires:
Music, Audiovisual, Visual arts, Drama, Literature.

This is the repertoire dimension Atana Note #06 (Funk, Authenticity Paradox)
and Análise 16 (intellectual property) work on. Music alone is **€12.59 bn,
+7.2 %** — about 90 % of the €13.97 bn global total — which sets the scale
context for the corpus's music-centric Brazilian work via `atana.ecad`.

GRAIN
-----
One row per (year, repertoire). 2024 only at v1 launch (5 rows); future
GCR editions extend by year with the same schema.

SOURCE
------
    https://www.cisac.org/cisac-global-collections-report-2025
    GCR 2025 landing page (public).

OUTPUT
------
    raw/cisac/gcr_2025_global_by_repertoire.parquet  (+ .meta.json)

Idempotent: inline data → DuckDB COPY to Parquet (no pyarrow); byte-identical
reruns. MotherDuck push gated behind a token (skipped when ATANA_ETL_SKIP_PUSH
is set). Schema: atana.cisac.

Usage:
    python etl/cisac__gcr_2025_global_by_repertoire_to_parquet.py
"""
import hashlib
import json
import os
from datetime import date
from pathlib import Path

import duckdb
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parent.parent
OUT = REPO_ROOT / "raw" / "cisac"
OUT.mkdir(parents=True, exist_ok=True)

SOURCE_PAGE = "https://www.cisac.org/cisac-global-collections-report-2025"
TOTAL_2024_EUR_MI = 13970.0   # from gcr_2025_global_by_stream

COLUMNS = [
    "year",
    "repertoire",        # 'Music' / 'Audiovisual' / 'Visual arts' / 'Drama' / 'Literature'
    "eur_mi",
    "yoy_pct",
    "source_page",
]

# Verbatim from the GCR 2025 landing page (2024 reference year).
ROWS = [
    (2024, "Music",        12590.0,  7.2),
    (2024, "Audiovisual",    727.0,  1.1),
    (2024, "Visual arts",    219.0,  0.9),
    (2024, "Drama",          208.0, -3.4),
    (2024, "Literature",     231.0,  7.3),
]


def build() -> pd.DataFrame:
    df = pd.DataFrame(
        [{"year": r[0], "repertoire": r[1], "eur_mi": r[2], "yoy_pct": r[3],
          "source_page": SOURCE_PAGE} for r in ROWS],
        columns=COLUMNS,
    )
    df = df.sort_values(["year", "eur_mi"], ascending=[True, False]).reset_index(drop=True)
    df["year"] = df["year"].astype("int32")
    return df


def validate(df: pd.DataFrame) -> None:
    print("Validating...")
    assert len(df) == 5, f"expected 5 rows, got {len(df)}"
    expected = {"Music", "Audiovisual", "Visual arts", "Drama", "Literature"}
    assert set(df["repertoire"]) == expected, \
        f"unexpected repertoire set: {sorted(df['repertoire'])}"
    print(f"  ✓ 5 rows, repertoires ∈ {{Music, Audiovisual, Visual arts, Drama, Literature}}")

    # The five repertoires must sum to the headline total (no leakage by design).
    s = float(df["eur_mi"].sum())
    diff = s - TOTAL_2024_EUR_MI
    assert abs(diff) <= 10.0, \
        f"five-repertoire sum €{s:,.0f} mi vs total €{TOTAL_2024_EUR_MI:,.0f} mi differs by €{diff:.0f}"
    print(f"  ✓ five repertoires sum €{s:,.0f} mi ≈ headline total €{TOTAL_2024_EUR_MI:,.0f} mi "
          f"(drift €{diff:+.0f} mi, within rounding)")

    music_share = float(df.loc[df["repertoire"] == "Music", "eur_mi"].iloc[0]) / s * 100
    assert 88.0 <= music_share <= 92.0, f"Music share {music_share:.1f}% off expected ~90%"
    print(f"  ✓ Music share of repertoire total = {music_share:.1f} % "
          f"(scale context for atana.ecad)")

    yoy = df.set_index("repertoire")["yoy_pct"].to_dict()
    assert yoy == {"Music": 7.2, "Audiovisual": 1.1, "Visual arts": 0.9,
                   "Drama": -3.4, "Literature": 7.3}, f"YoY off: {yoy}"
    print(f"  ✓ 2024 YoY: Music +7.2 · AV +1.1 · Visual arts +0.9 · "
          f"Drama −3.4 · Literature +7.3")


def write_parquet(df: pd.DataFrame) -> Path:
    out_path = OUT / "gcr_2025_global_by_repertoire.parquet"
    con = duckdb.connect()
    con.register("df_data", df)
    con.execute(f"COPY df_data TO '{out_path}' (FORMAT PARQUET, COMPRESSION ZSTD)")
    size_kb = out_path.stat().st_size / 1024
    print(f"  ✓ {out_path.relative_to(REPO_ROOT)} — {len(df)} rows, {size_kb:.1f} KB")
    return out_path


def write_meta(out_path: Path, df: pd.DataFrame) -> None:
    meta = {
        "table": out_path.stem,
        "schema": "cisac",
        "description": "CISAC Global Collections Report 2025 — 2024 global "
                       "royalty collections by repertoire (Music, Audiovisual, "
                       "Visual arts, Drama, Literature). EUR millions. Music "
                       "is ~90 % of the global total — the scale context for "
                       "atana.ecad's Brazilian music-royalty series.",
        "source": "CISAC Global Collections Report 2025 — public landing page.",
        "source_pages": [SOURCE_PAGE],
        "fetch_date": "2026-05-29",
        "etl_script": "etl/cisac__gcr_2025_global_by_repertoire_to_parquet.py",
        "etl_run_date": str(date.today()),
        "licence": "CISAC published figures — public release",
        "grain": "one row per (year, repertoire)",
        "row_count": int(len(df)),
        "notes": "2024 reference year. Five repertoires reconcile with the "
                 "€13.97 bn global total (sum €13,975 mi — drift +5 mi from "
                 "verbatim rounding). See docs/methodology/cisac_gcr.md.",
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
    print("Building atana.cisac.gcr_2025_global_by_repertoire...")
    df = build()
    validate(df)
    out_path = write_parquet(df)
    write_meta(out_path, df)
    maybe_push(df, "cisac", "gcr_2025_global_by_repertoire")
    print("Done.")


if __name__ == "__main__":
    main()
