# Methodology — `atana.ecad` from the ECAD Annual Report

Schema `atana.ecad`. Phase 4c.3 of the Atana Data expansion — the third lens on
the FCS *Intellectual property* domain: cultural-IP **income** actually
collected and distributed (music public-performance royalties).

**Source:** ECAD — *Escritório Central de Arrecadação e Distribuição* —
Relatório Anual 2025 (PDF, 32 pp.), supplemented by the
Transparência pages on <https://www4.ecad.org.br>.
**Coverage:** Brazil, national, annual **2018–2025** (arrecadação) and
**2021–2025** (distribuição + breakdowns).
**Licence:** ECAD published figures — public transparency disclosure.
**ETLs:** `etl/ecad__headline_series_to_parquet.py`,
`etl/ecad__arrecadacao_por_segmento_to_parquet.py`,
`etl/ecad__distribuicao_por_segmento_to_parquet.py`,
`etl/ecad__distribuicao_por_titular_tipo_to_parquet.py`.
**Ingested:** 2026-05-23 (v1, 3 rows) · **expanded:** 2026-05-28 (v2,
4 tables).

---

## 1. Why this is a hand-transcribed series

The IP domain reaches the corpus through three lenses: BCB (`atana.bcb`, 4c.1)
— the cross-border IP-royalty *flow*; INPI (`atana.inpi`, 4c.2) — the IP
registration *stock*; and ECAD here — IP *income*, the music royalties a
collective-management body actually collects from users and pays out to
rights-holders.

**ECAD publishes no machine-readable dataset.** The Transparência pages carry
headline figures as page text; the segment-by-segment breakdown is published
only as PNG chart images; the deeper data sits in annual-report PDFs. The
v2 expansion takes the ECAD **Relatório Anual 2025** (32 pp., released April
2026) — converted from PDF to markdown via `markitdown` — and transcribes its
tables and pie-chart values verbatim into four sibling Parquet tables. Image
charts are read by eye; text figures are copied verbatim. **No segmentation
is allocated by inference**; what the report leaves unsplit stays unsplit (see
§4 on the 1.25 % distribution gap).

## 2. What changed v1 → v2 (2026-05-28)

v1 (2026-05-23) carried a single 3-row table from the Transparência pages
(2023–2025). v2 (2026-05-28) extends to four tables sourced from the 2025
Annual Report:

| Table | Rows | Years | What it adds |
|---|---:|---|---|
| `arrecadacao_distribuicao` (extended) | 8 | 2018–2025 | 5 historical years; precise distribuição R$ value (vs v1's rounded billions); `custo_operacional_pct` |
| `arrecadacao_por_segmento` (new) | 6 | 2025 | The six-way arrecadação pie — Serviços Digitais 33.6 % through Cinema 1.3 % |
| `distribuicao_por_segmento` (new) | 13 | 2025 | The thirteen-channel distribuição pie; `is_digital` flag for the three pure-digital channels |
| `distribuicao_por_titular_tipo` (new) | 10 | 2021–2025 | The autoral and conexa parts each split nacional / estrangeiro |

**Schema break inside the headline table:** v1's `arrecadacao_brl_billion` /
`distribuicao_brl_billion` (rounded R$ bi) became `arrecadacao_brl_mi` (R$ mi
from p.12) and `distribuicao_brl` (exact R$ from p.13). The YoY columns are
now *computed in-script* from the values themselves — see §3 caveat (2).

## 3. The central caveats

These four caveats apply to anyone reading from `atana.ecad`. They are
flagged in each table's `notes` column and (where applicable) in the
`maybe_push`-synced MotherDuck schemas via meta-json.

### (1) Arrecadação ≠ distribuição — a structural ≈ 9.5 pp gap

In 2025, arrecadação's digital share was **33.6 %**; distribuição's
*pure-digital* share was **24.13 %** (Streaming Vídeo 13.43 + Streaming Audio
10.11 + Serviços Digitais 0.59). The ≈ 9.5 pp difference is not double-counting
or measurement noise. It is absorbed by:

- ECAD operating cost — **9 %** of arrecadação in 2025 (stable, per the
  report), captured in `arrecadacao_distribuicao.custo_operacional_pct`;
- **timing lag** — distribution of year N draws on arrecadação of N-1 and
  N-2 via the processing cycle, so the digital-platform money paid into
  ECAD in 2025 is partially distributed in 2026–2027;
- **deferred allocation** — a portion of digital arrecadação routes
  through aggregator categories ("Rádios + DG", "TV aberta + DG") rather
  than the pure-digital channels, blurring the comparison.

A practical consequence: per-year, distribuição can *exceed* arrecadação when
prior-year arrecadação was depressed and the lag catches up — this is what
happens in 2021 (ratio dist/arrec = 1.10) after the 2020 pandemic dip. The
ETL prints these ratios on every run; they live in 0.65–1.10 across the
2021–2025 window in v2.

### (2) The 2022 distribuição anomaly — needs PDF re-verification

The transcribed 2022 distribuição of **R$ 901,588,853** implies a −26.8 %
YoY versus 2021, which contradicts the +24.4 % arrecadação growth in 2022.
Two competing explanations:

- **(a) Genuine one-off drop** — a 2022 reprocessing event post-pandemic.
  The Relatório itself does not annotate this as such.
- **(b) Label swap in the markitdown conversion** — the 2021 caption
  "+36.66 % vs 2020" implies a 2020 baseline of ≈ R$ 901.6 mi, which is
  almost exactly the figure labelled "2022". So markitdown may have swapped
  the 2020 and 2022 labels.

The v2 ETL preserves the value as transcribed and flags it explicitly in
the row's `notes` column. **Verify against the printed PDF table on p.13
before any downstream analysis uses the 2022 distribuição figure.**

### (3) The 1.25 % gap in 2025 distribution-by-segment

The thirteen named segments on Relatório p.14 sum to **98.75 %**. The
remaining 1.25 % is not detailed on the page — likely "outros" or a rounding
artifact. The v2 ETL flags this in the `notes` column of the smallest-share
row (Festa Junina, 0.50 %) and surfaces it during validation. It is **not
silently allocated** to any named channel.

### (4) "78 % nacional" is a *cadastral* category, not a *creator* category

`distribuicao_por_titular_tipo` carries the headline reading "≈ 77 / 23
autoral, ≈ 79 / 21 conexa" in 2025. "Nacional" here means a titular
registered in Brazil — which includes the Brazilian *editoras* / *gravadoras*
that are subsidiaries of foreign majors (Universal Music Brasil, Sony Music
Brasil, Warner Music Brasil, etc.). Those subsidiaries redistribute upstream
to their parent companies under intra-group flow. So a query that reads
"77 % nacional" as "77 % of royalties go to Brazilian creators" is wrong.
The composition of the cadastral "nacional" share is the question Análise 21
(`analise_21_geografia_distribuicao_ecad.md`) drills into.

## 4. The four tables

### `arrecadacao_distribuicao` (8 rows, 2018–2025)

Headline series: total arrecadação (R$ mi, verbatim p.12), total
distribuição (R$ exact, verbatim p.13), titulares contemplados (thousands),
digital-services arrecadação share, custo operacional, derived YoY,
per-row `notes` and `source_page`. Years 2018–2020 carry only arrecadação;
distribuição starts in 2021.

### `arrecadacao_por_segmento` (6 rows, 2025 only)

The 2025 arrecadação pie at the highest level: Serviços Digitais 33.6 % ·
Televisão 20.4 % · Show e Eventos 19.5 % · Usuários Gerais 18.1 % ·
Rádio 7.1 % · Cinema 1.3 %. `valor_brl_mi` is derived: TOTAL × share / 100.
Sum to 100.00 %. Future Annual Reports add rows without schema change.

### `distribuicao_por_segmento` (13 rows, 2025 only)

The 2025 distribuição pie in the report's finer 13-channel split. The
`is_digital` flag marks the three pure-digital channels (Streaming Vídeo,
Streaming Audio, Serviços Digitais) and is FALSE for the mixed channels
"Rádios + DG" and "TV aberta + DG" — those carry both terrestrial and
digital simulcasts that the report does not separate. The pure-digital
share = 24.13 % (CLAUDE.md v30's 24.1 % rounding). The thirteen named
segments sum to 98.75 %; the 1.25 % gap is the documented anomaly (§3.3).

### `distribuicao_por_titular_tipo` (10 rows, 2021–2025 × {autoral, conexa})

Nacional vs estrangeiro split, separately for the autoral part (composers,
lyricists) and the conexa part (performers, phonogram producers). Identity
nacional + estrangeiro = 100 holds in every row. Autoral is stable; conexa
is more volatile (peaks at 82 / 18 in 2023, settles to 79 / 21 by 2025).
Read with §3.4 (the cadastral caveat) in mind.

## 5. Operational metrics not in any table

The 2025 Relatório also carries operational metrics that are **single-year
2025 snapshots** — heterogeneous enough that a long-format table for one year
would be over-engineering. They are documented here for traceability and feed
Análise 20 (IA generativa) directly:

- **Identified executions** in streaming platforms in 2025: **5.8 trillion**
- **Audiovisual content exhibitions** in 2025: **50 billion**
- YoY in identified executions, *Música ao Vivo*: **+97 %**
- YoY in identified music executions, *Televisão*: **+38 %**
- Generative-AI blocks accumulated in 2025: **11,400 obras + 7,400
  fonogramas** (first Brazilian legal actions on generative-AI music in
  2025, filed by the ECAD legal department)
- Judicial settlements concluded in 2025: **R$ 130 million**
- *Gestão de Roteiros Pendentes* (GRP) distribution in 2025: **R$ 50
  million** across 9,000+ recovered repertoires
- Average distribution per titular in 2025: **R$ 4.6 k / year**
  (≈ R$ 383 / month)
- ECAD operating cost on arrecadação: **9 %** (stable; captured in the
  headline table for 2025 only)

If a future Relatório year repeats these metrics — converting them from a
single-year prose recital into a time series — they earn a fifth table at
that point.

## 6. Domain mapping → 2025 UNESCO FCS

`canonical.domain_crosswalk` (`source_schema = 'ecad'`) maps the ECAD royalty
series to **Intellectual property** (transversal, `good`). The four v2 tables
all live under the same `ecad` source-schema entry — the crosswalk does not
get four new rows. The coverage meter stays **13/14** — ECAD continues to be
the third lens on a domain already reached by BCB (4c.1) and INPI (4c.2).

## 7. Refresh

Data is inline in each ETL (no external source file). To add a year to a
table, read the relevant Relatório Anual or Transparência page, append to
the `ROWS` constant in the relevant ETL, and re-run. All four ETLs are
idempotent — byte-identical reruns when the inputs do not change.

The Curious Scientist / DB-updater agents do not have a calendar trigger
for ECAD (the report is annual, released ~April; a calendar trigger could
be added at any time).

## 8. Validation (2026-05-28)

All four ETLs ran cleanly with `ATANA_ETL_SKIP_PUSH=1` in the sandbox build:

- `arrecadacao_distribuicao` — 8 rows 2018–2025; arrecadação YoYs (computed)
  reconcile with the PDF caption labels within ±0.2 pp; distrib/arrec
  ratios surfaced and the 2021 catch-up + 2022 anomaly visible; 2022 row
  carries the verification caveat; `custo_operacional_pct` = 9.0 in 2025
  only.
- `arrecadacao_por_segmento` — 6 rows; shares sum to 100.00 %; derived
  R$ 2,105 mi reconciles with the corpus total.
- `distribuicao_por_segmento` — 13 rows; shares sum to 98.75 % (the
  documented 1.25 % gap); pure-digital share = 24.13 %; gap note attached
  to the smallest-share row.
- `distribuicao_por_titular_tipo` — 10 rows; nacional + estrangeiro = 100
  in every row; (year, parte) unique.
- All four parquets byte-identical on rerun.

## 9. Citation

> ECAD (2026). *Relatório Anual 2025*. Escritório Central de Arrecadação e
> Distribuição. <https://www4.ecad.org.br>.

---

*Methodology note for `atana.ecad`. Prepared 2026-05-23 (v1), expanded
2026-05-28 (v2). Phase 4c.3. Pairs with `bcb_sgs_ip_services.md` (4c.1),
`inpi_indicadores.md` (4c.2) and `_atana_intel/phase4c_inpi_ecad_spec.md`.*
