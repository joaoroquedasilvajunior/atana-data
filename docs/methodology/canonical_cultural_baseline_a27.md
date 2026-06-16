# `canonical.cultural_sector_baseline_a27` — the Análise 27 reference baseline as a curated layer

> **Status (2026-06-16):** Sandbox-side ✅ built · GitHub ❌ pending push · MotherDuck ❌ pending sync
> 2 tables / 273 rows in `curated/cultural_sector_baseline_a27_*.parquet`

> Methodology note. Built 2026-06-16. Build script:
> `etl/canonical__build_cultural_baseline_a27.py` →
> `curated/cultural_sector_baseline_a27_trajectory.parquet` (270 rows) +
> `curated/cultural_sector_baseline_a27_three_rulers.parquet` (3 rows).

## 1. What this is

Análise 27 is the corpus's **reference baseline** for the Brazilian cultural
sector measured through IBGE SIIC capítulo 2 (Pesquisas estruturais em
empresas, PIA/PAS/PAC) over 2013, 2019–2023. This curated layer freezes the
analysis's canonical numbers into two Parquet tables so that downstream
cross-analyses can JOIN against them without re-reading the xlsx.

The Análise itself (`analise_27_conta_de_producao_referencia.md`, v1.2 at
ingest time) carries the narrative. This layer carries the numbers.

### Two tables

| Table | Grain | Rows | What it holds |
|---|---|---:|---|
| `cultural_sector_baseline_a27_trajectory` | `recorte × indicator × year` | **270** | Trajectory 2013→2023 of 5 indicators (VA, salários, empresas, ocupados, salário médio) across 9 recortes (cultural total, atividades centrais, telecom, software, 4 central domains B/C/E/F, total economia). Both nominal and IPCA-deflated to BRL 2023. |
| `cultural_sector_baseline_a27_three_rulers` | `ruler` | **3** | The 2023 snapshot under three measurement frames: IBGE SIIC inteiro (R$ 388 bi), IBGE só atividades centrais (R$ 138 bi), UNESCO FCS 2025 conservative estimate (R$ 150–164 bi, point R$ 157 bi). |

## 2. Why this exists as a canonical layer

Análise 27 is consumed as denominator by other corpus work:

- **Análise 14** (mai/2026) — the original IBGE estruturais peça; A27 supersedes its denominator framing.
- **Análise 25 / Note #19** (jun/2026) — Design + software 4-lens analysis; A27 grounds the Brazilian-cultural-VA scale.
- **Note #21** (jun/2026) — the R$ 388 bi figure appears in §3 as context.
- **Vol. 1 of the book** — A27 enters as the methodological-reference chapter.
- **Vol. 2 (Atana Index)** — Brazilian numbers anchor here.

The Curious Scientist criterion (`_atana_intel/phase6_corpus_criterion_and_vol2_scoping.md`)
asks: "consumed by what?" Three Notes and two book volumes is enough. Curated.

## 3. Source — and a critical correction at ingest

Source: `atana.ibge_estruturais.tab_2_1` through `tab_2_8` (Parquet form of
SIIC cap. 2 tables, already in the corpus since Phase 4a, 2026-05-23).

