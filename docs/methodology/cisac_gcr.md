# Methodology — `atana.cisac` from the CISAC Global Collections Report

Schema `atana.cisac`. **Phase 5a** of the Atana Data expansion — first ingest
of the *CISAC Global Collections Report* (GCR), the global counterpart to
`atana.ecad`. CISAC (International Confederation of Societies of Authors and
Composers) is the global federation of creator collective-management
organisations; its annual GCR reports worldwide royalty collections across
music, audiovisual, drama, literature and visual arts, sourced from 228
member societies across 111 countries.

**Source:** CISAC Global Collections Report 2025 (covering 2024 royalty data;
published November 2025). Public landing page; full PDF auth-walled.
**Coverage:** Global, annual. 2024 reference year at v1 launch.
**Licence:** CISAC published figures — public release on
<https://www.cisac.org/cisac-global-collections-report-2025>.
**ETLs:**
  `cisac__gcr_2025_global_by_stream_to_parquet.py`,
  `cisac__gcr_2025_global_by_repertoire_to_parquet.py`,
  `cisac__gcr_2025_global_by_region_to_parquet.py`,
  `cisac__gcr_2025_leading_smaller_markets_to_parquet.py`.
**Ingested:** 2026-05-29 (Tier 1).

---

## 1. Why this is here — and why two CISAC documents are easy to confuse

CISAC publishes two annual flagships that look similar from the outside:

- **CISAC Annual Report** (released 28 May 2026 for the 2026 edition):
  governance, advocacy, AI policy narrative. **No microdata.** This is the
  document the W22 v2 briefing originally flagged.
- **CISAC Global Collections Report** (most recent edition: **GCR 2025**,
  published ~November 2025, covering 2024 royalty data): the actual annual
  statistical release — the dataset on global creator royalties.

This methodology note is about the GCR. The Atana corpus ignores the Annual
Report's prose; the data lives in the GCR.

## 2. What the v1 ingest is

Tier 1 of the CISAC scoping (`_atana_intel/scoping_cisac_gcr_2025_2026-05-29.md`)
takes everything the *public landing page* of GCR 2025 already exposes — no
PDF extraction required. Four small tables, 25 rows total:

| Table | Rows | Description |
|---|---:|---|
| `gcr_2025_global_by_stream` | 4 | 2024 split by income stream (Digital, Live & background, Broadcast, Total) — EUR millions, YoY |
| `gcr_2025_global_by_repertoire` | 5 | 2024 split by creative repertoire (Music, Audiovisual, Visual arts, Drama, Literature) |
| `gcr_2025_global_by_region` | 6 | 2024 split by CISAC region (West Europe, Canada/USA, Asia-Pacific, Latin America, East Europe, Africa) |
| `gcr_2025_leading_smaller_markets_digital_share` | 10 | Top-10 "leading smaller markets" by 2024 digital share, with 2015–2024 growth |

Tier 2 (full PDF, country-level + 2015–2024 historical series, ~111 countries
× 4 streams × 10 years ≈ 4 000 rows) is the genuine prize and is deferred —
the PDF is auth-walled at `members.cisac.org`. See the scoping memo §5 for
access routes (GA press accreditation, CISAC contact form, or ABRAMUS/UBC
member access).

## 3. Central caveats

### (a) The named-streams gap

In `gcr_2025_global_by_stream`, the three named streams (Digital, Live &
background, Broadcast) sum to **€12.68 bn**; the total is **€13.97 bn**. The
**€1.29 bn (~9.2 %) residual** is absorbed by two minor streams CISAC calls
out in prose but not as headline rows: **physical formats** (which the GCR
notes is "−37.7 % below the 2015 figure") and **private copying** (which
also fell). The corpus convention is to ingest verbatim what the source
publishes as headline rows and never to allocate inferred residuals — so the
gap is documented, not filled. Same posture as the 1.25 % gap in
`atana.ecad.distribuicao_por_segmento`.

### (b) Repertoires and regions reconcile cleanly

`gcr_2025_global_by_repertoire`: five rows sum to **€13,975 mi** (drift +5
mi vs the €13.97 bn total — rounding only).
`gcr_2025_global_by_region`: six rows sum to **€13,972 mi** (drift +2 mi —
rounding only).
Both within ETL tolerances.

### (c) Latin America is the only declining region in 2024

LATAM **€786 mi, −0.6 %** — the only of six regions to contract in 2024,
"following two years of strong post-pandemic gains" per the GCR. This is the
LATAM-frame the Atana corpus did not previously carry. It joins to
`atana.ecad` (Brazil) and to `canonical.cmo_directory_alcam` (the 12-country
LATAM CMO directory). For rough triangulation: Brazil's 2024 ECAD distribuição
of R$ 1,569 mi ≈ €260 mi at year-average FX ≈ **a third of the LATAM CISAC
total**.

### (d) Mexico is the only LATAM country in the leading-smaller-markets table

