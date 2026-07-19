"""Portal da Transparência — Emendas Parlamentares headline series → Parquet.

Phase 11 Tier 1 of the Atana Data expansion. The **fourth federal cultural-
funding pipe** alongside Rouanet (indirect, via `atana.salic`), PNAB (direct
generalista, via `atana.pnab`), and LPG (direct AV, via `atana.lpg`).

Phase 11 scoping: `_atana_intel/phase11_emendas_scoping.md`.

TIER 1 — headline scope
-----------------------
This ETL populates the annual headline series ONLY. Full contratos +
inexigibilidade ingest is Tier 2 (deferred, ~3 sessions).

The Portal da Transparência API (`api.portaldatransparencia.gov.br`) requires
a free API key (5-min signup via gov.br account). In the sandbox this key is
not available, so the table ships with:

1. **All-functions benchmark rows** (2023, 2024) — from published Agência Brasil
   / CGU aggregate figures. Not cultural-subset, but establishes the size of
   the pipe and lets Note #23 anchor the "R$ 31 bi total in 2024" number.

2. **Cultura-subset rows** (Função 13) — NULL by default; populated when
   `PORTAL_TRANSPARENCIA_API_KEY` is set in the env and the ETL is run with
   `--refresh`. The API call is `/api-de-dados/emendas?ano=YYYY&funcao=13`
   iterated 2018+ (per scoping §2).

When João obtains the API key, the ETL populates the `funcao_13_cultura` rows.
Until then, the table is honest about the gap — the all-functions benchmark
is what's currently measurable in the corpus.

OUTPUT
------
    raw/emendas/headlines_annual.parquet  (+ .meta.json)
    grain: (year × scope) — one row per year × scope value

Schema:
    year                      INT32
    scope                     VARCHAR   'all_functions' | 'funcao_13_cultura'
    valor_autorizado_brl_mi   DOUBLE    R$ mi correntes (may be null pre-refresh)
    valor_pago_brl_mi         DOUBLE    R$ mi correntes (may be null pre-refresh)
    n_emendas                 INT32?    count (may be null)
    source_page               VARCHAR   citation
    notes                     VARCHAR   caveats
    fetch_date                VARCHAR   ISO date of transcription / API call

Idempotent: inline data → DuckDB COPY to Parquet (no pyarrow); byte-identical
reruns. MotherDuck push gated behind a token (skipped when ATANA_ETL_SKIP_PUSH
is set). Schema: atana.emendas.

Usage:
    # Ships headline-only (Tier 1a — all-functions benchmark):
    python etl/emendas__headlines_annual_to_parquet.py

    # Refresh cultura-subset from API (Tier 1b — requires key):
    PORTAL_TRANSPARENCIA_API_KEY=xxx python etl/emendas__headlines_annual_to_parquet.py --refresh
"""
import json
import os
import sys
from datetime import date
from pathlib import Path

import duckdb
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parent.parent
OUT = REPO_ROOT / "raw" / "emendas"
OUT.mkdir(parents=True, exist_ok=True)

COLUMNS = [
    "year",
    "scope",
    "valor_autorizado_brl_mi",
    "valor_pago_brl_mi",
    "n_emendas",
    "source_page",
    "notes",
    "fetch_date",
]

AGB_2023 = "Agência Brasil (2023-12) — 'Empenho de emendas parlamentares mais que dobra em 2023'"
GAZ_2024 = "Gazeta do Povo (2024-12) — 'Emendas de parlamentares somaram R$ 31 bilhões em 2024'"

# TIER 1a — All-functions benchmarks (publicly-reported aggregates)
# These are total emendas (all functions), NOT cultura-specific. Their purpose
# is to size the pipe: Note #23 anchors "R$ 31 bi in 2024" from here.
ALL_FUNCTIONS_ROWS = [
    (2023, "all_functions", 20_600.0, None, None,
     AGB_2023,
     "Total emendas individuais empenhadas em 2023 = R$ 20,6 bi (Agência "
     "Brasil, +93% YoY vs 2022). Cultura subset gated on Portal da "
     "Transparência API key — see notes/emendas_portal_transparencia.md §3.",
     "2026-07-19"),
    (2024, "all_functions", 31_400.0, None, None,
     GAZ_2024,
     "Total emendas 2024 (individuais + bancada + comissão) = R$ 31,4 bi "
     "(Gazeta do Povo). R$ 12,2 bi vieram de emendas individuais com destino "
     "definido. Cultura subset gated on API key.",
     "2026-07-19"),
]

# TIER 1b — Função 13 (Cultura) subset — POPULATED VIA --refresh WHEN KEY AVAILABLE
# Empty rows registered so the shape of the table shows the gap explicitly.
CULTURA_PLACEHOLDER_YEARS = [2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025]


