# `atana.lexml` — Legislative Genealogy of Brazil's Creative Economy

> **Status (2026-06-14):** GitHub ✅ `411644f` on origin/main · MotherDuck ✅ live · 6 tables / 1,034 rows in `raw/lexml/`

> Methodology note. Phase 2 (foundational corpus). ETL: `etl/lexml__jsonl_to_parquet.py`.
> **Consumed by:** Análise 9 *A genealogia institucional da economia criativa no Brasil (1998–2026)* — the legal-history anchor for the book's institutional chapter · Atana Note #04 *A genealogia institucional*.

## 1. What the source is

The **LexML** is the Senado Federal's open repository of Brazilian legislative acts (federal, state, municipal). The search interface and SRU API are public and CC-BY licensed.

`atana.lexml` is a curated subset: **every legal act that uses one of 8 tracked vocabulary terms** anywhere in its title or ementa, across 1998–2026, with juridical-force re-classification applied (legal vs. bibliographic vs. administrative-of-concrete-effect). Total corpus: **269 acts**, of which 9 (4.1 %) are truly normative, 205 (94.5 %) are administrative-with-concrete-effect, and 32 are bibliographic/non-binding.

The 8 vocabulary terms tracked: *economia criativa, indústrias criativas, indústrias culturais, setor criativo, economia da cultura, creative class, creative city, creative cluster*.

The juridical-force re-classification is the analytical contribution of Análise 9. The raw LexML returns flag every act as "legislação" regardless of normative weight; the re-classification distinguishes (a) acts that *create binding rules of general application* from (b) acts that *settle one administrative matter without normative weight* from (c) bibliographic references.

## 2. Tables (6 tables)

| Table | What |
|---|---|
| `corpus` | The unified 269-act corpus — title, date, federative level (federal / estadual / municipal), publisher, juridical-force re-classification, vocabulary terms matched. |
| `legal` | The 237 acts with `tipo_documento = legislação` per the LexML raw tag — a superset of what survives the re-classification. |
| `biblio` | The 32 bibliographic / non-binding references in the corpus. |
| `classified` | The acts × the 8 tracked vocabulary terms — one row per (act × term) match, supports finding which terms travel together. |
| `instruments` | Aggregation by *instrumento jurídico* (decreto / lei / portaria / resolução…) — 90 % of the corpus is decretos, which is itself the central finding. |
| `gestoes` | Acts × political administration — the 72 % concentration under the 2019–2022 Bolsonaro government emerges here. |

All tables are read directly into Parquet from the curated JSONL store at `a9_data/lexml_*.jsonl` (analysis-tree side). The ETL is a transparent dump — no transformation beyond column-name normalisation.

## 3. Methodology / ingest notes

- **Source acquisition:** the LexML SRU API was queried for each of the 8 vocabulary terms, paginated to exhaustion, deduplicated by URN.
- **Date filter:** 1998–present. Phrase "economia criativa" enters Brazilian legal discourse in the mid-2000s; the 1998 floor catches early "indústrias culturais" usage.
- **Juridical-force re-classification:** applied manually by reading each ementa (Análise 9 §3). Three categories: *normativa-geral* (creates binding rules), *administrativa-de-efeito-concreto* (settles a specific matter without normativeness), *bibliográfica*.
- **Federative level extraction:** parsed from the URN convention — *federal* if `urn:lex:br:federal:*`, *estadual* if `urn:lex:br:<uf>:*`, *municipal* if `urn:lex:br:<uf>:<municipio>:*`.
- **Vintage:** the corpus has a single capture date (2026-05-13). Federal acts are most likely current; subnational / municipal acts have unknown freshness.

## 4. Caveats (W1–W5)

| # | Alert |
|---|---|
| W1 | **The LexML coverage of subnational law is uneven.** The 94 % DF + SP concentration is partly a search-availability artefact — many small municipalities do not register acts in LexML. The finding holds for the LexML-visible universe, not necessarily the actual legal-production universe. |
| W2 | **The juridical-force re-classification is the analyst's read, not LexML's.** Reproducibility requires the rubric in Análise 9 §3 plus the ementas. A second-reader audit would tighten the 9 / 205 / 32 split. |
| W3 | **English terms (*creative class*, *creative city*, *creative cluster*) returned zero matches.** This is itself the finding — the "creative city" rhetoric never colonised Brazilian legal language even as the gerencial vocabulary spread. Don't read zero matches as a search failure. |
| W4 | **The corpus is search-driven, not exhaustive.** Acts that mention the cultural economy in their *texto* but not in *título / ementa* are not captured. |
| W5 | **Six complementary sources are pending for v2.0** of Análise 9: DOU/IN, TCU, BNDES Procult, FIRJAN Atlas, Plano MinC 2024, and one yet-to-name acervo. Each would extend the genealogy beyond LexML's bias toward federal-level acts. |

## 5. References

- Original publication: **LexML — Senado Federal**, `lexml.gov.br`.
- Análise 9 (`analise_09_genealogia_economia_criativa.md`) — the corpus's full reading and the 14 findings.
- Atana Note #04 — the public version of the genealogy.
- `_atana_intel/scoping_lexml_2026-05-12.md` — corpus-build notes including the SRU query patterns.
