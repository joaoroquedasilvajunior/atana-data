# TCU PNAB audit (Acórdão 1709/2025) — governance & accountability lens

> **Status (2026-06-14):** GitHub ✅ `5fa9c34` on origin/main · MotherDuck ✅ live · 2 tables / 8 rows in `raw/tcu/`

**Schema:** `atana.tcu` · **Tables:** 2 · **Rows:** 8 · **Ingested:** 2026-06-04 (Phase 5c)

The **Tribunal de Contas da União** is Brazil's federal audit court. Under the *Referencial de Controle de Políticas Públicas* it audited the *Política Nacional Aldir Blanc de Fomento à Cultura* (PNAB) — the largest single fomento policy in Brazilian cultural-economy history (R$ 15 bn statutory / R$ 3 bn-per-year). Acórdão **1709/2025** (sessão 30/07/2025, relator Augusto Nardes, processo TC 025.939/2024-6) carries the assessment.

This is the **first governance/audit lens** in the Atana corpus. It does not extend the FCS-domain coverage meter (the audit covers fomento policy, which by design crosses all 7 cultural domains); it adds a NEW institutional standpoint over the same policy the corpus already measures from the funded-projects side (`atana.salic`, Análises 5 / 7 / 8) and the funded-workforce side (`atana.rais`, `atana.ibge_pnadc`, Análises 11 / 12 / 17-19).

## §1. The pluralism cut

"What got funded" (SALIC microdata) **vs.** "what was held to account" (TCU governance findings). Same fomento policy, two institutional standpoints. The corpus now reads:

| Lens | Schema | Measures |
|---|---|---|
| Funded projects, distribution by proponent | `atana.salic` | Approval, captação, geography, segment, donor |
| Funded workforce + sectoral employment | `atana.rais`, `atana.ibge_pnadc` | Formal contracts, earnings, occupations |
| Funded organisations + small-business stratum | `atana.ibge_cempre` | Survival, MEI explosion |
| **Governance over the fomento system** | **`atana.tcu`** | **Maturity ratings, deliberations to MinC** |

## §2. Tables

### `pnab_governance_assessment` (4 rows × PNAB × 2025)

One row per (audit_year, governance_dimension). Four governance dimensions from the TCU Referencial:

| Dimension | Rating | Ordinal | Verbatim summary |
|---|---|---|---|
| Formulação dos objetivos | parcialmente institucionalizada | 2 | Clear normative intent; lacks SMART operational specification |
| Indicadores de desempenho | parcialmente institucionalizada | 2 | Some KPIs, insufficient across efficiency / effectiveness / outcome dimensions |
| Gestão de riscos e controles internos | **não institucionalizada** | **1** | Risk-management structures not institutionalised — the lowest TCU rating |
| Monitoramento e avaliação | parcialmente institucionalizada | 2 | M&E half-built; outcome evaluation not yet applicable (early execution) |

Mean maturity = **1.75 / 3**. No dimension reached "institucionalizada" (3). Gestão de riscos = 1 is the flagged accountability concern.

Ordinal scale (verbatim from TCU):
- **1** = não institucionalizada
- **2** = parcialmente institucionalizada
- **3** = institucionalizada

### `pnab_deliberations` (4 rows × PNAB × 2025)

One row per (audit_year, deliberation_item). The TCU's verbatim recommendations addressed to **MinC** as the policy operator:

| Item | What MinC owes back |
|---|---|
| Planejamento estratégico formal | Document the theory of change / lógica de intervenção explicitly |
| Metas (curto/médio/longo prazo) | Move beyond managerial goals to substantive policy targets at multiple horizons |
| Indicadores multidimensionais | Define KPIs covering eficiência / eficácia / efetividade / **equidade** — with data sources, deadlines, owners |
| Linha de base transparente | Define + formalise baseline; publish transparently |

The **equidade** dimension is notable — it lands directly on Atana's distributional focus across the cultural-economy series.

## §3. Why this matters for Atana

1. **Authoritative second-source on PNAB.** Until now the corpus had only Atana's own bimodality findings (Análise 8: 65 % captured 0 %, 15 % captured ~100 %) and SALIC-level series. TCU is the constitutional auditor — what it flags constrains MinC's room to operate.
2. **The equidade dimension is the policy entry-point.** TCU asks MinC for an equity KPI scheme; Atana already has the distributional decomposition (Análises 1-3, 12, 17-20). The fit is direct and operational.
3. **Cyclical update.** Acórdão 1709/2025 is plenário-published in 2025; the next TCU PNAB cycle (probably 2027 or 2028) appends rows by `audit_year`. The R$ 22 bn / ~29.7 k projects pending at MinC + Ancine (flagged in the W23 briefing) is a separate TCU finding — likely a separate `pnab_pendings` table in a Tier 2 follow-up.

## §4. What this schema is NOT

- **Not the PNAB programme law.** Lei 14.399/2022 instituiu PNAB; methodology of the policy itself is outside scope.
- **Not project-level audit microdata.** No project / proponent rows; the TCU document is governance-level findings only.
- **Not the R$ 22 bn pending payments figure.** That comes from a separate TCU set of findings on MinC + Ancine pending PC (prestação de contas); to be ingested in Tier 2.

## §5. Sources

- TCU press release: <https://portal.tcu.gov.br/imprensa/noticias/politica-nacional-de-cultura-e-auditada-pelo-tribunal-de-contas-da-uniao>
- Acórdão 1709/2025 - Plenário, processo TC 025.939/2024-6 (sessão 30/07/2025, relator Augusto Nardes)

## §6. Caveats

- TCU PNAB audits are episodic, not annual; cadence depends on TCU work-plan priority. Cf. §10 of the briefing.
- Verbatim recommendations are transcribed; the underlying full Acórdão PDF is publicly available but not extracted in this v1 (separate ingest in Tier 2 if needed).
- The maturity scale is the TCU's own (per the Referencial de Controle de Políticas Públicas) — not internationally comparable to OECD audit frameworks without explicit caveats.

## §7. Crosswalk position

`canonical.domain_crosswalk` → 1 row: `tcu / pnab-audit → Multiple — cultural fomento policy crosses all 7 cultural domains (approximate)`, ★-flagged. FCS coverage meter unchanged at 13/14: PNAB is a horizontal fomento instrument, not a domain.
