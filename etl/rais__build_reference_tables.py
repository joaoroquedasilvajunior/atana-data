"""rais__build_reference_tables.py — Sprint 0 deliverable.

Builds the two canonical reference tables that gate the Sprint 1 ETL:

  - raw/rais/_reference/cnae_cultural.parquet — 5-digit CNAE 2.0 subclasses
  - raw/rais/_reference/cbo_cultural.parquet  — CBO-Domiciliar families (4-digit roots)

Source of truth
---------------
IBGE Sistema de Informações e Indicadores Culturais 2007-2010, Notas Técnicas,
Quadros 1, 2, 3 (CNAE pages 17-19) and the CBO-Domiciliar list (pages 20-22).
Available at https://biblioteca.ibge.gov.br/visualizacao/livros/liv65974.pdf

The CNAE 2.0 hierarchy from this publication remains stable through the
2009-2020, 2011-2022, and 2013-2024 editions of SIIC (verified by spot-check
of the 2011-2022 informative). The CBO-Domiciliar family roots also remain
stable, though specific 6-digit CBO 2002 subgroups within each family have
seen incremental additions.

Direct vs indirect (CNAE only)
------------------------------
SIIC distinguishes "atividades diretamente relacionadas à cultura"
(directly cultural) from "atividades indiretamente relacionadas" (tarjadas
em cinza in the original — equipment manufacturing, ICT, telecom, retail).

Phase 2 default uses **direct only** (~35 subclasses). The Phase 3 SALIC × RAIS
paper has its natural sample in the direct list because Lei Rouanet operates
inside the "Artes" frame. The indirect list is included in the parquet with
flag=indirect for future broader analyses (e.g., creative-economy aggregations
using UNCTAD/BOP definitions).

Idempotent: rerunning produces byte-identical Parquet output.
"""

import os
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = REPO_ROOT / "raw" / "rais" / "_reference"


# ============================================================================
# CNAE 2.0 — cultural subclasses (from SIIC 2007-2010, Quadros 1, 2, 3)
# ============================================================================

