# RAIS — Methodology

> **Sprint 0 deliverable for the Atana RAIS infrastructure.**
> Defines the filtering universe, harmonization rules, schema design, and validation strategy for the `md:atana.rais.*` schema. This document gates the Sprint 1 ETL.

**Author:** João Roque, Atana
**Version:** 1.0 — 2026-05-18
**Status:** Ready for Sprint 1 review

---

## 1. Source and access

- **Source:** RAIS — Relação Anual de Informações Sociais, Ministério do Trabalho e Emprego.
- **Access path:** `basedosdados.br_me_rais.microdados_vinculos` and `microdados_estabelecimentos` on BigQuery, via the `basedosdados` Python library.
- **Years in scope:** 2014–2023 (10 years). 2009–2013 is a future extension if the panel needs to predate the Reforma Trabalhista (2017) by a wider margin.
- **License/use:** RAIS is administrative microdata published by MTE in CC BY 4.0 spirit through basedosdados (anonymized).
- **Storage:** Phase 2 outputs land in `raw/rais/` as Parquet and in `md:atana.rais.*` as cloud-canonical tables.

---

## 2. Population definition — two filter cuts, surfaced as per-row flags

We use two complementary filters at extraction time, producing a *union* of cultural vínculos (CNAE direct OR CBO family match). Each row carries `in_cut_a` and `in_cut_b` boolean flags so downstream analyses can intersect, union, or partition as needed. Sprint 1 does not materialize separate Cut A / Cut B / intersection tables — the single `vinculos_culturais` table with flag columns is more flexible and avoids redundant storage.

### 2.1 Cut A — CNAE-filtered (cultural *establishments*)

Filter `cnae_2_subclasse IN <list>` where `<list>` is `raw/rais/_reference/cnae_cultural.parquet` filtered to `relacao_cultura = 'direct'`. **33 5-digit subclasses across 12 CNAE divisions.**

This is the **establishment-side** definition of the cultural sector. A worker counts as cultural if their employer is a cultural firm, regardless of the worker's occupation. Matches the IBGE Conta-Satélite da Cultura logic for `Cultura no Cempre` and related establishment-side tabulations.

The `panel_cnae_municipio_ano` aggregate (§5.3) is built from Cut A.

### 2.2 Cut B — CBO-filtered (cultural *occupations*)

Filter `cbo_2002 LIKE 'NNNN%'` where `NNNN` ranges over the 62 CBO-Domiciliar families in `raw/rais/_reference/cbo_cultural.parquet`. The expansion produces ~600 6-digit CBO 2002 subgroups.

This is the **occupation-side** definition. Includes cultural workers in non-cultural establishments — a musician at a school, a designer at a software firm, an architect at a construction company. Matches the IBGE PNADC logic for `Pessoas ocupadas em ocupações culturais` (Tables 6.13–6.16 in our project).

**Cut B is the validation cut against PNADC.** RAIS Cut B totals should track PNADC totals × the formality rate, by year.

### 2.3 Cut A ∩ Cut B — the elite-formal cultural niche

Workers in cultural occupations *within* cultural establishments. Computed at query time via `WHERE in_cut_a AND in_cut_b` against `vinculos_culturais`. No separate table. This intersection is what AKM wage decomposition (Phase 4) operates on.

### 2.4 Why a single union table with flags, not three tables

The original Sprint 0 design proposed three separate tables (A, B, intersection). After the basedosdados-driven redesign (§5.bis), the single `vinculos_culturais` table with `in_cut_a`/`in_cut_b` boolean columns serves all three analytical needs at one-third the storage. The cost is slightly larger per-row width; the benefit is no redundant rows across tables.

| Question | Query against `vinculos_culturais` |
|---|---|
| Formal cultural employer landscape? | `WHERE in_cut_a` |
| Cultural workers across all employers? | `WHERE in_cut_b` |
| Cultural workers in cultural employers? | `WHERE in_cut_a AND in_cut_b` |
| Does Rouanet captação raise employment? | Defer — needs Phase 2b CNPJ join |

---

## 3. Reference tables — source of truth

Two parquet files in `raw/rais/_reference/` are the canonical filtering inputs. Both are deterministic outputs of `etl/rais__build_reference_tables.py`.

### 3.1 `cnae_cultural.parquet`

**Source:** IBGE *Sistema de Informações e Indicadores Culturais 2007-2010*, Notas Técnicas Quadros 1, 2, 3 (pages 17-19 and 26-27). Stable across the 2009-2020, 2011-2022, and 2013-2024 editions.