`gcr_2025_leading_smaller_markets_digital_share` lists 10 countries:
Mali 89.9 % · Vietnam 89.6 % · India 82.7 % · Indonesia 82.5 % · Philippines
80.9 % · Nepal 78.2 % · Thailand 69.1 % · **Mexico 65.1 %** · Hong Kong
64.0 % · Ukraine 63.3 %. SACM (the Mexican CISAC member society) is the
direct corpus join via `canonical.cmo_directory_alcam`. Mali growth is
NULL — no 2015 baseline (Mali joined CISAC reporting later); per-row note.

### (e) "Music is ~90 % of the global total"

The repertoire split confirms what the corpus already presumed: **Music
€12.59 bn = 90.1 % of global creator-royalty collections**. The
audiovisual / visual arts / drama / literature triplet is small (~€1.4 bn).
So the corpus's heavy investment in music-side detail (Brazil ECAD, ALCAM
directory, Note #06 Funk) is scale-appropriate; the AV-and-visual-arts
domain is a different conversation by an order of magnitude.

### (f) Currency

GCR reports in **EUR**, current prices. Brazil ECAD is **BRL**. The corpus
does not currently carry an EUR/BRL FX time series; for any direct ECAD ↔
GCR-LATAM reconciliation we would add one (BCB SGS series 21619 EUR/BRL
annual averages — fits the Phase 4c.1 BCB-SGS ETL pattern). Not done at v1.

## 4. Large-market comparators (in methodology, not in the table)

The GCR text gives three large-market digital-share comparators in prose
which are NOT in `gcr_2025_leading_smaller_markets_digital_share` (the table
stays strictly to CISAC's "leading smaller markets" framing):

- USA: 27.1 %
- France: 13.9 %
- UK: 11.4 %

These are kept here for reference; they would slot into a Tier 2 country-level
table at full GCR PDF extraction time.

## 5. The "first time" milestones from the GCR text (for context)

The Atana corpus often pivots on inflection points; the GCR explicitly names
several from its 2024 reading:

- **Digital crossed €5 bn** for the first time in 2024.
- **Live & background exceeded €3.5 bn** for the first time; +33 % above
  2015 and ~25 % above the pre-pandemic peak.
- **Digital became the single leading global income source in 2022**
  (overtaking broadcast). Cf. Brazil ECAD: digital became #1 arrecadação
  segment **in 2024** — a two-year lag against the global pivot.
- **Total collections +65.2 % since 2015**; digital **+110.6 % since 2020**.

These are stated in prose on the landing page; the full historical series
(2015–2024 by stream / repertoire / region) is in the PDF and will be a
Tier 2 ingest.

## 6. Domain mapping → 2025 UNESCO FCS

`canonical.domain_crosswalk` carries one new `cisac` source-schema row
(2026-05-29) mapping to **Intellectual property** (transversal, `good`). The
four v1 tables share the one crosswalk row. Coverage stays **13/14** — CISAC
deepens the IP domain that BCB (4c.1), INPI (4c.2) and ECAD (4c.3) already
reach; it does not unlock the only remaining unmet domain (*Intangible
cultural heritage*).

## 7. Refresh and the DB-updater

Data is inline in each ETL. CISAC publishes the GCR annually, ~November.
The DB-updater can carry a calendar trigger for the next edition (likely
**~November 2026** for the 2025 data year, GCR 2026). When that release
lands, append rows to the four `ROWS` lists with the new year and re-run;
the schemas extend naturally.

## 8. Validation (2026-05-29)

All four ETLs ran clean under `ATANA_ETL_SKIP_PUSH=1`; all parquets
byte-identical on rerun.

- `gcr_2025_global_by_stream` — 4 rows; named-streams + €1.29 bn residual =
  total; verbatim YoY (+11.2, +9.6, +0.8, +6.6).
- `gcr_2025_global_by_repertoire` — 5 rows; sum €13,975 mi ≈ total within
  rounding; Music = 90.1 % share.
- `gcr_2025_global_by_region` — 6 rows; sum €13,972 mi ≈ total; LATAM the
  only decliner (−0.6 %).
- `gcr_2025_leading_smaller_markets_digital_share` — 10 rows; Mali growth
  NULL with caveat; Mexico the only LATAM cell.
- `canonical.domain_crosswalk` — 85 → 86 rows, coverage unchanged 13/14.

## 9. Citation

> CISAC (2025). *Global Collections Report 2025*. International Confederation
> of Societies of Authors and Composers. November 2025.
> <https://www.cisac.org/cisac-global-collections-report-2025>.

---

*Methodology note for `atana.cisac`. Prepared 2026-05-29 at Tier 1 launch.
Phase 5a. Scoping memo:
`_atana_intel/scoping_cisac_gcr_2025_2026-05-29.md`. Pairs with
`ecad_relatorio_anual.md` (Brazil, 4c.3),
`cmo_directory_alcam.md` (LATAM CMO directory, 2026-05-25).*
