# REVIEW_THREAD_TRIAGE

## Resolvido no branch atual
- pipeline modular com entrada e saida claras para integracao
- secret store por OS com fallback seguro no Windows
- launcher Windows sem argumentos para usuario final
- filtros por setor emissor, executor, ambos e nenhum
- janela automatica de 4 semanas
- exportacao real nas telas principais do SAM
- cobertura de `pendentes`, `executadas`, `pendentes_execucao`, `consulta_ssa`, `consulta_ssa_print`, `reprogramacoes`, `aprovacao_emissao`, `aprovacao_cancelamento` e `derivadas_relacionadas`
- parser normalizado para `derivadas_relacionadas`
- base de sweep, runner, presets e `-Preset` no launcher Windows

## Falso positivo / nao aplicar
- qualquer ajuste de layout ou dashboard proprio fora do fluxo de extracao
- criar um script diferente para cada combinacao operacional
- reorder silencioso do conteudo exportado pelo SAM

## Refactor amplo sem bug concreto
- paralelizar sweep antes de consolidar requisitos de ordem, erro e manifest
- redesenhar toda a camada de reporting sem bug real especifico
- unificar todas as telas do SAM em uma DSL propria agora

## Fora de escopo atual
- agendamento
- filtro real por data de emissao no runtime de lote
- novas telas do menu `Relatorios` ainda nao priorizadas
- preenchimento do grupo `demais` sem lista operacional fechada