**Columns:**

| Column | Type | Notes |
|---|---|---|
| `cnae_2_subclasse_dotted` | str | e.g. `58.11-5` (display) |
| `cnae_2_subclasse` | str | e.g. `58115` (RAIS storage format) |
| `cnae_2_divisao` | str | e.g. `58` (2-digit roll-up) |
| `denominacao` | str | full IBGE descriptor |
| `secao_cnae` | str | C/G/J/M/N/P/R/S (CNAE section) |
| `relacao_cultura` | str | `direct` or `indirect` |
| `siic_dominio` | str | UNESCO/SIIC cultural domain |

**Counts:**

| | Direct | Indirect | Total |
|---|---:|---:|---:|
| Subclasses (5-digit) | 33 | 41 | 74 |
| Divisions (2-digit) | 12 | 11 | (overlap) |

### 3.2 `cbo_cultural.parquet`

**Source:** IBGE *Sistema de Informações e Indicadores Culturais 2007-2010*, Notas Técnicas pages 20-22 (CBO-Domiciliar family list).

**Columns:**

| Column | Type | Notes |
|---|---|---|
| `cbo_familia` | str | 4-digit root, e.g. `2624` |
| `denominacao` | str | full IBGE descriptor |
| `cbo_dominio` | str | internal grouping |
| `cbo_familia_grande_grupo` | str | first digit (CBO grande grupo) |
| `cbo_familia_subgrupo_principal` | str | first 2 digits |

**Counts:** 62 families across grande grupos 2 (15), 3 (22), 4 (1), 7 (22), 9 (2).

**RAIS expansion:** RAIS publishes CBO 2002 at 6-digit subgroup level. The Sprint 1 ETL expands each 4-digit family by `cbo_2002 LIKE 'NNNN%'`. Spot-check: family `2624` (Compositores, músicos e cantores) expands to 6-digit codes `262405` (Compositor), `262410` (Músico arranjador), `262415` (Músico intérprete cantor), `262420` (Músico intérprete instrumentista), `262425` (Músico regente), `262430` (Musicólogo).

### 3.3 What was corrected from roadmap §3.3

The original roadmap listed 25 CNAE codes informally. Sprint 0 SIIC cross-check produced the following corrections:

| Change | Code | Reason |
|---|---|---|
| Add | 18.11-3, 18.21-1, 18.22-9, 18.30-0 | Impressão e reprodução — SIIC Quadro 1, missed in roadmap |
| Add | 32.20-5 | Fabricação de instrumentos musicais — SIIC Quadro 1 |
| Add | 58.21-2, 58.22-1, 58.23-9 | Edição integrada à impressão — SIIC Quadro 3 |
| Add | 73.19-0 | Atividades de publicidade NSP — SIIC Quadro 3 |
| Add | 94.93-6 | Organizações associativas ligadas à cultura — SIIC Quadro 1 |
| Remove | 58.19-1 | Not in any SIIC quadro |

---

## 4. Harmonization decisions

### 4.1 CNAE 1.0 → 2.0 transition

CNAE 2.0 came into force in 2007 and applies retroactively to all IBGE economic statistics from 2007 reference year onward. Our panel starts in 2014 — well after the transition. **No harmonization needed for the 2014–2023 window.** Documented here to remove ambiguity for future panel extensions.

If/when the panel extends back to pre-2007 RAIS, we would adopt the IBGE official correspondence table (`Tabela de Correspondência CNAE 1.0 ↔ CNAE 2.0`) maintained at https://concla.ibge.gov.br/. The transition is non-1:1 for several cultural classes (notably 60.21-7 emerged from splitting older "rádio e televisão" classes), so harmonized pre-2007 series would be flagged with `cnae_harmonizado = True` and the original code preserved.

### 4.2 CBO 2002 stability

CBO 2002 has been the official RAIS occupation classification since 2003. Within our 2014–2023 window, CBO 2002 is stable. Minor revisions to individual 6-digit subgroups have not affected the 4-digit family roots used for filtering. **No harmonization needed.**

### 4.3 CBO vs CBO-Domiciliar

PNADC uses **CBO-Domiciliar** (4-digit families, designed for household-survey precision). RAIS uses **CBO 2002** (6-digit subgroups, designed for employer-reported precision). The SIIC cultural definition was originally specified in CBO-Domiciliar terms; we expand to CBO 2002 via `LIKE 'NNNN%'` filter to maintain comparability between PNADC and RAIS while exploiting RAIS' finer granularity.

