"""CISAC GCR 2025 — global collections by region → Parquet.

Phase 5a of the Atana Data expansion — third of four tables in `atana.cisac`
(Tier 1 of the CISAC scoping). The 2024 split of global royalty collections
across CISAC's six geographical regions.

Critical row for the corpus: **Latin America = €786 mi (−0.6 %)** — the
first comparable LATAM aggregate the Atana corpus carries. Sets the frame
for `atana.ecad` (Brazil's 2024 ECAD distribuição R$ 1.57 bi ≈ €260 mi at
year-average FX ≈ a third of the LATAM CISAC total) and for any future
per-country slice via `canonical.cmo_directory_alcam`.

GRAIN
-----
One row per (year, region). 2024 only at v1 launch (6 rows).

SOURCE
------
    https://www.cisac.org/cisac-global-collections-report-2025
    GCR 2025 landing page (public).

OUTPUT
------
    raw/cisac/gcr_2025_global_by_region.parquet  (+ .meta.json)

Idempotent: inline data → DuckDB COPY to Parquet (no pyarrow); byte-identical
reruns. MotherDuck push gated behind a token (skipped when ATANA_ETL_SKIP_PUSH
is set). Schema: atana.cisac.

Usage:
    python etl/cisac__gcr_2025_global_by_region_to_parquet.py
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
    "region",
    "eur_mi",
    "yoy_pct",
    "source_page",
]

# Verbatim from the GCR 2025 landing page (2024 reference year).
ROWS = [
    (2024, "West Europe",    7090.0,  6.1),
    (2024, "Canada/USA",     3520.0, 10.0),
    (2024, "Asia-Pacific",   1920.0,  2.9),
    (2024, "Latin America",   786.0, -0.6),
    (2024, "East Europe",     566.0, 13.8),
    (2024, "Africa",           90.0, 14.2),
]


def build() -> pd.DataFrame:
    df = pd.DataFrame(
        [{"year": r[0], "region": r[1], "eur_mi": r[2], "yoy_pct": r[3],
          "source_page": SOURCE_PAGE} for r in ROWS],
        columns=COLUMNS,
    )
    df = df.sort_values(["year", "eur_mi"], ascending=[True, False]).reset_index(drop=True)
    df["year"] = df["year"].astype("int32")
    return df


def validate(df: pd.DataFrame) -> None:
    print("Validating...")
    assert len(df) == 6, f"expected 6 rows, got {len(df)}"
    expected = {"West Europe", "Canada/USA", "Asia-Pacific",
                "Latin America", "East Europe", "Africa"}
    assert set(df["region"]) == expected, \
        f"unexpected region set: {sorted(df['region'])}"
    print(f"  ✓ 6 rows, regions ∈ {{West Europe, Canada/USA, Asia-Pacific, "
          f"Latin America, East Europe, Africa}}")

    s = float(df["eur_mi"].sum())
    diff = s - TOTAL_2024_EUR_MI
    assert abs(diff) <= 10.0, \
        f"six-region sum €{s:,.0f} mi vs total €{TOTAL_2024_EUR_MI:,.0f} mi differs by €{diff:.0f}"
    print(f"  ✓ six regions sum €{s:,.0f} mi ≈ headline total €{TOTAL_2024_EUR_MI:,.0f} mi "
          f"(drift €{diff:+.0f} mi, within rounding)")

    latam = float(df.loc[df["region"] == "Latin America", "eur_mi"].iloc[0])
    latam_share = latam / s * 100
    assert abs(latam - 786.0) < 1.0
    print(f"  ✓ Latin America = €{latam:,.0f} mi (−0.6 %) = "
          f"{latam_share:.1f} % of global — the LATAM frame for atana.ecad / cmo_directory_alcam")

    yoy = df.set_index("region")["yoy_pct"].to_dict()
    assert yoy == {"West Europe": 6.1, "Canada/USA": 10.0, "Asia-Pacific": 2.9,
                   "Latin America": -0.6, "East Europe": 13.8, "Africa": 14.2}, \
        f"YoY off: {yoy}"
    only_decliner = [r for r, v in yoy.items() if v < 0]
    assert only_decliner == ["Latin America"], \
        f"Latin America must be the only region with negative YoY; got {only_decliner}"
    print(f"  ✓ 2024 YoYs verbatim; Latin America is the only region with a "
          f"decline (−0.6 %)")


def write_parquet(df: pd.DataFrame) -> Path:
    out_path = OUT / "gcr_2025_global_by_region.parquet"
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
                       "royalty collections by region (West Europe, Canada/USA, "
                       "Asia-Pacific, Latin America, East Europe, Africa). "
                       "EUR millions. Latin America = €786 mi (−0.6 %) — the "
                       "LATAM frame the Atana corpus did not previously carry; "
                       "joins to atana.ecad (Brazil) and to "
                       "canonical.cmo_directory_alcam (the 12-country LATAM "
                       "CMO map).",
        "source": "CISAC Global Collections Report 2025 — public landing page.",
        "source_pages": [SOURCE_PAGE],
        "fetch_date": "2026-05-29",
        "etl_script": "etl/cisac__gcr_2025_global_by_region_to_parquet.py",
        "etl_run_date": str(date.today()),
        "licence": "CISAC published figures — public release",
        "grain": "one row per (year, region)",
        "row_count": int(len(df)),
        "notes": "2024 reference year. Six regions reconcile with the €13.97 bn "
                 "global total within rounding. Latin America is the only "
                 "region with a YoY decline in 2024 (−0.6 %), 'following two "
                 "years of strong post-pandemic gains' per the GCR. See "
                 "docs/methodology/cisac_gcr.md.",
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
    print("Building atana.cisac.gcr_2025_global_by_region...")
    df = build()
    validate(df)
    out_path = write_parquet(df)
    write_meta(out_path, df)
    maybe_push(df, "cisac", "gcr_2025_global_by_region")
    print("Done.")


if __name__ == "__main__":
    main()
