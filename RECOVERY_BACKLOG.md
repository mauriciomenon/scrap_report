# RECOVERY_BACKLOG

## NAO_BLOQUEANTE_DEFERIDO
- estabilizar export oficial de `derivadas_relacionadas` no fluxo Playwright
- investigar fonte confiavel de `Emitida Em` em `aprovacao_emissao` antes de qualquer liberacao de `emission_date`
- ampliar prova oficial de formatos nas telas ja liberadas:
  - `executadas`
  - `consulta_ssa_print`
  - `aprovacao_cancelamento`
  - `reprogramacoes`
- executar rodada real de `sweep-run` com preset em pelo menos um `report_kind` verde e consolidar evidencia
- preencher o grupo `demais` em `SETOR_PRIORITY_GROUPS`
- avaliar paralelismo controlado no sweep sem quebrar ordem nem rastreabilidade
- adicionar ordenacao opcional no derivado sem alterar a ordem fonte por padrao
- mapear e implementar telas ainda faltantes do menu `Relatorios`:
  - `SSAs sem Registro de APR`
  - `ATs Emitidas para uma SSA`
  - `SSAs por Documento`
- validar smoke Debian13 real em host com conectividade estavel ao PyPI
- revisar naming e manifest consolidado para rotinas de agenda futuras