**One subtle point:** CBO-Domiciliar occasionally regroups CBO 2002 families at the 4-digit level for survey-precision reasons. Our list is faithful to SIIC's CBO-Domiciliar codes, so the LIKE expansion produces the comparable RAIS subset by construction.

### 4.4 RAIS variable schema drift across years

Variables in RAIS have evolved across the 2014–2023 window:

| Period | Schema notes |
|---|---|
| 2014–2017 | Pre-eSocial. Variable names follow MTE legacy schema. |
| 2018–2020 | Transition: dual-system, some fields added (`tipo_admissao_pcd` etc.). |
| 2021– | eSocial unified schema. Some legacy fields are deprecated. |

basedosdados has already harmonized variable names across years — the columns `valor_remuneracao_media`, `cnae_2`, `cbo_2002`, `sigla_uf`, `id_municipio` exist with stable semantics in all years 2014–2023. Sprint 2 validation will spot-check this on three randomly-chosen variables.

**One known caveat:** `valor_remuneracao_media` is in nominal BRL of the reference year. Sprint 1 ETL produces both nominal and IPCA-deflated (base = 2024) values. The IPCA deflator series is sourced from `basedosdados.br_ipea_indices.ipca` (monthly), with annual mean computed at ETL time.

### 4.5 `sigla_uf = 'IGNORADO'` (discovered in Sprint 0 Check 1 probe)

Starting in 2022 (eSocial era), basedosdados surfaces a non-canonical UF category `IGNORADO` for vínculos whose MTE-reported UF could not be determined. The 2020 and 2021 microdata do not contain this category (those rows were either absent or dropped silently in the legacy schema).

| Year | Canonical UFs | IGNORADO present? |
|---|---:|---|
| 2020 | 27 | No |
| 2021 | 27 | No |
| 2022 | 27 | Yes |
| 2023 | 27 | Yes |

**Sprint 1 ETL decision:** retain IGNORADO rows in `vinculos_em_estabelecimentos_culturais` and `vinculos_em_ocupacoes_culturais` with `sigla_uf = 'IGNORADO'` and `id_municipio = NULL`. UF-stratified analyses (Phase 3 paper, choropleth maps) must explicitly exclude IGNORADO and report the dropped-row count.

**Caveat for cross-year comparisons:** YoY 2022–2023 vs YoY 2020–2021 are internally consistent (both pairs are like-for-like). YoY 2021–2022 mixes pre/post IGNORADO regimes; if the discrepancy is material (> 2% of total), Sprint 2 produces an IGNORADO-adjusted series.

### 4.6 `mes_admissao = 0` semantics

In RAIS vínculo records, `mes_admissao = 0` indicates the worker was already employed at the reporting establishment before the reference year began (no fresh admissão during the year). This is normal RAIS semantics. The Sprint 0 Check 1 probe surfaced 882k records with `mes_admissao = 0` in 2023 vs ~40-63k for each individual month 1-12 — these are the workers carried over from previous years.

Sprint 1 ETL retains `mes_admissao = 0` records (they represent the dominant share of active vínculos at any point) and adds a derived `vinculo_iniciado_no_ano BOOLEAN` column for convenience.

---

## 5. Schema design — `md:atana.rais.*` (3-table model)

> **Important:** the original 4-table design (with `cnpj_cultural_employer_panel` as CNPJ-keyed join target) was redesigned on 2026-05-18 after the dry run revealed that basedosdados' public RAIS strips both CNPJ and PIS for LGPD compliance. See §5.bis below. The CNPJ-keyed work is deferred to **Phase 2b** via MTE FTP — scoped in `notes/rais_phase2b_mte_ftp_scoping.md`.

Three tables, all written to MotherDuck and to GitHub Parquet under `raw/rais/`.

### 5.1 `estabelecimentos_culturais`

One row per establishment-year (no CNPJ identifier — see §5.bis). ~700k rows/year × 10 years ≈ 7M rows total.

