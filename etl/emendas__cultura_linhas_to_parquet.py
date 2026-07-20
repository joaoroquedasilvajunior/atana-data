"""Portal da Transparência — Emendas Cultura per-line fact table → Parquet.

Phase 11 Tier 2a. Deepens `atana.emendas` from annual headlines (Tier 1) to the
per-execution-line grain, carrying the fields the "control gradient" analysis
needs: WHO directed the money (nomeAutor), WHERE (localidadeDoGasto/UF), through
WHICH INSTRUMENT (tipoEmenda → RP category → control level), and on WHAT
(subfunção) — plus the full money breakdown incl. restos a pagar.

This is the author + instrument layer. It does NOT include the recipient (who
got paid) — that is Tier 2b (contratos / despesas-execucao). Genre/sobrepreço is
Tier 2c (curated, editorial-review gated).

CONTROL GRADIENT (the framing this table serves)
------------------------------------------------
Federal cultural money leaves the budget through instruments with very
different downstream control. This table classifies each emenda line into a
control level derived from tipoEmenda:

    RP-6 Individual (finalidade definida)  → controle "médio-alto"
    RP-7 Bancada                           → controle "médio"
    RP-8 Comissão                          → controle "médio-baixo"
    RP-9 Relator / REL. GERAL              → controle "baixo"  (under-tagged)
    Transferência Especial (sem finalidade)→ controle "mínimo" ("PIX orçamentário")

⚠️ The tipoEmenda→RP mapping is VERIFIED against the distinct-values dump the
certification prints (`_certify_dump()`), not assumed. tipoEmenda is stored
VERBATIM alongside the derived columns so the classification is auditable and
reversible.

CERTIFICATION
-------------
`--certify` mode dumps distinct tipoEmenda + localidade patterns and checks the
per-year line count + money sums against the Tier 1 `headlines_annual` table.
Same 5-check discipline as Tier 1 (see phase11_emendas_certify.py).

OUTPUT
------
    raw/emendas/cultura_linhas.parquet  (+ .meta.json)
    grain: one row per emenda execution line (função 13), 2018-2025 (~1,760 rows)

Usage:
    # Build/refresh from API (requires key):
    PORTAL_TRANSPARENCIA_API_KEY=xxx \
        python etl/emendas__cultura_linhas_to_parquet.py --refresh

    # Certification dump (distinct tipoEmenda, count/money vs Tier 1):
    PORTAL_TRANSPARENCIA_API_KEY=xxx \
        python etl/emendas__cultura_linhas_to_parquet.py --refresh --certify
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

CULTURA_YEARS = [2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025]

COLUMNS = [
    "codigo_emenda", "ano", "tipo_emenda", "rp_categoria", "controle_nivel",
    "nome_autor", "localidade_gasto", "uf", "funcao", "subfuncao",
    "valor_empenhado", "valor_liquidado", "valor_pago_ano",
    "valor_resto_pago", "valor_pago_total", "fetch_date",
]

# UF name → sigla (for parsing localidadeDoGasto when it's a state)
UF_MAP = {
    "acre": "AC", "alagoas": "AL", "amapá": "AP", "amazonas": "AM",
    "bahia": "BA", "ceará": "CE", "distrito federal": "DF", "espírito santo": "ES",
    "goiás": "GO", "maranhão": "MA", "mato grosso": "MT",
    "mato grosso do sul": "MS", "minas gerais": "MG", "pará": "PA",
    "paraíba": "PB", "paraná": "PR", "pernambuco": "PE", "piauí": "PI",
    "rio de janeiro": "RJ", "rio grande do norte": "RN",
    "rio grande do sul": "RS", "rondônia": "RO", "roraima": "RR",
    "santa catarina": "SC", "são paulo": "SP", "sergipe": "SE",
    "tocantins": "TO", "nacional": "BR",
}


def _br_float(v) -> float:
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


def _get_json(url: str, headers: dict, retries: int = 6):
    """GET + JSON with retry/backoff on transient 5xx/timeout; RAISE on final
    failure (certified pattern — a 504 must never silently truncate)."""
    import time
    import urllib.error
    import urllib.request
    delay, last = 2.0, None
    for attempt in range(1, retries + 1):
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=60) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            last = e
            if e.code in (429, 500, 502, 503, 504) and attempt < retries:
                print(f"      · transient HTTP {e.code} ({attempt}/{retries}) — retry {delay:.0f}s")
                time.sleep(delay); delay *= 1.7; continue
            raise
        except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
            last = e
            if attempt < retries:
                print(f"      · transient {type(e).__name__} ({attempt}/{retries}) — retry {delay:.0f}s")
                time.sleep(delay); delay *= 1.7; continue
            raise
    raise RuntimeError(f"exhausted {retries} retries for {url}: {last}")


def classify(tipo: str, autor: str) -> tuple[str, str]:
    """Map tipoEmenda (+ author sentinel) → (rp_categoria, controle_nivel).

    Keyword-based over the VERBATIM tipoEmenda. Auditable against the
    certification distinct-values dump. Unknown types → ('Outro','indefinido').
    """
    t = (tipo or "").lower()
    a = (autor or "").lower()
    # The INSTRUMENT (tipoEmenda) always wins over the author sentinel — a
    # "Emenda de Comissão" is RP-8 even if its author field says "relator".
    if "especial" in t and "finalidade" not in t:
        return "Transferência Especial (RP-6 especial)", "mínimo"
    if "individual" in t:
        return "Individual (RP-6)", "médio-alto"
    if "comiss" in t:
        return "Comissão (RP-8)", "médio-baixo"
    if "bancada" in t:
        return "Bancada (RP-7)", "médio"
    if "relator" in t:
        return "Relator (RP-9)", "baixo"
    # only fall back to the author sentinel when tipoEmenda is blank/unknown
    if "rel. geral" in a or a == "relator geral":
        return "Relator (RP-9)", "baixo"
    return "Outro/indefinido", "indefinido"


def parse_uf(localidade: str) -> str:
    if not localidade:
        return None
    key = str(localidade).strip().lower()
    if key in UF_MAP:
        return UF_MAP[key]
    # "Município (UF)" or "... - UF" heuristics
    import re
    m = re.search(r"\(([A-Z]{2})\)", str(localidade))
    if m:
        return m.group(1)
    m = re.search(r"[-/]\s*([A-Z]{2})\s*$", str(localidade))
    if m:
        return m.group(1)
    return None


def fetch() -> pd.DataFrame:
    key = os.environ.get("PORTAL_TRANSPARENCIA_API_KEY", "").strip()
    if not key:
        print("  ⚠ PORTAL_TRANSPARENCIA_API_KEY not set — cannot fetch.")
        sys.exit(1)
    base = "https://api.portaldatransparencia.gov.br/api-de-dados/emendas"
    headers = {"accept": "application/json", "chave-api-dados": key}
    import time
    import urllib.parse

    rows = []
    for year in CULTURA_YEARS:
        page, page_size, n = 1, None, 0
        while True:
            q = urllib.parse.urlencode({"ano": year, "codigoFuncao": 13, "pagina": page})
            data = _get_json(f"{base}?{q}", headers)
            if not data:
                break
            if page_size is None:
                page_size = len(data)
            for em in data:
                func = str(em.get("codigoFuncao") or em.get("funcao") or "").strip().lower()
                if func and func not in ("13", "cultura"):
                    continue
                tipo = em.get("tipoEmenda")
                autor = em.get("nomeAutor") or em.get("autor")
                rp, ctrl = classify(tipo, autor)
                pago = _br_float(em.get("valorPago"))
                resto = _br_float(em.get("valorRestoPago"))
                rows.append({
                    "codigo_emenda": em.get("codigoEmenda"),
                    "ano": year,
                    "tipo_emenda": tipo,
                    "rp_categoria": rp,
                    "controle_nivel": ctrl,
                    "nome_autor": autor,
                    "localidade_gasto": em.get("localidadeDoGasto"),
                    "uf": parse_uf(em.get("localidadeDoGasto")),
                    "funcao": em.get("funcao"),
                    "subfuncao": em.get("subfuncao"),
                    "valor_empenhado": _br_float(em.get("valorEmpenhado")),
                    "valor_liquidado": _br_float(em.get("valorLiquidado")),
                    "valor_pago_ano": pago,
                    "valor_resto_pago": resto,
                    "valor_pago_total": pago + resto,
                    "fetch_date": str(date.today()),
                })
                n += 1
            if len(data) < page_size:
                break
            page += 1
            time.sleep(2.1)
        print(f"  ✓ {year}: {n} lines")
    return pd.DataFrame(rows, columns=COLUMNS)


def validate(df: pd.DataFrame) -> None:
    print("Validating...")
    # cross-check line count + empenhado per year against Tier 1 headline table
    h = REPO_ROOT / "raw" / "emendas" / "headlines_annual.parquet"
    con = duckdb.connect()
    if h.exists():
        t1 = {r[0]: (r[1], r[2]) for r in con.execute(
            f"SELECT year, n_linhas_execucao, valor_empenhado_brl_mi "
            f"FROM '{h}' WHERE scope='funcao_13_cultura'").fetchall()}
        con.register("d", df)
        got = con.execute("""
            SELECT ano, COUNT(*), ROUND(SUM(valor_empenhado)/1e6,1)
            FROM d GROUP BY ano ORDER BY ano""").fetchall()
        ok = True
        for ano, n, emp in got:
            t = t1.get(ano)
            if t and t[0] is not None:
                if n != t[0] or abs(emp - t[1]) > 0.2:
                    print(f"  ✗ {ano}: lines {n} vs T1 {t[0]}; emp {emp} vs {t[1]}")
                    ok = False
        if ok:
            print("  ✓ per-year line count + empenhado match Tier 1 headlines")
    # every row classified
    unc = df[df["controle_nivel"] == "indefinido"]
    print(f"  · {len(unc)} lines with undefined control level "
          f"(distinct tipos: {sorted(set(unc['tipo_emenda'].dropna()))[:4]})")
    print(f"  ✓ {len(df)} total lines, {df['nome_autor'].nunique()} distinct authors")


def certify_dump(df: pd.DataFrame) -> None:
    con = duckdb.connect(); con.register("d", df)
    print("\n=== CERTIFY: distinct tipoEmenda → RP mapping ===")
    for r in con.execute("""
        SELECT tipo_emenda, rp_categoria, controle_nivel, COUNT(*) n,
               ROUND(SUM(valor_empenhado)/1e6,1) emp_mi
        FROM d GROUP BY 1,2,3 ORDER BY emp_mi DESC""").fetchall():
        print(f"  {r[3]:>4} lines · R$ {r[4]:>7.1f} mi · [{r[2]:>11}] {r[1]:<32} ← {r[0]!r}")

    print("\n=== control gradient — empenhado by control level (all years) ===")
    for r in con.execute("""
        SELECT controle_nivel, COUNT(*) n,
               ROUND(SUM(valor_empenhado)/1e6,1) emp,
               ROUND(SUM(valor_pago_total)/1e6,1) pago
        FROM d GROUP BY 1 ORDER BY emp DESC""").fetchall():
        print(f"  [{r[0]:>11}] {r[1]:>5} lines · empenhado R$ {r[2]:>7.1f} mi · pago_total R$ {r[3]:>7.1f} mi")

    print("\n=== top-15 authors by empenhado (all years) ===")
    for r in con.execute("""
        SELECT nome_autor, COUNT(*) n, ROUND(SUM(valor_empenhado)/1e6,1) emp
        FROM d GROUP BY 1 ORDER BY emp DESC LIMIT 15""").fetchall():
        print(f"  R$ {r[2]:>7.1f} mi · {r[1]:>3} lines · {r[0]}")

    print("\n=== localidade UF parse coverage ===")
    tot = len(df); parsed = df["uf"].notna().sum()
    print(f"  {parsed}/{tot} lines got a UF ({100*parsed/tot:.0f}%). "
          f"distinct localidades: {df['localidade_gasto'].nunique()}")


def write(df: pd.DataFrame) -> Path:
    out = OUT / "cultura_linhas.parquet"
    con = duckdb.connect(); con.register("d", df)
    con.execute(f"COPY d TO '{out}' (FORMAT PARQUET, COMPRESSION ZSTD)")
    print(f"  ✓ {out.relative_to(REPO_ROOT)} — {len(df)} rows, {out.stat().st_size/1024:.1f} KB")
    meta = {
        "table": "cultura_linhas", "schema": "emendas",
        "description": "Per-execution-line fact table for Função 13 (Cultura) "
                       "parliamentary amendments, 2018-2025. Author + instrument "
                       "(control-gradient) layer. tipoEmenda stored verbatim + "
                       "derived rp_categoria/controle_nivel. No recipient (Tier 2b) "
                       "or genre (Tier 2c).",
        "source": "Portal da Transparência API /emendas?codigoFuncao=13.",
        "grain": "one row per emenda execution line",
        "row_count": int(len(df)),
        "etl_script": "etl/emendas__cultura_linhas_to_parquet.py",
        "etl_run_date": str(date.today()),
        "caveats": [
            "tipoEmenda→RP mapping verified against --certify distinct dump.",
            "UF parsed from localidadeDoGasto where possible; 'Nacional'→BR.",
            "Recipient (who got paid) NOT here — Tier 2b contratos.",
            "Same E2 floor caveat as headlines (função 13 misses Turismo/RP-9-sem-função).",
        ],
    }
    out.with_suffix(".meta.json").write_text(json.dumps(meta, indent=2, ensure_ascii=False))
    print(f"  ✓ {out.with_suffix('.meta.json').relative_to(REPO_ROOT)}")
    return out


def maybe_push(df: pd.DataFrame) -> None:
    if os.environ.get("ATANA_ETL_SKIP_PUSH"):
        print("  · push skipped (ATANA_ETL_SKIP_PUSH)"); return
    def _jwt(t): t=(t or "").strip(); return t if (t.startswith("eyJ") and t.count(".")==2) else ""
    token = _jwt(os.environ.get("MOTHERDUCK_TOKEN")) or _jwt(
        (REPO_ROOT/".motherduck_token").read_text() if (REPO_ROOT/".motherduck_token").exists() else "")
    if not token:
        print("  · MotherDuck push skipped — no valid token."); return
    con = duckdb.connect(f"md:atana?motherduck_token={token}")
    con.execute("CREATE SCHEMA IF NOT EXISTS atana.emendas")
    con.register("d", df)
    con.execute("CREATE OR REPLACE TABLE atana.emendas.cultura_linhas AS SELECT * FROM d")
    n = con.execute("SELECT COUNT(*) FROM atana.emendas.cultura_linhas").fetchone()[0]
    print(f"  ✓ Synced atana.emendas.cultura_linhas ({n} rows)")


def main() -> None:
    if "--refresh" not in sys.argv:
        print("Tier 2a needs --refresh + PORTAL_TRANSPARENCIA_API_KEY (no scaffold mode).")
        sys.exit(0)
    print("Building atana.emendas.cultura_linhas (Tier 2a — author + instrument)...")
    df = fetch()
    validate(df)
    # write + push FIRST so a display-only dump bug can never cost a re-pull
    write(df)
    maybe_push(df)
    if "--certify" in sys.argv:
        certify_dump(df)
    print("Done.")


if __name__ == "__main__":
    main()
