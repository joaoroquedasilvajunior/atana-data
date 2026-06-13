"""_probe_federal_apis.py — Diagnostic probe.

Calls each API once with a known good keyword + year, then prints the raw
JSON structure so we can adjust the parser. Run BEFORE the full crawl.

Usage:
    python atana-data/etl/_probe_federal_apis.py
"""
import json
import requests

HEADERS = {
    "Accept": "application/json",
    "User-Agent": "atana-research/1.0 (joaoroquer@gmail.com)",
}


def probe_senado():
    print("\n" + "=" * 72)
    print("SENADO — probe ('economia criativa', 2015)")
    print("=" * 72)
    url = "https://legis.senado.leg.br/dadosabertos/materia/pesquisa/lista"
    params = {"palavraChave": "economia criativa", "ano": 2015}
    r = requests.get(url, params=params, headers=HEADERS, timeout=30)
    print(f"Status: {r.status_code}")
    try:
        data = r.json()
    except ValueError:
        print(f"Não-JSON: {r.text[:500]}")
        return
    print(f"Top-level keys: {list(data.keys())}")
    pesq = data.get("PesquisaBasicaMateria", {})
    print(f"PesquisaBasicaMateria keys: {list(pesq.keys())}")
    materias_block = pesq.get("Materias", {})
    if materias_block:
        print(f"Materias block keys: {list(materias_block.keys())}")
        materias = materias_block.get("Materia", [])
        if isinstance(materias, dict):
            materias = [materias]
        print(f"# matérias: {len(materias)}")
        if materias:
            print("\n--- First matéria (full JSON, truncated to 2000 chars) ---")
            print(json.dumps(materias[0], ensure_ascii=False, indent=2)[:2000])
    else:
        print("No Materias block returned.")


def probe_camara():
    print("\n" + "=" * 72)
    print("CÂMARA — probe variants ('economia criativa', 2015-2024)")
    print("=" * 72)

    # Variant 1: keywords param
    print("\n-- Variant 1: GET /proposicoes?keywords='economia criativa'&dataInicio=2015-01-01&dataFim=2024-12-31&itens=100 --")
    url = "https://dadosabertos.camara.leg.br/api/v2/proposicoes"
    params = {
        "keywords": "economia criativa",
        "dataInicio": "2015-01-01",
        "dataFim": "2024-12-31",
        "itens": 100,
    }
    r = requests.get(url, params=params, headers=HEADERS, timeout=30)
    print(f"Status: {r.status_code}")
    try:
        data = r.json()
        print(f"Top-level keys: {list(data.keys())}")
        dados = data.get("dados", [])
        print(f"# proposições returned: {len(dados)}")
        if dados:
            print("First proposição:")
            print(json.dumps(dados[0], ensure_ascii=False, indent=2))
        links = data.get("links", [])
        print(f"# pagination links: {len(links)}")
    except ValueError:
        print(f"Não-JSON: {r.text[:500]}")

    # Variant 2: keyword (singular)
    print("\n-- Variant 2: keyword (singular) --")
    params2 = {
        "keyword": "economia criativa",
        "dataInicio": "2015-01-01",
        "dataFim": "2024-12-31",
        "itens": 100,
    }
    r = requests.get(url, params=params2, headers=HEADERS, timeout=30)
    print(f"Status: {r.status_code}")
    try:
        data = r.json()
        print(f"# dados: {len(data.get('dados', []))}")
    except ValueError:
        pass

    # Variant 3: assunto
    print("\n-- Variant 3: tema --")
    params3 = {
        "tema": "economia criativa",
        "dataInicio": "2015-01-01",
        "dataFim": "2024-12-31",
        "itens": 100,
    }
    r = requests.get(url, params=params3, headers=HEADERS, timeout=30)
    print(f"Status: {r.status_code}")
    try:
        data = r.json()
        print(f"# dados: {len(data.get('dados', []))}")
    except ValueError:
        pass

    # Variant 4: ano only, then filter client-side on ementa
    print("\n-- Variant 4: search /proposicoes/?siglaTipo=PL&ano=2015&itens=200 ; then filter --")
    params4 = {"siglaTipo": "PL", "ano": 2015, "itens": 200}
    r = requests.get(url, params=params4, headers=HEADERS, timeout=30)
    print(f"Status: {r.status_code}")
    try:
        data = r.json()
        dados = data.get("dados", [])
        print(f"# proposições no ano 2015 (siglaTipo=PL): {len(dados)}")
        if dados:
            print("Schema of first proposição:")
            print(json.dumps(dados[0], ensure_ascii=False, indent=2))
            # Client-side filter for 'economia criativa' in ementa
            matches = [p for p in dados
                       if "economia criativa" in (p.get("ementa") or "").lower()]
            print(f"# com 'economia criativa' na ementa: {len(matches)}")
            for m in matches:
                print(f"  PL {m.get('numero')}/{m.get('ano')}: "
                      f"{(m.get('ementa') or '')[:200]}")
    except ValueError:
        pass


def main():
    probe_senado()
    probe_camara()


if __name__ == "__main__":
    main()