def build(refresh: bool = False) -> pd.DataFrame:
    rows = []
    for r in ALL_FUNCTIONS_ROWS:
        rows.append({k: v for k, v in zip(COLUMNS, r)})

    if refresh:
        rows.extend(_fetch_cultura_from_api())
    else:
        # Placeholder rows — cultura scope, all NULL — make the gap visible.
        for y in CULTURA_PLACEHOLDER_YEARS:
            rows.append({
                "year": y,
                "scope": "funcao_13_cultura",
                "valor_autorizado_brl_mi": None,
                "valor_pago_brl_mi": None,
                "n_emendas": None,
                "source_page": "Portal da Transparência API — pending",
                "notes": ("Awaits Portal da Transparência API key. Signup: "
                          "portaldatransparencia.gov.br/api-de-dados/cadastrar-email. "
                          "Then rerun with PORTAL_TRANSPARENCIA_API_KEY=xxx --refresh."),
                "fetch_date": None,
            })

    df = pd.DataFrame(rows, columns=COLUMNS)
    df = df.sort_values(["scope", "year"]).reset_index(drop=True)
    df["year"] = df["year"].astype("int32")
    df["n_emendas"] = df["n_emendas"].astype("Int32")
    return df


def _fetch_cultura_from_api() -> list[dict]:
    """Populate Função 13 (Cultura) rows via Portal da Transparência API.

    Requires env var PORTAL_TRANSPARENCIA_API_KEY. Rate-limited to 30 req/min
    (free tier). Per scoping §2, pulls per-year aggregate valor_autorizado +
    valor_pago + n_emendas for funcao=13.
    """
    import time
    import urllib.parse
    import urllib.request

    key = os.environ.get("PORTAL_TRANSPARENCIA_API_KEY", "").strip()
    if not key:
        print("  ⚠ PORTAL_TRANSPARENCIA_API_KEY not set — skipping cultura fetch.")
        return [{
            "year": y, "scope": "funcao_13_cultura",
            "valor_autorizado_brl_mi": None, "valor_pago_brl_mi": None,
            "n_emendas": None,
            "source_page": "Portal da Transparência API — key not provided",
            "notes": "PORTAL_TRANSPARENCIA_API_KEY missing.",
            "fetch_date": None,
        } for y in CULTURA_PLACEHOLDER_YEARS]

    fetched = []
    base = "https://api.portaldatransparencia.gov.br/api-de-dados/emendas"
    for year in CULTURA_PLACEHOLDER_YEARS:
        total_auth = 0.0
        total_pago = 0.0
        n_emendas = 0
        page = 1
        while True:
            q = urllib.parse.urlencode({"ano": year, "funcao": 13, "pagina": page})
            req = urllib.request.Request(f"{base}?{q}", headers={
                "accept": "application/json",
                "chave-api-dados": key,
            })
            try:
                with urllib.request.urlopen(req, timeout=30) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
            except Exception as e:
                print(f"  ✗ API error year={year} page={page}: {e}")
                break
            if not data:
                break
            for e in data:
                total_auth += float(e.get("valorEmpenhado", 0) or 0)
                total_pago += float(e.get("valorPago", 0) or 0)
                n_emendas += 1
            if len(data) < 15:  # default page size
                break
            page += 1
            time.sleep(2.1)  # 30 req/min rate limit — 2s+ between requests
        fetched.append({
            "year": year,
            "scope": "funcao_13_cultura",
            "valor_autorizado_brl_mi": round(total_auth / 1e6, 2),
            "valor_pago_brl_mi": round(total_pago / 1e6, 2),
            "n_emendas": n_emendas,
            "source_page": f"Portal da Transparência API — /emendas?ano={year}&funcao=13",
            "notes": f"Full pull {page} pages, ~{n_emendas} emendas.",
            "fetch_date": str(date.today()),
        })
        print(f"  ✓ {year}: {n_emendas} emendas · autorizado R$ "
              f"{total_auth/1e6:.1f} mi · pago R$ {total_pago/1e6:.1f} mi")
    return fetched


