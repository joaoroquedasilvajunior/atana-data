# Methodology — `canonical.cmo_directory_alcam`

The LATAM music-CMO reference directory. A curated 13-row table listing the
member societies of **ALCAM** — *Alianza Latinoamericana de Autores y
Compositores de Música*, the LATAM regional federation of music creator
collective-management societies (CMOs) inside CISAC.

**Schema / table:** `atana.canonical.cmo_directory_alcam`
**File:** `curated/cmo_directory_alcam.parquet` (+ `.meta.json`)
**Build script:** `etl/canonical__build_cmo_directory_alcam.py`
**Built:** 2026-05-25 · Tier 1 of the ALCAM scoping (`_atana_intel/scoping_alcammusica_2026-05-25.md`).

---

## 1. What this is

A small reference directory of entities — the 13 music CMOs that ALCAM
publishes on its members page. It is **not** a classification crosswalk (those
live in `canonical.domain_crosswalk`); it is a join key for any future
per-society data across LATAM.

The corpus already holds `atana.ecad` (Phase 4c.3) — a 3-row headline series
for ECAD, the Brazilian umbrella collector that aggregates and distributes
royalties for the Brazilian CISAC societies, of which two are ALCAM members
(ABRAMUS, UBC). This directory is the natural LATAM map of the **creator-side**
societies upstream of those collections, with a `linked_atana_schema` pointer
(`'ecad'`) that ties the Brazilian pair back to existing corpus data.

For the other 11 ALCAM countries the corpus carries no per-society data yet.
The directory is the prerequisite for the Tier-2 Phase-5 candidate — a LATAM
extension of the ECAD headline-series pattern across the full ALCAM membership
(see the scoping memo §4 Tier 2).

## 2. The table

13 rows, one per ALCAM member society. Brazil has two members (ABRAMUS + UBC);
the other 11 countries have one each. Total countries: 12.

| Column | Type | Description |
|---|---|---|
| `country` | VARCHAR | English country name (e.g. `Argentina`, `Brazil`) |
| `country_iso3` | VARCHAR | ISO 3166-1 alpha-3 |
| `society_acronym` | VARCHAR | Short name as used by ALCAM (e.g. `SADAIC`, `ABRAMUS`) — **always** the authoritative identifier captured from the source |
| `society_name` | VARCHAR | Best-known full Spanish/Portuguese form of the society's name; the URL remains the authoritative source — see §3 |
| `url` | VARCHAR | Official society URL, as linked from the ALCAM /sociedades page |
| `in_atana_corpus` | BOOLEAN | `true` iff the society's data is reachable through an existing corpus schema. Currently `true` only for `ABRAMUS` and `UBC` (via `atana.ecad`); `false` for the other 11. |
| `linked_atana_schema` | VARCHAR | The corpus schema this society is reachable through, e.g. `'ecad'`; `NULL` when `in_atana_corpus = false` |
| `source_url` | VARCHAR | The ALCAM directory page this row was captured from — `https://www.alcammusica.org/sociedades` |
| `as_of` | DATE | The capture date — `2026-05-25` |

**Invariants** (enforced in `validate()`):

- 13 rows, 12 distinct countries (Brazil ×2), 13 distinct acronyms.
- `country_iso3` is a 3-letter uppercase code.
- All `url` values are absolute http(s) URLs.
- `in_atana_corpus = true` ⇔ `linked_atana_schema IS NOT NULL`.
- The only societies with `in_atana_corpus = true` are `ABRAMUS` and `UBC`,
  both pointing to `linked_atana_schema = 'ecad'`.
- Row order: alphabetical by `country` then `society_acronym` — deterministic,
  for byte-identical reruns.

## 3. Source and per-row notes

The source is **`alcammusica.org/sociedades`**, captured 2026-05-25 with the
Atana sandbox's `web_fetch`. The page is a 13-tile Wix listing — each tile
shows a society logo, the country name, and a hyperlink to the society's own
homepage. The build inlines those 13 (country, acronym, URL) triples verbatim
from the captured HTML.

`society_name` is filled with the best-known canonical Spanish/Portuguese form
of each society's name. The ALCAM directory page itself does not print the
full name — only the acronym + country — so the names below are sourced from
prior domain knowledge and standard CISAC member-directory conventions. The
**URL of each society remains the authoritative source** for the official
name. Per-row notes:

- **SADAIC**, **ABRAMUS**, **UBC**, **SCD**, **SAYCO**, **SACM**, **AGADU**,
  **APDAYC**: high-confidence names — these are well-established societies
  with widely cited canonical Spanish/Portuguese forms.
- **SOBODAYCOM**, **ACAM**, **SAYCE**, **APA**: good-confidence names — the
  forms used (`Sociedad Boliviana de Autores y Compositores de Música`, etc.)
  follow the standard CISAC member-directory pattern; the URL is authoritative.
- **AEI** (Guatemala): the full official expansion is not visible from the
  ALCAM page and was not separately verified during this build. The
  `society_name` cell carries an explicit flag — `"AEI – Guatemala (sociedad
  de autores; full official name not verified — see methodology)"`. A future
  Tier-2 build that fetches each member site would set this from
  `aeiguatemala.org`.

A future build that scrapes each member homepage to capture the official name
verbatim is a clean upgrade path; the schema does not change.

## 4. Linkage to `atana.ecad`

ECAD (*Escritório Central de Arrecadação e Distribuição*) is the Brazilian
umbrella collector that aggregates per-execution royalties and redistributes
them to the country's CISAC member societies — ABRAMUS and UBC among them.
ECAD itself is **not** an ALCAM member (ALCAM is the creator-side federation;
ECAD is the collection arm), but the two Brazilian ALCAM societies feed into
ECAD's flow.

The directory makes that visible by setting `linked_atana_schema = 'ecad'` for
both Brazilian rows. A query joining `cmo_directory_alcam` to `atana.ecad` on
`linked_atana_schema = 'ecad'` therefore resolves the Brazilian creator-side
societies to the Brazilian collection-side headline data. For the other 11
countries the pointer is `NULL` until per-society data is brought in.

## 5. Not in scope

- **No financial figures.** The directory carries no arrecadación or
  distribución values — those would come from a separate `atana.cmo_latam.*`
  schema (Tier 2 / Phase 5 candidate).
- **No `domain_crosswalk` row.** A directory of entities is not a
  classification — the crosswalk maps codes to FCS domains. If/when Tier 2
  introduces an `atana.cmo_latam.headline_arrecadacao` raw schema, *that*
  schema gets one `cmo_latam` crosswalk row mapping to *Intellectual property*
  (the FCS T7 domain `atana.ecad` already reaches).
- **No CISAC totals or LATAM aggregates.** Those would come from CISAC's
  *Global Collections Report* (a separate, distinct source).
- **Not a versioned snapshot.** This is a living reference directory,
  un-timestamped, regenerated by the build script.

## 6. Update cadence

ALCAM membership changes rarely (new affiliations are typically announced at
the annual asamblea — most recently November 2025, Atlántida, Uruguay). Refresh
this build whenever a society joins or leaves; the next opportunity is the
2026 ALCAM general assembly.

Captured 2026-05-25 against 13 members; the next refresh window is the post-
2026-asamblea publication of the updated /sociedades page.
