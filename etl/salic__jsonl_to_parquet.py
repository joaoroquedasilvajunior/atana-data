"""Convert SALIC JSONL files to Parquet (raw/salic/) and sync to atana.salic.

Source files:
  - projetos_master.jsonl       (26,203 Lei Rouanet projects, 2019–2026)
  - edges_pronac_incent.jsonl   (8,504 incentivador → PRONAC edges)
  - propostas_recentes.jsonl    (3,000 recent proposals)

Usage:
    export MOTHERDUCK_TOKEN="..."
    python etl/salic__jsonl_to_parquet.py
"""
import json
import os
import sys
from pathlib import Path

import duckdb

REPO_ROOT = Path(__file__).resolve().parent.parent
OUT = REPO_ROOT / "raw" / "salic"
OUT.mkdir(parents=True, exist_ok=True)

SRC = Path(
    "/Users/joaoroque/Documents/Cultural production - book/"
    "Dados da Economia Cultural no Brasil/salic_api_data"
)
if not SRC.exists():
    SRC = Path(
        "/sessions/wizardly-admiring-feynman/mnt/"
        "Dados da Economia Cultural no Brasil/salic_api_data"
    )

MAPPING = {
    "projetos":           "projetos_master.jsonl",
    "edges_incentivador": "edges_pronac_incent.jsonl",
    "propostas_recentes": "propostas_recentes.jsonl",
}


def load_jsonl(path: Path) -> list[dict]:
    """Read a JSONL file into a list of dicts."""
    rows = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as e:
                print(f"  ⚠ Skipping malformed line in {path.name}: {e}")
    return rows


def convert(table_name: str, src_file: str) -> None:
    src_path = SRC / src_file
    if not src_path.exists():
        print(f"  ⚠ {src_path} not found, skipping")
        return
    out_path = OUT / f"{table_name}.parquet"

    print(f"Reading {src_file}...")
    rows = load_jsonl(src_path)
    print(f"  Loaded {len(rows):,} records")

    # Use DuckDB to write Parquet (handles JSON column nesting via JSON type)
    # First normalize: flatten all values that are not scalars/arrays into JSON strings
    normalized = []
    for r in rows:
        nr = {}
        for k, v in r.items():
            if isinstance(v, (dict, list)):
                nr[k] = json.dumps(v, ensure_ascii=False)
            else:
                nr[k] = v
        normalized.append(nr)

    local_con = duckdb.connect()
    local_con.execute("INSTALL json; LOAD json;")
    # Build a CTE via VALUES isn't scalable — use the JSON read trick
    # Write rows to a temp NDJSON file in /tmp and read via read_json_auto
    tmp = Path(f"/tmp/_salic_{table_name}.ndjson")
    with open(tmp, "w", encoding="utf-8") as f:
        for r in normalized:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    local_con.execute(
        f"COPY (SELECT * FROM read_json_auto('{tmp}', format='nd', maximum_object_size=100000000)) "
        f"TO '{out_path}' (FORMAT PARQUET, COMPRESSION ZSTD)"
    )
    tmp.unlink()
    size_kb = out_path.stat().st_size / 1024
    print(f"  ✓ {out_path.name} — {len(rows):,} rows, {size_kb:.1f} KB")

    token = os.environ.get("MOTHERDUCK_TOKEN")
    if token:
        con = duckdb.connect(f"md:atana?motherduck_token={token}")
        con.execute("CREATE SCHEMA IF NOT EXISTS atana.salic")
        con.execute(
            f"CREATE OR REPLACE TABLE atana.salic.{table_name} AS "
            f"SELECT * FROM '{out_path}'"
        )
        n = con.execute(f"SELECT COUNT(*) FROM atana.salic.{table_name}").fetchone()[0]
        print(f"    Synced atana.salic.{table_name} ({n:,} rows)")


def main() -> None:
    if not SRC.exists():
        sys.exit(f"Source folder not found: {SRC}")
    for table_name, src_file in MAPPING.items():
        convert(table_name, src_file)


if __name__ == "__main__":
    main()