def validate(df: pd.DataFrame) -> None:
    print("Validating...")
    scopes = set(df["scope"].unique())
    assert scopes == {"all_functions", "funcao_13_cultura"}, \
        f"unexpected scopes: {scopes}"
    print(f"  ✓ two scopes present: all_functions + funcao_13_cultura")

    all_fn = df[df["scope"] == "all_functions"]
    assert len(all_fn) >= 2, f"expected ≥2 all-function benchmark rows, got {len(all_fn)}"
    assert all_fn["valor_autorizado_brl_mi"].notna().all(), \
        "all-function rows must carry valor_autorizado"
    print(f"  ✓ {len(all_fn)} all-function benchmark rows populated (2023, 2024)")

    # 2024 = R$ 31,4 bi = 31400 mi — the widely-cited headline
    r24 = float(all_fn[all_fn["year"] == 2024]["valor_autorizado_brl_mi"].iloc[0])
    assert abs(r24 - 31400.0) < 1.0, f"2024 all-functions expected 31,400 mi, got {r24}"
    print(f"  ✓ 2024 all-functions benchmark = R$ 31,400 mi (matches Gazeta do Povo)")

    cul = df[df["scope"] == "funcao_13_cultura"]
    assert len(cul) == len(CULTURA_PLACEHOLDER_YEARS), \
        f"expected {len(CULTURA_PLACEHOLDER_YEARS)} cultura rows, got {len(cul)}"
    print(f"  ✓ {len(cul)} cultura placeholder rows registered (2018-2025)")


def write_parquet(df: pd.DataFrame) -> Path:
    out_path = OUT / "headlines_annual.parquet"
    con = duckdb.connect()
    con.register("df_data", df)
    con.execute(f"COPY df_data TO '{out_path}' (FORMAT PARQUET, COMPRESSION ZSTD)")
    size_kb = out_path.stat().st_size / 1024
    print(f"  ✓ {out_path.relative_to(REPO_ROOT)} — {len(df)} rows, {size_kb:.1f} KB")
    return out_path


def write_meta(out_path: Path, df: pd.DataFrame) -> None:
    meta = {
        "table": out_path.stem,
        "schema": "emendas",
        "description": (
            "Portal da Transparência — Emendas Parlamentares Federais headline "
            "series. Phase 11 Tier 1: registers the fourth federal cultural-"
            "funding pipe (alongside Rouanet/PNAB/LPG). Two scopes: "
            "all_functions (benchmark, R$ 20,6 bi in 2023 and R$ 31,4 bi in "
            "2024 — hand-transcribed from public reporting) and "
            "funcao_13_cultura (subset, populated via API-key refresh)."
        ),
        "source": (
            "Tier 1a all_functions: Agência Brasil 2023-12 + Gazeta do Povo "
            "2024-12. Tier 1b cultura: Portal da Transparência API "
            "(api.portaldatransparencia.gov.br/api-de-dados/emendas), gated on "
            "free API key from portaldatransparencia.gov.br/api-de-dados/cadastrar-email."
        ),
        "source_pages": sorted(set(df["source_page"].dropna().tolist())),
        "fetch_date": "2026-07-19",
        "etl_script": "etl/emendas__headlines_annual_to_parquet.py",
        "etl_run_date": str(date.today()),
        "licence": "Portal da Transparência — Dados abertos (CGU)",
        "grain": "one row per (year × scope)",
        "row_count": int(len(df)),
        "notes": (
            "Tier 1 — headline scope only. Full ingest (per-emenda × município "
            "× parlamentar) is Tier 2, deferred per _atana_intel/"
            "phase11_emendas_scoping.md §9. Cultura placeholder rows are "
            "populated when PORTAL_TRANSPARENCIA_API_KEY is set and --refresh "
            "flag is used."
        ),
    }
    out_path.with_suffix(".meta.json").write_text(
        json.dumps(meta, indent=2, ensure_ascii=False))
    print(f"  ✓ {out_path.with_suffix('.meta.json').relative_to(REPO_ROOT)}")


def maybe_push(df: pd.DataFrame, schema: str, table: str) -> None:
    """Push to MotherDuck if a valid JWT token is available."""
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
        print(f"  · MotherDuck push skipped for atana.{schema}.{table} — no valid token.")
        return
    con = duckdb.connect(f"md:atana?motherduck_token={token}")
    con.execute(f"CREATE SCHEMA IF NOT EXISTS atana.{schema}")
    con.register("df_data", df)
    con.execute(
        f"CREATE OR REPLACE TABLE atana.{schema}.{table} AS SELECT * FROM df_data")
    n = con.execute(f"SELECT COUNT(*) FROM atana.{schema}.{table}").fetchone()[0]
    print(f"  ✓ Synced atana.{schema}.{table} ({n} rows)")


def main() -> None:
    refresh = "--refresh" in sys.argv
    print(f"Building atana.emendas.headlines_annual (Tier 1{'b — with API refresh' if refresh else 'a — scaffold only'})...")
    df = build(refresh=refresh)
    validate(df)
    out_path = write_parquet(df)
    write_meta(out_path, df)
    maybe_push(df, "emendas", "headlines_annual")
    print("Done.")


if __name__ == "__main__":
    main()
