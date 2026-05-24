"""BCB SGS — intellectual-property-services balance of payments → Parquet.

Phase 4c.1 of the Atana Data expansion. Reaches the FCS transversal domain
*Intellectual property*: the Banco Central's balance-of-payments account for
intellectual-property services is the cross-border IP-royalty flow — what a
cultural-goods-trade module cannot see.

WHAT THIS INGESTS
-----------------
Two monthly time series from the BCB SGS (Sistema Gerenciador de Séries
Temporais), BPM6 basis — the account formerly "Royalties e licenças":

    series 22777 — Serviços de propriedade intelectual — receita  (credit)
    series 22778 — Serviços de propriedade intelectual — despesa  (debit)

API (open, no key):
    https://api.bcb.gov.br/dados/serie/bcdata.sgs.<code>/dados?formato=json
    → JSON array of {"data": "DD/MM/YYYY", "valor": "<number>"}

The raw JSON for each series is cached under raw/bcb/_source/ on first run; the
ETL reads the cache thereafter, so reruns are stable and offline. Delete the
cache (or pass --refresh) to pull a fresh vintage — a DB-updater job.

⚠️ This is the BoP **services** account, not the cultural sector specifically —
it is the all-economy IP-royalty flow. It is the standard proxy for the FCS
Intellectual property domain (see the methodology note); a cultural-only cut
would need the INPI / ECAD sources (Phase 4c.2 / 4c.3).

OUTPUT (long format):
    raw/bcb/ip_services_bop.parquet  (+ .meta.json)
    grain: series_code × date  (one row per series per month)

Idempotent. JSON → list-of-dicts → DuckDB COPY to Parquet (no pyarrow).
MotherDuck push gated behind a token (skipped when ATANA_ETL_SKIP_PUSH is set).
Schema: atana.bcb.

Usage:
    python etl/bcb__sgs_ip_services_to_parquet.py            # uses cache if present
    python etl/bcb__sgs_ip_services_to_parquet.py --refresh  # re-pull from the API
"""
import hashlib
import json
import os
import sys
import urllib.request
from datetime import date
from pathlib import Path

import duckdb
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parent.parent
OUT = REPO_ROOT / "raw" / "bcb"
SRC = OUT / "_source"
OUT.mkdir(parents=True, exist_ok=True)
SRC.mkdir(parents=True, exist_ok=True)

# BCB SGS series — Serviços de propriedade intelectual (BPM6)
SERIES = {
    22777: {"flow": "receita", "flow_en": "credit",
            "name": "Serviços de propriedade intelectual — receita"},
    22778: {"flow": "despesa", "flow_en": "debit",
            "name": "Serviços de propriedade intelectual — despesa"},
}
API = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.{code}/dados?formato=json"


