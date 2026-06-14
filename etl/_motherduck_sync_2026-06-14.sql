-- ─────────────────────────────────────────────────────────────────────────────
-- atana-data → MotherDuck sync block (2026-06-14)
--
-- 15 schemas, 146 CREATE OR REPLACE TABLE statements + 13 CREATE SCHEMA guards.
-- Every schema is guarded with CREATE SCHEMA IF NOT EXISTS — idempotent;
-- safe to rerun in whole or in parts.
-- ─────────────────────────────────────────────────────────────────────────────


-- ═══ NEW SCHEMAS — first MotherDuck sync ═══

-- ── atana.anthropic_eei ── 4 tables (NEW)
CREATE SCHEMA IF NOT EXISTS atana.anthropic_eei;
CREATE OR REPLACE TABLE atana.anthropic_eei.collaboration_by_country AS
  SELECT * FROM read_parquet('https://raw.githubusercontent.com/joaoroquedasilvajunior/atana-data/main/raw/anthropic_eei/collaboration_by_country.parquet');
CREATE OR REPLACE TABLE atana.anthropic_eei.country_usage AS
  SELECT * FROM read_parquet('https://raw.githubusercontent.com/joaoroquedasilvajunior/atana-data/main/raw/anthropic_eei/country_usage.parquet');
CREATE OR REPLACE TABLE atana.anthropic_eei.occupation_usage_global_v2 AS
  SELECT * FROM read_parquet('https://raw.githubusercontent.com/joaoroquedasilvajunior/atana-data/main/raw/anthropic_eei/occupation_usage_global_v2.parquet');
CREATE OR REPLACE TABLE atana.anthropic_eei.task_usage_by_country AS
  SELECT * FROM read_parquet('https://raw.githubusercontent.com/joaoroquedasilvajunior/atana-data/main/raw/anthropic_eei/task_usage_by_country.parquet');

-- ── atana.canonical.cmo_directory_alcam ── 1 table (NEW)
CREATE SCHEMA IF NOT EXISTS atana.canonical;
CREATE OR REPLACE TABLE atana.canonical.cmo_directory_alcam AS
  SELECT * FROM read_parquet('https://raw.githubusercontent.com/joaoroquedasilvajunior/atana-data/main/curated/cmo_directory_alcam.parquet');

-- ── atana.canonical.latam_trade_by_fcs_domain ── 1 table (NEW)
CREATE SCHEMA IF NOT EXISTS atana.canonical;
CREATE OR REPLACE TABLE atana.canonical.latam_trade_by_fcs_domain AS
  SELECT * FROM read_parquet('https://raw.githubusercontent.com/joaoroquedasilvajunior/atana-data/main/curated/latam_trade_by_fcs_domain.parquet');

-- ── atana.lpg ── 4 tables (NEW)
CREATE SCHEMA IF NOT EXISTS atana.lpg;
CREATE OR REPLACE TABLE atana.lpg.adesao_entes AS
  SELECT * FROM read_parquet('https://raw.githubusercontent.com/joaoroquedasilvajunior/atana-data/main/curated/lpg/adesao_entes.parquet');
CREATE OR REPLACE TABLE atana.lpg.execucao_financeira AS
  SELECT * FROM read_parquet('https://raw.githubusercontent.com/joaoroquedasilvajunior/atana-data/main/curated/lpg/execucao_financeira.parquet');
CREATE OR REPLACE TABLE atana.lpg.extratos_bancarios AS
  SELECT * FROM read_parquet('https://raw.githubusercontent.com/joaoroquedasilvajunior/atana-data/main/curated/lpg/extratos_bancarios.parquet');
CREATE OR REPLACE TABLE atana.lpg.relatorio_gestao AS
  SELECT * FROM read_parquet('https://raw.githubusercontent.com/joaoroquedasilvajunior/atana-data/main/curated/lpg/relatorio_gestao.parquet');

-- ── atana.macro ── 3 tables (NEW)
CREATE SCHEMA IF NOT EXISTS atana.macro;
CREATE OR REPLACE TABLE atana.macro.fx_brl_eur_annual AS
  SELECT * FROM read_parquet('https://raw.githubusercontent.com/joaoroquedasilvajunior/atana-data/main/raw/macro/fx_brl_eur_annual.parquet');
CREATE OR REPLACE TABLE atana.macro.fx_brl_usd_annual AS
  SELECT * FROM read_parquet('https://raw.githubusercontent.com/joaoroquedasilvajunior/atana-data/main/raw/macro/fx_brl_usd_annual.parquet');
CREATE OR REPLACE TABLE atana.macro.ipca AS
  SELECT * FROM read_parquet('https://raw.githubusercontent.com/joaoroquedasilvajunior/atana-data/main/raw/macro/ipca.parquet');

-- ── atana.pnab ── 4 tables (NEW)
CREATE SCHEMA IF NOT EXISTS atana.pnab;
CREATE OR REPLACE TABLE atana.pnab.execucao_financeira AS
  SELECT * FROM read_parquet('https://raw.githubusercontent.com/joaoroquedasilvajunior/atana-data/main/curated/pnab/execucao_financeira.parquet');
CREATE OR REPLACE TABLE atana.pnab.extratos_bancarios AS
  SELECT * FROM read_parquet('https://raw.githubusercontent.com/joaoroquedasilvajunior/atana-data/main/curated/pnab/extratos_bancarios.parquet');
CREATE OR REPLACE TABLE atana.pnab.governanca_entes AS
  SELECT * FROM read_parquet('https://raw.githubusercontent.com/joaoroquedasilvajunior/atana-data/main/curated/pnab/governanca_entes.parquet');
CREATE OR REPLACE TABLE atana.pnab.par_planos AS
  SELECT * FROM read_parquet('https://raw.githubusercontent.com/joaoroquedasilvajunior/atana-data/main/curated/pnab/par_planos.parquet');

