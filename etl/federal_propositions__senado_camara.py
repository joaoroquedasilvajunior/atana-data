"""federal_propositions__senado_camara.py — exhaustive crawl of federal legislative
proposições mentioning the 8 EC vocabulary terms.

Sources:
  - Senado Federal:  https://legis.senado.leg.br/dadosabertos (público, sem auth)
  - Câmara dos Deputados:  https://dadosabertos.camara.leg.br/api/v2 (público, sem auth)

Strategy:
  - Senado supports keyword search → query each term × year, parse FLAT schema
    (Codigo, Sigla, Numero, Ano, Ementa, Autor at root level of each matéria).
  - Câmara does NOT support keyword search (verified by probe — keywords/keyword/
    tema all return 400). Instead: fetch all proposições per year, paginate, and
    filter ementa client-side for the 8 vocabulary terms.

Output:
  - raw/lexml/federal_propositions.parquet
  - synced to atana.lexml.federal_propositions

Dependencies: requests pandas duckdb
Usage:
    export MOTHERDUCK_TOKEN="<full JWT>"
    python etl/federal_propositions__senado_camara.py
"""
import json
import os
import re
import sys
import time
from pathlib import Path

import duckdb
import pandas as pd
import requests

HERE = Path(__file__).resolve().parent.parent
OUT = HERE / "raw" / "lexml"
OUT.mkdir(parents=True, exist_ok=True)

VOCABULARY = [
    "economia criativa",
    "indústrias criativas",
    "indústrias culturais",
    "setor criativo",
    "economia da cultura",
    "creative class",
    "creative city",
    "creative cluster",
]

# Lowercase versions for case-insensitive ementa matching
VOCAB_LOWER = [t.lower() for t in VOCABULARY]
# Also strip accents for fuzzy matching
import unicodedata


def strip_accents(s: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFD", s)
        if unicodedata.category(c) != "Mn"
    )

VOCAB_STRIPPED = [strip_accents(t) for t in VOCAB_LOWER]

SENADO_BASE = "https://legis.senado.leg.br/dadosabertos"
CAMARA_BASE = "https://dadosabertos.camara.leg.br/api/v2"

HEADERS = {
    "Accept": "application/json",
    "User-Agent": "atana-research/1.0 (joaoroquer@gmail.com)",
}
TIMEOUT = 30


def get_with_retry(url, params=None, max_retries=5):
    for attempt in range(max_retries):
        try:
            r = requests.get(url, params=params, headers=HEADERS, timeout=TIMEOUT)
            if r.status_code == 200:
                return r
            if r.status_code in (400, 404):
                return r  # legitimate empty
            time.sleep(2 ** attempt)
        except requests.RequestException as e:
            print(f"    ⚠ retry {attempt+1}/{max_retries}: {e}")
            time.sleep(2 ** attempt)
    return None


def matches_vocab(text: str) -> list[str]:
    """Return list of vocabulary terms that match in the text (case-insensitive,
    accent-insensitive)."""
    if not text:
        return []
    txt_low = strip_accents(text.lower())
    return [orig for orig, lower in zip(VOCABULARY, VOCAB_STRIPPED)
            if lower in txt_low]


# ---------------------------------------------------------------------------
# Senado Federal — uses /materia/pesquisa/lista with palavraChave
# ---------------------------------------------------------------------------

def crawl_senado(term: str) -> list[dict]:
    """Senado API supports palavraChave search. Flat schema per matéria."""
    print(f"  [Senado] '{term}'")
    rows = []
    for ano in range(1998, 2027):
        url = f"{SENADO_BASE}/materia/pesquisa/lista"
        params = {"palavraChave": term, "ano": ano}
        r = get_with_retry(url, params)
        if r is None or r.status_code != 200:
            continue
        try:
            data = r.json()
        except ValueError:
            continue
        pesq = data.get("PesquisaBasicaMateria", {})
        materias_block = pesq.get("Materias", {})
        if not materias_block:
            continue
        materias = materias_block.get("Materia", [])
        if isinstance(materias, dict):
            materias = [materias]
        for m in materias:
            # Schema is FLAT — fields at root level, not nested
            rows.append({
                "casa": "Senado",
                "term_query": term,
                "ano_query": ano,
                "codigo": m.get("Codigo"),
                "sigla": m.get("Sigla"),
                "numero": m.get("Numero"),
                "ano_materia": m.get("Ano"),
                "data_apresentacao": m.get("Data"),
                "ementa": (m.get("Ementa") or "")[:1000] or None,
                "autor": m.get("Autor"),
                "url_detalhe": m.get("UrlDetalheMateria"),
            })
        time.sleep(0.2)
    print(f"    ✓ {len(rows)} matérias")
    return rows


# ---------------------------------------------------------------------------
# Câmara dos Deputados — keyword search NOT supported → fetch by year + filter
# ---------------------------------------------------------------------------

