#!/usr/bin/env python3
"""
canonical__build_cultural_baseline_a27.py

Builds the canonical Cultural Sector Baseline (Análise 27 synthesis).

INPUTS
  raw/ibge_estruturais/tab_2_*.parquet   (8 long-format tables, already ingested)
  raw/macro/ipca.parquet                  (BCB SGS 433, IPCA-anual médio)

OUTPUTS
  curated/cultural_sector_baseline_a27_trajectory.parquet
      Long-format synthesis: one row per (recorte × indicator × year),
      with both nominal and IPCA-2023-deflated values. Captures the IBGE
      view (total + centrais + 4 main central domains + 2 main peripheries).

  curated/cultural_sector_baseline_a27_three_rulers.parquet
      2023 snapshot: the three réguas (IBGE total, IBGE só centrais,
      UNESCO FCS 2025 conservative estimate) for VA.

  Both files are byte-identical on rerun. The script is idempotent.

USAGE
  cd atana-data/
  python3 etl/canonical__build_cultural_baseline_a27.py
"""
from __future__ import annotations
import duckdb
import json
import os
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
RAW = REPO / "raw"
CUR = REPO / "curated"
CUR.mkdir(exist_ok=True)

# IPCA deflator factor to BRL 2023
IPCA_TO_2023 = {
    2013: 1.7752, 2019: 1.2871, 2020: 1.2220,
    2021: 1.1180, 2022: 1.0610, 2023: 1.0000,
}

# Recortes from Análise 27 — labels match the xlsx row_label substrings
RECORTES = [
    ("total_economia",       "Economia total",                   "national"),
    ("cultural_total",       "Setor cultural — todos os domínios","ibge_cultural_total"),
    ("atividades_centrais",  "Setor cultural — atividades centrais","ibge_cultural_centrais"),
    ("B_apresentacoes",      "B. Apresentações artísticas",      "ibge_central_domain"),
    ("C_artes_visuais",      "C. Artes visuais",                 "ibge_central_domain"),
    ("E_audiovisual",        "E. Mídias audiovisuais",           "ibge_central_domain"),
    ("F_design",             "F. Design e serviços criativos",   "ibge_central_domain"),
    ("telecom",              "Telecomunicações (periferia IBGE)","ibge_peripheral"),
    ("software",             "Software (periferia IBGE)",        "ibge_peripheral"),
]
# Substring used to find the row in the xlsx (matches what gen_a27_charts.py used)
RECORTE_TO_LABEL_SUB = {
    "total_economia":      "Total geral",
    "cultural_total":      "Total dos domínios culturais",
    "atividades_centrais": "Total das atividades culturais centrais",
    "B_apresentacoes":     "B. Apresentações artísticas",
    "C_artes_visuais":     "C. Artes visuais",
    "E_audiovisual":       "E. Mídias audiovisuais",
    "F_design":            "F. Design e serviços criativos",
    # Telecom comprises TWO cultural-periphery CNAEs in the SIIC. Both are
    # summed via the list. (Análise 27 v1.1 originally captured only the first
    # row via openpyxl substring match — this ETL corrects that to the proper
    # aggregate.)
    "telecom":             ["Telecomunicações por fio", "Outras atividades de telecomunicações"],
    "software":            "Desenvolvimento e licenciamento",
}

# Indicators: (recorte_key, sheet_number, indicator_label, unit_metadata)
INDICATORS = [
    ("empresas",  "1", "Número de empresas",     "unidades"),
    ("ocupados",  "2", "Pessoal ocupado",         "pessoas"),
    ("salarios",  "3", "Salários e remunerações", "R$_1000_correntes"),
    ("vbp",       "6", "Valor bruto da produção", "R$_1000_correntes"),
    ("va",        "8", "Valor adicionado",        "R$_1000_correntes"),
]

YEARS = [2013, 2019, 2020, 2021, 2022, 2023]


