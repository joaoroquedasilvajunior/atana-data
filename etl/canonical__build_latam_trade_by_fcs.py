"""Build canonical.latam_trade_by_fcs_domain — the cross-LATAM cultural-trade
comparison through the FCS 2025 spine.

Phase 6a.2 of the Atana Data expansion. This materialises, as a curated Parquet
table, "the query the crosswalk was built to enable" — first executed as
session scouting on 2026-06-10 (phase6_corpus_criterion_and_vol2_scoping.md §2)
and promoted here to a measured, reproducible artifact.

WHAT THIS IS
------------
One table with the cultural-trade flows of the five corpus countries read
through the 14-domain 2025 UNESCO FCS spine via `canonical.domain_crosswalk`:

    Mexico      INEGI CSCM oferta-utilización, current MXN + derived USD
    Colombia    DANE CSECC supply-use balances, current COP + derived USD
    Costa Rica  CSCCR dedicated trade table, CRC + derived USD
    Brazil      IBGE Comex NCM — the five 100%-cultural goods chapters,
                R$ FOB + USD derived via atana.macro.fx_brl_usd_annual
    Argentina   SInCA CSC segments, constant-2004 ARS — **no USD column,
                deliberately** (brecha cambiaria; sinca_csc.md §8: the empty
                cell is the finding)

COMPARABILITY IS NOT ASSERTED — IT IS ANNOTATED. The five sources measure
different things under one name ("cultural trade"): supply-use product flows
(MX/CO), a dedicated trade table (CR), goods-only customs chapters (BR), and
coarse segments (AR). The `basis` and `comparability_note` columns carry this
on every row; Costa Rica's 2022+ coverage collapse and Colombia's provisional
years are kept visible, never patched. (House style — cf. Note #03.)

JOIN RECIPE (heterogeneous by source — documented in the phase6 memo §2.1):
    inegi    cw.source_label = area_general    (area_level='area_general',
                                                price_basis='corriente')
    dane     cw.source_code  = CAST(cuadro_num AS VARCHAR)
    cr_bccr  cw.source_label = sector          (sector <> 'Total')
    ibge     cw.source_code  = CAST(CAST(capitulo_ncm AS INT) AS VARCHAR)
                                               (is_pure_cultural)
    sinca    cw.source_code  = segment         (constante_2004; the
                                                'bienes_y_servicios' total row
                                                is excluded to avoid double
                                                counting its two components)

Output:
    curated/latam_trade_by_fcs_domain.parquet  (+ .meta.json)
    grain: country × year × flow × fcs2025_domain

Idempotent: reads raw/ Parquet + curated/domain_crosswalk.parquet, stable sort,
DuckDB COPY (ZSTD). Byte-identical reruns. MotherDuck sync is manual (schema
`atana.canonical`), per PUSH_INSTRUCTIONS.md.

Usage:
    python etl/canonical__build_latam_trade_by_fcs.py
"""
import hashlib
import json
from datetime import date
from pathlib import Path

import duckdb

REPO_ROOT = Path(__file__).resolve().parent.parent
RAW = REPO_ROOT / "raw"
CURATED = REPO_ROOT / "curated"
OUT = CURATED / "latam_trade_by_fcs_domain.parquet"

CW = (CURATED / "domain_crosswalk.parquet").as_posix()
MX = (RAW / "inegi" / "csc_comercio.parquet").as_posix()
CO = (RAW / "dane" / "csecc_comercio.parquet").as_posix()
CR = (RAW / "cr_bccr" / "csc_comercio.parquet").as_posix()
BR = (RAW / "ibge_comex" / "tab_10_1.parquet").as_posix()
AR = (RAW / "sinca" / "csc_comercio.parquet").as_posix()
FX = (RAW / "macro" / "fx_brl_usd_annual.parquet").as_posix()

NOTE_MX = ("CSCM oferta-utilización (goods+services product flows), current "
           "MXN; USD derived via fx_mxn_usd_annual (World Bank PA.NUS.FCRF).")
NOTE_CO = ("CSECC supply-use balances by product, current COP; USD derived "
           "via fx_cop_usd_annual. year_status carries definitivo/provisional/"
           "preliminar.")
NOTE_CR = ("CSCCR dedicated cultural-trade table, CRC; USD derived via "
           "fx_crc_usd_annual.")
NOTE_CR_BREAK = (" ⚠️ COVERAGE BREAK: from 2022 only Editorial is reported — "
                 "rows for the other sectors are absent/n.d., which is the "
                 "finding, not a data error (cr_bccr_csc.md).")
