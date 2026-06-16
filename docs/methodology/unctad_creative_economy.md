# `atana.unctad` — UNCTAD Creative Economy Trade Statistics

> **Status (2026-06-14):** GitHub ✅ `411644f` on origin/main · MotherDuck ✅ live · 26 tables / 25,443,890 rows · ⚠ 1 corrupt parquet in `raw/unctad/`

> Methodology note. Phase 1 (foundational corpus). ETL: `etl/unctad__export_parquet.py`.
> **Consumed by:** Análise 4 *Comércio criativo na América Latina* · Análise 6 *LATAM na Era Agêntica* · **Atana Index Vol. 1** (the entire publication is anchored on this schema) · Note #03 (UNCTAD × IBGE methodological pluralism) · Note #07 (UNCTAD × CSCM) · Note #08 (IFPI × CISAC × UNCTAD).

## 1. What the source is

**UNCTAD Creative Economy Statistics** is the United Nations Conference on Trade and Development's international compilation of creative-goods and creative-services trade by country, by CER (Creative Economy Reporting) code, by year. It is the only globally standardised series for cross-country comparison of cultural trade.

The corpus covers **15 LATAM countries × 1995–2024 × 13 CER goods leaves + 7 CER services categories**. UNCTAD publishes annually (typically October release); the 2024 vintage was ingested at the last refresh and is the current snapshot. Source data is filed by national customs / BoP authorities to UN Comtrade and re-aggregated by UNCTAD onto the CER codelist.

The CER framework groups creative goods into 7 top-level aggregates (CER010 Audiovisuals, CER020 Design, CER030 Publishing, CER040 Performing Arts goods, CER050 Visual Arts goods, CER060 New Media, CER070 Visual Arts other) which themselves decompose into the 13 leaves used in the HHI computation of Análises 4 and 6.

## 2. Tables (26 tables)

The schema is wide on the time dimension — one Parquet per year for goods, plus aggregated growth/services tables. Convention: `goods_value_<yyyy>` for the per-year goods snapshot, plus services + growth aggregations.

| Family | Tables | What |
|---|---|---|
| **Goods per year** (~23) | `goods_value_2002` … `goods_value_2024` | Per-year cross-section: country × CER leaf × value (US$ thousand). 23 vintages, ingested from the UNCTADstat downloads. |
| **Growth aggregation** | `goods_growth` | YoY and CAGR aggregations across the per-year tables — used by Análise 6 to compute the trajectory rather than year-pick. |
| **Services countries** | `services_countries` | Per-country creative-services trade values 1995–2024. Returns empty for Mexico, Chile, Argentina (the "Data Gap Zone" of fig8) — see W2. |
| **Services aggregation** | `services_aggregation` | Region-level services aggregates (Latin America, etc.) for the comparisons in Atana Index §3. |

The headline-charting schemas of the Atana Index (the fig8 quadrant, the latam_fig3 HHI) are computed in the analysis layer (`gen_latam_fig8_v4.py`, `gen_unctad_charts.py`) directly against these Parquets.

## 3. Methodology / ingest notes

- **ETL pattern:** the UNCTADstat downloads are CSV; `unctad__export_parquet.py` parses + writes Parquet (ZSTD). Idempotent.
- **Currency:** values in USD thousand throughout. Comparisons across years can be made nominal-USD; for real comparisons, deflate with an external CPI series (US BLS or similar — not in `atana.macro`).
- **CER 7-aggregate vs 13-leaf distinction is essential:** HHI computed over the 7 aggregates gives wrong concentration numbers (Atana Index v1.0–v1.5 carried this bug; v1.6 fixed it). Always use the 13 leaves when computing structural-concentration metrics.
- **Exposure index** (Atana Index §3): `(creative services + digital goods [CER010+CER060] + publishing [CER030]) / total creative exports`. The Atana definition; not UNCTAD's. For countries without services reported (MX/CL/AR), the index is computed on digital goods only as a *lower bound* — flagged in fig8 with the † symbol.
- **Readiness index** (Atana Index §3): `0.40 × services_share + 0.40 × log-scale + 0.20 × (1 − HHI) × 100`. For countries without services: `0.50 × scale + 0.50 × diversification`.

## 4. Caveats (W1–W6)

| # | Alert |
|---|---|
| W1 | **The 2024 ingest is the current snapshot;** the next UNCTAD release (typically October 2026) will revise some 2023 values too. The DB-updater agent monitors this — see `_atana_intel/agents/db_updater.md`. |
| W2 | **Services are not reported for Mexico, Chile, Argentina** in UNCTAD's compilation as of the 2024 vintage — Mexico is the largest LATAM economy but appears in fig8 as goods-only (the 'Data Gap Zone'). Note #07 documents the cross-source repair: cross with INEGI CSCM and Mexico moves from Q3 (Data Gap) to Q1 (Transformation Race). |
| W3 | **The UNCTAD CER codelist is not the same as Brazil's NCM cultural codelist** — see figT8 of Análise 10 for the methodological gap visualised. Cross-source readings must declare which classification is in play. |
| W4 | **Definitions vary across national customs filings.** A "creative good" is ultimately a declaration choice at the border; cross-country comparisons carry this implicit standardisation noise. UNCTAD's harmonisation reduces but does not eliminate it. |
| W5 | **HHI computed at country level** carries small-economy noise — Bolivia at 0.952 means *one CER leaf accounts for 95 % of cultural exports* (jewellery); the metric is structurally informative but a single-product economy will always look 'concentrated'. |
| W6 | **The 1995–2001 vintage is missing for some countries** because UNCTADstat's coverage starts later for smaller economies. Time-series back to 1995 is reliable only for the largest LATAM countries (Brazil, Mexico, Argentina, Colombia). |

## 5. References

- Original publication: **UNCTADstat — Creative Economy**, `unctadstat.unctad.org`.
- Análise 4 + Análise 6 — the LATAM-trade and LATAM-on-the-Two-Time-Zones anchors.
- Atana Index Vol. 1 (`Atana_Index_Vol1.html`) — the corpus's most public consumer of this schema.
- Note #03 — the UNCTAD × IBGE Comex pluralism note that opens the corpus's methodological-pluralism convention.