```sql
CREATE TABLE atana.rais.estabelecimentos_culturais (
    ano                              INT,
    sigla_uf                         VARCHAR,
    id_municipio                     VARCHAR,         -- IBGE 7-digit code
    cnae_2_subclasse                 VARCHAR,         -- 7-digit (basedosdados raw): CNAE class + 2-digit suffix
    cnae_2_classe                    VARCHAR,         -- 5-digit derived for SIIC-level join (see §5.ter)
    cnae_2_divisao                   VARCHAR,         -- 2-digit derived
    siic_dominio                     VARCHAR,         -- derived from cnae_cultural lookup
    tamanho_estabelecimento          VARCHAR,         -- 1-10 categories
    tipo_estabelecimento             VARCHAR,
    natureza_juridica                VARCHAR,
    natureza_estabelecimento         VARCHAR,
    indicador_simples                INT,             -- Simples Nacional regime
    indicador_atividade_ano          INT,
    indicador_pat                    INT,             -- Programa de Alimentação do Trabalhador
    indicador_rais_negativa          INT,             -- "RAIS negativa" = active CNPJ with zero vínculos
    quantidade_vinculos_ativos       INT,             -- as of 31/12
    quantidade_vinculos_clt          INT,
    quantidade_vinculos_estatutarios INT
);
```

### 5.2 `vinculos_culturais`

One row per (year, vínculo) for Cut A ∪ Cut B (CNAE direct OR CBO family match). No worker identifier. Cardinality ~2M rows/year × 10 ≈ 20M rows.

```sql
CREATE TABLE atana.rais.vinculos_culturais (
    ano                              INT,
    sigla_uf                         VARCHAR,
    id_municipio                     VARCHAR,
    id_municipio_trabalho            VARCHAR,
    cnae_2_subclasse                 VARCHAR,         -- 7-digit (basedosdados raw)
    cnae_2_classe                    VARCHAR,         -- 5-digit derived for SIIC-level join
    cnae_2_divisao                   VARCHAR,         -- 2-digit derived
    siic_dominio                     VARCHAR,         -- derived
    cbo_2002                         VARCHAR,         -- 6-digit
    cbo_familia                      VARCHAR,         -- 4-digit prefix for joins
    in_cut_a                         BOOLEAN,         -- CNAE matches direct cultural list
    in_cut_b                         BOOLEAN,         -- CBO family matches cultural list
    idade                            INT,
    sexo                             VARCHAR,
    raca_cor                         VARCHAR,
    grau_instrucao_apos_2005         VARCHAR,
    nacionalidade                    VARCHAR,
    valor_remuneracao_media          DOUBLE,          -- nominal BRL
    valor_remuneracao_media_ipca     DOUBLE,          -- IPCA-deflated (added by post-pass)
    valor_remuneracao_dezembro       DOUBLE,
    valor_remuneracao_dezembro_ipca  DOUBLE,
    valor_salario_contratual         DOUBLE,
    valor_salario_contratual_ipca    DOUBLE,
    tipo_salario                     VARCHAR,
    quantidade_horas_contratadas     INT,
    mes_admissao                     INT,             -- 0 = pre-existing (see §4.6)
    vinculo_iniciado_no_ano          BOOLEAN,         -- derived: mes_admissao between 1-12
    tipo_admissao                    VARCHAR,
    mes_desligamento                 INT,
    motivo_desligamento              VARCHAR,
    causa_desligamento_1             VARCHAR,
    tempo_emprego                    DOUBLE,          -- decimal years
    tipo_vinculo                     VARCHAR,         -- 10-95 codes
    indicador_trabalho_intermitente  INT,
    indicador_trabalho_parcial       INT,
    indicador_simples                INT,
    indicador_portador_deficiencia   INT,
    tamanho_estabelecimento          VARCHAR,         -- establishment attrs at vínculo level
    tipo_estabelecimento             VARCHAR,
    natureza_juridica                VARCHAR,
    vinculo_ativo_3112               INT              -- 1 if active on Dec 31
);
```

### 5.3 `panel_cnae_municipio_ano` (derived aggregate)

One row per (CNAE 5-digit × município × year). Aggregated from `vinculos_culturais` filtered to Cut A, joined with establishment counts from `estabelecimentos_culturais`. The grain for cross-source joins (SALIC by município/CNAE; PNADC validation). Cardinality ~5,500 municípios × 33 CNAEs × 10 years × sparsity ≈ 0.5–1M rows total.

