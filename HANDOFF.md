# HANDOFF

## Estado atual do branch
- repo: `C:\Users\mauri\git\scrap_report`
- branch: `master`
- remoto: `origin/master`
- baseline runtime atual: `b893356`
- status: runtime estabilizado, docs em sync neste ciclo, release nova pendente

## Current truth
O projeto esta operacional em tres camadas:
- execucao unitaria de scraping e staging
- geracao de relatorios derivados por tipo de planilha
- varredura em lote por plano e preset

O ponto importante agora nao e falta de runtime geral. O ponto importante e que os casos especiais restantes foram explicitados e nao estao mais escondidos em heuristica.

Para recorte multi-setor do mesmo relatorio, o modo recomendado agora e:
- um pedido unico
- expansao automatica em um item por setor
- um arquivo por setor
- um manifest unico de controle

## Report kinds suportados
- `pendentes`
- `executadas`
- `pendentes_execucao`
- `consulta_ssa`
- `consulta_ssa_print`
- `aprovacao_emissao`
- `aprovacao_cancelamento`
- `derivadas_relacionadas`
- `reprogramacoes`

## Matriz curta de filtros
- `numero_ssa` validado:
  - `consulta_ssa`
  - `consulta_ssa_print`
  - `aprovacao_emissao`
- `data de emissao` validada:
  - `executadas`
  - `pendentes`
  - `pendentes_execucao`
  - `consulta_ssa`
  - `consulta_ssa_print`
  - `aprovacao_cancelamento`
  - `reprogramacoes`
- `data de emissao` bloqueada:
  - `aprovacao_emissao`
  - `derivadas_relacionadas`

## Casos especiais reais
### `aprovacao_emissao`
- `setor_executor` usa alias de runtime para `divisao_emissora`
- baseline exporta normalmente
- `numero_ssa` foi validado
- `emission_date` segue bloqueado porque o export atual nao entrega `Emitida Em` confiavel

### `derivadas_relacionadas`
- usa parser derivado proprio
- o parser esta validado
- o gargalo atual nao e parser; e export oficial instavel no fluxo Playwright

## Evidencia recente
### `derivadas_relacionadas`
- manifest: [staging\sweep_derivadas_relacionadas_baseline.json](C:\Users\mauri\git\scrap_report\staging\sweep_derivadas_relacionadas_baseline.json)
- erro validado:
  - `report_kind=derivadas_relacionadas nao entregou download no fluxo oficial; tela segue especial por export instavel`

### `aprovacao_emissao`
- baseline: [staging\sweep_aprovacao_emissao_baseline_none.json](C:\Users\mauri\git\scrap_report\staging\sweep_aprovacao_emissao_baseline_none.json)
- bloqueio de data: [staging\sweep_aprovacao_emissao_emission_date_blocked.json](C:\Users\mauri\git\scrap_report\staging\sweep_aprovacao_emissao_emission_date_blocked.json)
- derivado baseline: [ssas_dados_20260322_231441_748743.xlsx](C:\Users\mauri\git\scrap_report\staging\reports\ssas_dados_20260322_231441_748743.xlsx)
- observacao:
  - `87` linhas
  - coluna `Emitida Em` presente
  - apenas `1` valor nao nulo na rodada atual

## Commits relevantes apos `v0.1.1`
- `5436620` `STABILITY_PATCH: explicitar alias aprovacao emissao`
- `0e109f4` `STABILITY_PATCH: explicitar parser derivadas`
- `a2ef27c` `STABILITY_PATCH: liberar numero ssa aprovacao`
- `55ccbe6` `STABILITY_PATCH: explicitar export derivadas`
- `b893356` `STABILITY_PATCH: explicitar bloqueio emissao`

## Quality gates mais recentes
- `py_compile`: verde
- `ruff`: verde
- `ty`: verde
- `pytest` focado: `86 passed`

## Riscos residuais reais
- `derivadas_relacionadas` ainda depende de estabilizar export oficial
- `aprovacao_emissao` ainda depende de uma fonte confiavel de `Emitida Em` antes de liberar `emission_date`
- `demais` continua vazio em `SETOR_PRIORITY_GROUPS`
- faltam algumas telas adicionais do menu `Relatorios`

## Proximos passos naturais
1. criar nova tag/release incremental com a documentacao do modo multi-setor recomendado
2. se voltar ao codigo, priorizar export oficial de `derivadas_relacionadas`
3. depois avaliar se existe criterio forte para `Emitida Em` em `aprovacao_emissao`
