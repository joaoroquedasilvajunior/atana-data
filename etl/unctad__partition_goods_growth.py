"""One-time housekeeping — partition raw/unctad/goods_growth.parquet by Period.

The complete goods_growth table is ~115 MB as a single file, which GitHub rejects
(100 MB per-file limit). `goods_value` is already partitioned (one file per year) for
exactly this reason; this does the same for `goods_growth`, keyed on Period.

Reads the local clean single file — no MotherDuck token, no re-download. Writes
raw/unctad/goods_growth/goods_growth_<period>.parquet (27 files, ~4-5 MB each),
verifies the row total round-trips, and prints the git steps.

    cd atana-data
    python3 etl/unctad__partition_goods_growth.py
"""
import sys
from pathlib import Path

import duckdb

REPO_ROOT = Path(__file__).resolve().parent.parent
SRC = REPO_ROOT / "raw" / "unctad" / "goods_growth.parquet"
OUT = REPO_ROOT / "raw" / "unctad" / "goods_growth"


def main() -> int:
    if not SRC.exists():
        print(f"  · source not found: {SRC}", file=sys.stderr)
        return 1
    con = duckdb.connect()
    src = SRC.as_posix()
    try:
        total = con.execute(f"SELECT count(*) FROM read_parquet('{src}')").fetchone()[0]
    except Exception as e:
        print(f"  · source unreadable (still corrupt?): {e}", file=sys.stderr)
        return 1
    periods = [r[0] for r in con.execute(
        f"SELECT DISTINCT Period FROM read_parquet('{src}') ORDER BY Period").fetchall()]
    print(f"  source: {total:,} rows across {len(periods)} periods")

    OUT.mkdir(parents=True, exist_ok=True)
    for p in periods:
        out = OUT / f"goods_growth_{p}.parquet"
        con.execute(
            f"COPY (SELECT * FROM read_parquet('{src}') WHERE Period={p}) "
            f"TO '{out.as_posix()}' (FORMAT PARQUET, COMPRESSION ZSTD)"
        )
    got = con.execute(
        f"SELECT count(*) FROM read_parquet('{OUT.as_posix()}/goods_growth_*.parquet')"
    ).fetchone()[0]
    con.close()

    if got != total:
        print(f"  ✗ row mismatch: partitions {got:,} vs source {total:,}", file=sys.stderr)
        return 2
    biggest = max(f.stat().st_size for f in OUT.glob("goods_growth_*.parquet"))
    print(f"  ✓ {got:,} rows in {len(periods)} files; largest {biggest/1e6:.1f} MB "
          f"(all < GitHub's 100 MB limit)")
    print("\n  Next (git) — replaces the unpushable single-file commit:")
    print("    rm -f .git/index.lock   # only if a stale lock blocks you")
    print("    git reset --mixed HEAD~1")
    print("    git rm --cached raw/unctad/goods_growth.parquet")
    print("    git add raw/unctad/goods_growth/ .gitignore "
          "etl/unctad__export_parquet.py etl/unctad__partition_goods_growth.py")
    print("    git commit -m 'Housekeeping: partition unctad/goods_growth by period "
          "(was 1 corrupt + oversized 115MB file); clean data under GitHub 100MB limit'")
    print("    git push")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