NOTE_BR = ("IBGE Comex NCM, the five 100%-cultural GOODS chapters only "
           "(37/46/49/92/97), R$ FOB; USD via atana.macro fx_brl_usd_annual. "
           "⚠️ Narrower basis than the CSC supply-use sources — goods-only, "
           "no services, no partially-cultural chapters. The classification "
           "difference is visible by design.")
NOTE_AR = ("SInCA CSC segments, CONSTANT-2004 ARS thousand. NO USD column, "
           "deliberately: under the multiple-exchange-rate regime any single "
           "ARS→USD conversion asserts a rate choice that changes the result "
           "(sinca_csc.md §8 — the empty cell is the finding). Series ends "
           "2022; bienes_culturales is source-derived (total − services).")

SQL = f"""
WITH cw AS (SELECT * FROM '{CW}'),
mx AS (
  SELECT 'Mexico' AS country, 'MEX' AS country_iso3, t.year,
         CASE t.flow WHEN 'exportacion' THEN 'exports' ELSE 'imports' END AS flow,
         cw.fcs2025_domain,
         sum(t.value_usd_million)  AS value_usd_million,
         sum(t.value_mxn_million)  AS value_native,
         'MXN million (current)'   AS native_currency,
         'csc_supply_use'          AS basis,
         'inegi'                   AS source_schema,
         '{NOTE_MX}'               AS comparability_note
  FROM '{MX}' t
  JOIN cw ON cw.source_schema='inegi' AND cw.source_label = t.area_general
  WHERE t.flow IN ('exportacion','importacion')
    AND t.price_basis='corriente' AND t.area_level='area_general'
  GROUP BY ALL),
co AS (
  SELECT 'Colombia', 'COL', t.year,
         CASE t.flow WHEN 'exportacion' THEN 'exports' ELSE 'imports' END,
         cw.fcs2025_domain,
         sum(t.value_usd_million),
         sum(t.value_cop_million),
         'COP million (current)',
         'csc_supply_use',
         'dane',
         '{NOTE_CO}'
  FROM '{CO}' t
  JOIN cw ON cw.source_schema='dane'
         AND cw.source_code = CAST(t.cuadro_num AS VARCHAR)
  WHERE t.flow IN ('exportacion','importacion')
  GROUP BY ALL),
cr AS (
  SELECT 'Costa Rica', 'CRI', t.year,
         CASE t.flow WHEN 'exportacion' THEN 'exports' ELSE 'imports' END,
         cw.fcs2025_domain,
         sum(t.value_usd_million),
         sum(t.value_crc_million),
         'CRC million',
         'csc_trade_table',
         'cr_bccr',
         '{NOTE_CR}' || CASE WHEN t.year >= 2022 THEN '{NOTE_CR_BREAK}' ELSE '' END
  FROM '{CR}' t
  JOIN cw ON cw.source_schema='cr_bccr' AND cw.source_label = t.sector
  WHERE t.sector <> 'Total'
  GROUP BY ALL),
br_long AS (
  SELECT t.year, CAST(CAST(t.capitulo_ncm AS INT) AS VARCHAR) AS chap,
         'exports' AS flow, t.exp_cultural_brl_mi AS brl
  FROM '{BR}' t WHERE t.is_pure_cultural
  UNION ALL
  SELECT t.year, CAST(CAST(t.capitulo_ncm AS INT) AS VARCHAR),
         'imports', t.imp_cultural_brl_mi
  FROM '{BR}' t WHERE t.is_pure_cultural),
br AS (
  SELECT 'Brazil', 'BRA', b.year, b.flow,
         cw.fcs2025_domain,
         sum(b.brl / fx.fx_brl_per_usd),
         sum(b.brl),
         'BRL million (current, FOB)',
         'ncm_goods_only_pure_chapters',
         'ibge_comex',
         '{NOTE_BR}'
  FROM br_long b
  JOIN '{FX}' fx ON fx.year = b.year
  JOIN cw ON cw.source_schema='ibge_comex' AND cw.source_code = b.chap
  GROUP BY ALL),
ar AS (
  SELECT 'Argentina', 'ARG', t.year,
         CASE t.flow WHEN 'exportacion' THEN 'exports' ELSE 'imports' END,
         cw.fcs2025_domain,
         CAST(NULL AS DOUBLE),
         sum(t.value_ars_thousand),
         'ARS thousand (constant 2004)',
         'csc_segment_constant2004',
         'sinca',
         '{NOTE_AR}'
  FROM '{AR}' t
  JOIN cw ON cw.source_schema='sinca' AND cw.source_code = t.segment
  WHERE t.flow IN ('exportacion','importacion')
    AND t.price_basis='constante_2004'
    AND t.segment IN ('bienes_culturales','servicios_culturales')
  GROUP BY ALL)
SELECT * FROM mx UNION ALL SELECT * FROM co UNION ALL SELECT * FROM cr
UNION ALL SELECT * FROM br UNION ALL SELECT * FROM ar
ORDER BY country, year, flow, fcs2025_domain NULLS FIRST
"""


