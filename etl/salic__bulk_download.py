"""SALIC bulk download + cycle-state refresh — complete the projetos sample and
keep open-cycle PRONACs in sync with the live API.

Implements §2.1 of `desenho_pesquisa_salic_2026-05-16.md`. The current md:atana.salic.projetos
holds ~48,189 records of a ~56,578 universe. This script fills the gap with paginated calls,
respecting the W-S10 throttling (max 8 concurrent, 30s pause every 60 pages).

Usage:
    export MOTHERDUCK_TOKEN="<full JWT — not a placeholder>"

    # default — discover new PRONACs and insert them (idempotent)
    python etl/salic__bulk_download.py

    # discover new PRONACs AND refresh cycle-state of open-cycle ones
    python etl/salic__bulk_download.py --refresh-existing

    # only refresh open-cycle PRONACs (skip discovery)
    python etl/salic__bulk_download.py --refresh-only

Idempotent in both modes. Discovery skips PRONACs already cached. Refresh
overwrites valor_captado / situacao only when the API reports new values,
and logs every change into atana.salic.refresh_log for cycle-progress
reconstruction (Option B of Análise 8).

v2 — 2026-05-16 — Fixed two bugs:
  - API total is at payload["total"], not in X-Total-Count header (was causing 0-page loops)
  - INSERT uses explicit column list (was hitting 23-vs-35 column mismatch)
v3 — 2026-06-13 — Added cycle-state refresh:
  - --refresh-existing / --refresh-only flags
  - atana.salic.refresh_log table for snapshot diffing
  - refresh targets only open-cycle PRONACs (cycle_closed=FALSE, ano≥2020)
"""
import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

import duckdb

API_BASE = "https://api.salic.cultura.gov.br/api/v1/projetos"
TMP_DIR = Path("/tmp/salic_bulk")
TMP_DIR.mkdir(parents=True, exist_ok=True)

PAGE_SIZE = 100               # max allowed by API
PAUSE_EVERY_PAGES = 10
PAUSE_SECONDS = 6
LONG_PAUSE_EVERY_PAGES = 60   # W-S10
LONG_PAUSE_SECONDS = 30

YEARS_TO_BACKFILL = [2019, 2020, 2021, 2022, 2023, 2024, 2025, 2026]

# Refresh mode tuning — per-PRONAC GET is lighter than pagination
REFRESH_PAUSE_EVERY = 60         # pause every 60 PRONACs
REFRESH_PAUSE_SECONDS = 15
REFRESH_MIN_ANO_PROJETO = 2020   # only refresh PRONACs from 2020 onwards

# Fields whose changes we want to track in refresh_log
REFRESH_TRACKED_FIELDS = ["valor_captado", "situacao", "valor_aprovado"]

# Exact column list of atana.salic.projetos (matches base table schema).
# Order matters for INSERT INTO ... SELECT cols.
PROJETOS_COLS = [
    "cgccpf", "nome", "valor_solicitado", "data_inicio", "providencia",
    "segmento", "data_termino", "local_realizacao", "valor_projeto",
    "valor_captado", "situacao", "PRONAC", "UF", "outras_fontes",
    "municipio", "tipologia", "ano_projeto", "proponente",
    "valor_proposta", "valor_aprovado", "mecanisnmo", "tipicidade",
    "enquadradmento",
]


def md_token() -> str:
    token = os.environ.get("MOTHERDUCK_TOKEN")
    if not token or token.startswith("eyJ...") or len(token) < 100:
        sys.exit(
            "MOTHERDUCK_TOKEN missing or placeholder. Set the full JWT first.\n"
            "Hint: grep -h 'eyJhbGc' gen_latam_fig3_fig9.py | head -1"
        )
    return token


def fetch_page(year: int, offset: int, retries: int = 5) -> dict:
    """Fetch one page. Returns {"total": int, "items": list[dict]}."""
    year_2dig = year - 2000  # W-S1: ano_projeto is 2-digit
    url = f"{API_BASE}?ano_projeto={year_2dig}&limit={PAGE_SIZE}&offset={offset}"
    last_err = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={
                "User-Agent": "atana-data/1.0 (research)",
                "Accept": "application/json",
            })
            with urllib.request.urlopen(req, timeout=60) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
            total = int(payload.get("total", 0))
            items = payload.get("_embedded", {}).get("projetos", [])
            return {"total": total, "items": items}
        # Broadened catch: includes ConnectionResetError, OSError, and any URL/network/JSON issue
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError,
                ConnectionResetError, ConnectionError, OSError) as e:
            last_err = e
            backoff = 10 * (2 ** attempt)  # 10, 20, 40, 80, 160
            print(f"    WARN fetch failed (attempt {attempt+1}/{retries}): {type(e).__name__}: {e}; sleeping {backoff}s")
            time.sleep(backoff)
    raise RuntimeError(f"Failed after {retries} retries: {last_err}")


