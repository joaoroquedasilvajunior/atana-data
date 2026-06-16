# `atana.macro` — BRL annual exchange-rate reference series (USD + EUR)

> **Status (2026-06-14):** GitHub ✅ `411644f` on origin/main · MotherDuck ✅ live · 3 tables / 93 rows in `raw/macro/`

> Methodology note for `raw/macro/fx_brl_usd_annual.parquet` and
> `raw/macro/fx_brl_eur_annual.parquet`. Prepared 2026-06-10 (Phase 6a, first item).
> ETL: `etl/macro__fx_brl_annual_to_parquet.py`.

## 1. What this is — and is not

Two small **convenience reference series**, in the exact convention of
`fx_mxn_usd_annual` / `fx_cop_usd_annual` / `fx_crc_usd_annual`: annual-average
exchange rates used to derive USD (or EUR) views of BRL-denominated corpus tables.
They are **not** cultural statistics and **not** Atana measurements — they exist so
that `atana.ibge_comex` (R$ FOB) can join cross-LATAM comparisons, and so that
ECAD (R$) × CISAC (€) readings stop relying on eyeballed rates (the A24 caveat).

## 2. Sources and construction

### `fx_brl_usd_annual` (1994–2025, 32 rows)

| Column | Description |
|---|---|
| `year` | Calendar year |
| `fx_brl_per_usd` | Annual-average BRL per USD |
| `source` | `worldbank_pa_nus_fcrf` (primary) or `bcb_sgs_3698_annual_mean` (extension) |
| `n_obs` | Months averaged (BCB rows only; NULL for WB rows) |

- **Primary:** World Bank Open Data **PA.NUS.FCRF** ("Official exchange rate, LCU
  per US$, period average"; underlying IMF IFS) — deliberately the *same indicator*
  used for the MX/CO/CR reference series, so all USD-derived columns in the corpus
  share one FX methodology.
- **Extension:** years the World Bank has not yet published (currently **2025**) are
  filled from **BCB SGS 3698** (dólar venda, média de período mensal), annualised as
  the simple mean of the 12 monthly values, and flagged in `source`.
- **Cross-check (build-time assertion):** for all overlapping years 1995–2024 the two
  sources agree within 2%. 1994 is WB-only — SGS 3698's pre-July-1994 observations
  are denominated in cruzeiros reais (pre-Plano Real) and are excluded.

### `fx_brl_eur_annual` (1999–2025, 27 rows)

- **BCB SGS 21619** (euro, venda, daily quotes), annualised as the simple mean of
  daily observations; years with fewer than 200 daily observations are dropped.
- This is the series Análise 24 flagged as missing ("sem série BCB ingerida ainda";
  the ECAD↔CISAC conversion used an approximate ~6.03 BRL/EUR). The measured 2025
  annual average is **6.3095**; 2024 is **5.8340**.

Raw API responses are cached under `raw/macro/_source/` (sha256 in the
`.meta.json` sidecars); reruns are offline and byte-identical. `--refresh`
re-pulls — a DB-updater refresh job once the schema is live.

## 3. Validation (2026-06-10)

- **Idempotency:** two consecutive runs → byte-identical Parquet (sha256 verified).
- **Spot values:** 2024 USD 5.388935 (WB); 2023 USD 4.994380; 2015 USD 3.327;
  2025 USD 5.587892 (BCB, 12 months); 2024 EUR 5.834022 (253 daily obs).
- **External benchmark:** converting `ibge_comex.tab_10_1` 2024 cultural exports
  (R$ 4,029 mi FOB) with this series gives **US$ 747.6 mi** — Análise 10 §figT8
  published **US$ 746 mi** from an independent derivation. Match within 0.2%.

## 4. Usage rules (the flow-vs-stock caveat)

1. **Flows** (annual trade, annual royalty distributions): convert with the
   matching year's annual average — that is what these tables are for.
2. **Stocks / point-in-time values** (a balance on 31/12, a single transaction):
   do **not** use the annual average; fetch the period-end or transaction-date rate.
3. **High-volatility years** (2020, 2025): the annual mean hides large intra-year
   swings; if a finding is sensitive to FX, show the BRL series alongside.
4. Never present a USD- or EUR-derived figure as the source agency's own number —
   the derivation must be attributed (the `fx_*` table + this note).

## 5. What this unlocks

- **Brazil's row** in `canonical.latam_trade_by_fcs_domain` (the cross-LATAM
  FCS-domain trade comparison — see `_atana_intel/phase6_corpus_criterion_and_vol2_scoping.md` §2).
- **A24 precision fix:** ECAD R$ ↔ CISAC € comparisons on measured rates.
- Any future USD view of `rais` wage series, `salic` captação, `ecad` arrecadação.

## 6. Citation

> World Bank. *Official exchange rate (LCU per US$, period average)* — PA.NUS.FCRF, Brazil. World Bank Open Data, CC BY 4.0.
> Banco Central do Brasil. *SGS — Sistema Gerenciador de Séries Temporais*, séries 3698 (dólar venda, média mensal) e 21619 (euro venda, diária). Dados abertos.

---

*Pairs with `inegi_csc.md` §FX, `dane_csecc.md`, `cr_bccr_csc.md`, and the Phase 6 scoping memo. Schema `atana.macro` is new — first MotherDuck sync is João's checkpoint.*