-- ═══ RE-SYNCS — local ahead of (or missing from) MotherDuck ═══

-- ── atana.cisac ── 4 tables (re-sync)
CREATE SCHEMA IF NOT EXISTS atana.cisac;
CREATE OR REPLACE TABLE atana.cisac.gcr_2025_global_by_region AS
  SELECT * FROM read_parquet('https://raw.githubusercontent.com/joaoroquedasilvajunior/atana-data/main/raw/cisac/gcr_2025_global_by_region.parquet');
CREATE OR REPLACE TABLE atana.cisac.gcr_2025_global_by_repertoire AS
  SELECT * FROM read_parquet('https://raw.githubusercontent.com/joaoroquedasilvajunior/atana-data/main/raw/cisac/gcr_2025_global_by_repertoire.parquet');
CREATE OR REPLACE TABLE atana.cisac.gcr_2025_global_by_stream AS
  SELECT * FROM read_parquet('https://raw.githubusercontent.com/joaoroquedasilvajunior/atana-data/main/raw/cisac/gcr_2025_global_by_stream.parquet');
CREATE OR REPLACE TABLE atana.cisac.gcr_2025_leading_smaller_markets_digital_share AS
  SELECT * FROM read_parquet('https://raw.githubusercontent.com/joaoroquedasilvajunior/atana-data/main/raw/cisac/gcr_2025_leading_smaller_markets_digital_share.parquet');

-- ── atana.ecad ── 4 tables (re-sync)
CREATE SCHEMA IF NOT EXISTS atana.ecad;
CREATE OR REPLACE TABLE atana.ecad.arrecadacao_distribuicao AS
  SELECT * FROM read_parquet('https://raw.githubusercontent.com/joaoroquedasilvajunior/atana-data/main/raw/ecad/arrecadacao_distribuicao.parquet');
CREATE OR REPLACE TABLE atana.ecad.arrecadacao_por_segmento AS
  SELECT * FROM read_parquet('https://raw.githubusercontent.com/joaoroquedasilvajunior/atana-data/main/raw/ecad/arrecadacao_por_segmento.parquet');
CREATE OR REPLACE TABLE atana.ecad.distribuicao_por_segmento AS
  SELECT * FROM read_parquet('https://raw.githubusercontent.com/joaoroquedasilvajunior/atana-data/main/raw/ecad/distribuicao_por_segmento.parquet');
CREATE OR REPLACE TABLE atana.ecad.distribuicao_por_titular_tipo AS
  SELECT * FROM read_parquet('https://raw.githubusercontent.com/joaoroquedasilvajunior/atana-data/main/raw/ecad/distribuicao_por_titular_tipo.parquet');

-- ── atana.ibge_cempre ── 23 tables (re-sync)
CREATE SCHEMA IF NOT EXISTS atana.ibge_cempre;
CREATE OR REPLACE TABLE atana.ibge_cempre.tab_1_1_1 AS
  SELECT * FROM read_parquet('https://raw.githubusercontent.com/joaoroquedasilvajunior/atana-data/main/raw/ibge_cempre/tab_1_1_1.parquet');
CREATE OR REPLACE TABLE atana.ibge_cempre.tab_1_1_2 AS
  SELECT * FROM read_parquet('https://raw.githubusercontent.com/joaoroquedasilvajunior/atana-data/main/raw/ibge_cempre/tab_1_1_2.parquet');
CREATE OR REPLACE TABLE atana.ibge_cempre.tab_1_1_3 AS
  SELECT * FROM read_parquet('https://raw.githubusercontent.com/joaoroquedasilvajunior/atana-data/main/raw/ibge_cempre/tab_1_1_3.parquet');
CREATE OR REPLACE TABLE atana.ibge_cempre.tab_1_1_4 AS
  SELECT * FROM read_parquet('https://raw.githubusercontent.com/joaoroquedasilvajunior/atana-data/main/raw/ibge_cempre/tab_1_1_4.parquet');
CREATE OR REPLACE TABLE atana.ibge_cempre.tab_1_1_5 AS
  SELECT * FROM read_parquet('https://raw.githubusercontent.com/joaoroquedasilvajunior/atana-data/main/raw/ibge_cempre/tab_1_1_5.parquet');
CREATE OR REPLACE TABLE atana.ibge_cempre.tab_1_1_6 AS
  SELECT * FROM read_parquet('https://raw.githubusercontent.com/joaoroquedasilvajunior/atana-data/main/raw/ibge_cempre/tab_1_1_6.parquet');
CREATE OR REPLACE TABLE atana.ibge_cempre.tab_1_1_6_a AS
  SELECT * FROM read_parquet('https://raw.githubusercontent.com/joaoroquedasilvajunior/atana-data/main/raw/ibge_cempre/tab_1_1_6_a.parquet');
CREATE OR REPLACE TABLE atana.ibge_cempre.tab_1_1_7 AS
  SELECT * FROM read_parquet('https://raw.githubusercontent.com/joaoroquedasilvajunior/atana-data/main/raw/ibge_cempre/tab_1_1_7.parquet');
CREATE OR REPLACE TABLE atana.ibge_cempre.tab_1_1_9 AS
  SELECT * FROM read_parquet('https://raw.githubusercontent.com/joaoroquedasilvajunior/atana-data/main/raw/ibge_cempre/tab_1_1_9.parquet');
CREATE OR REPLACE TABLE atana.ibge_cempre.tab_1_2_1 AS
  SELECT * FROM read_parquet('https://raw.githubusercontent.com/joaoroquedasilvajunior/atana-data/main/raw/ibge_cempre/tab_1_2_1.parquet');