```sql
CREATE TABLE atana.rais.panel_cnae_municipio_ano (
    ano                              INT,
    sigla_uf                         VARCHAR,
    id_municipio                     VARCHAR,
    cnae_2_classe                    VARCHAR,         -- 5-digit; the SIIC-comparable grain
    cnae_2_divisao                   VARCHAR,
    siic_dominio                     VARCHAR,
    n_estabelecimentos               INT,             -- from estabelecimentos_culturais
    n_vinculos_total                 INT,             -- all Cut A vínculos
    n_vinculos_cut_b                 INT,             -- those with cultural CBO
    salario_mediano                  DOUBLE,
    salario_mediano_ipca             DOUBLE,
    salario_dezembro_mediano         DOUBLE,
    salario_dezembro_mediano_ipca    DOUBLE,
    horas_medianas                   DOUBLE,
    idade_mediana                    DOUBLE,
    pct_mulheres                     DOUBLE,
    pct_pretos_pardos                DOUBLE,
    pct_clt                          DOUBLE,
    pct_intermitente                 DOUBLE,
    pct_parcial                      DOUBLE
);
```

### 5.ter CNAE 2.0: class (5-digit) vs subclasse (7-digit)

basedosdados stores `cnae_2_subclasse` as a 7-digit zero-padded code: the IBGE CNAE 2.0 5-digit class plus a 2-digit subclasse suffix (e.g. `5811500` = `5811-5/00` = "Edição de livros"). The SIIC publication and our `_reference/cnae_cultural.parquet` use the 5-digit class root (e.g. `58115` covers all subclasse variants of "Edição de livros"). The ETL:

1. Filters at SQL level via `SUBSTR(cnae_2_subclasse, 1, 5) IN (...)` against the 5-digit reference list.
2. Preserves the full 7-digit `cnae_2_subclasse` in the output (for any future need to distinguish e.g. `0312-4/01` "Pesca de peixes em água doce" from `0312-4/02` "Pesca de crustáceos em água doce").
3. Adds a derived `cnae_2_classe` (5-digit) for joins with the SIIC reference parquet and for the `panel_cnae_municipio_ano` grain.

All cross-source joins (with SALIC, PNADC, UNCTAD) use `cnae_2_classe` because the SIIC methodology defines cultural activities at the class level.

### 5.bis basedosdados de-identification constraint (discovered 2026-05-18)

basedosdados strips identifying columns from both RAIS microdata tables:

- `microdados_vinculos` has **no CNPJ** (no `id_estabelecimento_jurid`, no `cnpj`) and **no PIS** (no `pis`, no `pis_pasep`).
- `microdados_estabelecimentos` has **no CNPJ** (but does expose `cep`, which is much coarser).

This is a deliberate LGPD-compliance choice — exposing CNPJ + PIS together would make every vínculo personally re-identifiable. The schema retains establishment *attributes* (`tamanho`, `natureza_juridica`, `tipo_estabelecimento`) but not the establishment *identifier*.

**Implications:**

| Capability | Available via basedosdados? |
|---|---|
| Labor-market characterization (worker demographics, wages, formality, regional concentration) | YES — full |
| Establishment-attribute distribution | YES — full |
| Cross-section by CNAE × município × year | YES — see Table 5.3 |
| Longitudinal worker panel | NO — no PIS |
| Firm-level employer panel | NO — no CNPJ |
| SALIC × RAIS H1 causal identification (Rouanet captação → firm employment) | NO — needs CNPJ |
| SALIC × RAIS H0 aggregate comparison (Rouanet proponente universe vs RAIS firm universe at sector/region level) | YES — via Table 5.3 |

**Phase 3 paper split:**

- **H0 paper** (now): *"Most Lei Rouanet proponentes operate outside the formal employment frame."* Aggregate-level claim. Feasible with this Sprint 1 output alone.
- **H1 paper** (Phase 2b): *"Rouanet captação causes formal employment growth at proponente CNPJs."* Causal claim. Requires CNPJ-level join via MTE FTP — see `notes/rais_phase2b_mte_ftp_scoping.md`.

---

## 6. Worker anonymization — PIS/PASEP hashing (Phase 2b only)

> **Not applicable to Sprint 1 / basedosdados pipeline.** basedosdados strips PIS from the public vínculos table (§5.bis). This section governs the Phase 2b MTE FTP pipeline where PIS is present in the raw files.

When Phase 2b lands, PIS will be hashed at ETL time before any storage:

**Scheme:**
```python
import hashlib
SECRET = os.environ["ATANA_PIS_SALT"]   # 32-byte random, never committed
def hash_pis(pis: str) -> str:
    canonical = pis.zfill(11)
    return hashlib.sha256((SECRET + canonical).encode()).hexdigest()[:16]
```