CNAE_CULTURAL = [
    # ------------- DIRECT — INDÚSTRIAS DE TRANSFORMAÇÃO (seção C) -------------
    ("18.11-3", "18113", "18", "Impressão de jornais, livros, revistas e outras publicações periódicas", "C", "direct", "livro_imprensa"),
    ("18.21-1", "18211", "18", "Serviços de pré-impressão", "C", "direct", "livro_imprensa"),
    ("18.22-9", "18229", "18", "Serviços de acabamentos gráficos", "C", "direct", "livro_imprensa"),
    ("18.30-0", "18300", "18", "Reprodução de materiais gravados em qualquer suporte", "C", "direct", "midias_audiovisuais"),
    ("32.20-5", "32205", "32", "Fabricação de instrumentos musicais", "C", "direct", "artes_visuais_artesanato"),

    # ------------- DIRECT — INFORMAÇÃO E COMUNICAÇÃO (seção J) -------------
    ("58.11-5", "58115", "58", "Edição de livros", "J", "direct", "livro_imprensa"),
    ("58.12-3", "58123", "58", "Edição de jornais", "J", "direct", "livro_imprensa"),
    ("58.13-1", "58131", "58", "Edição de revistas", "J", "direct", "livro_imprensa"),
    ("58.21-2", "58212", "58", "Edição integrada à impressão de livros", "J", "direct", "livro_imprensa"),
    ("58.22-1", "58221", "58", "Edição integrada à impressão de jornais", "J", "direct", "livro_imprensa"),
    ("58.23-9", "58239", "58", "Edição integrada à impressão de revistas", "J", "direct", "livro_imprensa"),
    ("59.11-1", "59111", "59", "Atividades de produção cinematográfica, de vídeos e de programas de televisão", "J", "direct", "midias_audiovisuais"),
    ("59.12-0", "59120", "59", "Atividades de pós-produção cinematográfica, de vídeos e de programas de televisão", "J", "direct", "midias_audiovisuais"),
    ("59.13-8", "59138", "59", "Distribuição cinematográfica, de vídeo e de programas de televisão", "J", "direct", "midias_audiovisuais"),
    ("59.14-6", "59146", "59", "Atividades de exibição cinematográfica", "J", "direct", "midias_audiovisuais"),
    ("59.20-1", "59201", "59", "Atividades de gravação de som e de edição de música", "J", "direct", "midias_audiovisuais"),
    ("60.10-1", "60101", "60", "Atividades de rádio", "J", "direct", "midias_audiovisuais"),
    ("60.21-7", "60217", "60", "Atividades de televisão aberta", "J", "direct", "midias_audiovisuais"),
    ("60.22-5", "60225", "60", "Programadoras e atividades relacionadas à televisão por assinatura", "J", "direct", "midias_audiovisuais"),

    # ------------- DIRECT — ATIVIDADES PROFISSIONAIS (seção M) -------------
    ("71.11-1", "71111", "71", "Serviços de arquitetura", "M", "direct", "design_servicos_criativos"),
    ("73.11-4", "73114", "73", "Agências de publicidade", "M", "direct", "design_servicos_criativos"),
    ("73.12-2", "73122", "73", "Agenciamento de espaços para publicidade, exceto em veículos de comunicação", "M", "direct", "design_servicos_criativos"),
    ("73.19-0", "73190", "73", "Atividades de publicidade não especificadas anteriormente", "M", "direct", "design_servicos_criativos"),
    ("74.10-2", "74102", "74", "Design e decoração de interiores", "M", "direct", "design_servicos_criativos"),
    ("74.20-0", "74200", "74", "Atividades fotográficas e similares", "M", "direct", "midias_audiovisuais"),

    # ------------- DIRECT — EDUCAÇÃO (seção P) -------------
    ("85.92-9", "85929", "85", "Ensino de arte e cultura", "P", "direct", "apresentacoes_celebracoes"),

    # ------------- DIRECT — ARTES, CULTURA, ESPORTE E RECREAÇÃO (seção R) -------------
    ("90.01-9", "90019", "90", "Artes cênicas, espetáculos e atividades complementares", "R", "direct", "apresentacoes_celebracoes"),
    ("90.02-7", "90027", "90", "Criação artística", "R", "direct", "artes_visuais_artesanato"),
    ("90.03-5", "90035", "90", "Gestão de espaços para artes cênicas, espetáculos e outras atividades artísticas", "R", "direct", "apresentacoes_celebracoes"),
    ("91.01-5", "91015", "91", "Atividades de bibliotecas e arquivos", "R", "direct", "patrimonio_cultural"),
    ("91.02-3", "91023", "91", "Atividades de museus e de exploração, restauração artística e conservação de lugares e prédios históricos e atrações similares", "R", "direct", "patrimonio_cultural"),
    ("91.03-1", "91031", "91", "Atividades de jardins botânicos, zoológicos, parques nacionais, reservas ecológicas e áreas de proteção ambiental", "R", "direct", "patrimonio_cultural"),

    # ------------- DIRECT — OUTRAS ATIVIDADES DE SERVIÇOS (seção S) -------------
    ("94.93-6", "94936", "94", "Atividades de organizações associativas ligadas à cultura e à arte", "S", "direct", "apresentacoes_celebracoes"),

    # ============================================================================
    # INDIRECT — equipment, ICT, telecom, retail (SIIC tarja cinza)
    # Included for future broader analyses; Phase 2 default excludes these.
    # ============================================================================
    ("26.10-8", "26108", "26", "Fabricação de componentes eletrônicos", "C", "indirect", "midias_audiovisuais"),
    ("26.21-3", "26213", "26", "Fabricação de equipamentos de informática", "C", "indirect", "midias_audiovisuais"),
    ("26.22-1", "26221", "26", "Fabricação de periféricos para equipamentos de informática", "C", "indirect", "midias_audiovisuais"),
    ("26.31-1", "26311", "26", "Fabricação de equipamentos transmissores de comunicação", "C", "indirect", "midias_audiovisuais"),
    ("26.32-9", "26329", "26", "Fabricação de aparelhos telefônicos e de outros equipamentos de comunicação", "C", "indirect", "midias_audiovisuais"),
    ("26.40-0", "26400", "26", "Fabricação de aparelhos de recepção, reprodução, gravação e amplificação de áudio e vídeo", "C", "indirect", "midias_audiovisuais"),
    ("26.70-1", "26701", "26", "Fabricação de equipamentos e instrumentos ópticos, fotográficos e cinematográficos", "C", "indirect", "midias_audiovisuais"),
    ("26.80-9", "26809", "26", "Fabricação de mídias virgens, magnéticas e ópticas", "C", "indirect", "midias_audiovisuais"),
    ("32.11-6", "32116", "32", "Lapidação de gemas e fabricação de artefatos de ourivesaria e joalheria", "C", "indirect", "artes_visuais_artesanato"),
    ("32.12-4", "32124", "32", "Fabricação de bijuterias e artefatos semelhantes", "C", "indirect", "artes_visuais_artesanato"),
    ("32.40-0", "32400", "32", "Fabricação de brinquedos e jogos recreativos", "C", "indirect", "design_servicos_criativos"),
    ("46.47-8", "46478", "46", "Comércio atacadista de artigos de escritório e de papelaria; livros, jornais e outras publicações", "G", "indirect", "livro_imprensa"),
    ("46.51-6", "46516", "46", "Comércio atacadista de computadores, periféricos e suprimentos de informática", "G", "indirect", "midias_audiovisuais"),
    ("46.52-4", "46524", "46", "Comércio atacadista de componentes eletrônicos e equipamentos de telefonia e comunicação", "G", "indirect", "midias_audiovisuais"),
    ("47.51-2", "47512", "47", "Comércio varejista especializado de equipamentos e suprimentos de informática", "G", "indirect", "midias_audiovisuais"),
    ("47.52-1", "47521", "47", "Comércio varejista especializado de equipamentos de telefonia e comunicação", "G", "indirect", "midias_audiovisuais"),
    ("47.56-3", "47563", "47", "Comércio varejista especializado de instrumentos musicais e acessórios", "G", "indirect", "artes_visuais_artesanato"),
    ("47.61-0", "47610", "47", "Comércio varejista de livros, jornais, revistas e papelaria", "G", "indirect", "livro_imprensa"),
    ("47.62-8", "47628", "47", "Comércio varejista de discos, CDs, DVDs e fitas", "G", "indirect", "midias_audiovisuais"),
    ("47.83-1", "47831", "47", "Comércio varejista de joias e relógios", "G", "indirect", "artes_visuais_artesanato"),
    ("47.85-7", "47857", "47", "Comércio varejista de artigos usados", "G", "indirect", "artes_visuais_artesanato"),
    ("61.10-8", "61108", "61", "Telecomunicações por fio", "J", "indirect", "midias_audiovisuais"),
    ("61.20-5", "61205", "61", "Telecomunicações sem fio", "J", "indirect", "midias_audiovisuais"),
    ("61.30-2", "61302", "61", "Telecomunicações por satélite", "J", "indirect", "midias_audiovisuais"),
    ("61.41-8", "61418", "61", "Operadoras de televisão por assinatura por cabo", "J", "indirect", "midias_audiovisuais"),
    ("61.42-6", "61426", "61", "Operadoras de televisão por assinatura por micro-ondas", "J", "indirect", "midias_audiovisuais"),
    ("61.43-4", "61434", "61", "Operadoras de televisão por assinatura por satélite", "J", "indirect", "midias_audiovisuais"),
    ("61.90-6", "61906", "61", "Outras atividades de telecomunicações", "J", "indirect", "midias_audiovisuais"),
    ("62.01-5", "62015", "62", "Desenvolvimento de programas de computador sob encomenda", "J", "indirect", "design_servicos_criativos"),
    ("62.02-3", "62023", "62", "Desenvolvimento e licenciamento de programas de computador customizáveis", "J", "indirect", "design_servicos_criativos"),
    ("62.03-1", "62031", "62", "Desenvolvimento e licenciamento de programas de computador não customizáveis", "J", "indirect", "design_servicos_criativos"),
    ("63.11-9", "63119", "63", "Tratamento de dados, provedores de serviços de aplicação e serviços de hospedagem na internet", "J", "indirect", "midias_audiovisuais"),
    ("63.19-4", "63194", "63", "Portais, provedores de conteúdo e outros serviços de informação na internet", "J", "indirect", "midias_audiovisuais"),
    ("63.91-7", "63917", "63", "Agências de notícias", "J", "indirect", "livro_imprensa"),
    ("63.99-2", "63992", "63", "Outras atividades de prestação de serviços de informação não especificadas anteriormente", "J", "indirect", "livro_imprensa"),
    ("71.19-7", "71197", "71", "Atividades técnicas relacionadas à arquitetura e engenharia", "M", "indirect", "design_servicos_criativos"),
    ("77.22-5", "77225", "77", "Aluguel de fitas de vídeo, DVDs e similares", "N", "indirect", "midias_audiovisuais"),
    ("77.23-3", "77233", "77", "Aluguel de objetos do vestuário, joias e acessórios", "N", "indirect", "artes_visuais_artesanato"),
    ("85.93-7", "85937", "85", "Ensino de idiomas", "P", "indirect", "apresentacoes_celebracoes"),
    ("93.21-2", "93212", "93", "Parques de diversão e parques temáticos", "R", "indirect", "apresentacoes_celebracoes"),
    ("93.29-8", "93298", "93", "Atividades de recreação e lazer não especificadas anteriormente", "R", "indirect", "apresentacoes_celebracoes"),
]