def main() -> None:
    con = duckdb.connect()
    df = con.execute(SQL).fetchdf()
    df.columns = ["country", "country_iso3", "year", "flow", "fcs2025_domain",
                  "value_usd_million", "value_native", "native_currency",
                  "basis", "source_schema", "comparability_note"]

    # ── Validation ───────────────────────────────────────────────────────
    by_c = df.groupby("country").size().to_dict()
    assert set(by_c) == {"Mexico", "Colombia", "Costa Rica", "Brazil",
                         "Argentina"}, by_c
    # MX 2021 exports total ≈ 3,685.1 USD mi (verified against raw 2026-06-10)
    v = df[(df.country == "Mexico") & (df.year == 2021) &
           (df.flow == "exports")]["value_usd_million"].sum()
    assert 3684 < v < 3686, v
    # BR 2024 exports, pure chapters ≈ 409.6 USD mi (282.6+88.8+33.0+5.2)
    v = df[(df.country == "Brazil") & (df.year == 2024) &
           (df.flow == "exports")]["value_usd_million"].sum()
    assert 408 < v < 411, v
    # CO 2024 Audiovisual exports ≈ 162.3 (the ×4.2 finding)
    v = df[(df.country == "Colombia") & (df.year == 2024) &
           (df.flow == "exports") &
           (df.fcs2025_domain == "Audiovisual")]["value_usd_million"].sum()
    assert 161 < v < 164, v
    # AR: USD strictly NULL on every row (the documented incommensurability)
    assert df[df.country == "Argentina"]["value_usd_million"].isna().all()
    assert df[(df.country == "Argentina")]["year"].max() == 2022
    # CR coverage break: 2022+ has fewer *measured* (non-null) domains than
    # 2021 — the n.d. rows are kept, with NULL values (the finding).
    _cr = df[(df.country == "Costa Rica") & (df.flow == "exports")]
    cr21 = _cr[(_cr.year == 2021) & _cr.value_usd_million.notna()
               ]["fcs2025_domain"].nunique()
    cr24 = _cr[(_cr.year == 2024) & _cr.value_usd_million.notna()
               ]["fcs2025_domain"].nunique()
    assert cr21 == 4 and cr24 < cr21, (cr21, cr24)
    print(f"  · validation OK — {len(df):,} rows; per-country {by_c}")

    # ── Write ────────────────────────────────────────────────────────────
    con.register("df_out", df)
    con.execute(f"COPY df_out TO '{OUT}' (FORMAT PARQUET, COMPRESSION ZSTD)")
    print(f"  ✓ {OUT.relative_to(REPO_ROOT)} — {len(df):,} rows, "
          f"{OUT.stat().st_size/1024:.1f} KB")

    inputs = [CW, MX, CO, CR, BR, AR, FX]
    meta = {
        "table": OUT.stem,
        "description": "Cross-LATAM cultural trade by 2025 UNESCO FCS domain "
                       "— MX/CO/CR/BR/AR resolved through "
                       "canonical.domain_crosswalk. Comparability is "
                       "annotated per row (basis, comparability_note), never "
                       "asserted: Brazil is goods-only NCM; Argentina is "
                       "constant-2004 ARS with a deliberately empty USD "
                       "column (sinca_csc.md §8).",
        "source": "Derived — atana.inegi/dane/cr_bccr/ibge_comex/sinca × "
                  "canonical.domain_crosswalk × atana.macro FX",
        "source_files": [{"file": Path(p).name,
                          "sha256": hashlib.sha256(
                              Path(p).read_bytes()).hexdigest()}
                         for p in inputs],
        "grain": "country × year × flow × fcs2025_domain",
        "etl_script": "etl/canonical__build_latam_trade_by_fcs.py",
        "etl_run_date": str(date.today()),
        "licence": "CC BY 4.0 (derived from CC BY / open national sources)",
    }
    mp = OUT.with_suffix(".meta.json")
    mp.write_text(json.dumps(meta, indent=2, ensure_ascii=False))
    print(f"  ✓ {mp.relative_to(REPO_ROOT)}")
    print("  · MotherDuck sync manual (atana.canonical) — "
          "PUSH_INSTRUCTIONS.md.")


if __name__ == "__main__":
    main()
