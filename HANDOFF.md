# HANDOFF

## Estado atual do branch
- repo: `C:\Users\mauri\git\scrap_report`
- branch: `master`
- remoto: `origin/master`
- commit atual de referencia: `25f46e1`
- status: runtime e launcher Windows atualizados e sincronizados com remoto

## Current truth
O projeto saiu da fase inicial de migracao e entrou em estado operacional.
Hoje existem tres camadas claras:
- execucao unitaria de scraping e staging
- geracao de relatorios derivados por tipo de planilha
- varredura em lote por plano e preset

## Entrypoints operacionais
- `EXECUTAR_SCRAP_WINDOWS.ps1`: entrypoint oficial
- `EXECUTAR_SCRAP_WINDOWS.cmd`: launcher para usuario final
- `scripts/main_windows.ps1`: alias legado
- `scripts/scrape_sam_windows.ps1`: wrapper principal do Windows
- `python -m scrap_report.cli`: entrypoint CLI completo

## Runtime principal
- `config.py`: defaults, filtros e grupos de setores
- `scraper.py`: navegacao Playwright nas telas SAM
- `pipeline.py`: scrape + stage + reporting
- `reporting.py`: parser e artefatos derivados
- `sweep.py`: `FilterSpec`, `SweepPlan`, `SweepRunner` e presets
- `cli.py`: `windows-flow`, `sweep-run`, `pipeline`, `report-from-excel`, `secret` e demais comandos

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

## Estado validado em ambiente real
### Conteudo validado
- `pendentes`
- `executadas`
- `pendentes_execucao`
- `consulta_ssa`
- `consulta_ssa_print`
- `derivadas_relacionadas`
- `aprovacao_cancelamento`
- `reprogramacoes`

### Fluxo estavel com 0 linhas na rodada validada
- `aprovacao_emissao`

## Matriz atual de `data de emissao`
Validado no runtime:
- `executadas`
- `pendentes`
- `pendentes_execucao`
- `consulta_ssa`
- `consulta_ssa_print`
- `aprovacao_cancelamento`
- `reprogramacoes`

Bloqueado no runtime:
- `aprovacao_emissao`
- `derivadas_relacionadas`

Regra de formato:
- aceitos no parser central:
  - `DD/MM/YYYY`
  - `DDMMYYYY`
  - `YYYY-MM-DD`
- rejeitado cedo:
  - `MM/DD/YYYY`

## Filtros e setores
Defaults operacionais atuais:
- `Setor Emissor = IEE3`
- `Setor Executor = MEL4`

Suporte atual:
- apenas emissor
- apenas executor
- ambos
- nenhum

Grupos de prioridade registrados:
- principal: `IEE3`, `MEL4`, `MEL3`
- segundo_plano: `IEE1`, `IEE2`, `IEE4`
- terceiro_plano: `MEL1`, `MEL2`, `IEQ1`, `IEQ2`, `IEQ3`, `ILA1`, `ILA2`, `ILA3`
- prioritarios: uniao dos tres grupos acima
- demais: reservado para preenchimento futuro

## Sweep atual
Ja entregue:
- `FilterSpec`
- `SweepPlan`
- `SweepRunner`
- presets operacionais
- integracao de `-Preset` ao launcher Windows

Ainda nao entregue:
- agendamento
- paralelismo
- presets ligados a rotina de agenda

## Artefatos
- bruto staged: `staging\*.xlsx` ou `staging\*.pdf`
- derivados: `staging\reports\*.xlsx`
- manifests unitarios e de lote: caminho informado em `--output-json`

## Evidencia tecnica consolidada
### Windows / SAM
- fluxo no-args validado
- fluxo com parametros validado
- `consulta_ssa_print` validada com pdf real
- `derivadas_relacionadas` validada com parser normalizado
- preset no launcher Windows validado por smoke de encaminhamento

### Quality gates recentes
- `py_compile`: verde nos slices recentes
- `ruff`: verde nos slices recentes
- `ty`: verde nos slices recentes
- `pytest` focado: verde nos slices recentes, incluindo `test_sweep.py`

## Riscos residuais reais
- `data de emissao` no sweep ainda e parcial por `report_kind`
- `aprovacao_emissao` segue bloqueado por semantica fraca do export
- `derivadas_relacionadas` segue bloqueado por instabilidade de export
- grupo `demais` ainda esta vazio
- ainda faltam algumas telas adicionais do menu `Relatorios`
- smoke Debian13 real segue dependente de conectividade externa estavel

## Proximos passos naturais
1. rodar um sweep real com preset em um report kind verde e validar artefatos ponta a ponta
2. decidir se a proxima prioridade e `data de emissao` no sweep ou novas telas do menu `Relatorios`
3. preencher o grupo `demais` quando a lista operacional estiver pronta
