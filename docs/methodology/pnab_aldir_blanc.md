# `atana.pnab` — Política Nacional Aldir Blanc

> **Status (2026-06-14):** GitHub ✅ `549bc99` on origin/main · MotherDuck ⏳ pending first sync · 4 tables / 232,928 rows in `curated/pnab/`

> Methodology note. Phase PNAB ingest, 2026-06-13. ETL: `etl/pnab__to_parquet.py`
> → 4 Parquet tables in `curated/pnab/`. Accretion-criterion gate 3 (consumers:
> Note #20 published, candidate Análise 26 / Note #11, TCU×PNAB analysis).

## §1 Origem

A PNAB (Política Nacional Aldir Blanc), instituída pela **Lei Complementar
195/2022** e regulamentada pelo **Decreto 11.453/2023**, é o fundo permanente de
fomento federal à cultura pós-pandemia. Opera por **transferência direta** do
Tesouro a estados e municípios — sem mediação fiscal corporativa, ao contrário da
Lei Rouanet (`atana.salic`). Fonte: dataset *"Implementação e Execução da PNAB"*
do Portal de Dados da Cultura (mantenedor DFD/SEFIC; atualização mensal, última
extração capturada 14/11/2025), CC BY 4.0.

## §2 Ciclos e janelas temporais

- **Ciclo 1** — exercício 2023–2024; R$ 3,00 bi distribuídos a 5.425 entes (27
  estados+DF + 5.398 municípios = 97 % dos 5.570 municípios). Execução financeira,
  extratos bancários e PAR Ciclo 1 cobrem este ciclo.
- **Ciclo 2** — exercício 2024–2025, **em execução**. Só o PAR (planos) foi
  extraído; a execução financeira do Ciclo 2 ainda não foi publicada pelo portal.

## §3 Schema das 4 tabelas

| Tabela | Linhas | Conteúdo |
|---|---:|---|
| `execucao_financeira` | 5.425 | execução por ente, Ciclo 1 (recebido/rendimentos/saldo/gasto/%) |
| `par_planos` | 10.131 | planos de ação Ciclo 1∪2 harmonizados (5.084 + 5.047) |
| `governanca_entes` | 5.084 | derivada do PAR Ciclo 1: Conselho×Plano×Fundo + escore 0–3 |
| `extratos_bancarios` | 212.288 | transações Ciclo 1 (uf, ente, recebedor, descrição, tipo, data, valor) |

Convenção: snake_case ASCII; `cod_ibge` VARCHAR (2 díg. estado / 7 díg. município);
valores em **BRL nominal** (ver §4). Offsets reais dos xlsx (verificados,
divergem do prompt): execução header r4/dados r6; PAR C1 header r3/dados r5;
PAR C2 sheet "Informações do PAR" header r3/dados r5; extrato header r4/dados r6.

### §3.1 Chave entre tabelas — NÃO é CNPJ
Ao contrário do que o prompt de planejamento assumia, **nem `execucao_financeira`
nem `extratos_bancarios` carregam CNPJ**. A chave de junção real é:
- `execucao` ↔ `par_planos` ↔ `governanca`: **`cod_ibge`** (validação 8.2 = 100 %
  de interseção).
- `extratos` ↔ resto: apenas **`uf` + `ente` (nome)** — o extrato não tem
  `cod_ibge` nem CNPJ. Junção por nome é difusa; declarar ao usar.

### §3.2 Harmonização Ciclo 1 × Ciclo 2 (decisão §13 do prompt)
O PAR Ciclo 2 tem layout **materialmente diferente** do Ciclo 1 — workbook de 16
abas, aba principal "Informações do PAR" com 16 colunas (vs 26 do Ciclo 1, aba
única). **Decisão:** uma única tabela `par_planos` harmonizada sobre o **núcleo
analítico comum** (cod_ibge, uf, ente, cnpj_ente, codigo_plano_acao,
valor_plano_brl, data_envio_par, tem_conselho/plano/fundo, ciclo), com um
discriminador `ciclo`. Os campos **ricos só do Ciclo 1** (cnpj_fundo, nome_fundo,
responsáveis, meta-*, ações afirmativas, atividades periféricas, participação
social) ficam **NULL** nas linhas do Ciclo 2. Campos **só do Ciclo 2** mapeados:
`situacao`, `ano_par`. O `valor_plano_brl` do Ciclo 2 vem da coluna "Valor total
do PAR referente aos 4 anos". Preferiu-se harmonizar (vs duas tabelas ragged)
porque o núcleo comum — governança + valor + chave — está presente nos dois e é o
que a análise de governança × execução exige.

## §4 Caveats

- **BRL nominal, não deflacionado.** A janela PNAB (2023–2025) é curta; o deflator
  IPCA p/ BRL 2024 ≈ 1,0. Escolha consciente — `atana.salic` (Rouanet) está
  deflacionada em BRL 2024; para o comparativo Rouanet×PNAB, deflacionar a Rouanet
  de volta a nominal do ano OU deflacionar a PNAB é decisão da sessão de análise.
- **Outlier-canário Rondônia (estado):** pct_gasto = 0,000721 (gastou R$ 14.692 de
  R$ 20,4 mi recebidos). Mantido como achado real — potencial subreporte ou
  congelamento; cruzar com `atana.tcu`. Não corrigido.
- **Extrato: débitos ≠ valor gasto.** A soma de débitos do extrato é R$ 6,25 bi,
  contra R$ 2,82 bi de `valor_gasto`, porque os extratos incluem **aplicações
  financeiras automáticas e transferências internas** (ex.: "Aplicação automática"),
  não apenas pagamento a beneficiários. Filtrar por descrição antes de somar gasto
  efetivo. Vocabulário de `tipo_operacao` e `descricao_lancamento` a ser perfilado
  na sessão de análise.
- **Granularidade declaratória do PAR.** Campos textuais (ações afirmativas,
  atividades periféricas, participação social) são auto-declarados, com ortografia
  e detalhe muito variáveis. NLP futura.
- **Vocabulário de governança fechado:** apenas "Sim"/"Não" (sem "Em construção");
  escore 0–3 é limpo.
- **Arredondamento DAX no portal.** A identidade `recebido+rendimentos ≈ saldo+gasto`
  tem pequenas inconsistências de arredondamento do portal MinC — não corrigidas.

## §5 Comparativo com `atana.salic` (Rouanet)
Dois instrumentos federais de magnitude quase idêntica (≈ R$ 3 bi/ano cada), lógicas
opostas: Rouanet = captação fiscal mediada por marketing corporativo; PNAB =
transferência intergovernamental direta. **Execução agregada:** PNAB ≈ **94 %**
(R$ 2,82 bi de R$ 3,00 bi) vs Rouanet ≈ **51 %**. O comparativo é a peça política
nuclear candidata (Análise 26 / Note #11). ⚠️ Junção SALIC↔PNAB exige decisão de
deflator (§4) e não há chave de ente comum direta (Rouanet é por projeto/proponente,
PNAB por ente federativo).

## §6 Relação com `atana.tcu`
O Acórdão 1709/2025 do TCU auditou exatamente a PNAB (maturidade média 1,75/3;
*gestão de riscos* = 1; *equidade* exigida por deliberação). O cruzamento
`governanca_entes` × execução × achados-TCU é direto e alimenta a oferta Public
Funding Architecture Review. **Achado de governança (validação 8.4):** o pct de
execução salta de 90,9 % (escore 0) para 93,8 % (escore 1) e **platô** em
93,7–94,4 % (escores 2–3) — ter *algum* instrumento de governança prediz execução;
os marginais somam pouco. Quase-monotônico, com o passo decisivo em 0→1.

## §7 Cobertura FCS
PNAB mapeada como **transversal · "Multiple — not separable"** no
`canonical.domain_crosswalk` (92ª linha) — os PARs locais cobrem todos os domínios
culturais, não um só; mapeamento por escopo administrativo, não equivalência 1:1
(confidence `good`). Não altera o medidor de cobertura (13/14).

## §8 Validações (2026-06-13, contra Parquet local)
8.1 total recebido = R$ 3,000 bi ✓ · gasto R$ 2,820 bi (94,0 %) ✓ · 27+5.398=5.425
entes ✓ · regional Sul/SE 96,5 % · CO 95,2 % · NE 91,0 % · N 89,9 % (match exato) ·
Rondônia 0,000721 ✓ · 8.2 interseção execução↔PAR(C1) on cod_ibge = 100 % ·
8.4 governança documentada em §6 · idempotência byte-idêntica ✓ (sha256 2 runs).

## §9 Citação
> Brasil, Ministério da Cultura — *Implementação e Execução da Política Nacional Aldir Blanc* (Ciclo 1 + Ciclo 2). Portal de Dados da Cultura, CC BY 4.0. LC 195/2022; Decreto 11.453/2023. Ingerido em `atana.pnab` (`atana-data`), 2026-06-13.
