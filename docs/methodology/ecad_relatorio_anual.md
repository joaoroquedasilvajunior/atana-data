# Methodology — `atana.ecad` from the ECAD Annual Reports

Schema `atana.ecad`. Phase 4c.3 of the Atana Data expansion — the third lens on
the FCS *Intellectual property* domain: cultural-IP **income** actually
collected and distributed (music public-performance royalties).

**Source:** ECAD — *Escritório Central de Arrecadação e Distribuição* —
Relatórios Anuais 2020 / 2021 / 2022 / 2024 (versão-mercado) / 2025 (PDFs,
markitdown-converted) + the Transparência 2023 page.
**Coverage:** Brazil, national, annual. Arrecadação **2019–2025**; arrecadação
by segmento **2020–2025** (ex-2023); distribuição **2021–2025**; distribuição
by segmento **2025**; distribuição by titular type **2016–2025**.
**Licence:** ECAD published figures — public transparency disclosure.
**ETLs:** `ecad__headline_series_to_parquet.py`,
`ecad__arrecadacao_por_segmento_to_parquet.py`,
`ecad__distribuicao_por_segmento_to_parquet.py`,
`ecad__distribuicao_por_titular_tipo_to_parquet.py`.
**Ingested:** 2026-05-23 (v1) · **expanded:** 2026-05-28 (v2) ·
**corrected + multi-year:** 2026-05-29 (v3).

---

## 1. Why this is a hand-transcribed series

The IP domain reaches the corpus through three lenses: BCB (`atana.bcb`, 4c.1)
— the cross-border IP-royalty *flow*; INPI (`atana.inpi`, 4c.2) — the IP
registration *stock*; and ECAD here — IP *income*. **ECAD publishes no
machine-readable dataset.** The data sits inside annual-report PDFs (converted
via `markitdown`) and Transparência pages; charts are PNG/JPEG images read by
eye, text figures copied verbatim. No segmentation is allocated by inference.

## 2. Version history

| v | Date | Change |
|---|---|---|
| v1 | 2026-05-23 | 1 table, 3 rows (2023–2025), Transparência headline series |
| v2 | 2026-05-28 | 4 tables (8+6+13+10 rows) from the Relatório 2025 |
| **v3** | **2026-05-29** | **Arrecadação year-scramble corrected; multi-year segment + titular series added from Relatórios 2020/2022/2024. 4 tables, 70 rows (7+30+13+20).** |

### The v2 → v3 arrecadação correction (important)

v2 took its 8-row arrecadação series (2018–2025) from the Relatório 2025
*historical chart*. That chart's year labels were **scrambled by markitdown** —
the value set was right but the years 2018–2021 were permuted, and the stated
YoY labels were permuted *with* the values. Because the scramble was
self-consistent, it passed v2's internal YoY validation; it is only detectable
against contemporary reports. The cross-source reference (built 2026-05-29 from
the Relatório 2020 and 2022) is that external check:

- Relatório 2020: **2019 = R$ 1,121 mi → 2020 = R$ 905.8 mi (−19.2 %)**
- Relatório 2022: **2021 = R$ 1,086,436,152 → 2022 = R$ 1,393,765,668 (+28.3 %)**

The signature error: R$ 905.8 mi — the iconic 2020 pandemic low quoted in every
contemporary report — appeared in v2 as **2018**. v3 rewrites the series:

| year | arrecadação (R$ mi) | source |
|---:|---:|---|
| 2019 | 1,121 | Relatório 2020 |
| 2020 | 905.8 | Relatório 2020 (pandemic −19.2 %) |
| 2021 | 1,086 | Relatório 2022 |
| 2022 | 1,394 | Relatório 2022 |
| 2023 | 1,631 | Transparência 2023 (+17 % vs 2022; rounded headline R$ 1.6 bi) |
| 2024 | 1,831 | Relatório 2024 |
| 2025 | 2,105 | Relatório 2025 |

**2018 is dropped** — it is not in any available report. The leftover scrambled
value R$ 1,106 mi may belong to 2018 but is unverified and set aside (acquire a
2018/2019 report to recover it). YoY is computed in-script from the corrected
values and re-validated against the contemporary −19.2 % (2020) and +28.3 %
(2022) figures.

## 3. The central caveats

### (1) Arrecadação ≠ distribuição — a structural ≈ 9.5 pp gap

