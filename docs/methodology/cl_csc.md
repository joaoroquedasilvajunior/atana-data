# `atana.cl_csc` — Chile Cuenta Satélite de Cultura (BCCh + MINCAP + CEPAL)

> **Status (2026-06-16):** Sandbox-side ✅ built · GitHub ❌ pending push · MotherDuck ❌ pending sync
> 1 table / 3 rows in `raw/cl_csc/bcch_pilot_headline_consumption.parquet`

> Methodology note. Phase 7a.0 of the Atana Data LATAM expansion — the **fifth
> non-Brazilian national source** after Mexico (`atana.inegi`), Colombia
> (`atana.dane`), Argentina (`atana.sinca`) and Costa Rica (`atana.cr_bccr`).
> Phase 7a.1 (INE Estadísticas Culturales Informe Anual 2024 — employment +
> production + participation tables) is separately scoped and deferred.

## 1. What this is

The Cuenta Satélite de Cultura de Chile launched its **first results in 2024**,
jointly developed by:

- **MINCAP** — Ministerio de las Culturas, las Artes y el Patrimonio (host)
- **Banco Central de Chile (BCCh)** — anchor in the Cuentas Nacionales system
- **CEPAL** — technical methodological support

This Phase 7a.0 ingest captures the single **headline indicator** publicly
stated by MINCAP at this stage of the pilot: *consumo efectivo de los hogares
en productos culturales* (% del consumo total efectivo de los hogares), for
three explicitly stated years.

## 2. Maturity caveat — this is a 3-row Tier 1 ingest, not a full CSC

Chile's CSC pilot has published **headline indicators only** as of mid-2026.
The underlying tables (production by cultural sector, employment, trade, ACC
classification) exist in MINCAP/BCCh working files but are not yet released
as a continuous open series. The 2026-05-22 inventory's "pilot only" label
remains substantively correct — what has changed is that pilot first results
have been formally launched (2024) and a headline indicator is now publicly
quotable.

The deeper Chilean data the corpus needs for `canonical.latam_trade_by_fcs_domain`
or for a 5-lens Vol 2 analysis lives in two places not ingested here:

- **INE Chile *Estadísticas Culturales: Informe Anual 2024*** (Dec 2024) —
  SII tax records × ENE survey → "Actividades Características de Cultura"
  (ACC). Multi-year employment + production + participation. **This is the
  real ingest target for Phase 7a.1.**
- BCCh underlying CSC release — to be probed when MINCAP publishes the full
  pilot tables.

## 3. The headline series

| year | value | unit | indicator |
|---:|---:|---|---|
| 2018 | 1.7 | % | Consumo efectivo de los hogares en productos culturales, % del consumo efectivo total de los hogares |
| ≈2020 | 1.4 | % | (idem) — pandemic low |
| 2022 | 1.4 | % | (idem) — last year with BCCh data available |

The **intermediate years 2019 and 2021 are deliberately omitted** — they are
not explicitly stated in MINCAP's cuenta pública prose, and inferring them
would assert structure that the source does not. Phase 7a.1 (full BCCh
release) should resolve to a 5-row annual series.

The **2020 row carries a soft year-label** (`≈2020 (pandemic low)`) because
MINCAP wrote "hasta la pandemia" rather than nominating a specific year.
This is the conventional pandemic-trough year for Chile but the source does
not lock it.

## 4. Provenance — verbatim source

> "La recopilación de estadísticas precisas es indispensable para mejorar
> las políticas culturales y darle más sostenibilidad al sector. En este
> sentido, el año 2024 se lanzaron los primeros resultados de la Cuenta
> Satélite de Cultura, después de un trabajo metodológico riguroso, sistemático
> y colaborativo entre la Comisión Económica para América Latina y el Caribe
> (Cepal), el Banco Central y el Ministerio de las Culturas. […] Al analizar
> la demanda y el uso de los productos culturales, se obtiene que el consumo
> efectivo de los hogares en productos culturales disminuyo desde el 2018
> hasta la pandemia, de 1,7% a 1,4%; mientras que luego de la pandemia, se ha
> mantenido en un 1,4% hasta el 2022 (último año con datos del Banco Central
> de Chile disponibles)."