CREATE OR REPLACE TABLE atana.ibge_cempre.tab_1_2_1_a AS
  SELECT * FROM read_parquet('https://raw.githubusercontent.com/joaoroquedasilvajunior/atana-data/main/raw/ibge_cempre/tab_1_2_1_a.parquet');
CREATE OR REPLACE TABLE atana.ibge_cempre.tab_1_2_2 AS
  SELECT * FROM read_parquet('https://raw.githubusercontent.com/joaoroquedasilvajunior/atana-data/main/raw/ibge_cempre/tab_1_2_2.parquet');
CREATE OR REPLACE TABLE atana.ibge_cempre.tab_1_2_2_a AS
  SELECT * FROM read_parquet('https://raw.githubusercontent.com/joaoroquedasilvajunior/atana-data/main/raw/ibge_cempre/tab_1_2_2_a.parquet');
CREATE OR REPLACE TABLE atana.ibge_cempre.tab_1_2_3 AS
  SELECT * FROM read_parquet('https://raw.githubusercontent.com/joaoroquedasilvajunior/atana-data/main/raw/ibge_cempre/tab_1_2_3.parquet');
CREATE OR REPLACE TABLE atana.ibge_cempre.tab_1_2_4 AS
  SELECT * FROM read_parquet('https://raw.githubusercontent.com/joaoroquedasilvajunior/atana-data/main/raw/ibge_cempre/tab_1_2_4.parquet');
CREATE OR REPLACE TABLE atana.ibge_cempre.tab_1_2_5 AS
  SELECT * FROM read_parquet('https://raw.githubusercontent.com/joaoroquedasilvajunior/atana-data/main/raw/ibge_cempre/tab_1_2_5.parquet');
CREATE OR REPLACE TABLE atana.ibge_cempre.tab_1_2_6 AS
  SELECT * FROM read_parquet('https://raw.githubusercontent.com/joaoroquedasilvajunior/atana-data/main/raw/ibge_cempre/tab_1_2_6.parquet');
CREATE OR REPLACE TABLE atana.ibge_cempre.tab_1_2_7 AS
  SELECT * FROM read_parquet('https://raw.githubusercontent.com/joaoroquedasilvajunior/atana-data/main/raw/ibge_cempre/tab_1_2_7.parquet');
CREATE OR REPLACE TABLE atana.ibge_cempre.tab_1_2_8 AS
  SELECT * FROM read_parquet('https://raw.githubusercontent.com/joaoroquedasilvajunior/atana-data/main/raw/ibge_cempre/tab_1_2_8.parquet');
CREATE OR REPLACE TABLE atana.ibge_cempre.tab_1_3_1 AS
  SELECT * FROM read_parquet('https://raw.githubusercontent.com/joaoroquedasilvajunior/atana-data/main/raw/ibge_cempre/tab_1_3_1.parquet');
CREATE OR REPLACE TABLE atana.ibge_cempre.tab_1_3_2 AS
  SELECT * FROM read_parquet('https://raw.githubusercontent.com/joaoroquedasilvajunior/atana-data/main/raw/ibge_cempre/tab_1_3_2.parquet');
CREATE OR REPLACE TABLE atana.ibge_cempre.tab_1_3_3 AS
  SELECT * FROM read_parquet('https://raw.githubusercontent.com/joaoroquedasilvajunior/atana-data/main/raw/ibge_cempre/tab_1_3_3.parquet');
CREATE OR REPLACE TABLE atana.ibge_cempre.tab_1_3_4 AS
  SELECT * FROM read_parquet('https://raw.githubusercontent.com/joaoroquedasilvajunior/atana-data/main/raw/ibge_cempre/tab_1_3_4.parquet');

-- ── atana.ibge_estruturais ── 8 tables (re-sync)
CREATE SCHEMA IF NOT EXISTS atana.ibge_estruturais;
CREATE OR REPLACE TABLE atana.ibge_estruturais.tab_2_1 AS
  SELECT * FROM read_parquet('https://raw.githubusercontent.com/joaoroquedasilvajunior/atana-data/main/raw/ibge_estruturais/tab_2_1.parquet');
CREATE OR REPLACE TABLE atana.ibge_estruturais.tab_2_2 AS
  SELECT * FROM read_parquet('https://raw.githubusercontent.com/joaoroquedasilvajunior/atana-data/main/raw/ibge_estruturais/tab_2_2.parquet');
CREATE OR REPLACE TABLE atana.ibge_estruturais.tab_2_3 AS
  SELECT * FROM read_parquet('https://raw.githubusercontent.com/joaoroquedasilvajunior/atana-data/main/raw/ibge_estruturais/tab_2_3.parquet');
CREATE OR REPLACE TABLE atana.ibge_estruturais.tab_2_4 AS
  SELECT * FROM read_parquet('https://raw.githubusercontent.com/joaoroquedasilvajunior/atana-data/main/raw/ibge_estruturais/tab_2_4.parquet');
CREATE OR REPLACE TABLE atana.ibge_estruturais.tab_2_5 AS
  SELECT * FROM read_parquet('https://raw.githubusercontent.com/joaoroquedasilvajunior/atana-data/main/raw/ibge_estruturais/tab_2_5.parquet');
CREATE OR REPLACE TABLE atana.ibge_estruturais.tab_2_6 AS
  SELECT * FROM read_parquet('https://raw.githubusercontent.com/joaoroquedasilvajunior/atana-data/main/raw/ibge_estruturais/tab_2_6.parquet');
CREATE OR REPLACE TABLE atana.ibge_estruturais.tab_2_7 AS
  SELECT * FROM read_parquet('https://raw.githubusercontent.com/joaoroquedasilvajunior/atana-data/main/raw/ibge_estruturais/tab_2_7.parquet');
CREATE OR REPLACE TABLE atana.ibge_estruturais.tab_2_8 AS
  SELECT * FROM read_parquet('https://raw.githubusercontent.com/joaoroquedasilvajunior/atana-data/main/raw/ibge_estruturais/tab_2_8.parquet');

