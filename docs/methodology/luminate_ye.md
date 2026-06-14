# Luminate Year-End Music Industry Report — consumer / catalog-supply lens

> **Status (2026-06-14):** GitHub ✅ `5fa9c34` on origin/main · MotherDuck ✅ live · 4 tables / 14 rows in `raw/luminate/`

**Schema:** `atana.luminate` · **Tables:** 4 · **Rows:** 14 · **Ingested:** 2026-06-04 (Phase 5c)

**Luminate** is the data company behind the Billboard charts (jointly owned with PMC) and the Recording Academy's GRAMMY analytics. Its *Year-End Music Industry Report* aggregates global streaming consumption from the platform surface — what listeners played, how much catalog exists, and how concentrated paid consumption is by country and genre.

This is the **fourth music-money lens** in the Atana corpus, closing the cross-lens frame the corpus has been building:

| Lens | Schema | Stage of the value chain |
|---|---|---|
| Author payout (Brazil, music-only) | `atana.ecad` | What rights-holders receive in BRL |
| Author collection (global, all repertoire) | `atana.cisac` | What CMOs collect globally |
| Recorded-music revenue (global, all repertoire) | `atana.ifpi` | Label-side revenue (mechanicals + distribution) |
| **Consumer / catalog supply (global)** | **`atana.luminate`** | **What listeners play; how much catalog exists** |

Each lens at a different stage. The cross-reading is the value of the conjunction.

## §1. Tier 1 — what's in this ingest

Headline figures from Luminate's *Year-End 2025 Music Industry Report* (released January 2026). Numbers verified against Music Business Worldwide coverage (22 January 2026), which transcribes the report's published figures.

The May 2026 *State of the Industry* conference deck, also from Luminate, is a separate release; PDF-gated behind a Luminate lead form. Not in this ingest.

## §2. Tables

### `ye2025_global_headline` (1 row × 2025)

The global headline. **5.1 trillion** ondemand audio streams globally (+9.6 % YoY), ex-US **3.7 tn** (+11.6 %), US **1.4 tn** (+4.6 %) — the rest-of-world component is now ~73 % of the global stream count and growing faster. Catalog supply: **253 million tracks** on streaming services at year-end, +37.9 mi YoY ≈ 106 k uploaded per day. **120.5 million tracks (47.6 %) received fewer than 10 streams in 2025** — the catalog-saturation finding (`long-tail of almost-zero`).

### `ye2025_top_markets_paid_share` (4 rows × 2025)

The countries that together account for ~half of global *paid* (premium) ondemand audio streams: **USA, Mexico, Brazil, Germany**. USA holds 31 % of global paid streams alone (rank #1). Volume growth in paid streams: USA +65.5 bn, Mexico +50.9 bn, Brazil +38.6 bn — the LATAM positioning is consistent with IFPI's regional ranking (LATAM +17.1 %, fastest-growing region) and with Mexico #10 / Brazil #8 in the IFPI top markets.

### `ye2025_us_genre_share` (5 rows × 2025)

US-only genre breakdown: R&B/Hip-Hop 25.5 % (−0.8 pp, still #1), Rock 15.3 % (flat), Pop 12.6 % (+0.3), **Latin 8.0 % (+0.6 pp = largest share gainer)**, Christian/Gospel 3.5 % (+0.4). Latin's US-share gain matches the IFPI LATAM +17.1 % regional narrative — the same gravity inside the US market itself.

### `ye2025_most_local_markets` (4 rows × 2025)

The countries where domestic-language repertoire dominates streaming most: India 79.2 %, **Brazil 75.2 %**, Turkey 69.9 %, Nigeria 62.2 %. Brazil's 75.2 % paired with Brazil's #3 absolute paid-stream volume growth (+38.6 bn YoY) is the *Authenticity Paradox in stereo*: massive local consumption × massive volume growth × CISAC LATAM author collection contracting (−0.6 %). Three camera angles on the same year.

## §3. Cross-lens reading — Note #08 extension

The W23 briefing flagged this as a Note #08 *extension* candidate. The cross-source quantification:

- **IFPI LATAM 2024 retail = +17.1 %** (label-side revenue, recorded music)
- **CISAC LATAM 2024 collections = −0.6 %** (author-royalty collection from CMOs)
- **Luminate Brazil paid-stream volume growth 2025 = +38.6 bn (#3 absolute globally)** (consumer-platform side)
- **Luminate Brazil local repertoire share 2025 = 75.2 % (#2 globally)** (consumer-platform side)

Putting the four together: Brazil consumes massively local repertoire on streaming; the platform side captures a large premium-stream volume growth; the recorded-music side captures regional growth; but the *authors* in the LATAM region collected less. This is the **Authenticity Paradox** documented in a single year of evidence — value flows to platform + label, not to creator + CMO, even in markets where local repertoire dominates.

The Mexico case is the convergence-pole: IFPI México +13.3 % × INEGI CSCM 2024 Música y conciertos +14.9 % × Luminate Mexico paid-stream volume growth +50.9 bn (#2 absolute) — three lenses pointing the same direction. Brazil is the divergence-pole. The contrast between the two is the substantive content of the Note #08 extension.

## §4. What this schema is NOT

- **Not the Luminate Connect microdata.** Per-track and per-artist Luminate streaming data sits behind the Luminate Connect paywall ($$). v1 captures publicly cited headline figures only.
- **Not multi-year history.** v1 carries 2025 only. The May 2026 mid-year State of the Industry deck would extend to 2026-H1; Tier 2 work.
- **Not exhaustive country coverage.** Only the four countries the Year-End Report explicitly names in the paid-stream concentration cell. Genre detail is US-only in the public Year-End summary.

## §5. Sources

- Luminate Year-End 2025 Music Industry Report: <https://luminatedata.com/reports/yearend-music-industry-report-2025>
- Music Business Worldwide coverage (22 Jan 2026): <https://www.musicbusinessworldwide.com/half-of-all-paid-music-streams-globally-derive-from-just-4-countries-and-other-highlights-from-luminates-latest-report>

## §6. Caveats

- Local-repertoire share is measured by *language*, not rights-ownership country. A Brazilian Portuguese song owned by a Universal Music Brasil subsidiary still counts as local repertoire here. This is the definitional gap with the IFPI label-side accounting.
- Luminate excludes ad-free YouTube Music and certain national platforms (e.g., specific China-based services) — see Luminate methodology notes; cross-lens comparisons against IFPI / CISAC carry that residual offset.
- The "free vs paid" stream split is reported by Luminate but only partially cited in the public Year-End; full split is in the conference deck.
- Year-End Report is published annually in January, covering the previous year. Cadence: monitor for Year-End 2026 (~Jan 2027) and the May 2026 State of the Industry (already past). Curious Scientist monitors.

## §7. Crosswalk position

`canonical.domain_crosswalk` → 1 row: `luminate / ye2025-streaming-supply → Music (cultural, good)`, ★-flagged as the fourth music-money lens. FCS coverage meter unchanged at 13/14 — Luminate deepens Music, doesn't extend coverage.