def existing_pronacs(con) -> set[str]:
    rows = con.execute("SELECT PRONAC FROM atana.salic.projetos WHERE PRONAC IS NOT NULL").fetchall()
    return {str(r[0]) for r in rows}


def download_year(year: int, existing: set[str]) -> list[dict]:
    """Paginate through one year, collect novel records.

    Returns whatever was collected before any failure. Caller is responsible
    for inserting what was returned. Failure of a single page raises after
    all retries are exhausted; the function-level try/except in main() handles
    the resume on next run (idempotent — already-cached PRONACs are skipped).
    """
    new_records = []
    offset = 0
    page_count = 0
    total_universe = None
    try:
        while True:
            page = fetch_page(year, offset)
            if total_universe is None:
                total_universe = page["total"]
                print(f"  Year {year}: universe = {total_universe:,} records")
                if total_universe == 0:
                    print(f"  Year {year}: nothing to fetch")
                    return []
            items = page["items"]
            if not items:
                print(f"    Page {page_count + 1}: empty items — stopping")
                break

            novel = [it for it in items if str(it.get("PRONAC")) not in existing]
            new_records.extend(novel)
            for it in novel:
                existing.add(str(it.get("PRONAC")))

            offset += PAGE_SIZE
            page_count += 1

            if page_count % 5 == 0 or page_count == 1:
                print(f"    page {page_count} | offset {offset}/{total_universe} | "
                      f"+{len(novel)} novel | cumulative new {len(new_records):,}")

            if page_count % LONG_PAUSE_EVERY_PAGES == 0:
                print(f"    [long pause {LONG_PAUSE_SECONDS}s — W-S10 throttling]")
                time.sleep(LONG_PAUSE_SECONDS)
            elif page_count % PAUSE_EVERY_PAGES == 0:
                time.sleep(PAUSE_SECONDS)

            if offset >= total_universe:
                print(f"  Year {year}: reached end of universe ({offset} ≥ {total_universe})")
                break
    except Exception as e:
        # On any unrecoverable failure, return what we have so far so the caller can save it
        print(f"  ⚠ Year {year} interrupted at page {page_count} (offset {offset}); "
              f"saving partial {len(new_records):,} records and continuing to next year")
        print(f"    Failure: {type(e).__name__}: {e}")
        return new_records

    return new_records


def upsert_to_motherduck(records: list[dict], con) -> int:
    """Insert into atana.salic.projetos via NDJSON intermediate. Explicit column list."""
    if not records:
        return 0
    tmp = TMP_DIR / f"new_{int(time.time())}.ndjson"
    with open(tmp, "w", encoding="utf-8") as f:
        for r in records:
            # Normalize all values: nested → JSON string; everything else preserved
            clean = {}
            for k in PROJETOS_COLS:
                v = r.get(k)
                if isinstance(v, (dict, list)):
                    clean[k] = json.dumps(v, ensure_ascii=False)
                else:
                    clean[k] = v
            f.write(json.dumps(clean, ensure_ascii=False) + "\n")

    con.execute("INSTALL json; LOAD json;")
    cols_sql = ", ".join(f'"{c}"' for c in PROJETOS_COLS)
    con.execute(f"""
        INSERT INTO atana.salic.projetos ({cols_sql})
        SELECT {cols_sql}
        FROM read_json_auto('{tmp}', format='nd', maximum_object_size=10000000)
    """)
    n_inserted = len(records)
    tmp.unlink()
    return n_inserted