-- ── atana.ibge_tic ── 8 tables (re-sync)
CREATE SCHEMA IF NOT EXISTS atana.ibge_tic;
CREATE OR REPLACE TABLE atana.ibge_tic.tab_7_1 AS
  SELECT * FROM read_parquet('https://raw.githubusercontent.com/joaoroquedasilvajunior/atana-data/main/raw/ibge_tic/tab_7_1.parquet');
CREATE OR REPLACE TABLE atana.ibge_tic.tab_7_2 AS
  SELECT * FROM read_parquet('https://raw.githubusercontent.com/joaoroquedasilvajunior/atana-data/main/raw/ibge_tic/tab_7_2.parquet');
CREATE OR REPLACE TABLE atana.ibge_tic.tab_7_3 AS
  SELECT * FROM read_parquet('https://raw.githubusercontent.com/joaoroquedasilvajunior/atana-data/main/raw/ibge_tic/tab_7_3.parquet');
CREATE OR REPLACE TABLE atana.ibge_tic.tab_7_4 AS
  SELECT * FROM read_parquet('https://raw.githubusercontent.com/joaoroquedasilvajunior/atana-data/main/raw/ibge_tic/tab_7_4.parquet');
CREATE OR REPLACE TABLE atana.ibge_tic.tab_7_5 AS
  SELECT * FROM read_parquet('https://raw.githubusercontent.com/joaoroquedasilvajunior/atana-data/main/raw/ibge_tic/tab_7_5.parquet');
CREATE OR REPLACE TABLE atana.ibge_tic.tab_7_6 AS
  SELECT * FROM read_parquet('https://raw.githubusercontent.com/joaoroquedasilvajunior/atana-data/main/raw/ibge_tic/tab_7_6.parquet');
CREATE OR REPLACE TABLE atana.ibge_tic.tab_7_7 AS
  SELECT * FROM read_parquet('https://raw.githubusercontent.com/joaoroquedasilvajunior/atana-data/main/raw/ibge_tic/tab_7_7.parquet');
CREATE OR REPLACE TABLE atana.ibge_tic.tab_7_8 AS
  SELECT * FROM read_parquet('https://raw.githubusercontent.com/joaoroquedasilvajunior/atana-data/main/raw/ibge_tic/tab_7_8.parquet');

-- ── atana.ibge_turismo ── 5 tables (re-sync)
CREATE SCHEMA IF NOT EXISTS atana.ibge_turismo;
CREATE OR REPLACE TABLE atana.ibge_turismo.tab_9_1 AS
  SELECT * FROM read_parquet('https://raw.githubusercontent.com/joaoroquedasilvajunior/atana-data/main/raw/ibge_turismo/tab_9_1.parquet');
CREATE OR REPLACE TABLE atana.ibge_turismo.tab_9_2 AS
  SELECT * FROM read_parquet('https://raw.githubusercontent.com/joaoroquedasilvajunior/atana-data/main/raw/ibge_turismo/tab_9_2.parquet');
CREATE OR REPLACE TABLE atana.ibge_turismo.tab_9_3 AS
  SELECT * FROM read_parquet('https://raw.githubusercontent.com/joaoroquedasilvajunior/atana-data/main/raw/ibge_turismo/tab_9_3.parquet');
CREATE OR REPLACE TABLE atana.ibge_turismo.tab_9_4 AS
  SELECT * FROM read_parquet('https://raw.githubusercontent.com/joaoroquedasilvajunior/atana-data/main/raw/ibge_turismo/tab_9_4.parquet');
CREATE OR REPLACE TABLE atana.ibge_turismo.tab_9_5 AS
  SELECT * FROM read_parquet('https://raw.githubusercontent.com/joaoroquedasilvajunior/atana-data/main/raw/ibge_turismo/tab_9_5.parquet');

-- ── atana.ifpi ── 4 tables (re-sync)
CREATE SCHEMA IF NOT EXISTS atana.ifpi;
CREATE OR REPLACE TABLE atana.ifpi.gmr_2026_global_by_format AS
  SELECT * FROM read_parquet('https://raw.githubusercontent.com/joaoroquedasilvajunior/atana-data/main/raw/ifpi/gmr_2026_global_by_format.parquet');
CREATE OR REPLACE TABLE atana.ifpi.gmr_2026_global_by_region AS
  SELECT * FROM read_parquet('https://raw.githubusercontent.com/joaoroquedasilvajunior/atana-data/main/raw/ifpi/gmr_2026_global_by_region.parquet');
CREATE OR REPLACE TABLE atana.ifpi.gmr_2026_global_headline AS
  SELECT * FROM read_parquet('https://raw.githubusercontent.com/joaoroquedasilvajunior/atana-data/main/raw/ifpi/gmr_2026_global_headline.parquet');
CREATE OR REPLACE TABLE atana.ifpi.gmr_2026_top_markets AS
  SELECT * FROM read_parquet('https://raw.githubusercontent.com/joaoroquedasilvajunior/atana-data/main/raw/ifpi/gmr_2026_top_markets.parquet');

-- ── atana.inegi ── 5 tables (re-sync)
CREATE SCHEMA IF NOT EXISTS atana.inegi;
CREATE OR REPLACE TABLE atana.inegi.csc_comercio AS
  SELECT * FROM read_parquet('https://raw.githubusercontent.com/joaoroquedasilvajunior/atana-data/main/raw/inegi/csc_comercio.parquet');
CREATE OR REPLACE TABLE atana.inegi.cscm_2024_pib_by_area AS
  SELECT * FROM read_parquet('https://raw.githubusercontent.com/joaoroquedasilvajunior/atana-data/main/raw/inegi/cscm_2024_pib_by_area.parquet');
