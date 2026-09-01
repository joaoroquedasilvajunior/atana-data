# `atana.pnab.beneficiarios` — PNAB beneficiary microdata (Phase 10a)

> **Status (2026-08-31):** built locally ✅ · validated 5/5 · idempotent (byte-identical) ·
> **MotherDuck sync PENDING (manual, João)** · GitHub commit PENDING. Table 6 of `atana.pnab`.

## §1 Origem
Export *"PNAB — dados abertos completo"* do Portal de Dados da Cultura (MinC, DFD/SEFIC),
CC BY 4.0. Uma linha por **beneficiário × ente** do repasse direto da PNAB (Lei Complementar
195/2022), com o documento do beneficiário **mascarado** (LGPD). O MinC entrega o arquivo já
cruzado com seis bases administrativas, o que o torna a única tabela do corpus que enxerga
*quem recebeu na ponta* e não apenas *qual ente recebeu*.

## §2 Escopo e reconciliação
**167.817 registros × 59 colunas + `valor_brl` (DOUBLE), R$ 2,87 bi.** O total reconcilia com o
Ciclo 1 já no corpus (`execucao_financeira`, ~R$ 3 bi) — é o **mesmo dinheiro desagregado**, não
um universo novo; provavelmente **Ciclo 1 apenas** (o arquivo não traz coluna de ciclo/ano). São
**64.130 documentos distintos** mascarados: 167.817 linhas são registros beneficiário×ente, não
pessoas únicas — nunca somar como pessoas. **Reconciliação forte:** o split por tipo de ente reproduz exatamente a manchete do I Seminário de Avaliação da PNAB já no corpus (`ciclo1_avaliacao_headlines`): **145.235 municipais + 22.582 estaduais = 167.817** — esta é a microdata que a entrada de 2026-07-05 do manifesto reservou como **Phase 10a**.

## §3 As seis bases cruzadas (sufixo da coluna = fonte)
`_bbagil` pagamento (uf, cod_ibge, documento mascarado, tipo, valor) · `_receita_cpf` (sexo,
idade, faixa etária, ocupação principal, MEI) · `_receita_cnpj` (CNAE principal/secundária,
porte, natureza jurídica, flags cultural/audiovisual/educação) · `_rais` (raça/cor, escolaridade,
PCD, tipo de vínculo, CBO 2002, vínculo ativo 2024, faixa salarial, flag CBO cultural) ·
`_rel_trabalhista_inss` (CBO) · `_cnefe` (situação/tipo do domicílio) · `_cadunico` (renda
familiar total e per capita, PBF, características do domicílio) · `pertence_bpc` · `_ibge`
(população, capital, porte populacional, macrorregião, categoria do município).

## §4 Chave e junção com o resto de `atana.pnab`
Junta às tabelas-ente por **`cod_ibge_bbagil`** (2 díg. estado / 7 díg. município) ↔ `cod_ibge`
de `execucao_financeira` / `par_planos` / `governanca_entes`. Sem CNPJ do ente e sem chave para
`extratos_bancarios` além de uf+nome. O documento mascarado impede rastreio individual e qualquer
junção pessoa-a-pessoa.

## §5 Caveats (obrigatórios em qualquer análise)
- **LGPD:** documento mascarado (`000******16`); 64.130 distintos; linhas ≠ pessoas.
- **Seleção nos joins:** os campos de RAIS/CadÚnico/CNPJ preenchem só o subconjunto
  formal/registrado — a maioria é NULL (ex.: 78,8% sem vínculo RAIS, logo o recorte de raça
  cobre uma minoria). Declarar sempre a base do denominador.
- **BRL nominal, Ciclo 1** (convenção §4 de `pnab_aldir_blanc.md`; IPCA da janela ≈ 1).
- **PJ vs PF:** 56% do dinheiro a CNPJ, 44% a CPF — "transferência ao trabalhador" inclui
  organizações; separar antes de qualquer leitura de renda pessoal.
- **Outlier DF:** repasse médio por beneficiário R$ 104.760, muito acima dos demais — manter
  como ponto a investigar, cruzar com `atana.tcu`; não corrigir.
- **Formato de origem:** CSV `;`-delimitado, decimal '.', BOM no header, quebras de linha em
  campos de texto — 167.817 registros (não as ~431k linhas cruas). Fonte gitignored
  (`raw/pnab/_source/`, 125 MB); só o Parquet (4,3 MB) é versionado.

## §6 Crosswalk
Sem linha nova em `canonical.domain_crosswalk`: a tabela herda o mapeamento da PNAB (transversal;
transferência direta) e a dimensão cultural fina vem das flags CNAE/CBO já embutidas nas colunas
`flag_cnae_cultural_receita_cnpj` e `flag_cbo_cultural_rais`. Cobertura FCS inalterada.

## §7 Achados que a tabela destrava (read-only, verificados)
PJ 56% × PF 44%; sexo M R$ 680 mi × F R$ 582 mi; inversão geográfica vs. Rouanet (Nordeste 30%
× Sudeste 37% do dinheiro, mas repasse médio Nordeste R$ 10.790 × Sudeste R$ 23.353); 78,8% sem
vínculo RAIS e 3,4% MEI (a informalidade como maioria); 5% do dinheiro a famílias PBF. Consome:
Note #31 (Rouanet × PNAB), `_atana_intel/pnab_microdata_scoping.md`.