def ensure_refresh_log_table(con) -> None:
    """Create atana.salic.refresh_log if not exists. Idempotent."""
    con.execute("""
        CREATE TABLE IF NOT EXISTS atana.salic.refresh_log (
            pronac VARCHAR,
            refresh_ts TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            old_valor_captado DOUBLE,
            new_valor_captado DOUBLE,
            captado_delta DOUBLE,
            old_situacao VARCHAR,
            new_situacao VARCHAR,
            situacao_changed BOOLEAN,
            old_valor_aprovado DOUBLE,
            new_valor_aprovado DOUBLE,
            error_msg VARCHAR
        )
    """)
    print("✓ atana.salic.refresh_log ready")


def fetch_pronac(pronac: str, retries: int = 3) -> dict | None:
    """Fetch one PRONAC by id. Returns the project dict or None on hard failure."""
    url = f"{API_BASE}/{pronac}"
    last_err = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={
                "User-Agent": "atana-data/1.0 (research)",
                "Accept": "application/json",
            })
            with urllib.request.urlopen(req, timeout=45) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
            # API may return the project directly or wrapped in _embedded
            if "_embedded" in payload and "projetos" in payload["_embedded"]:
                items = payload["_embedded"]["projetos"]
                return items[0] if items else None
            return payload
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None  # PRONAC no longer exists in upstream
            last_err = e
            time.sleep(5 * (2 ** attempt))
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError,
                ConnectionResetError, ConnectionError, OSError) as e:
            last_err = e
            time.sleep(5 * (2 ** attempt))
    print(f"    WARN fetch_pronac({pronac}) failed after {retries} retries: {last_err}")
    return None


def pronacs_to_refresh(con) -> list[tuple[str, float | None, str | None, float | None, int | None]]:
    """Return rows for PRONACs whose cycle is still open OR cycle_closed is unknown.

    Restrict to ano_projeto >= REFRESH_MIN_ANO_PROJETO to keep the call volume
    manageable. Returns list of tuples (pronac, valor_captado, situacao,
    valor_aprovado, ano_int).
    """
    rows = con.execute(f"""
        SELECT
          p.PRONAC,
          p.valor_captado,
          p.situacao,
          p.valor_aprovado,
          CASE
            WHEN p.ano_projeto IS NULL THEN NULL
            WHEN LENGTH(p.ano_projeto) = 2 THEN 2000 + CAST(p.ano_projeto AS INTEGER)
            WHEN LENGTH(p.ano_projeto) = 4 THEN CAST(p.ano_projeto AS INTEGER)
            ELSE NULL
          END AS ano_int
        FROM atana.salic.projetos p
        LEFT JOIN atana.salic.cycle_status_map m ON p.situacao = m.situacao
        WHERE p.PRONAC IS NOT NULL
          AND (m.is_cycle_closed IS NULL OR m.is_cycle_closed = FALSE)
        QUALIFY ano_int IS NULL OR ano_int >= {REFRESH_MIN_ANO_PROJETO}
        ORDER BY p.PRONAC
    """).fetchall()
    return rows


