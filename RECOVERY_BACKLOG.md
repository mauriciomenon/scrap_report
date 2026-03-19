# RECOVERY_BACKLOG

## NAO_BLOQUEANTE_DEFERIDO
- completar `data de emissao` nos `report_kind` ainda bloqueados:
  - `aprovacao_emissao`
  - `derivadas_relacionadas`
- ampliar prova oficial de formatos nas telas ja liberadas:
  - `executadas`
  - `consulta_ssa_print`
  - `aprovacao_cancelamento`
  - `reprogramacoes`
- adicionar presets operacionais de agenda, sem criar script novo
- preencher o grupo `demais` em `SETOR_PRIORITY_GROUPS`
- executar rodada real de sweep com preset em pelo menos um report kind verde e guardar evidencia consolidada
- avaliar paralelismo controlado no sweep sem quebrar ordem nem rastreabilidade
- adicionar ordenacao opcional no derivado sem alterar a ordem fonte por padrao
- classificar semanticamente `relacao` em `derivadas_relacionadas`, mantendo o bruto como evidencia
- mapear e implementar telas ainda faltantes do menu `Relatorios`:
  - `SSAs sem Registro de APR`
  - `ATs Emitidas para uma SSA`
  - `SSAs por Documento`
- validar smoke Debian13 real em host com conectividade estavel ao PyPI
- revisar naming e manifest consolidado para rotinas de agenda futuras
