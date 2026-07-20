"""Portal da Transparência — Emendas Parlamentares headline series → Parquet.

Phase 11 Tier 1 of the Atana Data expansion. The **fourth federal cultural-
funding pipe** alongside Rouanet (indirect, via `atana.salic`), PNAB (direct
generalista, via `atana.pnab`), and LPG (direct AV, via `atana.lpg`).

Phase 11 scoping: `_atana_intel/phase11_emendas_scoping.md`.
Certification:    `_atana_intel/phase11_emendas_certify.py` (5-check protocol).

CERTIFICATION-DRIVEN SCHEMA (v2, 2026-07-19)
--------------------------------------------
The first `--refresh` run (v1) exposed two problems, both fixed here:

1. **Honest field names.** The Portal `/emendas` object has NO `valorAutorizado`
   field. Its money fields are: valorEmpenhado, valorLiquidado, valorPago,
   valorRestoInscrito, valorRestoCancelado, valorRestoPago. v1's
   `valor_autorizado_brl_mi` was really *empenhado* → renamed
   `valor_empenhado_brl_mi`.

2. **Restos a pagar dominate disbursement.** A típica cultural emenda commits
   in year Y and pays most of it in Y+1/Y+2 through *restos a pagar*, NOT
   through in-year valorPago. Example (2024, RICARDO BARROS): empenhado
   R$ 23.200, pago-no-ano R$ 734, restoPago R$ 22.466 — 97 % of the money
   reached the beneficiary via restos. v1's `valor_pago_brl_mi` (in-year only)
   understated true disbursement ~5×. Fixed: this table now carries
   `valor_pago_ano_brl_mi` (in-year), `valor_resto_pago_brl_mi` (via restos),
   and `valor_pago_total_brl_mi = pago_ano + resto_pago` — the true total
   disbursement. **Any execution-rate claim MUST use pago_total, not pago_ano.**

Also from certification:
- `n_linhas_execucao` counts execution *lines*, not distinct emendas: RP-9
  Relator-Geral emendas share the sentinel code `"REL. GERAL"` and appear as
  several lines (different subfunção). Money sums across lines are correct; the
  line count is the honest grain. `n_emendas_distintas` also stored.

TIER 1 — headline scope
-----------------------
Annual aggregates ONLY, two scopes:

1. `all_functions` — total emendas (all functions), 2023/2024, hand-transcribed
   from public reporting (Agência Brasil, Gazeta do Povo). Sizes the pipe.
   Only `valor_empenhado_brl_mi` is populated (the reported headline).

2. `funcao_13_cultura` — Função 13 subset, 2018-2025, pulled from the Portal
   API (`--refresh` + PORTAL_TRANSPARENCIA_API_KEY). All money columns present.

Full per-emenda × município × parlamentar ingest is Tier 2 (deferred, ~3
sessions) — see scoping §3.

⚠️ SCOPE CAVEAT (E2). Função 13 is a FLOOR, not the whole cultural-emendas
universe: cultural shows routed through Turismo (função 23) or through
transferências especiais (RP-8/RP-9 without função) are invisible here.

OUTPUT
------
    raw/emendas/headlines_annual.parquet  (+ .meta.json)
    grain: (year × scope) — one row per year × scope value

Idempotent: inline benchmarks + API pull → DuckDB COPY to Parquet (no pyarrow).
MotherDuck push gated (skipped when ATANA_ETL_SKIP_PUSH set). Schema: atana.emendas.

Usage:
    python etl/emendas__headlines_annual_to_parquet.py            # scaffold only
    PORTAL_TRANSPARENCIA_API_KEY=xxx \
        python etl/emendas__headlines_annual_to_parquet.py --refresh  # + cultura
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
    "valor_empenhado_brl_mi",       # committed (was mis-named "autorizado")
    "valor_liquidado_brl_mi",       # liquidated in-year
    "valor_pago_ano_brl_mi",        # paid in-year
    "valor_resto_pago_brl_mi",      # paid via restos a pagar (later years)
    "valor_pago_total_brl_mi",      # = pago_ano + resto_pago (TRUE disbursement)
    "n_linhas_execucao",            # execution lines (RP-9 = several per code)
    "n_emendas_distintas",          # distinct codigoEmenda
    "source_page",
    "notes",
    "fetch_date",
]

_NULL_MONEY = {
    "valor_liquidado_brl_mi": None,
    "valor_pago_ano_brl_mi": None,
    "valor_resto_pago_brl_mi": None,
    "valor_pago_total_brl_mi": None,
    "n_linhas_execucao": None,
    "n_emendas_distintas": None,
}

AGB_2023 = "Agência Brasil (2023-12) — 'Empenho de emendas parlamentares mais que dobra em 2023'"
GAZ_2024 = "Gazeta do Povo (2024-12) — 'Emendas de parlamentares somaram R$ 31 bilhões em 2024'"

# TIER 1a — All-functions benchmarks (publicly-reported aggregates).
# NOT cultura-specific. Only valor_empenhado_brl_mi is populated (the headline
# figure the press reported); other money columns are NULL by construction.
ALL_FUNCTIONS_ROWS = [
    dict(year=2023, scope="all_functions", valor_empenhado_brl_mi=20_600.0,
         **_NULL_MONEY, source_page=AGB_2023,
         notes=("Total emendas individuais empenhadas em 2023 = R$ 20,6 bi "
                "(Agência Brasil, +93% YoY). All-functions benchmark, not "
                "cultura. Only empenhado reported."),
         fetch_date="2026-07-19"),
    dict(year=2024, scope="all_functions", valor_empenhado_brl_mi=31_400.0,
         **_NULL_MONEY, source_page=GAZ_2024,
         notes=("Total emendas 2024 (individuais + bancada + comissão) = "
                "R$ 31,4 bi (Gazeta do Povo). All-functions benchmark, not "
                "cultura. Only empenhado reported."),
         fetch_date="2026-07-19"),
]

CULTURA_YEARS = [2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025]


def _get_json(url: str, headers: dict, retries: int = 6):
    """GET + parse JSON with retry/backoff on transient errors.

    Certification finding (2026-07-19): a transient HTTP 504 Gateway Time-out
    mid-pagination previously caused the caller's loop to `break`, silently
    TRUNCATING the year (2018 dropped 212→90 lines, 2019 169→75). Fix: retry
    5xx / 429 / URLError / timeout with exponential backoff, and RAISE on final
    failure so the run aborts loudly rather than writing partial data.
    """
    import time
    import urllib.error
    import urllib.request

    delay = 2.0
    last = None
    for attempt in range(1, retries + 1):
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=60) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            last = e
            if e.code in (429, 500, 502, 503, 504) and attempt < retries:
                print(f"      · transient HTTP {e.code} (attempt {attempt}/{retries}) "
                      f"— retrying in {delay:.0f}s")
                time.sleep(delay); delay *= 1.7; continue
            raise
        except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
            last = e
            if attempt < retries:
                print(f"      · transient {type(e).__name__} (attempt "
                      f"{attempt}/{retries}) — retrying in {delay:.0f}s")
                time.sleep(delay); delay *= 1.7; continue
            raise
    raise RuntimeError(f"exhausted {retries} retries for {url}: {last}")


def _br_float(v) -> float:
    """Parse a Portal Brazilian-formatted money string ('1.234.567,89')."""
    if v is None or v == "":
        return 0.0
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).strip()
    if "," in s and "." in s:
        s = s.replace(".", "").replace(",", ".")
    elif "," in s:
        s = s.replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return 0.0


def build(refresh: bool = False) -> pd.DataFrame:
    rows = list(ALL_FUNCTIONS_ROWS)
    if refresh:
        rows.extend(_fetch_cultura_from_api())
    else:
        for y in CULTURA_YEARS:
            rows.append(dict(
                year=y, scope="funcao_13_cultura",
                valor_empenhado_brl_mi=None, **_NULL_MONEY,
                source_page="Portal da Transparência API — pending",
                notes=("Awaits Portal da Transparência API key. Signup: "
                       "portaldatransparencia.gov.br/api-de-dados/cadastrar-email. "
                       "Rerun with PORTAL_TRANSPARENCIA_API_KEY=xxx --refresh."),
                fetch_date=None))

    df = pd.DataFrame(rows, columns=COLUMNS)
    df = df.sort_values(["scope", "year"]).reset_index(drop=True)
    df["year"] = df["year"].astype("int32")
    df["n_linhas_execucao"] = df["n_linhas_execucao"].astype("Int32")
    df["n_emendas_distintas"] = df["n_emendas_distintas"].astype("Int32")
    return df


def _fetch_cultura_from_api() -> list[dict]:
    """Pull Função 13 (Cultura) annual aggregates from the Portal API.

    Query param is `codigoFuncao=13` (verified by certification — `funcao=13`
    silently returns ALL functions). Money fields parsed with _br_float.
    valor_pago_total = valorPago (in-year) + valorRestoPago (via restos).
    """
    import time
    import urllib.parse
    import urllib.request

    key = os.environ.get("PORTAL_TRANSPARENCIA_API_KEY", "").strip()
    if not key:
        print("  ⚠ PORTAL_TRANSPARENCIA_API_KEY not set — cultura rows NULL.")
        return [dict(
            year=y, scope="funcao_13_cultura",
            valor_empenhado_brl_mi=None, **_NULL_MONEY,
            source_page="Portal da Transparência API — key not provided",
            notes="PORTAL_TRANSPARENCIA_API_KEY missing.", fetch_date=None)
            for y in CULTURA_YEARS]

    base = "https://api.portaldatransparencia.gov.br/api-de-dados/emendas"
    fetched = []
    for year in CULTURA_YEARS:
        emp = liq = pago = resto = 0.0
        n_lines = 0
        codes = set()
        page, page_size = 1, None
        sample_fields: list[str] = []
        headers = {"accept": "application/json", "chave-api-dados": key}
        while True:
            q = urllib.parse.urlencode(
                {"ano": year, "codigoFuncao": 13, "pagina": page})
            # _get_json retries transient 5xx/timeout and RAISES on final
            # failure — so a 504 can no longer silently truncate the year.
            data = _get_json(f"{base}?{q}", headers)
            if not data:
                break
            if page_size is None:
                page_size = len(data)
                sample_fields = list(data[0].keys())
            for em in data:
                # client-side função guard (Portal returns label 'Cultura')
                func = str(em.get("codigoFuncao") or em.get("funcao") or "").strip().lower()
                if func and func not in ("13", "cultura"):
                    continue
                emp += _br_float(em.get("valorEmpenhado"))
                liq += _br_float(em.get("valorLiquidado"))
                pago += _br_float(em.get("valorPago"))
                resto += _br_float(em.get("valorRestoPago"))
                n_lines += 1
                codes.add(em.get("codigoEmenda"))
            # terminate on a short page (never trust a hardcoded size)
            if len(data) < page_size:
                break
            page += 1
            time.sleep(2.1)  # 30 req/min free-tier rate limit

        pago_total = pago + resto
        fetched.append(dict(
            year=year, scope="funcao_13_cultura",
            valor_empenhado_brl_mi=round(emp / 1e6, 2),
            valor_liquidado_brl_mi=round(liq / 1e6, 2),
            valor_pago_ano_brl_mi=round(pago / 1e6, 2),
            valor_resto_pago_brl_mi=round(resto / 1e6, 2),
            valor_pago_total_brl_mi=round(pago_total / 1e6, 2),
            n_linhas_execucao=n_lines,
            n_emendas_distintas=len(codes),
            source_page=f"Portal da Transparência API — /emendas?ano={year}&codigoFuncao=13",
            notes=(f"{n_lines} execution lines, {len(codes)} distinct codes "
                   f"(RP-9 share the sentinel 'REL. GERAL'). pago_total = "
                   f"pago_ano + resto_pago. Fields: {', '.join(sample_fields[:8])}."),
            fetch_date=str(date.today())))
        print(f"  ✓ {year}: {n_lines} lines · emp R$ {emp/1e6:.1f} mi · "
              f"pago_ano R$ {pago/1e6:.1f} mi · resto_pago R$ {resto/1e6:.1f} mi "
              f"· pago_total R$ {pago_total/1e6:.1f} mi "
              f"({100*pago_total/emp if emp else 0:.0f}% of emp)")
    return fetched


def validate(df: pd.DataFrame) -> None:
    print("Validating...")
    scopes = set(df["scope"].unique())
    assert scopes == {"all_functions", "funcao_13_cultura"}, f"scopes: {scopes}"
    print("  ✓ two scopes present")

    all_fn = df[df["scope"] == "all_functions"]
    assert all_fn["valor_empenhado_brl_mi"].notna().all()
    r24 = float(all_fn[all_fn["year"] == 2024]["valor_empenhado_brl_mi"].iloc[0])
    assert abs(r24 - 31400.0) < 1.0, f"2024 benchmark {r24} != 31400"
    print("  ✓ all-functions benchmarks (2023, 2024) — 2024 = R$ 31,400 mi")

    cul = df[df["scope"] == "funcao_13_cultura"]
    assert len(cul) == len(CULTURA_YEARS)
    print(f"  ✓ {len(cul)} cultura rows (2018-2025)")

    # If populated: invariants pago_ano ≤ liquidado ≤ empenhado; total = ano+resto
    pop = cul[cul["valor_empenhado_brl_mi"].notna()]
    if len(pop):
        for _, r in pop.iterrows():
            emp, liq = r["valor_empenhado_brl_mi"], r["valor_liquidado_brl_mi"]
            pa, rp, tot = (r["valor_pago_ano_brl_mi"], r["valor_resto_pago_brl_mi"],
                           r["valor_pago_total_brl_mi"])
            assert pa <= liq + 0.05, f"{r['year']}: pago_ano>liq"
            assert liq <= emp + 0.05, f"{r['year']}: liq>emp"
            assert abs((pa + rp) - tot) < 0.05, f"{r['year']}: total != ano+resto"
            assert tot <= emp + 0.05, f"{r['year']}: pago_total>emp"
        print(f"  ✓ invariants hold for {len(pop)} populated cultura rows "
              f"(pago_ano≤liq≤emp; total=ano+resto; total≤emp)")
        # surface the true execution rate
        rates = [(int(r["year"]),
                  round(100 * r["valor_pago_total_brl_mi"] / r["valor_empenhado_brl_mi"]))
                 for _, r in pop.iterrows() if r["valor_empenhado_brl_mi"]]
        print("  · execution rate (pago_total/emp): "
              + ", ".join(f"{y} {v}%" for y, v in rates))
    else:
        print("  · cultura rows are NULL scaffolds (run --refresh to populate)")


def write_parquet(df: pd.DataFrame) -> Path:
    out_path = OUT / "headlines_annual.parquet"
    con = duckdb.connect()
    con.register("df_data", df)
    con.execute(f"COPY df_data TO '{out_path}' (FORMAT PARQUET, COMPRESSION ZSTD)")
    print(f"  ✓ {out_path.relative_to(REPO_ROOT)} — {len(df)} rows, "
          f"{out_path.stat().st_size/1024:.1f} KB")
    return out_path


def write_meta(out_path: Path, df: pd.DataFrame) -> None:
    meta = {
        "table": out_path.stem,
        "schema": "emendas",
        "description": (
            "Portal da Transparência — Emendas Parlamentares Federais headline "
            "series (v2, certification-driven schema). Fourth federal cultural-"
            "funding pipe. Two scopes: all_functions benchmark (2023 R$ 20,6 bi, "
            "2024 R$ 31,4 bi) and funcao_13_cultura (2018-2025, full money "
            "breakdown incl. restos a pagar). valor_pago_total = pago_ano + "
            "resto_pago is the TRUE disbursement; in-year pago alone understates "
            "it ~5× because cultural emendas pay mostly through restos."),
        "source": (
            "Tier 1a: Agência Brasil 2023-12 + Gazeta do Povo 2024-12. Tier 1b: "
            "Portal da Transparência API /emendas?codigoFuncao=13, free key from "
            "portaldatransparencia.gov.br/api-de-dados/cadastrar-email."),
        "certification": "_atana_intel/phase11_emendas_certify.py — C2/C3/C4/C5 "
                         "pass; C1 drove this v2 schema (restos + honest names).",
        "source_pages": sorted(set(df["source_page"].dropna().tolist())),
        "fetch_date": "2026-07-19",
        "etl_script": "etl/emendas__headlines_annual_to_parquet.py",
        "etl_run_date": str(date.today()),
        "licence": "Portal da Transparência — Dados abertos (CGU)",
        "grain": "one row per (year × scope)",
        "row_count": int(len(df)),
        "caveats": [
            "E2 — Função 13 is a FLOOR; cultural money in Turismo (fn 23) or "
            "transferências especiais (RP-8/9 sem função) is invisible.",
            "n_linhas_execucao counts execution lines; RP-9 relator emendas "
            "share the sentinel code 'REL. GERAL' — n_emendas_distintas < lines.",
            "Any execution-rate claim must use valor_pago_total, not pago_ano.",
        ],
    }
    out_path.with_suffix(".meta.json").write_text(
        json.dumps(meta, indent=2, ensure_ascii=False))
    print(f"  ✓ {out_path.with_suffix('.meta.json').relative_to(REPO_ROOT)}")


def maybe_push(df: pd.DataFrame, schema: str, table: str) -> None:
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
    con.execute(f"CREATE OR REPLACE TABLE atana.{schema}.{table} AS SELECT * FROM df_data")
    n = con.execute(f"SELECT COUNT(*) FROM atana.{schema}.{table}").fetchone()[0]
    print(f"  ✓ Synced atana.{schema}.{table} ({n} rows)")


def main() -> None:
    refresh = "--refresh" in sys.argv
    print(f"Building atana.emendas.headlines_annual (v2 — Tier 1"
          f"{'b + API refresh' if refresh else 'a scaffold'})...")
    df = build(refresh=refresh)
    validate(df)
    out_path = write_parquet(df)
    write_meta(out_path, df)
    maybe_push(df, "emendas", "headlines_annual")
    print("Done.")


if __name__ == "__main__":
    main()