def build_trajectory():
    """Read the 5 indicator parquets and build the long-format trajectory."""
    con = duckdb.connect(":memory:")
    rows = []
    for ind_key, sheet_num, ind_label, unit in INDICATORS:
        df = con.execute(f"""
          SELECT row_label, year, value
          FROM read_parquet('{RAW}/ibge_estruturais/tab_2_{sheet_num}.parquet')
          WHERE year IN ({','.join(map(str, YEARS))})
        """).fetchall()
        is_monetary = unit.startswith("R$")
        for rec_key, label_sub_or_list in RECORTE_TO_LABEL_SUB.items():
            rec_label, rec_type = next(
                (label, typ) for k, label, typ in RECORTES if k == rec_key
            )
            # Normalize: substring → list, so the same logic sums multi-row recortes
            label_subs = label_sub_or_list if isinstance(label_sub_or_list, list) else [label_sub_or_list]
            for target_year in YEARS:
                # Sum all rows matching ANY label substring for this year
                matches = [
                    (row_label, value) for row_label, year, value in df
                    if row_label and year == target_year and value is not None
                    and any(s.lower() in row_label.lower() for s in label_subs)
                ]
                if not matches:
                    continue
                total = sum(float(v) for _, v in matches)
                deflator = IPCA_TO_2023.get(target_year, 1.0)
                value_real = total * deflator if is_monetary else total
                rows.append({
                    "recorte_key": rec_key,
                    "recorte_label": rec_label,
                    "recorte_type": rec_type,
                    "indicator_key": ind_key,
                    "indicator_label": ind_label,
                    "unit_native": unit,
                    "year": int(target_year),
                    "value_nominal": total,
                    "value_real_brl2023": value_real if is_monetary else None,
                    "ipca_deflator_to_2023": deflator if is_monetary else None,
                    "n_source_rows_aggregated": len(matches),
                    "source_table": f"atana.ibge_estruturais.tab_2_{sheet_num}",
                })
    return rows


def build_three_rulers():
    """Build the 2023 snapshot for the three réguas — IBGE total, IBGE centrais, FCS estimate.

    Values are pulled from atana.ibge_estruturais.tab_2_8 (long-format parquet) using
    canonical substring matches against the publication-as-ingested row labels.
    Telecom is summed across the two telecom-service CNAEs (excluding manufacturing).
    """
    con = duckdb.connect(":memory:")
    # IBGE total VA 2023
    ibge_total = con.execute(f"""
      SELECT value FROM read_parquet('{RAW}/ibge_estruturais/tab_2_8.parquet')
      WHERE year = 2023 AND row_label LIKE '%Total dos domínios culturais%'
    """).fetchone()[0]
    # IBGE centrais VA 2023
    ibge_centrais = con.execute(f"""
      SELECT value FROM read_parquet('{RAW}/ibge_estruturais/tab_2_8.parquet')
      WHERE year = 2023 AND row_label LIKE '%Total das atividades culturais centrais%'
    """).fetchone()[0]
    # Software 2023
    software = con.execute(f"""
      SELECT value FROM read_parquet('{RAW}/ibge_estruturais/tab_2_8.parquet')
      WHERE year = 2023 AND row_label LIKE 'Desenvolvimento e licenciamento%'
    """).fetchone()[0]
    # Telecom 2023 — sum across the two telecom-service CNAEs
    # ("Telecomunicações por fio…" + "Outras atividades de telecomunicações")
    telecom_rows = con.execute(f"""
      SELECT value FROM read_parquet('{RAW}/ibge_estruturais/tab_2_8.parquet')
      WHERE year = 2023
        AND (row_label LIKE 'Telecomunicações por fio%'
             OR row_label LIKE 'Outras atividades de telecomunicações%')
    """).fetchall()
    telecom = sum(r[0] for r in telecom_rows if r[0] is not None)

    other_periphery = ibge_total - ibge_centrais - software - telecom

    # FCS conservative estimate (Análise 27 §11)
    # = 100 % centrais + 15 % software + 10 % other periphery + 0 % telecom
    fcs_low  = ibge_centrais + software * 0.10 + other_periphery * 0.05
    fcs_mid  = ibge_centrais + software * 0.15 + other_periphery * 0.10
    fcs_high = ibge_centrais + software * 0.20 + other_periphery * 0.15

    rows = [
        {
            "ruler_key": "ibge_siic_total",
            "ruler_label": "IBGE SIIC — setor cultural inteiro",
            "ruler_framework": "IBGE SIIC 2024 (PIA/PAS/PAC, recorte cultural)",
            "scope_description": "Atividades centrais + periféricas (telecom + software + equipamentos)",
            "va_brl2023": ibge_total / 1e6,           # Mi para Bi
            "va_brl_low": None,
            "va_brl_high": None,
            "uncertainty_note": "Valor publicado pelo IBGE — sem faixa.",
            "use_when": "Em diálogo com debate brasileiro institucional (MinC, OEC, IPEA, FGV).",
        },
        {
            "ruler_key": "ibge_siic_centrais",
            "ruler_label": "IBGE SIIC — só atividades centrais",
            "ruler_framework": "IBGE SIIC 2024 — recorte das 7 atividades centrais",
            "scope_description": "Patrimônio, Apresentações, Artes visuais, Livro/imprensa, AV, Design, Educação cultural",
            "va_brl2023": ibge_centrais / 1e6,
            "va_brl_low": None,
            "va_brl_high": None,
            "uncertainty_note": "Valor publicado pelo IBGE — sem faixa.",
            "use_when": "Quando o argumento é sobre o 'centro' do setor, sem a infraestrutura.",
        },
        {
            "ruler_key": "fcs_2025_conservative",
            "ruler_label": "UNESCO FCS 2025 — estimativa conservadora",
            "ruler_framework": "UNESCO Framework for Cultural Statistics 2025 (CCE)",
            "scope_description": "Atividades culturais pelos 14 domínios FCS; software ≈ 15 % cultural; telecom = 0; outras periferias ≈ 10 %",
            "va_brl2023": fcs_mid / 1e6,
            "va_brl_low": fcs_low / 1e6,
            "va_brl_high": fcs_high / 1e6,
            "uncertainty_note": "Reclassificação aplicada externamente; faixa expressa a sensibilidade das suposições (Análise 27 §11).",
            "use_when": "Em diálogo com multilaterais (BID, UNESCO, OEI, CEPAL).",
        },
    ]
    return rows