# ============================================================================
# CBO-Domiciliar — cultural families (from SIIC 2007-2010, pages 20-22)
# ============================================================================
# Each entry is a 4-digit family root. RAIS uses CBO 2002 at 6-digit subgroup
# level. The Sprint 1 ETL expands these roots to all matching 6-digit codes via
# LIKE 'NNNN%' filter against the RAIS cbo_2002 column.

CBO_CULTURAL = [
    ("2330", "Professores e instrutores (com formação de nível superior) no ensino profissional", "ensino_arte"),
    ("2531", "Profissionais de marketing, publicidade e comercialização", "publicidade"),
    ("2611", "Profissionais do jornalismo", "livro_imprensa"),
    ("2612", "Profissionais da informação", "livro_imprensa"),
    ("2613", "Arquivologistas e museólogos", "patrimonio"),
    ("2614", "Filólogos, tradutores e intérpretes", "livro_imprensa"),
    ("2615", "Escritores e redatores", "livro_imprensa"),
    ("2616", "Especialistas em editoração", "livro_imprensa"),
    ("2617", "Locutores e comentaristas", "audiovisual"),
    ("2621", "Produtores de espetáculos", "espetaculos"),
    ("2622", "Coreógrafos e bailarinos", "espetaculos"),
    ("2623", "Atores, diretores de espetáculos e afins", "espetaculos"),
    ("2624", "Compositores, músicos e cantores", "musica"),
    ("2625", "Desenhistas industriais (designer), escultores, pintores e afins (inclui o artesão)", "artes_visuais"),
    ("2627", "Decoradores de interiores e cenógrafos", "design"),
    ("3313", "Professores (com formação de nível médio) no ensino profissionalizante", "ensino_arte"),
    ("3322", "Professores leigos no ensino profissionalizante", "ensino_arte"),
    ("3331", "Instrutores e professores de escolas livres", "ensino_arte"),
    ("3524", "Agentes de fiscalização de espetáculos e meios de comunicação", "espetaculos"),
    ("3544", "Leiloeiros e avaliadores", "artes_visuais"),
    ("3711", "Técnicos em biblioteconomia", "patrimonio"),
    ("3712", "Técnicos em museologia", "patrimonio"),
    ("3713", "Técnicos em artes gráficas", "livro_imprensa"),
    ("3721", "Cinegrafistas", "audiovisual"),
    ("3722", "Fotógrafos", "audiovisual"),
    ("3723", "Técnicos em operações de máquinas de transmissão de dados", "audiovisual"),
    ("3731", "Técnicos em operação de estação de rádio", "audiovisual"),
    ("3732", "Técnicos em operação de estação de televisão", "audiovisual"),
    ("3741", "Técnicos em operação de aparelhos de sonorização", "audiovisual"),
    ("3742", "Técnicos em operação de aparelhos de cenografia", "espetaculos"),
    ("3743", "Técnicos em operação de aparelhos de projeção", "audiovisual"),
    ("3751", "Decoradores e vitrinistas de nível médio", "design"),
    ("3761", "Bailarinos de danças populares", "espetaculos"),
    ("3762", "Músicos e cantores populares", "musica"),
    ("3763", "Palhaços, acrobatas e afins", "espetaculos"),
    ("3764", "Apresentadores de espetáculos", "espetaculos"),
    ("3765", "Modelos", "design"),
    ("4151", "Escriturários de serviços de biblioteca e documentação", "patrimonio"),
    ("7421", "Confeccionadores de instrumentos musicais", "artes_visuais"),
    ("7501", "Supervisores de joalheria e afins", "artes_visuais"),
    ("7502", "Supervisores de vidraria, cerâmica e afins", "artes_visuais"),
    ("7519", "Joalheiros e artesãos de metais preciosos e semipreciosos", "artes_visuais"),
    ("7521", "Sopradores e moldadores de vidro e afins", "artes_visuais"),
    ("7522", "Cortadores, polidores, jateadores e gravadores de vidros e afins", "artes_visuais"),
    ("7523", "Ceramistas (preparação e fabricação)", "artes_visuais"),
    ("7524", "Vidreiros e ceramistas (acabamento e decoração)", "artes_visuais"),
    ("7606", "Supervisores das artes gráficas", "livro_imprensa"),
    ("7611", "Trabalhadores da preparação da tecelagem", "artes_visuais"),
    ("7612", "Operadores da preparação da tecelagem", "artes_visuais"),
    ("7613", "Operadores de tear e máquinas similares", "artes_visuais"),
    ("7660", "Trabalhadores polivalentes das artes gráficas", "livro_imprensa"),
    ("7661", "Trabalhadores da pré-impressão gráfica", "livro_imprensa"),
    ("7662", "Trabalhadores da impressão gráfica", "livro_imprensa"),
    ("7663", "Trabalhadores do acabamento gráfico", "livro_imprensa"),
    ("7664", "Trabalhadores de laboratório fotográfico", "audiovisual"),
    ("7681", "Trabalhadores artesanais da tecelagem", "artes_visuais"),
    ("7682", "Trabalhadores artesanais da confecção de roupas", "artes_visuais"),
    ("7683", "Trabalhadores artesanais da confecção de calçados e artefatos de couros e peles", "artes_visuais"),
    ("7686", "Trabalhadores tipográficos, linotipistas e afins", "livro_imprensa"),
    ("7687", "Encadernadores e recuperadores de livros (pequenos lotes ou a unidade)", "livro_imprensa"),
    ("9152", "Reparadores de instrumentos musicais", "musica"),
    ("9912", "Mantenedores de equipamentos de lazer", "espetaculos"),
]


