# `atana.ibge_comex` — IBGE Brazilian Cultural Foreign Trade (SIIC Ch. 10)

> **Status (2026-06-14):** GitHub ✅ `0921400` on origin/main · MotherDuck ✅ live · 4 tables / 1,298 rows in `raw/ibge_comex/`

> Methodology note. Phase 1 (foundational corpus). ETL: `etl/ibge_comex__xlsx_to_parquet.py`.
> **Consumed by:** Análise 10 (anchor) · Atana Index Vol. 1 (Brazil drill-down in §6.bis) · Note #03 (cross-source UNCTAD × IBGE methodological gap) · Note #18 (OECD No. 59 × IBGE Comex Authenticity Paradox).

## 1. What the source is

The **IBGE — Informações Culturais (SIIC) chapter 10** is *Comércio exterior de bens e serviços culturais*. It re-cuts two underlying administrative sources through a fixed list of cultural-trade codes:

- **SECEX/MDIC** for goods — declared NCM customs codes, in BRL FOB, monthly aggregated to annual.
- **Banco Central do Brasil (BCB) Balance of Payments** for the audiovisual services line — in BRL current, BPM6 basis (post-2016) / BPM5 basis (pre-2016, with a break).

Chapter 10 is **the only published series that gives Brazil's cultural trade by capítulo NCM in BRL**, harmonised to a stable cultural codelist. It is also the only Brazilian source that pairs goods and services in one chapter, allowing a goods-vs-services comparison without leaving the IBGE corpus.

## 2. Tables (4 tables)

| Table | What |
|---|---|
| `tab_10_1` | Cultural balance — exports / imports / balance by capítulo NCM × ano (2014–2024). The headline cultural-balance series. |
| `tab_10_2` | Same as 10.1 but expressed as **% of cultural total per year** — gives the composition of the cultural import / export basket. |
| `tab_10_3` | **Top-20 trade partners × ano × fluxo (export vs import)** for cultural trade. This is the source of the "China 41 % → 56 % of cultural imports" finding in Análise 10. |
| `tab_10_4` | **Audiovisual services balance** — receita / despesa / saldo in BRL (BCB BoP, 2014–2024). The carve-out that distinguishes Brazil's services position from its goods-side dependency. |

## 3. Methodology / ingest notes

- **ETL pattern:** openpyxl → DuckDB COPY → Parquet (ZSTD). Wide format preserved as-published; the column for value carries the BRL number, the column immediately right carries the share when applicable.
- **No deflation in-schema** — values are BRL nominal of the published vintage. For real comparisons across years, deflate with `atana.macro.ipca` or convert to USD via `atana.macro.fx_brl_usd_annual`. The figT8 chart in Análise 10 reconciles the SECEX/IBGE NCM measurement (R$ 4 bi / US$ 746 mi 2024) against the UNCTAD CER measurement (US$ 1.358 mi goods + US$ 7.188 mi services), showing the 5.3× gap between bens and serviços as the central finding.
- **BPM5 → BPM6 break:** the audiovisual services series in 10.4 crosses a methodological break in 2016 when BCB migrated from BPM5 to BPM6 for the BoP. The 2014–2015 cells are BPM5; 2016 onward is BPM6. This is the artefact behind the "audiovisual surplus reversal" reading in Análise 10 §7 — note the artefact when narrating.

## 4. Caveats (W1–W6)

| # | Alert |
|---|---|
| W1 | **The cultural codelist is goods-only on the NCM side.** All BCB services other than audiovisual (e.g. publishing services, music streaming royalties) are absent. The "Brazil cultural trade balance" headline is a goods-balance figure, not a goods+services figure. |
| W2 | **Capítulos 84 + 85 + 95 = 77 % of cultural imports.** Cultural goods imports are dominated by *equipamentos e materiais de apoio* — the "balança cultural" is, in practice, a *balança de equipamentos*. Use the cultural cut, don't claim it measures cultural-industry output. |
| W3 | **Capítulo 97 (objetos de arte) grew +680 % in exports over the decade.** Single capítulo, single product line — verify with primary SECEX data before headlining this as a trend. |
| W4 | **BRL nominal across vintages** — apparent series growth in BRL terms is partly nominal. The "déficit doubled" reading in Análise 10 v1 was corrected (revision 2026-05-18) — in real R$ +15 %, in USD −11 %. The structural composition still holds; the magnitude doesn't. |
| W5 | **Audiovisual services 2024 inversion** — the saldo collapses from +R$ 1.2 bi to −R$ 16 mi in a single year, driven by a doubling of despesa. Either a reclassification or a real shift; cross-check with BCB notes técnicas before publishing. |
| W6 | **The cultural codelist used by SIIC is not the same as UNCTAD's CER goods codelist** — see Note #03 for the methodological gap. The pluralism is the finding, not a problem. |

## 5. References

- Data Context Skill at `.claude/skills/ibge-comercio-exterior-cultural/` (SKILL.md, key_metrics.md, warnings.md, recipes.md).
- Original publication: **IBGE — Informações Culturais 2024**, capítulo 10.
- CLAUDE.md §8 (Análise 10 anchor) and §13.2 (Atana Index Vol. 1 §6.bis).