def refresh_cached_pronacs(con, dry_run: bool = False) -> dict:
    """Iterate over open-cycle PRONACs, fetch fresh state from API,
    UPDATE atana.salic.projetos when a delta is detected, INSERT a row
    into atana.salic.refresh_log for every fetch (even no-change), so the
    log doubles as a snapshot history for cycle-progress reconstruction.
    """
    targets = pronacs_to_refresh(con)
    n_total = len(targets)
    print(f"\nRefresh targets — open-cycle PRONACs (ano≥{REFRESH_MIN_ANO_PROJETO}): {n_total:,}")
    if n_total == 0:
        return {"checked": 0, "updated": 0, "errors": 0}

    stats = {"checked": 0, "updated": 0, "errors": 0, "no_change": 0, "missing_404": 0}
    log_rows: list[dict] = []

    for i, (pronac, old_cap, old_sit, old_apr, _ano) in enumerate(targets, 1):
        fresh = fetch_pronac(str(pronac))
        stats["checked"] += 1

        if fresh is None:
            log_rows.append({
                "pronac": str(pronac),
                "old_valor_captado": old_cap,
                "new_valor_captado": None,
                "captado_delta": None,
                "old_situacao": old_sit,
                "new_situacao": None,
                "situacao_changed": None,
                "old_valor_aprovado": old_apr,
                "new_valor_aprovado": None,
                "error_msg": "fetch_failed_or_404",
            })
            stats["errors"] += 1
            stats["missing_404"] += 1
        else:
            new_cap = fresh.get("valor_captado")
            new_sit = fresh.get("situacao")
            new_apr = fresh.get("valor_aprovado")
            # cast numeric fields defensively
            try:
                new_cap = float(new_cap) if new_cap not in (None, "") else None
            except (TypeError, ValueError):
                new_cap = None
            try:
                new_apr = float(new_apr) if new_apr not in (None, "") else None
            except (TypeError, ValueError):
                new_apr = None

            old_cap_f = float(old_cap) if old_cap is not None else None
            old_apr_f = float(old_apr) if old_apr is not None else None
            captado_delta = (new_cap - old_cap_f) if (new_cap is not None and old_cap_f is not None) else None
            sit_changed = (new_sit != old_sit)

            something_changed = (
                (new_cap is not None and old_cap_f != new_cap) or
                sit_changed or
                (new_apr is not None and old_apr_f != new_apr)
            )

            log_rows.append({
                "pronac": str(pronac),
                "old_valor_captado": old_cap_f,
                "new_valor_captado": new_cap,
                "captado_delta": captado_delta,
                "old_situacao": old_sit,
                "new_situacao": new_sit,
                "situacao_changed": sit_changed,
                "old_valor_aprovado": old_apr_f,
                "new_valor_aprovado": new_apr,
                "error_msg": None,
            })

            if something_changed:
                stats["updated"] += 1
                if not dry_run:
                    con.execute("""
                        UPDATE atana.salic.projetos
                        SET valor_captado = ?,
                            situacao = ?,
                            valor_aprovado = ?
                        WHERE PRONAC = ?
                    """, [new_cap, new_sit, new_apr, str(pronac)])
            else:
                stats["no_change"] += 1

        # progress + throttle
        if i % 50 == 0 or i == 1:
            print(f"    refresh {i}/{n_total} | updated {stats['updated']} | "
                  f"no_change {stats['no_change']} | errors {stats['errors']}")
        if i % REFRESH_PAUSE_EVERY == 0:
            time.sleep(REFRESH_PAUSE_SECONDS)
        else:
            time.sleep(0.5)  # gentle baseline pause

        # flush log every 200 rows to avoid memory pressure
        if len(log_rows) >= 200:
            _flush_refresh_log(log_rows, con, dry_run)
            log_rows = []

    if log_rows:
        _flush_refresh_log(log_rows, con, dry_run)

    print(f"\n=== Refresh complete ===")
    for k, v in stats.items():
        print(f"  {k}: {v:,}")
    return stats


def _flush_refresh_log(log_rows: list[dict], con, dry_run: bool) -> None:
    if dry_run or not log_rows:
        return
    tmp = TMP_DIR / f"refresh_{int(time.time() * 1000)}.ndjson"
    with open(tmp, "w", encoding="utf-8") as f:
        for r in log_rows:
            f.write(json.dumps(r, ensure_ascii=False, default=str) + "\n")
    con.execute("INSTALL json; LOAD json;")
    con.execute(f"""
        INSERT INTO atana.salic.refresh_log (
            pronac, old_valor_captado, new_valor_captado, captado_delta,
            old_situacao, new_situacao, situacao_changed,
            old_valor_aprovado, new_valor_aprovado, error_msg
        )
        SELECT
            pronac, old_valor_captado, new_valor_captado, captado_delta,
            old_situacao, new_situacao, situacao_changed,
            old_valor_aprovado, new_valor_aprovado, error_msg
        FROM read_json_auto('{tmp}', format='nd')
    """)
    tmp.unlink()