CREATE OR REPLACE TABLE atana.inegi.cscm_2024_pib_by_origin AS
  SELECT * FROM read_parquet('https://raw.githubusercontent.com/joaoroquedasilvajunior/atana-data/main/raw/inegi/cscm_2024_pib_by_origin.parquet');
CREATE OR REPLACE TABLE atana.inegi.cscm_2024_pib_growth_series AS
  SELECT * FROM read_parquet('https://raw.githubusercontent.com/joaoroquedasilvajunior/atana-data/main/raw/inegi/cscm_2024_pib_growth_series.parquet');
CREATE OR REPLACE TABLE atana.inegi.cscm_2024_pib_headline AS
  SELECT * FROM read_parquet('https://raw.githubusercontent.com/joaoroquedasilvajunior/atana-data/main/raw/inegi/cscm_2024_pib_headline.parquet');

-- ── atana.inpi ── 68 tables (re-sync)
CREATE SCHEMA IF NOT EXISTS atana.inpi;
CREATE OR REPLACE TABLE atana.inpi.di_concessao_1_classe_di AS
  SELECT * FROM read_parquet('https://raw.githubusercontent.com/joaoroquedasilvajunior/atana-data/main/raw/inpi/di_concessao_1_classe_di.parquet');
CREATE OR REPLACE TABLE atana.inpi.di_concessao_2024_pais_1_classe_di AS
  SELECT * FROM read_parquet('https://raw.githubusercontent.com/joaoroquedasilvajunior/atana-data/main/raw/inpi/di_concessao_2024_pais_1_classe_di.parquet');
CREATE OR REPLACE TABLE atana.inpi.di_concessao_di AS
  SELECT * FROM read_parquet('https://raw.githubusercontent.com/joaoroquedasilvajunior/atana-data/main/raw/inpi/di_concessao_di.parquet');
CREATE OR REPLACE TABLE atana.inpi.di_concessao_di_cidade AS
  SELECT * FROM read_parquet('https://raw.githubusercontent.com/joaoroquedasilvajunior/atana-data/main/raw/inpi/di_concessao_di_cidade.parquet');
CREATE OR REPLACE TABLE atana.inpi.di_concessao_di_origem AS
  SELECT * FROM read_parquet('https://raw.githubusercontent.com/joaoroquedasilvajunior/atana-data/main/raw/inpi/di_concessao_di_origem.parquet');
CREATE OR REPLACE TABLE atana.inpi.di_concessao_di_pais AS
  SELECT * FROM read_parquet('https://raw.githubusercontent.com/joaoroquedasilvajunior/atana-data/main/raw/inpi/di_concessao_di_pais.parquet');
CREATE OR REPLACE TABLE atana.inpi.di_concessao_di_uf AS
  SELECT * FROM read_parquet('https://raw.githubusercontent.com/joaoroquedasilvajunior/atana-data/main/raw/inpi/di_concessao_di_uf.parquet');
CREATE OR REPLACE TABLE atana.inpi.di_deposito_1_classe_di AS
  SELECT * FROM read_parquet('https://raw.githubusercontent.com/joaoroquedasilvajunior/atana-data/main/raw/inpi/di_deposito_1_classe_di.parquet');
CREATE OR REPLACE TABLE atana.inpi.di_deposito_1_classe_di_origem AS
  SELECT * FROM read_parquet('https://raw.githubusercontent.com/joaoroquedasilvajunior/atana-data/main/raw/inpi/di_deposito_1_classe_di_origem.parquet');
CREATE OR REPLACE TABLE atana.inpi.di_deposito_2024_pais_1_classe_di AS
  SELECT * FROM read_parquet('https://raw.githubusercontent.com/joaoroquedasilvajunior/atana-data/main/raw/inpi/di_deposito_2024_pais_1_classe_di.parquet');
CREATE OR REPLACE TABLE atana.inpi.di_deposito_di AS
  SELECT * FROM read_parquet('https://raw.githubusercontent.com/joaoroquedasilvajunior/atana-data/main/raw/inpi/di_deposito_di.parquet');
CREATE OR REPLACE TABLE atana.inpi.di_deposito_di_cidade AS
  SELECT * FROM read_parquet('https://raw.githubusercontent.com/joaoroquedasilvajunior/atana-data/main/raw/inpi/di_deposito_di_cidade.parquet');
CREATE OR REPLACE TABLE atana.inpi.di_deposito_di_cnae AS
  SELECT * FROM read_parquet('https://raw.githubusercontent.com/joaoroquedasilvajunior/atana-data/main/raw/inpi/di_deposito_di_cnae.parquet');
CREATE OR REPLACE TABLE atana.inpi.di_deposito_di_origem AS
  SELECT * FROM read_parquet('https://raw.githubusercontent.com/joaoroquedasilvajunior/atana-data/main/raw/inpi/di_deposito_di_origem.parquet');
CREATE OR REPLACE TABLE atana.inpi.di_deposito_di_pais AS
  SELECT * FROM read_parquet('https://raw.githubusercontent.com/joaoroquedasilvajunior/atana-data/main/raw/inpi/di_deposito_di_pais.parquet');
CREATE OR REPLACE TABLE atana.inpi.di_deposito_di_tipo_nj AS
  SELECT * FROM read_parquet('https://raw.githubusercontent.com/joaoroquedasilvajunior/atana-data/main/raw/inpi/di_deposito_di_tipo_nj.parquet');
CREATE OR REPLACE TABLE atana.inpi.di_deposito_di_uf AS
  SELECT * FROM read_parquet('https://raw.githubusercontent.com/joaoroquedasilvajunior/atana-data/main/raw/inpi/di_deposito_di_uf.parquet');
CREATE OR REPLACE TABLE atana.inpi.di_vigentes_di AS
  SELECT * FROM read_parquet('https://raw.githubusercontent.com/joaoroquedasilvajunior/atana-data/main/raw/inpi/di_vigentes_di.parquet');