In 2025, arrecadação's digital share was 33.6 %; distribuição's pure-digital
share was 24.13 % (Streaming Vídeo 13.43 + Audio 10.11 + Serviços Digitais
0.59). The ≈ 9.5 pp gap is absorbed by ECAD operating cost (9 % in 2025; **15 %
in 2020** — 10 % ECAD + 5 % associações — a documented efficiency reduction,
though the two figures may have different perimeters), processing lag
(distribution of year N draws on arrecadação of N-1/N-2), and deferred
allocation through the mixed "Rádios + DG" / "TV aberta + DG" channels.

### (2) Distribuição 2021/2022 are likely scrambled too — NOT yet corrected

The reference corrected arrecadação only; it gives no contemporary distribuição
series. But the confirmed arrecadação-chart scramble (§2) raises the
probability that the distribuição chart (Relatório 2025 p.13) was scrambled the
same way. The current values give distribuição 2021 = R$ 1,232 mi (> 2021
arrecadação R$ 1,086 mi; ratio 1.14) and 2022 = R$ 901.6 mi (−26.8 % YoY,
implausible against +28.3 % arrecadação growth). The **clean reconstruction** —
2021 ≈ R$ 901.6 mi (tracking the 2020 pandemic arrecadação with lag), 2022 ≈
R$ 1,232 mi — removes the anomaly and restores monotonicity. This is
*inference*, not a contemporary source, so the values are **not reordered**;
the 2021 and 2022 rows of `arrecadacao_distribuicao` carry the hypothesis in
`notes`, flagged for verification against the printed PDF p.13.

### (3) The 1.25 % gap in 2025 distribution-by-segment

The thirteen named segments on Relatório p.14 sum to 98.75 %. The remaining
1.25 % is not detailed (likely "outros"/rounding). Flagged on the
smallest-share row of `distribuicao_por_segmento`; not allocated.

### (4) "Nacional" is cadastral, and it is NOT stable over time

`distribuicao_por_titular_tipo` carries the autoral/conexa nacional split,
2016–2025. "Nacional" means a titular *registered in Brazil* — which includes
Brazilian subsidiaries of foreign majors (Universal/Sony/Warner Music Brasil)
that redistribute upstream. So "77 % nacional" ≠ "77 % of royalties reach
Brazilian creators." Two further points refine Análise 21:

- The split is **volatile**, not stable: autoral nacional 68 % (2016) → 76 %
  (2019–22) → 77 % (2025); conexa nacional 79 % (2016) → 89 % (2018 peak) →
  75 % (2020 trough) → 82 % (2023) → 79 % (2025).
- The **overall** repertoire nacional share (a different aggregate, not split
  by parte) rose **65 % (2023, Transparência) → ≈ 78 % (2025)** — a +13 pp move
  in two years. Análise 21 treated 78 % as stable; this is the refinement. The
  overall figure is documented here but not tabled (it has no parte dimension).

## 4. The four tables

### `arrecadacao_distribuicao` (7 rows, 2019–2025)

Headline series: arrecadação (R$ mi, corrected — §2), distribuição (R$ exact,
2021–2025; 2021/2022 flagged — §3.2), titulares contemplados (thousands; 2020
263, 2023 323, 2024/2025 345), digital-services arrecadação share (backfilled:
2020 18 · 2021 23 · 2022 22.8 · 2024 26 · 2025 33.6; 2019/2023 NULL), custo
operacional (2020 15 % · 2025 9 %), computed YoY, per-row `notes`, `source_page`.

### `arrecadacao_por_segmento` (30 rows, 2020–2025 ex-2023)

Six-way arrecadação split per year (Televisão, Serviços Digitais, Usuários
Gerais, Show e Eventos, Rádio, Cinema). `share_pct` verbatim per Relatório;
`valor_brl_mi` derived from the corrected per-year total; each year sums to
100 %. **2023 omitted** — its pie is a JPEG at source; only the digital share
(~24–25 %, estimated) is recoverable. **2020 UG/Rádio** shares carry a
label-pairing caveat in `notes` (the markitdown reading may have swapped UG 12 /
Rádio 20 for UG 20 / Rádio 12; 2021 structure suggests the latter). The 2021
and 2022 per-segment R$ absolutes published in the Relatório 2022
(Total 2021 = R$ 1,086,436,152; 2022 = R$ 1,393,765,668; Shows +310 %, Cinema
+133 %) reconcile with these shares to within rounding — used as a cross-check,
not stored separately.

