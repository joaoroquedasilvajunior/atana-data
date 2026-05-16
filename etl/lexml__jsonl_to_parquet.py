"""Convert LexML legislative corpus JSONL files to Parquet and sync to atana.lexml.

Source files (in a9_data/):
  - lexml_corpus.jsonl        (269 acts, full corpus)
  - lexml_legal.jsonl         (237 acts with normative force)
  - lexml_biblio.jsonl        (32 administrative/programmatic acts)
  - lexml_classified.jsonl    (217 with subnational metadata)
  - lexml_with_ementas.jsonl  (217 with full ementas)

Usage:
    export MOTHERDUCK_TOKEN="..."
    python etl/lexml__jsonl_to_parquet.py
"""
import json
import os
import sys
from pathlib import Path

import duckdb

REPO_ROOT = Path(__file__).resolve().parent.parent
OUT = REPO_ROOT / "raw" / "lexml"
OUT.mkdir(parents=True, exist_ok=True)

SRC = Path(
    "/Users/joaoroque/Documents/Cultural production - book/"
    "Dados da Economia Cultural no Brasil/a9_data"
)
if not SRC.exists():
    SRC = Path(
        "/sessions/wizardly-admiring-feynman/mnt/"
        "Dados da Economia Cultural no Brasil/a9_data"
    )

MAPPING = {
    "corpus":         "lexml_corpus.jsonl",
    "legal":          "lexml_legal.jsonl",
    "biblio":         "lexml_biblio.jsonl",
    "classified":     "lexml_classified.jsonl",
    "with_ementas":   "lexml_with_ementas.jsonl",
}


def convert(table_name: str, src_file: str) -> None:
    src_path = SRC / src_file
    if not src_path.exists():
        print(f"  ⚠ {src_path} not found, skipping")
        return
    out_path = OUT / f"{table_name}.parquet"

    # Normalize nested values to JSON strings
    rows = []
    with open(src_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            r = json.loads(line)
            nr = {k: (json.dumps(v, ensure_ascii=False)
                      if isinstance(v, (dict, list)) else v)
                  for k, v in r.items()}
            rows.append(nr)

    tmp = Path(f"/tmp/_lexml_{table_name}.ndjson")
    with open(tmp, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    local_con = duckdb.connect()
    local_con.execute("INSTALL json; LOAD json;")
    local_con.execute(
        f"COPY (SELECT * FROM read_json_auto('{tmp}', format='nd', maximum_object_size=10000000)) "
        f"TO '{out_path}' (FORMAT PARQUET, COMPRESSION ZSTD)"
    )
    tmp.unlink()
    size_kb = out_path.stat().st_size / 1024
    print(f"  ✓ {out_path.name} — {len(rows):,} rows, {size_kb:.1f} KB")

    token = os.environ.get("MOTHERDUCK_TOKEN")
    if token:
        con = duckdb.connect(f"md:atana?motherduck_token={token}")
        con.execute("CREATE SCHEMA IF NOT EXISTS atana.lexml")
        con.execute(
            f"CREATE OR REPLACE TABLE atana.lexml.{table_name} AS "
            f"SELECT * FROM '{out_path}'"
        )
        n = con.execute(f"SELECT COUNT(*) FROM atana.lexml.{table_name}").fetchone()[0]
        print(f"    Synced atana.lexml.{table_name} ({n:,} rows)")


def main() -> None:
    if not SRC.exists():
        sys.exit(f"Source folder not found: {SRC}")
    for table_name, src_file in MAPPING.items():
        convert(table_name, src_file)


if __name__ == "__main__":
    main()