CREATE OR REPLACE TABLE atana.inpi.ig_10_alteracoes_de_registro AS
  SELECT * FROM read_parquet('https://raw.githubusercontent.com/joaoroquedasilvajunior/atana-data/main/raw/inpi/ig_10_alteracoes_de_registro.parquet');
CREATE OR REPLACE TABLE atana.inpi.ig_1_total_geral AS
  SELECT * FROM read_parquet('https://raw.githubusercontent.com/joaoroquedasilvajunior/atana-data/main/raw/inpi/ig_1_total_geral.parquet');
CREATE OR REPLACE TABLE atana.inpi.ig_2_total_por_pais AS
  SELECT * FROM read_parquet('https://raw.githubusercontent.com/joaoroquedasilvajunior/atana-data/main/raw/inpi/ig_2_total_por_pais.parquet');
CREATE OR REPLACE TABLE atana.inpi.ig_3_total_por_estado AS
  SELECT * FROM read_parquet('https://raw.githubusercontent.com/joaoroquedasilvajunior/atana-data/main/raw/inpi/ig_3_total_por_estado.parquet');
CREATE OR REPLACE TABLE atana.inpi.ig_4_total_por_especie AS
  SELECT * FROM read_parquet('https://raw.githubusercontent.com/joaoroquedasilvajunior/atana-data/main/raw/inpi/ig_4_total_por_especie.parquet');
CREATE OR REPLACE TABLE atana.inpi.ig_5_total_por_tipo_de_pro_serv AS
  SELECT * FROM read_parquet('https://raw.githubusercontent.com/joaoroquedasilvajunior/atana-data/main/raw/inpi/ig_5_total_por_tipo_de_pro_serv.parquet');
CREATE OR REPLACE TABLE atana.inpi.ig_6_registro_ig AS
  SELECT * FROM read_parquet('https://raw.githubusercontent.com/joaoroquedasilvajunior/atana-data/main/raw/inpi/ig_6_registro_ig.parquet');
CREATE OR REPLACE TABLE atana.inpi.ig_7_registros_origem_prod_serv AS
  SELECT * FROM read_parquet('https://raw.githubusercontent.com/joaoroquedasilvajunior/atana-data/main/raw/inpi/ig_7_registros_origem_prod_serv.parquet');
CREATE OR REPLACE TABLE atana.inpi.ig_8_vigentes_origem_e_ano AS
  SELECT * FROM read_parquet('https://raw.githubusercontent.com/joaoroquedasilvajunior/atana-data/main/raw/inpi/ig_8_vigentes_origem_e_ano.parquet');
CREATE OR REPLACE TABLE atana.inpi.ig_9_vigentes_tipo_pro_serv AS
  SELECT * FROM read_parquet('https://raw.githubusercontent.com/joaoroquedasilvajunior/atana-data/main/raw/inpi/ig_9_vigentes_tipo_pro_serv.parquet');
CREATE OR REPLACE TABLE atana.inpi.mrc_deposito_mrc AS
  SELECT * FROM read_parquet('https://raw.githubusercontent.com/joaoroquedasilvajunior/atana-data/main/raw/inpi/mrc_deposito_mrc.parquet');
CREATE OR REPLACE TABLE atana.inpi.mrc_deposito_mrc_2024_entrada_pais AS
  SELECT * FROM read_parquet('https://raw.githubusercontent.com/joaoroquedasilvajunior/atana-data/main/raw/inpi/mrc_deposito_mrc_2024_entrada_pais.parquet');
CREATE OR REPLACE TABLE atana.inpi.mrc_deposito_mrc_cidade AS
  SELECT * FROM read_parquet('https://raw.githubusercontent.com/joaoroquedasilvajunior/atana-data/main/raw/inpi/mrc_deposito_mrc_cidade.parquet');
CREATE OR REPLACE TABLE atana.inpi.mrc_deposito_mrc_classes AS
  SELECT * FROM read_parquet('https://raw.githubusercontent.com/joaoroquedasilvajunior/atana-data/main/raw/inpi/mrc_deposito_mrc_classes.parquet');
CREATE OR REPLACE TABLE atana.inpi.mrc_deposito_mrc_cnae AS
  SELECT * FROM read_parquet('https://raw.githubusercontent.com/joaoroquedasilvajunior/atana-data/main/raw/inpi/mrc_deposito_mrc_cnae.parquet');
CREATE OR REPLACE TABLE atana.inpi.mrc_deposito_mrc_direto_classe AS
  SELECT * FROM read_parquet('https://raw.githubusercontent.com/joaoroquedasilvajunior/atana-data/main/raw/inpi/mrc_deposito_mrc_direto_classe.parquet');
CREATE OR REPLACE TABLE atana.inpi.mrc_deposito_mrc_direto_pais AS
  SELECT * FROM read_parquet('https://raw.githubusercontent.com/joaoroquedasilvajunior/atana-data/main/raw/inpi/mrc_deposito_mrc_direto_pais.parquet');
CREATE OR REPLACE TABLE atana.inpi.mrc_deposito_mrc_direto_pais_classe AS
  SELECT * FROM read_parquet('https://raw.githubusercontent.com/joaoroquedasilvajunior/atana-data/main/raw/inpi/mrc_deposito_mrc_direto_pais_classe.parquet');
CREATE OR REPLACE TABLE atana.inpi.mrc_deposito_mrc_madri_classe AS
  SELECT * FROM read_parquet('https://raw.githubusercontent.com/joaoroquedasilvajunior/atana-data/main/raw/inpi/mrc_deposito_mrc_madri_classe.parquet');
CREATE OR REPLACE TABLE atana.inpi.mrc_deposito_mrc_madri_pais AS
  SELECT * FROM read_parquet('https://raw.githubusercontent.com/joaoroquedasilvajunior/atana-data/main/raw/inpi/mrc_deposito_mrc_madri_pais.parquet');
