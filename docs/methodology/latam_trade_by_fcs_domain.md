# `canonical.latam_trade_by_fcs_domain` — cross-LATAM cultural trade through the FCS 2025 spine

> Methodology note. Built 2026-06-10 (Phase 6a.2). Build script:
> `etl/canonical__build_latam_trade_by_fcs.py` → `curated/latam_trade_by_fcs_domain.parquet`.
> This is the materialised form of "the query the crosswalk was built to enable"
> (`_atana_intel/phase6_corpus_criterion_and_vol2_scoping.md` §2).

## 1. What this is

One curated table — **794 rows**, grain `country × year × flow × fcs2025_domain` —
holding the cultural-trade flows of the five corpus countries resolved onto the
2025 UNESCO FCS domain spine via `canonical.domain_crosswalk`:

| Country | Rows | Years | Source basis (`basis`) | USD? |
|---|---:|---|---|---|
| Mexico | 306 | 2008–2024 | `csc_supply_use` — CSCM oferta-utilización, current MXN | ✅ derived (fx_mxn) |
| Colombia | 242 | 2014–2024 | `csc_supply_use` — CSECC product balances, current COP | ✅ derived (fx_cop) |
| Costa Rica | 120 | 2010–2024 | `csc_trade_table` — CSCCR dedicated table, CRC | ✅ derived (fx_crc) |
| Brazil | 88 | 2014–2024 | `ncm_goods_only_pure_chapters` — IBGE Comex, R$ FOB | ✅ derived (`atana.macro`) |
| Argentina | 38 | 2004–2022 | `csc_segment_constant2004` — SInCA segments, ARS | **❌ NULL by design** |

## 2. Comparability is annotated, not asserted

The five sources measure different things under the one name "cultural trade".
Every row carries `basis` + `comparability_note`; the three structural caveats:

1. **Brazil is the narrow column** — goods-only, customs-based, restricted to the
   five 100%-cultural NCM chapters (37/46/49/92/97). No services, no
   partially-cultural chapters. Brazil's numbers are therefore a *floor*, not a
   comparable total; the classification difference vs the CSC supply-use sources
   is deliberate and visible (the Note #03 move at LATAM scale).
2. **Argentina's empty USD cells are the finding** — under the brecha cambiaria
   any single ARS→USD conversion asserts a rate choice; see `sinca_csc.md` §8.
   Values are constant-2004 ARS thousand; series ends 2022.
3. **Costa Rica's 2022+ rows go n.d. outside Editorial** — the coverage break is
   kept as NULL-valued rows with a ⚠️ note, never dropped or interpolated.

Also: Colombia carries `year_status` vintages (definitivo/provisional/preliminar)
upstream; Mexico 2024 is preliminary upstream; FX-derived USD inherits the
flow-vs-stock rules of `macro_fx_brl.md` §4 and its per-country siblings.

## 3. Headline findings at build time (2026-06-10)

- **Colombia Audiovisual exports ×4.2 in three years** — US$ 38.8M (2021) →
  **162.3M** (2024). The largest relative move in the table; unpublished cross-source.
- **Mexico ICT/digital ×2.4** — US$ 439.8M (2021) → 1,043.0M (2024).
- **Mexico dwarfs the rest**: ~US$ 3.7bn cultural exports (2021) vs Colombia
  ~US$ 117M, Costa Rica ~US$ 36M, Brazil (goods-floor) ~US$ 264M.
- **Brazil's pure-chapter exports 2021→2024**: Visual arts 174.4→282.6 ·
  Books 62.8→88.8 · AV 21.8→33.0 · Music 4.7→5.2 (the cap-97 art pillar of A10).

## 4. Validation (in-script, every build)

Per-country presence; MX 2021 exports ≈ US$ 3,685.1M; BR 2024 exports ≈ 409.6
(sum of the four domains); CO 2024 AV ≈ 162.3; AR USD strictly NULL, max year
2022; CR measured-domain count drops after 2021. Idempotent — byte-identical
reruns (sha256-verified 2026-06-10). Input files' sha256 recorded in the
`.meta.json` sidecar.

## 5. Consumers

Atana Index **Vol 2** backbone table · the cross-LATAM Atana Note carried in the
research backlog since May · the Data Subscription demo query. (Accretion
criterion gate 1 — see phase6 memo §1.)

## 6. Citation

> Atana. *LATAM cultural trade by 2025 UNESCO FCS domain* — derived from INEGI CSCM, DANE CSECC, BCCR CSCCR, IBGE/SECEX Comex and SInCA CSC via the Atana domain crosswalk. atana-data, CC BY 4.0.