**Critical correction made during this ingest** (logged in `db_update_log.md`,
the build script `corrections` block, and the Análise's v1.2 nota de correção):

> v1.0 and v1.1 of Análise 27 reported telecomunicações as R$ 18.8 bi (2023).
> Reconciliation against the Parquet found that the SIIC cultural-periphery
> includes **two** telecom CNAEs, not one:
>
> - "Telecomunicações por fio, sem fio e por satélite" — R$ 87.3 bi (2023)
> - "Outras atividades de telecomunicações" — R$ 18.8 bi (2023)
>
> The R$ 18.8 figure was an openpyxl substring-match artifact (the original
> Análise 27 charts script `gen_a27_charts.py` matched on
> `"Atividades de telecomunicações"` which, due to lexicographic ordering,
> picked up only the second row). Correct total: **R$ 106.1 bi**.

The trajectory Parquet now carries `n_source_rows_aggregated` exposing this:
the `telecom` recorte rows have `n_source_rows_aggregated = 2`, all others = 1.

### Substantive implication

Telecom did NOT grow +53% real over 2013–2023 (as v1.1 claimed) — it was
**flat-to-declining (−1.2% real)**. The story of real growth in Brazilian
cultural VA is **software alone (+76% real)**, not software + telecom.
The §4 narrative of the Análise was rewritten on the same day this layer was
built; see the v1.2 nota de correção in `analise_27_conta_de_producao_referencia.md`.

## 4. Deflation

IPCA factor 2013→2023 = **1.7752** (BCB SGS 433, série `atana.macro.ipca`).
Year-by-year factors, all hard-coded inline in the build script:

| year | IPCA factor → 2023 |
|---:|---:|
| 2013 | 1.7752 |
| 2019 | 1.2871 |
| 2020 | 1.2220 |
| 2021 | 1.1180 |
| 2022 | 1.0610 |
| 2023 | 1.0000 |

Applied only to monetary indicators (`va`, `salarios`, `salario_medio`).
Non-monetary (`empresas`, `ocupados`) carry `value_real_brl2023 = NULL` and
`ipca_deflator_to_2023 = NULL`. This matches the Atana convention for
deflated trajectories (Análises 14/18/22/23/25, paper acadêmico H0).

## 5. The "three rulers" table

`cultural_sector_baseline_a27_three_rulers.parquet` is the canonical answer to
"how big is the Brazilian cultural sector in 2023?":

| ruler | VA (BRL bi, 2023) | basis |
|---|---:|---|
| IBGE SIIC — setor cultural inteiro (centrais + periferias) | **387.9** | SIIC convention, measured |
| IBGE SIIC — só atividades centrais | **138.5** | SIIC convention, measured |
| UNESCO FCS 2025 / CCE — reclassificação conservadora | **157.0** *(range 150–164)* | Atana estimate via `canonical.domain_crosswalk`, declared assumptions in Análise 27 §11 |

The FCS estimate is **declarative, not measured** — it's the conservative
re-mapping of IBGE recortes through the corpus's `domain_crosswalk`, with
explicit fractional cultural shares for software (15%, range 10–20%), telecom
(0%, by FCS infrastructure-not-output convention), and demais periferia
(10%, range 5–15%). The range columns `va_brl_low` / `va_brl_high` preserve
this uncertainty.

The point of the three rulers is **pluralism, not arbitration**. None of the
three is "the right number" — each is right under its frame. The same data,
read by three rulers, gives three answers. Análise 27 §11 nominates this as
the same methodological move as Notes #03, #07, #08, #18 — the corpus's
distinctive analytical commitment.

## 6. Schema

### `cultural_sector_baseline_a27_trajectory`

| column | type | notes |
|---|---|---|
| `recorte_key` | VARCHAR | machine key (9 values: `total_economia`, `cultural_total`, `atividades_centrais`, `telecom`, `software`, `B_apresentacoes`, `C_artes_visuais`, `E_audiovisual`, `F_design`) |
| `recorte_label` | VARCHAR | human label |
| `recorte_type` | VARCHAR | `total_economy` / `cultural_aggregate` / `cultural_central` / `cultural_periphery` / `cultural_domain` |
| `indicator_key` | VARCHAR | `va` / `salarios` / `empresas` / `ocupados` / `salario_medio` |
| `indicator_label` | VARCHAR | human label |
| `unit_native` | VARCHAR | `R$ mil` / `unidades` / `pessoas` |
| `year` | INTEGER | 2013, 2019, 2020, 2021, 2022, 2023 |
| `value_nominal` | DOUBLE | as reported by SIIC |
| `value_real_brl2023` | DOUBLE | IPCA-deflated to 2023; NULL for non-monetary |
| `ipca_deflator_to_2023` | DOUBLE | applied factor; NULL for non-monetary |
| `n_source_rows_aggregated` | INTEGER | how many SIIC rows were summed for this recorte (1 for all single-CNAE recortes; 2 for `telecom`) |
| `source_table` | VARCHAR | `atana.ibge_estruturais.tab_2_*` |

### `cultural_sector_baseline_a27_three_rulers`

| column | type | notes |
|---|---|---|
| `ruler_key` | VARCHAR | `ibge_siic_total` / `ibge_siic_centrals_only` / `unesco_fcs_2025` |
| `ruler_label` | VARCHAR | human label |
| `ruler_basis` | VARCHAR | `measured` / `derived_estimate` |
| `va_brl2023` | DOUBLE | point estimate, BRL bi |
| `va_brl_low` | DOUBLE | range floor (NULL for measured rulers) |
| `va_brl_high` | DOUBLE | range ceiling (NULL for measured rulers) |
| `year` | INTEGER | 2023 |
| `assumptions` | VARCHAR | text — FCS row carries the share assumptions; IBGE rows carry the SIIC convention |
| `source_table` | VARCHAR | upstream |

## 7. Validation

Per-recorte presence: all 9 recortes × 5 indicators × 6 years = 270 rows for
trajectory, exactly 3 rows for three_rulers. Cross-checks:

- `cultural_total` 2023 VA = R$ 387.9 bi (matches Análise 27 §1 box).
- `atividades_centrais` 2023 VA = R$ 138.5 bi (matches §3 box).
- `telecom` 2023 VA = R$ 106.1 bi sum of 2 CNAEs (the corrected value; matches §3 corrected box).
- `software` 2023 VA = R$ 84.3 bi (matches §4 box).
- Identity check: centrais (138.5) + software (84.3) + telecom (106.1) + demais (59.0) = R$ 387.9 bi ✓.
- IPCA 2013→2023 cultural total: nominal R$ 199.1 bi → real R$ 353.5 bi (matches §3 trajectory table).

Idempotent — byte-identical reruns (the build script writes through a tempfile
to handle the sandbox cross-mount permission constraint, then atomically
replaces).

## 8. Read recipe

```sql
-- The fast version of "how big is the Brazilian cultural sector in 2023?"
SELECT ruler_label, va_brl2023, va_brl_low, va_brl_high
FROM   atana.canonical.cultural_sector_baseline_a27_three_rulers
ORDER  BY va_brl2023 DESC;

-- Real-terms trajectory of cultural VA by recorte
SELECT recorte_label, year, value_real_brl2023
FROM   atana.canonical.cultural_sector_baseline_a27_trajectory
WHERE  indicator_key = 'va' AND recorte_type IN ('cultural_aggregate', 'cultural_central', 'cultural_periphery')
ORDER  BY recorte_label, year;

-- Verify the telecom correction is in
SELECT recorte_key, year, value_nominal/1e6 AS brl_bi, n_source_rows_aggregated
FROM   atana.canonical.cultural_sector_baseline_a27_trajectory
WHERE  recorte_key = 'telecom' AND indicator_key = 'va'
ORDER  BY year;
```

## 9. How to cite

> João Roque da Silva Junior, 2026. *Brazilian cultural sector reference
> baseline 2013-2023 (Análise 27, v1.2).* `atana.canonical.cultural_sector_baseline_a27`,
> derived from IBGE SIIC capítulo 2 via `atana.ibge_estruturais` and IPCA
> deflated through `atana.macro.ipca`. Three-rulers row carries an authorial
> reclassification through `canonical.domain_crosswalk` (FCS 2025).
> atana.studio/data/.

---

*Methodology note for `atana.canonical.cultural_sector_baseline_a27`. Prepared
2026-06-16. Atana / atana.studio · CC BY 4.0.*
