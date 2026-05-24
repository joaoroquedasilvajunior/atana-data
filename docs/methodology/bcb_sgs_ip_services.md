# Methodology — BCB SGS intellectual-property-services balance of payments

Schema `atana.bcb`. Phase 4c.1 of the Atana Data expansion — the first of the
three Intellectual-property sources, and the one that reaches the FCS
*Intellectual property* transversal domain.

**Source:** Banco Central do Brasil — *Sistema Gerenciador de Séries Temporais*
(SGS), series **22777** (receita) and **22778** (despesa), BPM6 basis.
**Account:** *Serviços de propriedade intelectual* — the balance-of-payments
intellectual-property line, formerly "Royalties e licenças" under BPM5.
**API:** `https://api.bcb.gov.br/dados/serie/bcdata.sgs.<code>/dados?formato=json`
**Coverage:** Brazil, national, monthly.
**Licence:** open data — Banco Central do Brasil.
**ETL:** `etl/bcb__sgs_ip_services_to_parquet.py`
**Status:** ETL written 2026-05-23 — **data pull pending** (see §6).

---

## 1. Why this source

A cultural-goods-trade module sees physical cultural goods crossing a border;
it cannot see the **cross-border flow of intellectual-property payments** —
royalties and licence fees for the use of copyrights, trademarks, patents and
franchises. That flow is the FCS transversal domain *Intellectual property*.
The BCB's balance-of-payments account for IP services is the cleanest
continuous Brazilian measure of it: an open, structured, monthly series, the
same access pattern the corpus already uses for the BCB SGS IPCA series.

## 2. The `ip_services_bop` table

Built from the two SGS series, stacked. Long format, one row per series per
month.

| Column | Type | Description |
|---|---|---|
| `series_code` | BIGINT | `22777` (receita) or `22778` (despesa) |
| `series_name` | VARCHAR | the SGS series name |
| `flow` | VARCHAR | `receita` / `despesa` |
| `flow_en` | VARCHAR | `credit` / `debit` |
| `date` | DATE | reference month (SGS dates the first of the month) |
| `year` | BIGINT | reference year |
| `month` | BIGINT | reference month (1–12) |
| `value_usd_million` | DOUBLE | the BoP value — see the unit caveat, §5 |

`receita` (credit) is the inflow — payments Brazil *receives* for the use of
its intellectual property; `despesa` (debit) is the outflow — payments Brazil
*makes* to use foreign intellectual property. Brazil has historically run a
large structural deficit on this account (it pays far more IP rent than it
earns) — a query of credit minus debit will show it.

## 3. ⚠️ All-economy, not cultural-only

This is the **whole-economy** IP-services balance — it covers software
licensing, industrial patents, trademark and franchise fees across every
sector, not the cultural sector alone. It is the standard *proxy* for the FCS
Intellectual property domain at the macro level, and it is what reaches that
domain in `canonical.domain_crosswalk`. A cultural-specific IP cut needs the
two companion Phase 4c sources:

- **INPI** (Phase 4c.2) — registration counts for computer programs,
  industrial designs, geographical indications and cultural-class trademarks.
- **ECAD** (Phase 4c.3) — music-copyright collection and distribution.

Until those land, read `bcb.ip_services_bop` as the macro IP-rent flow, not as
a cultural-sector figure.

## 4. Refresh

The ETL caches each series' raw JSON under `raw/bcb/_source/sgs_<code>.json` on
first run and reads the cache thereafter — reruns are stable and offline.
`python etl/bcb__sgs_ip_services_to_parquet.py --refresh` deletes nothing but
re-pulls the API and overwrites the cache with a fresh vintage. The BCB SGS is
a continuously-updated source, so this is a natural DB-updater target.

## 5. Limitations and caveats

- **All-economy, not cultural** — see §3. The single most important caveat.
- **Unit.** `value_usd_million` follows the BCB SGS balance-of-payments
  convention (US$ million). **Confirm against the SGS series metadata page on
  first run** — the ETL prints the latest values for an eyeball check.
- **Series identity unverified at build time.** The series numbers (22777 /
  22778) are taken from the Phase 4 scoping pass (`phase4_scoping.md` §A.3,
  web-verified there). The ETL was written without a live API probe — the
  sandbox could not reach the BCB API — so the first run is also the first
  verification. If the series return something other than the IP-services
  account, stop and re-scope.
- **BPM5 → BPM6 break.** The account was "Royalties e licenças" under BPM5 and
  "Serviços de propriedade intelectual" under BPM6; a long back-series may
  cross that methodological break. Check the series start date.

## 6. Status — pending the data pull

The ETL is complete and runnable; the **data has not yet been pulled**. The
Atana sandbox cannot reach the BCB API, so the pull is a machine-side step for
João: run `python etl/bcb__sgs_ip_services_to_parquet.py` on a machine with
network access. That run fetches the API, builds `raw/bcb/ip_services_bop.parquet`
and (with a token) syncs `atana.bcb`. Only after that run does the crosswalk's
coverage meter actually stand at 13/14.

## 7. Domain mapping → 2025 UNESCO FCS

Once `bcb.ip_services_bop` is ingested, `canonical.domain_crosswalk` gains a
`bcb` row mapping this account to *Intellectual property* (transversal,
`good`, with a note recording the all-economy caveat of §3) — taking the
crosswalk's coverage meter from 12/14 to **13/14**. Per the project discipline
that the crosswalk reflects what the corpus actually holds, that row is added
**with** the verified data, not ahead of it — so the crosswalk extension is the
immediate follow-up to the first successful BCB ETL run, not part of this
ETL-only delivery.

## 8. Citation

> Banco Central do Brasil (2026). *Sistema Gerenciador de Séries Temporais —
> séries 22777 e 22778, Serviços de propriedade intelectual (BPM6)*. Banco
> Central do Brasil.

---

*Methodology note for `atana.bcb`. Prepared 2026-05-23. Phase 4c.1. Pairs with
`_atana_intel/phase4_scoping.md` §A.3 and the pending `inpi` / `ecad`
methodology notes (Phase 4c.2 / 4c.3).*