def crawl_camara_year(ano: int) -> list[dict]:
    """Fetch all proposições for a year, paginate, filter ementa client-side."""
    url = f"{CAMARA_BASE}/proposicoes"
    out = []
    pagina = 1
    pages_seen = 0
    while True:
        params = {
            "ano": ano,
            "itens": 200,
            "pagina": pagina,
            "ordem": "ASC",
            "ordenarPor": "id",
        }
        r = get_with_retry(url, params)
        if r is None or r.status_code != 200:
            break
        try:
            data = r.json()
        except ValueError:
            break
        dados = data.get("dados", [])
        if not dados:
            break
        for p in dados:
            ementa = p.get("ementa") or ""
            matches = matches_vocab(ementa)
            if matches:
                out.append({
                    "casa": "Câmara",
                    "term_query": ";".join(matches),
                    "ano_query": ano,
                    "codigo": str(p.get("id")),
                    "sigla": p.get("siglaTipo"),
                    "numero": str(p.get("numero")),
                    "ano_materia": str(p.get("ano")),
                    "data_apresentacao": p.get("dataApresentacao"),
                    "ementa": ementa[:1000],
                    "autor": None,  # would require separate /proposicoes/{id}/autores call
                    "url_detalhe": p.get("uri"),
                })
        pages_seen += 1
        # Check if there's a 'next' link in pagination
        links = data.get("links", [])
        has_next = any(L.get("rel") == "next" for L in links)
        if not has_next:
            break
        pagina += 1
        time.sleep(0.1)
        # Safety cap — no year should need >100 pages
        if pages_seen > 100:
            print(f"    ⚠ Câmara ano={ano} hit safety cap at 100 pages")
            break
    return out


def crawl_camara() -> list[dict]:
    """Fetch ALL Câmara proposições 1998-2026, filter ementa client-side."""
    print(f"\n[Câmara] crawling all proposições by year, client-side filter on {len(VOCABULARY)} termos")
    all_rows = []
    for ano in range(1998, 2027):
        t0 = time.time()
        year_rows = crawl_camara_year(ano)
        dt = time.time() - t0
        print(f"  ano {ano}: {len(year_rows):>3} matches ({dt:.1f}s)")
        all_rows.extend(year_rows)
    return all_rows


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print(f"Vocabulary ({len(VOCABULARY)} termos):")
    for t in VOCABULARY:
        print(f"  · {t}")

    print(f"\n[1/2] Senado Federal — keyword search × {len(VOCABULARY)} termos × ~29 anos")
    senado_rows = []
    for term in VOCABULARY:
        senado_rows.extend(crawl_senado(term))
    print(f"[Senado] {len(senado_rows):,} raw rows")

    print(f"\n[2/2] Câmara dos Deputados — fetch all by year + client-side filter")
    camara_rows = crawl_camara()
    print(f"[Câmara] {len(camara_rows):,} matches")

    all_rows = senado_rows + camara_rows
    print(f"\n[total] {len(all_rows):,} raw rows")

    if not all_rows:
        print("⚠ Nenhuma proposição encontrada.")
        return

    df = pd.DataFrame(all_rows)

    # Dedup by stable per-casa code
    df = df.drop_duplicates(subset=["casa", "codigo"], keep="first").reset_index(drop=True)
    print(f"[dedup by codigo] {len(df):,} unique proposições")

    # Persist locally
    out_path = OUT / "federal_propositions.parquet"
    con = duckdb.connect()
    con.execute("INSTALL parquet; LOAD parquet;")
    con.register("df", df)
    con.execute(
        f"COPY df TO '{out_path}' (FORMAT PARQUET, COMPRESSION ZSTD)"
    )
    print(f"\n✓ Saved {out_path}")

    # Sync to MotherDuck
    token = os.environ.get("MOTHERDUCK_TOKEN")
    if token:
        mcon = duckdb.connect(f"md:atana?motherduck_token={token}")
        mcon.execute("CREATE SCHEMA IF NOT EXISTS atana.lexml")
        mcon.execute(
            f"CREATE OR REPLACE TABLE atana.lexml.federal_propositions AS "
            f"SELECT * FROM '{out_path}'"
        )
        n = mcon.execute(
            "SELECT COUNT(*) FROM atana.lexml.federal_propositions"
        ).fetchone()[0]
        print(f"✓ Synced atana.lexml.federal_propositions ({n:,} rows)")

    # Summaries
    print("\n[breakdown by casa]")
    print(df.groupby("casa").size().to_string())

    print("\n[breakdown by sigla — top 15]")
    print(df.groupby("sigla").size().sort_values(ascending=False).head(15).to_string())

    print("\n[breakdown by ano_materia]")
    print(df.groupby(["casa", "ano_materia"]).size().head(50).to_string())

    # Critical test: how many promulgated federal laws?
    promulgated_siglas = ["LEI", "LEI ORDINÁRIA", "LCP", "LEI COMPLEMENTAR",
                          "LEI COMPLEMENTAR FEDERAL", "DEC", "DECRETO"]
    promulgated = df[df["sigla"].isin(promulgated_siglas)]
    print(f"\n[*** promulgated federal laws (LEI/LCP/DEC) in corpus: {len(promulgated)} ***]")
    if len(promulgated) > 0:
        print(promulgated[["casa", "sigla", "numero", "ano_materia", "ementa"]]
              .to_string(index=False)[:3000])

    # Top 20 ementas overall (preview)
    print("\n[top 20 most relevant ementas — for QA]")
    sample = df[["casa", "sigla", "numero", "ano_materia", "ementa"]].head(20)
    for _, r in sample.iterrows():
        ementa_short = (r["ementa"] or "")[:180]
        print(f"  {r['casa'][:6]:<6} {r['sigla']:<6} {r['numero']}/{r['ano_materia']}: {ementa_short}")


if __name__ == "__main__":
    main()