def fetch_series(code: int, refresh: bool) -> list:
    """Return the raw SGS JSON for one series — from cache, or pulled live."""
    cache = SRC / f"sgs_{code}.json"
    if cache.exists() and not refresh:
        print(f"  · series {code}: using cached {cache.relative_to(REPO_ROOT)}")
        return json.loads(cache.read_text())
    url = API.format(code=code)
    print(f"  · series {code}: fetching {url}")
    req = urllib.request.Request(url, headers={"User-Agent": "atana-data-etl"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        raw = resp.read().decode("utf-8")
    data = json.loads(raw)
    cache.write_text(json.dumps(data, ensure_ascii=False, indent=0))
    print(f"    cached → {cache.relative_to(REPO_ROOT)} ({len(data)} points)")
    return data


def _num(value):
    if value is None:
        return None
    s = str(value).strip()
    if s in ("", "-", "..."):
        return None
    try:
        return float(s.replace(" ", "").replace(",", "."))
    except ValueError:
        return None


def build(refresh: bool) -> pd.DataFrame:
    rows = []
    for code, meta in SERIES.items():
        for point in fetch_series(code, refresh):
            d = str(point.get("data", "")).strip()       # DD/MM/YYYY
            parts = d.split("/")
            if len(parts) != 3:
                continue
            day, month, year = (int(parts[0]), int(parts[1]), int(parts[2]))
            rows.append(dict(
                series_code=code,
                series_name=meta["name"],
                flow=meta["flow"],
                flow_en=meta["flow_en"],
                date=date(year, month, day),
                year=year,
                month=month,
                value_usd_million=_num(point.get("valor")),
            ))
    df = pd.DataFrame(rows).sort_values(
        ["series_code", "date"]).reset_index(drop=True)
    return df


def write_parquet(df: pd.DataFrame, table_name: str) -> Path:
    out_path = OUT / f"{table_name}.parquet"
    con = duckdb.connect()
    con.register("df_data", df)
    con.execute(f"COPY df_data TO '{out_path}' (FORMAT PARQUET, COMPRESSION ZSTD)")
    size_kb = out_path.stat().st_size / 1024
    print(f"  ✓ {out_path.relative_to(REPO_ROOT)} — {len(df):,} rows, {size_kb:.1f} KB")
    return out_path


def write_meta(out_path: Path, df: pd.DataFrame) -> None:
    srcs = []
    for code in SERIES:
        f = SRC / f"sgs_{code}.json"
        h = hashlib.sha256(f.read_bytes()).hexdigest() if f.exists() else None
        srcs.append({"file": f.name, "sha256": h})
    yr = df["year"]
    meta = {
        "table": out_path.stem,
        "schema": "bcb",
        "description": "Brazil balance-of-payments — intellectual-property "
                       "services, BCB SGS series 22777 (receita) and 22778 "
                       "(despesa), BPM6 basis. Monthly, long format. The "
                       "cross-border IP-royalty flow — reaches the FCS "
                       "Intellectual property transversal domain.",
        "source": "Banco Central do Brasil — Sistema Gerenciador de Séries "
                   "Temporais (SGS), series 22777 / 22778",
        "source_url": "https://www3.bcb.gov.br/sgspub/",
        "source_files": srcs,
        "fetch_date": str(date.today()),
        "etl_script": "etl/bcb__sgs_ip_services_to_parquet.py",
        "etl_run_date": str(date.today()),
        "licence": "open data — Banco Central do Brasil",
        "grain": "series_code × date (one row per series per month)",
        "coverage": (f"{int(yr.min())}–{int(yr.max())}"
                     if len(df) else "—"),
        "notes": "value_usd_million is the BCB SGS BoP convention (US$ "
                 "million) — confirm against the SGS series metadata page. "
                 "This is the all-economy IP-services account, not a "
                 "cultural-only cut; see docs/methodology/bcb_sgs_ip_services.md.",
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
              f"valid token. Put a JWT in {REPO_ROOT}/.motherduck_token, re-run.")
        return
    con = duckdb.connect(f"md:atana?motherduck_token={token}")
    con.execute(f"CREATE SCHEMA IF NOT EXISTS atana.{schema}")
    con.register("df_data", df)
    con.execute(
        f"CREATE OR REPLACE TABLE atana.{schema}.{table} AS SELECT * FROM df_data")
    n = con.execute(f"SELECT COUNT(*) FROM atana.{schema}.{table}").fetchone()[0]
    print(f"  ✓ Synced atana.{schema}.{table} ({n:,} rows)")


def main() -> None:
    refresh = "--refresh" in sys.argv
    print("Building atana.bcb.ip_services_bop (SGS 22777 + 22778)...")
    df = build(refresh)
    if df.empty:
        raise SystemExit("No data parsed — check the SGS API response.")
    # sanity print — eyeball the result, the ETL was written without a live probe
    print(f"  · parsed {len(df):,} rows; "
          f"{df['year'].min()}–{df['year'].max()}; "
          f"latest: " + "; ".join(
              f"{m['flow']} "
              f"{df[df.series_code==c].iloc[-1]['value_usd_million']}"
              for c, m in SERIES.items()))
    out_path = write_parquet(df, "ip_services_bop")
    write_meta(out_path, df)
    maybe_push(df, "bcb", "ip_services_bop")
    print("Done.")


if __name__ == "__main__":
    main()