def regenerate_v2(con) -> None:
    print("\n=== Regenerating atana.salic.projetos_v2 ===")
    con.execute("""
    CREATE OR REPLACE TABLE atana.salic.projetos_v2 AS
    WITH base AS (
      SELECT p.*,
        CASE
          WHEN p.ano_projeto IS NULL THEN NULL
          WHEN LENGTH(p.ano_projeto) = 2 THEN 2000 + CAST(p.ano_projeto AS INTEGER)
          WHEN LENGTH(p.ano_projeto) = 4 THEN CAST(p.ano_projeto AS INTEGER)
          ELSE NULL
        END AS year_int
      FROM atana.salic.projetos p
    )
    SELECT
      b.*,
      m.cycle_status_label,
      m.is_cycle_closed,
      CASE WHEN b.valor_captado > 0 THEN TRUE ELSE FALSE END AS cap_positive,
      CASE WHEN b.valor_solicitado > 0
           THEN COALESCE(b.valor_captado, 0) / b.valor_solicitado
           ELSE NULL END AS cap_rate_sol,
      CASE WHEN b.valor_aprovado > 0
           THEN COALESCE(b.valor_captado, 0) / b.valor_aprovado
           ELSE NULL END AS cap_rate_apr,
      b.valor_solicitado * d.deflator_to_2024 AS valor_solicitado_brl2024,
      b.valor_aprovado   * d.deflator_to_2024 AS valor_aprovado_brl2024,
      b.valor_captado    * d.deflator_to_2024 AS valor_captado_brl2024,
      b.valor_proposta   * d.deflator_to_2024 AS valor_proposta_brl2024,
      b.valor_projeto    * d.deflator_to_2024 AS valor_projeto_brl2024,
      d.deflator_to_2024
    FROM base b
    LEFT JOIN atana.salic.cycle_status_map m ON b.situacao = m.situacao
    LEFT JOIN atana.macro.ipca d ON b.year_int = d.year
    """)
    n = con.execute("SELECT COUNT(*) FROM atana.salic.projetos_v2").fetchone()[0]
    print(f"  projetos_v2 rebuilt: {n:,} rows")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    p.add_argument("--refresh-existing", action="store_true",
                   help="After discovery, refresh cycle-state of open-cycle PRONACs.")
    p.add_argument("--refresh-only", action="store_true",
                   help="Skip discovery; only refresh open-cycle PRONACs and exit.")
    p.add_argument("--dry-run", action="store_true",
                   help="Refresh mode only: fetch but do not UPDATE/INSERT (read-only probe).")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    token = md_token()
    con = duckdb.connect(f"md:atana?motherduck_token={token}")

    # Always ensure the refresh_log table exists — cheap and idempotent
    ensure_refresh_log_table(con)

    do_discovery = not args.refresh_only
    do_refresh = args.refresh_existing or args.refresh_only

    if do_discovery:
        print("Bulk download — SALIC API → md:atana.salic.projetos")
        print("=" * 60)
        existing = existing_pronacs(con)
        print(f"PRONACs already cached: {len(existing):,}\n")

        total_new = 0
        for year in YEARS_TO_BACKFILL:
            print(f"--- Year {year} ---")
            try:
                new = download_year(year, existing)
                print(f"  Total novel for {year}: {len(new):,}")
                inserted = upsert_to_motherduck(new, con)
                print(f"  Inserted into md:atana.salic.projetos: {inserted:,}")
                total_new += inserted
            except Exception as e:
                print(f"  ✗ Year {year} failed (will retry on next run): {type(e).__name__}: {e}")
                import traceback
                traceback.print_exc()
                continue

            # Inter-year pause — server tends to throttle on sustained load
            print(f"  [inter-year pause 60s]")
            time.sleep(60)
            print()

        print(f"=== Bulk download complete: +{total_new:,} new records ===")

    if do_refresh:
        print("\n" + "=" * 60)
        print(f"Refresh mode — open-cycle PRONACs from {REFRESH_MIN_ANO_PROJETO}+"
              f"{' (DRY RUN)' if args.dry_run else ''}")
        print("=" * 60)
        refresh_cached_pronacs(con, dry_run=args.dry_run)

    regenerate_v2(con)

    repo_root = Path(__file__).resolve().parent.parent
    parquet_path = repo_root / "raw" / "salic" / "projetos.parquet"
    parquet_path.parent.mkdir(parents=True, exist_ok=True)
    con.execute(f"""
        COPY (SELECT * FROM atana.salic.projetos) TO '{parquet_path}'
        (FORMAT PARQUET, COMPRESSION ZSTD)
    """)
    print(f"\n✓ Parquet refreshed: {parquet_path}")

    # also persist refresh_log as Parquet for off-line analysis
    if do_refresh:
        log_path = repo_root / "raw" / "salic" / "refresh_log.parquet"
        con.execute(f"""
            COPY (SELECT * FROM atana.salic.refresh_log) TO '{log_path}'
            (FORMAT PARQUET, COMPRESSION ZSTD)
        """)
        print(f"✓ refresh_log Parquet snapshot: {log_path}")

    print("Next: run regression M1 + M2 against atana.salic.projetos_v2")


if __name__ == "__main__":
    main()
