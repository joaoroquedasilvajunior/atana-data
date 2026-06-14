# Methodology — `atana.ifpi` from the IFPI Global Music Report

> **Status (2026-06-14):** GitHub ✅ `8ea01bc` on origin/main · MotherDuck 🔜 pending re-sync after schema change · 4 tables / 25 rows in `raw/ifpi/`

Schema `atana.ifpi`. **Phase 5b** of the Atana Data expansion — first ingest of
the *IFPI Global Music Report* (GMR), the global record-label-side music-revenue
flagship. The third music-money lens in the corpus after `atana.ecad` (Brazil
author royalties) and `atana.cisac` (global author royalties).

**Source:** IFPI Global Music Report 2026 (covering 2025 recorded-music
revenues; press release 18 March 2026). Public landing page; Premium Edition
country-by-country tables paywalled.
**Coverage:** Global, annual. 2025 reference year at v1 launch.
**Licence:** IFPI published figures — public press release on
<https://www.ifpi.org/global-music-report-2026-global-recorded-music-revenues-grow-6-4-as-record-companies-drive-innovation/>.
**ETLs:**
  `ifpi__gmr_2026_global_headline_to_parquet.py`,
  `ifpi__gmr_2026_global_by_format_to_parquet.py`,
  `ifpi__gmr_2026_global_by_region_to_parquet.py`,
  `ifpi__gmr_2026_top_markets_to_parquet.py`.
**Ingested:** 2026-06-01 (Tier 1).

---

## 1. Three music-money lenses, three institutional standpoints

The corpus now reads music revenue through three structurally distinct
sources:

| Lens | Source | What it measures | Who reports |
|---|---|---|---|
| **Author royalties (Brazil)** | `atana.ecad` | Public-performance music royalties collected from venues / broadcasters / digital platforms and distributed to composers, lyricists, publishers, performers and phonogram producers | ECAD (BR) |
| **Author royalties (global)** | `atana.cisac` | The CISAC global aggregate of all 228 author-society royalty collections in 111 countries | CISAC |
| **Recorded music (global)** | `atana.ifpi` ← THIS SCHEMA | Record-label revenue from sound-recording exploitation (streaming subscriptions, downloads, physical sales, sync, performance rights paid to the master-recording owner) | IFPI |

The label side (mechanical / master-recording rights) and the author side
(composition / publishing rights) flow through different value chains and can
move in opposite directions on the same market in the same year — see §3.

## 2. What the v1 ingest is

Tier 1 of the IFPI scoping. Inline-data ingest of everything the GCR 2026
**press release** already exposes — no PDF or Premium Edition required.
**`atana.ifpi`, 4 tables, 25 rows:**

| Table | Rows | Description |
|---|---:|---|
| `gmr_2026_global_headline` | 1 | 2025 global recorded-music revenue: US$ 31.7 bn (+6.4 %), 11th consecutive growth year, 837 mi paid streaming users |
| `gmr_2026_global_by_format` | 5 | Streaming (total) / Paid subscription streaming / Physical / Performance rights / Total |
| `gmr_2026_global_by_region` | 7 | USA & Canada / Europe / Asia / Latin America / Australasia / MENA / Sub-Saharan Africa — every region grew in 2025 |
| `gmr_2026_top_markets` | 12 | Countries with 2025 growth named verbatim in the press release; 7 carry the global rank |

**Not in v1 (paywalled, deferred):** the full country-by-country top-200,
the 2015-onwards historical series, format-by-region cross-tabs, and the
granular sub-format detail. These live in the GMR 2026 Premium Edition and
are a future Tier-2 ingest gated on access.

## 3. Central caveats

### (a) IFPI vs CISAC — the LATAM divergence is the v1 headline

Same year (2025 data), same region, opposite direction:

- IFPI 2025: **Latin America +17.1 %** in recorded-music revenue (fastest-
  growing region; 16th consecutive year of growth; streaming 88.1 % of
  regional revenue).
- CISAC 2024: **Latin America −0.6 %** in author-royalty collections (the
  *only* region with a decline).

The two figures are not strictly the same accounting year (IFPI 2025 vs
CISAC 2024, since CISAC publishes a year later on its own cycle), but the
direction-of-travel difference is structural, not phase. The label side
(IFPI) collects revenue from the digital platforms directly; the author
side (CISAC, and through it the national CMOs like SACM/SADAIC/SCD) collects
performance-of-the-composition royalties through a slower, more dispute-prone
multi-territory licensing chain. **The +17.7 pp gap is the corpus's first
quantitative evidence of value-chain capture across institutional layers** —
exactly the "three music-money lenses" cross-lens question the Curious
Scientist surfaced.

### (b) The named-format coverage gap (~21 %)

The press release names four formats with stated values:

- Total streaming: US$ ≈ 22 bn, 69.6 % of global, YoY not stated
- Paid subscription streaming (a SUBSET of total streaming, not additive):
  52.4 %, +8.8 %
