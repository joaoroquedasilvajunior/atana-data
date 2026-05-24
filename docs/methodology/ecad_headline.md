# Methodology — ECAD headline royalty series

Schema `atana.ecad`. Phase 4c.3 of the Atana Data expansion — the third lens on
the FCS *Intellectual property* domain: cultural-IP **income** actually
collected and distributed (music public-performance royalties).

**Source:** ECAD — *Escritório Central de Arrecadação e Distribuição* —
Transparência pages.
**Pages:** `transparencia-2023/`, `transparencia-2024/`, `transparencia/` (2025)
on <https://www4.ecad.org.br>.
**Coverage:** Brazil, national, annual **2023–2025**.
**Licence:** ECAD published figures — public transparency disclosure.
**ETL:** `etl/ecad__headline_series_to_parquet.py`
**Ingested:** 2026-05-23.

---

## 1. Why this is a headline series, not a full ingest

The Intellectual-property domain now has three lenses: BCB (`atana.bcb`, 4c.1) —
the cross-border IP-royalty *flow*; INPI (`atana.inpi`, 4c.2) — the IP
registration *stock*; and ECAD here — IP *income*, the music royalties a
collective-management body actually collects from users and pays out to
rights-holders.

But **ECAD publishes no machine-readable dataset.** Its Transparência pages
carry the headline figures as page text; the segment-by-segment breakdown
(rádio, TV, shows, cinema, digital, sonorização ambiental…) is published **only
as PNG chart images**; the deeper data sits in annual-report PDFs. There is no
CSV/XLSX equivalent of the BCB API or the INPI/SIIC spreadsheets.

So this ingest takes the **headline series only** — total arrecadação and
distribuição per year — transcribed verbatim from the three Transparência
pages. It is a small, honest table, not a full data ingest. João chose this
(option 1) over PDF table-extraction; the choice and its limits are explicit.

## 2. The `arrecadacao_distribuicao` table

One row per reference year. **3 rows** (2023, 2024, 2025).

| Column | Type | Description |
|---|---|---|
| `year` | BIGINT | 2023 / 2024 / 2025 |
| `arrecadacao_brl_billion` | DOUBLE | total collected, R$ billion — rounded headline figure |
| `arrecadacao_yoy_pct` | BIGINT | year-on-year growth ECAD states for that year |
| `distribuicao_brl_billion` | DOUBLE | total distributed, R$ billion — rounded headline figure |
| `distribuicao_yoy_pct` | BIGINT | year-on-year growth ECAD states for that year |
| `titulares_contemplados_mil` | BIGINT | rights-holders paid, thousands |
| `digital_services_arrec_share_pct` | DOUBLE | Serviços Digitais share of arrecadação; NULL for 2023 |
| `source_page` | VARCHAR | the Transparência page the row is transcribed from |

The series: arrecadação R$ 1.6 bn → 1.8 → 2.1; distribuição R$ 1.3 bn → 1.5 →
1.7 (2023→2025). The digital-services share of collection rose 26% → 33.6%
(2024→2025) — the streaming-era recomposition, an Authenticity-Paradox
indicator (cf. Atana Note #06).

## 3. Limitations and caveats — read before use

- **Rounded headline figures.** The values are ECAD's published *rounded*
  headline numbers (R$ X.X billion), not precise to the real. Precise figures
  are in the annual *Balanço Patrimonial* PDFs — out of scope for this ingest.
- **No segment detail.** Per-segment arrecadação/distribuição is image-only at
  source and is **not** in this table. Only the digital-services share is
  captured, because it is the one segment figure stated cleanly in text.
- **Three years only.** The Transparência pages surface 2023–2025; earlier
  years would require the annual-report PDFs (2020–2022 editions exist).
- **`titulares` / national-repertoire wording shifts** across years on the
  source pages — only the unambiguous figures (arrecadação, distribuição,
  titulares count, digital share) are ingested; the national-vs-foreign
  repertoire split is deliberately omitted as cross-year-incomparable.
- **Music only.** ECAD covers music public-performance copyright — a slice of
  the IP domain, not all of it.

## 4. Domain mapping → 2025 UNESCO FCS

`canonical.domain_crosswalk` (`source_schema = 'ecad'`) maps the ECAD royalty
series to *Intellectual property* (transversal, `good`). The coverage meter
stays 13/14 — ECAD is the third lens on a domain already reached.

## 5. Refresh

The data is inline in the ETL (transcribed from the pages — there is no source
file). To add a year, read the new Transparência page and append a row to
`ROWS` in `etl/ecad__headline_series_to_parquet.py`.

## 6. Validation (2026-05-23)

- 3 rows, 2023–2025; arrecadação ≥ distribuição every year (ECAD retains 9%,
  associations 6%); both series monotonically rising.
- Idempotency — re-running the ETL produces byte-identical Parquet.

## 7. Citation

> ECAD (2024–2026). *Transparência — resultados de arrecadação e distribuição
> de direitos autorais de execução pública musical*. Escritório Central de
> Arrecadação e Distribuição.

---

*Methodology note for `atana.ecad`. Prepared 2026-05-23. Phase 4c.3. Pairs with
`bcb_sgs_ip_services.md` (4c.1), `inpi_indicadores.md` (4c.2) and
`_atana_intel/phase4c_inpi_ecad_spec.md`.*