**Properties:**
- The same PIS/PASEP produces the same hash across all years → longitudinal panel via PIS works.
- The salt is per-Atana, never published. Even if downstream tables become public, hashed PIS cannot be reversed to plaintext without the salt.
- 16-hex output (64-bit) is collision-safe at the scale of ~150M PIS values in Brazil.

**Reproducibility caveat:** the salt is held only by the ETL operator. If the salt is lost, panel rebuilds are non-reproducible. Phase 2b task: encrypt and store the salt in 1Password and in a sealed envelope before first ETL run.

The `rais__generate_pis_salt.py` script and the `ATANA_PIS_SALT` environment variable remain in the codebase as Phase 2b setup; they are not required for the Sprint 1 basedosdados ETL.

---

## 7. Validation strategy (Sprint 2 plan)

Three validation passes before Sprint 3 release:

### 7.1 Aggregate cross-check vs SIIC published series

For each year 2014–2023, compare:

- Cut A total formal vínculos → SIIC Tabela 1.x (formal employment in cultural sector)
- Cut B total formal vínculos → derivable from PNADC formality rate × PNADC cultural workforce
- Cut C → no published comparator; spot-check against IBGE Tabela 6.10 (position in occupation)

**Acceptance:** Cut A and Cut B within ±5% of the SIIC/PNADC reference; document deviations.

### 7.2 Within-year duplicate detection

Workers with 2+ jobs in the same year — expected ~15% rate (literature). Sprint 2 produces `notes/rais_validation_findings.md` with the distribution.

### 7.3 CNAE 1.0 → 2.0 boundary

Verify that 2014 totals are not anomalously low compared to 2013 (the CNAE 1.0 → 2.0 transition was 2007, but reporting compliance can lag). If 2014 < 0.9 × 2015, investigate.

### 7.4 PIS hash consistency

For each PIS that appears in 2014 and 2023 (~30% of workers via PNADC longitudinal estimates), verify the hash matches. Sprint 2 sample = 1000 PIS hashes spot-checked.

---

## 8. Sprint 1 → Sprint 2 → Sprint 3 handoff

Sprint 0 ends with this document, the two parquet reference files, and the `rais_sprint0_check1.py` runnable. Sprint 1 begins by:

1. Reading `cnae_cultural.parquet` and `cbo_cultural.parquet` to drive the filter SQL.
2. Iterating years 2023 → 2014 (latest first to fail-fast on schema drift).
3. Writing per-year Parquet to `raw/rais/<table>/year=YYYY/part-0.parquet`.
4. Syncing to `md:atana.rais.*` after each year completes.

Sprint 1 deliverables are 4 fully-populated tables. Sprint 2 deliverables are the validation report. Sprint 3 deliverables are the GitHub push and the CLAUDE.md update.

---

## 9. Decisions deferred to Phase 3

These are documented here so Sprint 1 doesn't accidentally lock them in:

- **PIS-anonymized employer × employee panel.** Future request: join `cnpj_cultural_employer_panel` to `vinculos_em_estabelecimentos_culturais` for AKM. Schema supports this without modification.
- **Sample for SALIC × RAIS Phase 3:** approved-but-non-captant proponentes form the control; the data already supports the linkage.
- **2024 data ingestion:** add to `cnpj_cultural_employer_panel` when basedosdados publishes (expected Q4 2026 per their normal cadence).

---

## 10. References

- IBGE, *Sistema de Informações e Indicadores Culturais 2007-2010*. Rio de Janeiro: IBGE, 2013. Notas Técnicas, Quadros 1–3 (CNAE) and pp. 20-22 (CBO). Available at <https://biblioteca.ibge.gov.br/visualizacao/livros/liv65974.pdf>.
- IBGE, *Sistema de Informações e Indicadores Culturais 2011-2022* (informativo). 2024. <https://agenciadenoticias.ibge.gov.br/media/com_mediaibge/arquivos/ecf9ac7b96205d8c5179a9727b77a055.pdf>.
- IBGE, *Sistema de Informações e Indicadores Culturais 2013-2024* (informativo). 2025. <https://agenciadenoticias.ibge.gov.br/media/com_mediaibge/arquivos/b6c6d2b70f490c4eba9e52403fcec31b.pdf>.
- IBGE Concla — *Busca Online CNAE 2.0*. <https://concla.ibge.gov.br/busca-online-cnae.html>.
- Base dos Dados, *RAIS — Microdados de vínculos*. <https://basedosdados.org/dataset/br-me-rais>.
- Atana, *RAIS Research Roadmap*. 2026-05-18. Internal document.