- Physical: +8.0 % YoY, USD value not stated
- Performance rights: US$ 2.9 bn (≈ 9.1 %), +0.3 %

Total streaming (69.6 %) + Performance rights (9.1 %) = 78.7 %. The
remaining ~21.3 % is absorbed by **Physical** (modal range historically
~16-17 %) plus **Downloads + sync** (not separately named). The corpus
convention: ingest verbatim, do not allocate. Same posture as
`atana.cisac.gcr_2025_global_by_stream`'s ~9.2 % residual and
`atana.ecad.distribuicao_por_segmento`'s 1.25 % gap.

### (c) Reporting currency and FX

IFPI reports in **USD** at "independently sourced 2025 exchange rates";
**all historic local-currency values are restated annually by IFPI** so
market values can vary retrospectively because of FX movement. The corpus's
other music sources (ECAD = BRL, CISAC = EUR) need explicit FX handling for
any direct comparison — not done at v1.

### (d) Top-markets table is a press-release SUBSET, not the GMR ranking

`gmr_2026_top_markets` (12 rows) carries the countries the press release
prose names with their 2025 YoY values. It is NOT the GMR's full top-20 or
top-200 list — that is in the Premium Edition. Seven of the 12 also carry
their 2025 global rank: USA #1, Japan #2, China #4, Brazil #8, Canada #9,
Mexico #10, Australia #13. **Brazil and Mexico both in the top-10 is the
LATAM headline** the corpus did not previously carry.

## 4. Cross-corpus joins that v1 unlocks

- **Brazil:** `atana.ifpi.gmr_2026_top_markets` (Brazil +14.1 %, #8) ×
  `atana.ecad.arrecadacao_distribuicao` (Brazil 2025 arrecadação R$ 2,105 mi)
  × `atana.cisac.gcr_2025_global_by_region` (LATAM context €786 mi).
- **Mexico:** `atana.ifpi.gmr_2026_top_markets` (Mexico +13.3 %, #10) ×
  `atana.cisac.gcr_2025_leading_smaller_markets_digital_share` (Mexico
  65.1 % digital — the only LATAM cell in the GCR top-10) ×
  `atana.inegi.cscm_2024_pib_by_area` (Música y conciertos +14.9 % —
  fastest-growing CSCM cultural area). **Three independent music-Mexico
  signals**, all up double digits in 2024-2025.
- **LATAM:** `atana.ifpi.gmr_2026_global_by_region` (+17.1 %) ×
  `atana.cisac.gcr_2025_global_by_region` (−0.6 %). The cross-lens
  divergence the corpus did not previously have.

## 5. Domain mapping → 2025 UNESCO FCS

`canonical.domain_crosswalk` carries one new `ifpi` source-schema row
(2026-06-01) mapping to **Intellectual property** (transversal, `good`). All
four v1 tables share the one crosswalk row. Coverage stays **13/14** — IFPI
is the *recorded-music revenue* facet of the IP domain, alongside BCB (4c.1
flow), INPI (4c.2 stock), ECAD (4c.3 author royalties BR) and CISAC (5a author
royalties global).

## 6. Refresh and the DB-updater

IFPI publishes the GMR annually, ~March (covering the prior year). The
DB-updater can carry a calendar trigger for the next edition (GMR 2027 for
2026 data, ~March 2027). When the release lands, append rows to the four
`ROWS` lists with the new year and re-run; schemas extend by year.

## 7. Validation (2026-06-01)

All four ETLs ran clean under `ATANA_ETL_SKIP_PUSH=1`; all parquets
byte-identical on rerun.

- `gmr_2026_global_headline` — US$ 31.7 bn / +6.4 % / 837 mi paid users / 11th
  consecutive year.
- `gmr_2026_global_by_format` — 5 formats; named-streams residual (~21 %) is
  the documented anomaly; streaming US$ 22 bn / 31.7 bn = 69.4 % ≈ stated 69.6 %.
- `gmr_2026_global_by_region` — 7 regions; every region grew; LATAM fastest;
  MENA streaming share 97.5 % highest.
- `gmr_2026_top_markets` — 12 countries, 7 with global rank; Brazil + Mexico
  both top-10 confirmed.
- `canonical.domain_crosswalk` 86 → **87** rows; coverage 13/14.

## 8. Citation

> IFPI (2026). *Global Music Report 2026: Global Recorded Music Revenues Grow
> 6.4 % as Record Companies Drive Innovation*. International Federation of
> the Phonographic Industry, press release, 18 March 2026.
> <https://www.ifpi.org/global-music-report-2026-global-recorded-music-revenues-grow-6-4-as-record-companies-drive-innovation/>.

---

*Methodology note for `atana.ifpi`. Prepared 2026-06-01 at Tier 1 launch.
Phase 5b. Pairs with `ecad_relatorio_anual.md` (BR author royalties, 4c.3),
`cisac_gcr.md` (global author royalties, 5a) and `inegi_csc.md` (Mexico CSC,
extended in Phase 5b non-trade modules).*