CREATE OR REPLACE TABLE atana.inpi.mrc_deposito_mrc_madri_pais_classes AS
  SELECT * FROM read_parquet('https://raw.githubusercontent.com/joaoroquedasilvajunior/atana-data/main/raw/inpi/mrc_deposito_mrc_madri_pais_classes.parquet');
CREATE OR REPLACE TABLE atana.inpi.mrc_deposito_mrc_natureza AS
  SELECT * FROM read_parquet('https://raw.githubusercontent.com/joaoroquedasilvajunior/atana-data/main/raw/inpi/mrc_deposito_mrc_natureza.parquet');
CREATE OR REPLACE TABLE atana.inpi.mrc_deposito_mrc_origem AS
  SELECT * FROM read_parquet('https://raw.githubusercontent.com/joaoroquedasilvajunior/atana-data/main/raw/inpi/mrc_deposito_mrc_origem.parquet');
CREATE OR REPLACE TABLE atana.inpi.mrc_deposito_mrc_origem_classes AS
  SELECT * FROM read_parquet('https://raw.githubusercontent.com/joaoroquedasilvajunior/atana-data/main/raw/inpi/mrc_deposito_mrc_origem_classes.parquet');
CREATE OR REPLACE TABLE atana.inpi.mrc_deposito_mrc_pais AS
  SELECT * FROM read_parquet('https://raw.githubusercontent.com/joaoroquedasilvajunior/atana-data/main/raw/inpi/mrc_deposito_mrc_pais.parquet');
CREATE OR REPLACE TABLE atana.inpi.mrc_deposito_mrc_tipo_nj AS
  SELECT * FROM read_parquet('https://raw.githubusercontent.com/joaoroquedasilvajunior/atana-data/main/raw/inpi/mrc_deposito_mrc_tipo_nj.parquet');
CREATE OR REPLACE TABLE atana.inpi.mrc_deposito_mrc_uf AS
  SELECT * FROM read_parquet('https://raw.githubusercontent.com/joaoroquedasilvajunior/atana-data/main/raw/inpi/mrc_deposito_mrc_uf.parquet');
CREATE OR REPLACE TABLE atana.inpi.mrc_deposito_setores_industriais AS
  SELECT * FROM read_parquet('https://raw.githubusercontent.com/joaoroquedasilvajunior/atana-data/main/raw/inpi/mrc_deposito_setores_industriais.parquet');
CREATE OR REPLACE TABLE atana.inpi.mrc_dept_mrc_direto_2024_pais_nice AS
  SELECT * FROM read_parquet('https://raw.githubusercontent.com/joaoroquedasilvajunior/atana-data/main/raw/inpi/mrc_dept_mrc_direto_2024_pais_nice.parquet');
CREATE OR REPLACE TABLE atana.inpi.mrc_marcas_vigentes AS
  SELECT * FROM read_parquet('https://raw.githubusercontent.com/joaoroquedasilvajunior/atana-data/main/raw/inpi/mrc_marcas_vigentes.parquet');
CREATE OR REPLACE TABLE atana.inpi.mrc_marcas_vigentes_classes AS
  SELECT * FROM read_parquet('https://raw.githubusercontent.com/joaoroquedasilvajunior/atana-data/main/raw/inpi/mrc_marcas_vigentes_classes.parquet');
CREATE OR REPLACE TABLE atana.inpi.mrc_mrc_vigentes_natureza AS
  SELECT * FROM read_parquet('https://raw.githubusercontent.com/joaoroquedasilvajunior/atana-data/main/raw/inpi/mrc_mrc_vigentes_natureza.parquet');
CREATE OR REPLACE TABLE atana.inpi.mrc_registro_mrc AS
  SELECT * FROM read_parquet('https://raw.githubusercontent.com/joaoroquedasilvajunior/atana-data/main/raw/inpi/mrc_registro_mrc.parquet');
CREATE OR REPLACE TABLE atana.inpi.mrc_registro_mrc_2024_pais AS
  SELECT * FROM read_parquet('https://raw.githubusercontent.com/joaoroquedasilvajunior/atana-data/main/raw/inpi/mrc_registro_mrc_2024_pais.parquet');
CREATE OR REPLACE TABLE atana.inpi.mrc_registro_mrc_classe_madri AS
  SELECT * FROM read_parquet('https://raw.githubusercontent.com/joaoroquedasilvajunior/atana-data/main/raw/inpi/mrc_registro_mrc_classe_madri.parquet');
CREATE OR REPLACE TABLE atana.inpi.mrc_registro_mrc_contagem_classes AS
  SELECT * FROM read_parquet('https://raw.githubusercontent.com/joaoroquedasilvajunior/atana-data/main/raw/inpi/mrc_registro_mrc_contagem_classes.parquet');
CREATE OR REPLACE TABLE atana.inpi.mrc_registro_mrc_diret_ano_classe AS
  SELECT * FROM read_parquet('https://raw.githubusercontent.com/joaoroquedasilvajunior/atana-data/main/raw/inpi/mrc_registro_mrc_diret_ano_classe.parquet');
CREATE OR REPLACE TABLE atana.inpi.mrc_registro_mrc_diret_pais_ano AS
  SELECT * FROM read_parquet('https://raw.githubusercontent.com/joaoroquedasilvajunior/atana-data/main/raw/inpi/mrc_registro_mrc_diret_pais_ano.parquet');
CREATE OR REPLACE TABLE atana.inpi.mrc_registro_mrc_diret_uf_ano AS
  SELECT * FROM read_parquet('https://raw.githubusercontent.com/joaoroquedasilvajunior/atana-data/main/raw/inpi/mrc_registro_mrc_diret_uf_ano.parquet');