def build_cnae() -> pd.DataFrame:
    df = pd.DataFrame(CNAE_CULTURAL, columns=[
        "cnae_2_subclasse_dotted",   # 18.11-3
        "cnae_2_subclasse",          # 18113 (RAIS storage format)
        "cnae_2_divisao",            # 18
        "denominacao",
        "secao_cnae",                # C, J, M, P, R, S
        "relacao_cultura",           # direct | indirect
        "siic_dominio",              # SIIC cultural domain
    ])
    df = df.sort_values(["relacao_cultura", "cnae_2_subclasse"]).reset_index(drop=True)
    return df


def build_cbo() -> pd.DataFrame:
    df = pd.DataFrame(CBO_CULTURAL, columns=[
        "cbo_familia",     # 4-digit root used for LIKE 'NNNN%' filter
        "denominacao",
        "cbo_dominio",     # internal grouping
    ])
    df["cbo_familia_grande_grupo"] = df["cbo_familia"].str[0]  # first digit = grande grupo
    df["cbo_familia_subgrupo_principal"] = df["cbo_familia"].str[:2]
    df = df.sort_values("cbo_familia").reset_index(drop=True)
    return df


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    cnae = build_cnae()
    cbo = build_cbo()
    cnae.to_parquet(OUT_DIR / "cnae_cultural.parquet", index=False, compression="snappy")
    cbo.to_parquet(OUT_DIR / "cbo_cultural.parquet", index=False, compression="snappy")

    # Console summary
    print(f"CNAE cultural reference: {len(cnae)} subclasses")
    print(f"  direct  : {(cnae.relacao_cultura == 'direct').sum()}")
    print(f"  indirect: {(cnae.relacao_cultura == 'indirect').sum()}")
    print(f"  divisions: {sorted(cnae.cnae_2_divisao.unique())}")
    print()
    print(f"CBO cultural reference: {len(cbo)} families (CBO-Domiciliar 4-digit)")
    print(f"  grande_grupos: {sorted(cbo.cbo_familia_grande_grupo.unique())}")
    print()
    print(f"Outputs:")
    print(f"  {OUT_DIR / 'cnae_cultural.parquet'}")
    print(f"  {OUT_DIR / 'cbo_cultural.parquet'}")


if __name__ == "__main__":
    main()