The Serviços Digitais trajectory — the "digital headline" Análise 23 was after:
**18 % (2020) → 23 (2021) → 22.8 (2022, post-pandemic Shows dilute it) →
[~24–25 est. 2023] → 26 (2024, first year as the #1 segment) → 33.6 (2025)**.
Pre-2020 it was ~10 % (Relatório 2024). It crossed ~10 % around 2019–2020.

### `distribuicao_por_segmento` (13 rows, 2025)

The 2025 distribuição thirteen-channel split with `is_digital` (TRUE only for
Streaming Vídeo, Streaming Audio, Serviços Digitais — pure-digital share
24.13 %). Sums to 98.75 % (§3.3). Unchanged from v2.

### `distribuicao_por_titular_tipo` (20 rows, 2016–2025 × {autoral, conexa})

Nacional vs estrangeiro split per parte. Identity nacional + estrangeiro = 100
in every row. 2016–2020 from Relatório 2020; 2021–2025 from Relatório 2025.
Read with §3.4.

## 5. Operational metrics (multi-year reference, not tabled)

Documented for traceability; feeds Análise 20/23. A 5th table is deferred until
a metric repeats cleanly enough to be a safe series.

| Métrica | 2020 | 2023 | 2024 | 2025 |
|---|---|---|---|---|
| Execuções streaming identificadas | — | 3.2 tri | 6.6 tri | 5.8 tri |
| Obras musicais cadastradas | 14.5 mi | 21 mi | 24.8 mi | — |
| Titulares contemplados | 263 mil | 323 mil | 345 mil | 345 mil |
| Custo operacional (ECAD+assoc.) | 15 % (10+5) | — | — | 9 % |

⚠️ Execuções streaming 6.6 tri (2024) → 5.8 tri (2025) looks like a fall — a
counting-methodology change is more likely; do not use as a series without
verification. The custo 15 % → 9 % reduction may compare different perimeters.
Other 2025 operational metrics (5.8 tri executions, 50 bi AV exhibitions,
11,400 obras + 7,400 fonogramas blocked for generative-AI indication, R$ 130 mi
judicial settlements, R$ 50 mi GRP distribution, R$ 4.6 k/year avg per titular)
are in the Análise 20 record.

## 6. Domain mapping → 2025 UNESCO FCS

`canonical.domain_crosswalk` (`source_schema = 'ecad'`) maps the ECAD series to
**Intellectual property** (transversal, `good`). All four tables share the one
`ecad` crosswalk row; coverage stays **13/14**. ECAD is the third IP lens after
BCB (4c.1) and INPI (4c.2).

## 7. Refresh

Data is inline in each ETL. To add a year, read the relevant Relatório/Transp.
page, append to the constant, and re-run. All ETLs are idempotent
(byte-identical reruns). The single open acquisition is the **2023 arrecadação
segment split** (JPEG-only) — a 2023 report PDF would close the segment series.

## 8. Validation (2026-05-29)

All ETLs ran cleanly with `ATANA_ETL_SKIP_PUSH=1`; all parquets byte-identical
on rerun.

- `arrecadacao_distribuicao` — 7 rows 2019–2025; corrected YoYs match
  contemporary reports (2020 −19.2 %, 2022 +28.4 % vs +28.3 % stated, 2023
  +17.0 %); the R$ 905.8 mi pandemic low correctly on 2020; 2021/2022
  distribuição scramble flagged; digital + custo backfilled.
- `arrecadacao_por_segmento` — 30 rows; every year sums to 100 %; valor_brl_mi
  reconciles with each corrected total; digital trajectory verified; 2020
  UG/Rádio caveat present.
- `distribuicao_por_segmento` — 13 rows; 98.75 %; pure-digital 24.13 %.
- `distribuicao_por_titular_tipo` — 20 rows; nacional + estrangeiro = 100 each;
  source boundary consistent.

## 9. Open analysis follow-ups (Atana Assistant — pending João's decision)

Data-side is done; these are *analysis-markdown* updates the corpus
deliberately leaves to a human decision:

- **Análise 23** — replace the estimated digital band with the real series;
  correct "#1 in 2025" → "#1 in 2024"; the digital trajectory is now data.
- **Análise 21** — the nacional share rose 65 %→78 % (2023→2025); it is not
  stable as the analysis currently states.

## 10. Citation

> ECAD (2020–2026). *Relatórios Anuais* 2020, 2021, 2022, 2024, 2025; *Portal da
> Transparência*. Escritório Central de Arrecadação e Distribuição.
> <https://www4.ecad.org.br>.

---

*Methodology note for `atana.ecad`. v1 2026-05-23, v2 2026-05-28, v3
2026-05-29. Phase 4c.3. Pairs with `bcb_sgs_ip_services.md` (4c.1),
`inpi_indicadores.md` (4c.2).*