— *MINCAP, Informe Final Cuenta Pública Participativa 2025* (published early
2026), pp. ~21 of the PDF; full URL:
`https://www.cultura.gob.cl/cuentapublica/wp-content/uploads/sites/28/2026/01/informe-final-convencion-cuenta-publica-2025.pdf`

## 5. Crosswalk mapping

`canonical.domain_crosswalk` is extended **93 → 94 rows** with one `cl_csc`
row mapping to the FCS 2025 transversal domain **Social participation**
(`mapping_confidence = approximate`, ★ flagged). The FCS Social participation
domain has no consumption-share equivalent in spine; reading household
cultural-consumption-share as a participation proxy is **looser** than the
IBGE TIC/turismo rows already in the corpus, but the mapping rationale is the
same as the Phase 4b proxy claim.

**FCS coverage meter: 13/14 unchanged** — Chile is a new SOURCE in the
domain, not a new DOMAIN. Only *Intangible cultural heritage* remains
unreached (out of scope by decision).

## 6. Cross-source positioning in the corpus

| Country | First non-Brazilian source ingested | Phase | Reach |
|---|---|---|---|
| Mexico | INEGI CSCM trade module (5,984 rows) | 3a | Cultural trade |
| Colombia | DANE CSECC trade module (484 rows) | 3b | Cultural trade |
| Argentina | SInCA CSC (228 rows, USD NULL by design) | 3c | Cultural trade |
| Costa Rica | CSCCR trade table (150 rows) | 3d | Cultural trade |
| **Chile** | **BCCh CSC pilot headline (3 rows)** | **7a.0** | **Social participation proxy** |

Chile is the first LATAM country to enter via a **non-trade** lens. That's a
direct consequence of the data maturity: a continuous trade module for Chile
would require the INE annual + a separate Banco Central comercio exterior
cultural cut (Phase 7a.1+).

## 7. Read recipe

```sql
-- The 3-point pilot series
SELECT year, year_label, indicator_value, indicator_unit, notes
FROM   atana.cl_csc.bcch_pilot_headline_consumption
ORDER  BY year;

-- Five-country LATAM households-into-culture cross
WITH chile AS (
  SELECT year, indicator_value AS pct_share, 'CL' AS country
  FROM atana.cl_csc.bcch_pilot_headline_consumption
)
SELECT * FROM chile;
-- (UY/AR/MX/CO/CR have no directly comparable household-consumption-share
-- indicator in the corpus — this is the first row of what would be a
-- proper participation cross.)
```

## 8. Validation

- 3 rows, exactly years {2018, 2020, 2022}.
- Values 2018=1.7 %, 2020=1.4 %, 2022=1.4 % — verbatim.
- Single indicator across all rows (consumption share).
- Idempotent — byte-identical reruns confirmed (`raw/cl_csc/bcch_pilot_headline_consumption.parquet`
  re-emits identically when `python3 etl/cl_csc__bcch_pilot_headline_to_parquet.py`
  is run twice in succession).

## 9. How to cite

> MINCAP — Ministerio de las Culturas, las Artes y el Patrimonio (Chile), 2026.
> *Informe Final Cuenta Pública Participativa 2025*. Ingested into the Atana
> corpus as `atana.cl_csc.bcch_pilot_headline_consumption` (3 rows). Source
> headline of the BCCh+MINCAP+CEPAL Cuenta Satélite de Cultura first results,
> launched 2024. Phase 7a.0 of the Atana Data LATAM expansion.

---

*Methodology note for `atana.cl_csc`. Prepared 2026-06-16. Atana / atana.studio · CC BY 4.0.*