CREATE OR REPLACE TABLE atana.inpi.mrc_registro_mrc_madri_pais_ano AS
  SELECT * FROM read_parquet('https://raw.githubusercontent.com/joaoroquedasilvajunior/atana-data/main/raw/inpi/mrc_registro_mrc_madri_pais_ano.parquet');
CREATE OR REPLACE TABLE atana.inpi.mrc_registro_mrc_origem AS
  SELECT * FROM read_parquet('https://raw.githubusercontent.com/joaoroquedasilvajunior/atana-data/main/raw/inpi/mrc_registro_mrc_origem.parquet');
CREATE OR REPLACE TABLE atana.inpi.mrc_regt_mrc_diret_2024_pais_nice AS
  SELECT * FROM read_parquet('https://raw.githubusercontent.com/joaoroquedasilvajunior/atana-data/main/raw/inpi/mrc_regt_mrc_diret_2024_pais_nice.parquet');
CREATE OR REPLACE TABLE atana.inpi.mrc_regt_mrc_madri_2024_pais_nice AS
  SELECT * FROM read_parquet('https://raw.githubusercontent.com/joaoroquedasilvajunior/atana-data/main/raw/inpi/mrc_regt_mrc_madri_2024_pais_nice.parquet');
CREATE OR REPLACE TABLE atana.inpi.prg_deposito_prg_municipio AS
  SELECT * FROM read_parquet('https://raw.githubusercontent.com/joaoroquedasilvajunior/atana-data/main/raw/inpi/prg_deposito_prg_municipio.parquet');
CREATE OR REPLACE TABLE atana.inpi.prg_deposito_prg_origem AS
  SELECT * FROM read_parquet('https://raw.githubusercontent.com/joaoroquedasilvajunior/atana-data/main/raw/inpi/prg_deposito_prg_origem.parquet');
CREATE OR REPLACE TABLE atana.inpi.prg_deposito_prg_pais AS
  SELECT * FROM read_parquet('https://raw.githubusercontent.com/joaoroquedasilvajunior/atana-data/main/raw/inpi/prg_deposito_prg_pais.parquet');
CREATE OR REPLACE TABLE atana.inpi.prg_deposito_prg_tipo_nj AS
  SELECT * FROM read_parquet('https://raw.githubusercontent.com/joaoroquedasilvajunior/atana-data/main/raw/inpi/prg_deposito_prg_tipo_nj.parquet');
CREATE OR REPLACE TABLE atana.inpi.prg_deposito_prg_uf AS
  SELECT * FROM read_parquet('https://raw.githubusercontent.com/joaoroquedasilvajunior/atana-data/main/raw/inpi/prg_deposito_prg_uf.parquet');
CREATE OR REPLACE TABLE atana.inpi.prg_registro_prg AS
  SELECT * FROM read_parquet('https://raw.githubusercontent.com/joaoroquedasilvajunior/atana-data/main/raw/inpi/prg_registro_prg.parquet');
CREATE OR REPLACE TABLE atana.inpi.prg_total_geral AS
  SELECT * FROM read_parquet('https://raw.githubusercontent.com/joaoroquedasilvajunior/atana-data/main/raw/inpi/prg_total_geral.parquet');

-- ═══ §SANITY — paste after the block above ═══
SELECT 'atana.anthropic_eei.country_usage'              AS schema_table,    178 AS expected, COUNT(*) AS actual FROM atana.anthropic_eei.country_usage
UNION ALL SELECT 'atana.anthropic_eei.task_usage_by_country',              5321,             COUNT(*) FROM atana.anthropic_eei.task_usage_by_country
UNION ALL SELECT 'atana.lpg.execucao_financeira',                         10984,             COUNT(*) FROM atana.lpg.execucao_financeira
UNION ALL SELECT 'atana.lpg.relatorio_gestao',                            18180,             COUNT(*) FROM atana.lpg.relatorio_gestao
UNION ALL SELECT 'atana.pnab.execucao_financeira',                         5425,             COUNT(*) FROM atana.pnab.execucao_financeira
UNION ALL SELECT 'atana.pnab.extratos_bancarios',                        212288,             COUNT(*) FROM atana.pnab.extratos_bancarios
UNION ALL SELECT 'atana.macro.fx_brl_usd_annual',                            32,             COUNT(*) FROM atana.macro.fx_brl_usd_annual
UNION ALL SELECT 'atana.macro.ipca',                                         34,             COUNT(*) FROM atana.macro.ipca
UNION ALL SELECT 'atana.canonical.cmo_directory_alcam',                      13,             COUNT(*) FROM atana.canonical.cmo_directory_alcam
UNION ALL SELECT 'atana.canonical.latam_trade_by_fcs_domain',               794,             COUNT(*) FROM atana.canonical.latam_trade_by_fcs_domain
UNION ALL SELECT 'atana.canonical.domain_crosswalk',                         93,             COUNT(*) FROM atana.canonical.domain_crosswalk
UNION ALL SELECT 'atana.ifpi.gmr_2026_global_headline',                       1,             COUNT(*) FROM atana.ifpi.gmr_2026_global_headline
UNION ALL SELECT 'atana.inpi.mrc_deposito_mrc_classes',                      28,             COUNT(*) FROM atana.inpi.mrc_deposito_mrc_classes
UNION ALL SELECT 'atana.ibge_estruturais.tab_2_1',                          354,             COUNT(*) FROM atana.ibge_estruturais.tab_2_1
UNION ALL SELECT 'atana.ecad.arrecadacao_distribuicao',                       7,             COUNT(*) FROM atana.ecad.arrecadacao_distribuicao
ORDER BY 1;

-- After all rows show actual == expected:
--   cd .../atana-data && python3 etl/_audit_methodology_status.py --apply
-- then commit + push the methodology + manifest updates.
