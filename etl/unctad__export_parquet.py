"""Export UNCTAD tables from md:atana to local Parquet files in raw/unctad/.

Strategy:
- Small tables (services_countries, services_regional, goods_growth): single Parquet file
- Large table (goods_value, 25M rows): partitioned by year, one file per year

Each year of goods_value compresses to ~13 MB with ZSTD — well under GitHub's 100 MB
per-file limit. Total ~320 MB across 23 year files.

Usage:
    export MOTHERDUCK_TOKEN="eyJ..."
    python etl/unctad__export_parquet.py

Idempotent: skips files that already exist with non-zero size.
"""
import os
import sys
import time
from pathlib import Path

import duckdb

REPO_ROOT = Path(__file__).resolve().parent.parent
OUT = REPO_ROOT / "raw" / "unctad"
OUT.mkdir(parents=True, exist_ok=True)

TOKEN = os.environ.get("MOTHERDUCK_TOKEN")
if not TOKEN:
    sys.exit("Set MOTHERDUCK_TOKEN environment variable before running.")

con = duckdb.connect(f"md:atana?motherduck_token={TOKEN}")


def export_single(table: str, out_path: Path) -> None:
    if out_path.exists() and out_path.stat().st_size > 1000:
        print(f"  ✓ {out_path.name} (cached, skipped)")
        return
    t0 = time.time()
    con.execute(
        f"COPY (SELECT * FROM atana.unctad.{table}) TO '{out_path}' "
        "(FORMAT PARQUET, COMPRESSION ZSTD)"
    )
    size_mb = out_path.stat().st_size / 1024 / 1024
    print(f"  ✓ {out_path.name} — {size_mb:.2f} MB ({time.time() - t0:.1f}s)")


def export_partitioned_by_year(table: str, out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    years = con.execute(
        f"SELECT DISTINCT Year FROM atana.unctad.{table} ORDER BY Year"
    ).fetchall()
    for (y,) in years:
        p = out_dir / f"{table}_{y}.parquet"
        if p.exists() and p.stat().st_size > 1000:
            continue
        t0 = time.time()
        con.execute(
            f"COPY (SELECT * FROM atana.unctad.{table} WHERE Year={y}) "
            f"TO '{p}' (FORMAT PARQUET, COMPRESSION ZSTD)"
        )
        size_mb = p.stat().st_size / 1024 / 1024
        print(f"  ✓ {p.name} — {size_mb:.2f} MB ({time.time() - t0:.1f}s)")


def main() -> None:
    print("Exporting UNCTAD tables to raw/unctad/...")
    print()
    print("Small tables (single file):")
    export_single("services_countries", OUT / "services_countries.parquet")
    export_single("services_regional", OUT / "services_regional.parquet")
    export_single("goods_growth", OUT / "goods_growth.parquet")

    print()
    print("Large table goods_value (partitioned by year):")
    export_partitioned_by_year("goods_value", OUT / "goods_value")

    print()
    print("Done. Verify with:")
    print(f"  duckdb -c \"SELECT COUNT(*) FROM read_parquet('{OUT}/goods_value/goods_value_*.parquet')\"")


if __name__ == "__main__":
    main()