def write_parquet(rows, name):
    """Write rows to a Parquet via DuckDB COPY. Idempotent."""
    import tempfile
    con = duckdb.connect(":memory:")
    # Use /tmp for the staging json so cross-mount delete works.
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        f.write(json.dumps(rows))
        json_tmp = f.name
    try:
        con.execute(f"""
          COPY (SELECT * FROM read_json_auto('{json_tmp}'))
          TO '{CUR}/{name}.parquet' (FORMAT PARQUET, COMPRESSION ZSTD);
        """)
    finally:
        try: os.unlink(json_tmp)
        except OSError: pass  # tempfile cleanup best-effort
    n = con.execute(f"SELECT COUNT(*) FROM read_parquet('{CUR}/{name}.parquet')").fetchone()[0]
    print(f"  ✓ {CUR}/{name}.parquet  ({n} rows)")


def write_meta(name, n_rows, description):
    """Write a .meta.json companion."""
    meta = {
        "name": name,
        "rows": n_rows,
        "description": description,
        "source": "atana.ibge_estruturais (long-format) + atana.macro.ipca (deflator)",
        "ipca_factors_to_2023": IPCA_TO_2023,
        "build_script": "etl/canonical__build_cultural_baseline_a27.py",
        "consumed_by": "Análise 27 (linha de base); cross-analyses with atana.salic, atana.pnab, atana.lpg, atana.rais.",
        "license": "CC BY 4.0",
    }
    path = CUR / f"{name}.meta.json"
    path.write_text(json.dumps(meta, indent=2, ensure_ascii=False))
    print(f"  ✓ {path}")


def main():
    print("Building canonical.cultural_sector_baseline_a27 …")
    print()
    print("[1/2] Trajectory (long format)")
    rows = build_trajectory()
    write_parquet(rows, "cultural_sector_baseline_a27_trajectory")
    write_meta("cultural_sector_baseline_a27_trajectory", len(rows),
               "Long-format trajectory of Brazilian cultural sector by IBGE SIIC cap. 2: "
               "9 recortes × 5 indicators × 6 years (2013, 2019-2023). Each monetary row "
               "carries both nominal value and IPCA-2023-deflated value. Source: atana.ibge_estruturais.")
    print()
    print("[2/2] Three réguas snapshot (2023)")
    rows3 = build_three_rulers()
    write_parquet(rows3, "cultural_sector_baseline_a27_three_rulers")
    write_meta("cultural_sector_baseline_a27_three_rulers", len(rows3),
               "Three rulers (IBGE total, IBGE centrais, UNESCO FCS 2025 conservative) for "
               "VA of the Brazilian cultural sector 2023. Sourced from Análise 27 §11.")
    print()
    print("Done.")


if __name__ == "__main__":
    main()
