# ROUND_STATUS

## Sessao atual
- data: `2026-03-19`
- pasta: `C:\Users\mauri\git\scrap_report`
- branch: `master`
- commit atual: `25f46e1`

## Snapshot executivo
- repo publico existente: sim
- branch operacional: `master`
- runtime atual: estavel para os fluxos principais do SAM
- launcher Windows: unitario e preset ligados ao mesmo entrypoint
- sweep: base, runner e presets entregues

## Estado consolidado por fase
### Fase 1 - launcher e fluxo Windows
- `7ccc6a9`: `windows-flow` sequencial com secret seguro
- `6020e37`: fallback real de shell e setup simplificado
- `fa6d07a`: backend Windows sem instalacao manual extra
- `ceaf855`: wrapper one-command e docs iniciais
- `926d512`: correcao de parse PS1 e `both`
- `0d188f7`: launcher no-args e desktop flow
- `2b669e6`: launcher com args opcionais e cert handling

Resultado:
- usuario final pode rodar sem conhecer CLI interna
- secret e resolvido de forma segura
- `both` ficou suportado no wrapper

### Fase 2 - navegacao real do SAM e cobertura de telas
- `60f59ca`: uso das rotas nativas de relatorio
- `a05a444`: filtro de emissao limitado a 4 semanas
- `41c603e`: estabilizacao de filtros e exportacao real
- `f9a3bb5`: `pendentes_execucao`
- `1e58f11`: `consulta_ssa`
- `4885b47`: `reprogramacoes`
- `49f1b6f`: `aprovacao_emissao`
- `d915407`: `aprovacao_cancelamento`
- `7cd1cb7`: `derivadas_relacionadas`
- `409ed33`: parser normalizado para `derivadas_relacionadas`

Resultado:
- telas principais do SAM foram mapeadas e operadas via Playwright
- export por lupa + dropdown + `ExportToExcel` ficou estabilizado
- `consulta_ssa_print` passou a gerar pdf staged

### Fase 3 - escopo de setores
- `03f36aa`: suporte a emissor, executor, ambos e nenhum

Resultado:
- filtros `ALL`, `*` e vazio passam a significar sem filtro
- runtime e reporting deixaram de depender de hardcode unico

### Fase 4 - sweep e presets
- `ffe2807`: base de planejamento (`FilterSpec`, `SweepPlan`)
- `eb924f3`: `SweepRunner` e manifest consolidado
- `571937e`: presets operacionais
- `3a8da8e`: preset ligado ao launcher Windows
- `bafbdf9`: gate seguro de `data de emissao`
- `52ef379`: base geral de filtros e `numero_ssa`
- `27fbba3`: `data de emissao` em `pendentes`
- `904d865`: `data de emissao` em `pendentes_execucao`
- `44d846d`: `data de emissao` em `consulta_ssa`

Resultado:
- lote e planejado por grupos de setores
- falha por item nao mata o lote inteiro
- o entrypoint Windows aceita `-Preset` sem script novo
- `data de emissao` agora esta validada de forma parcial e controlada por `report_kind`

### Fase 5 - expansao final de `data de emissao`
- `44d846d`: `consulta_ssa`
- `25f46e1`: `consulta_ssa_print`, `aprovacao_cancelamento` e `reprogramacoes`

## Report kinds atuais
- `pendentes`
- `executadas`
- `pendentes_execucao`
- `consulta_ssa`
- `consulta_ssa_print`
- `aprovacao_emissao`
- `aprovacao_cancelamento`
- `derivadas_relacionadas`
- `reprogramacoes`

## Validacao recente por slice documental e operacional
### `ffe2807` - base de sweep
- `py_compile`: ok
- `ruff`: ok
- `ty`: ok
- `pytest -q tests/test_sweep.py tests/test_config_secrets.py`: `25 passed`

### `eb924f3` - runner de lote
- `py_compile`: ok
- `ruff`: ok
- `ty`: ok
- `pytest -q tests/test_sweep.py tests/test_cli.py tests/test_config_secrets.py`: `57 passed`

### `571937e` - presets operacionais
- `py_compile`: ok
- `ruff`: ok
- `ty`: ok
- `pytest -q tests/test_sweep.py tests/test_cli.py tests/test_config_secrets.py`: `63 passed`

### `3a8da8e` - preset no launcher Windows
- parser PowerShell dos 3 wrappers: ok
- smoke com `uv` stub no launcher oficial: ok
- smoke com `uv` stub no alias legado: ok
- smoke com `uv` stub para `both`: ok

### `44d846d` - `consulta_ssa` com `data de emissao`
- `py_compile`: ok
- `ruff`: ok
- `ty`: ok
- `pytest -q tests/test_config_secrets.py tests/test_scraper_contract.py tests/test_sweep.py`: `62 passed`
- prova real oficial:
  - `consulta_ssa` com `numero_ssa=202602521` e `2026-02-23`: `ok`
  - `consulta_ssa` com `02/23/2026`: erro cedo por formato US

### `25f46e1` - expansao final de `data de emissao`
- `py_compile`: ok
- `ruff`: ok
- `ty`: ok
- `pytest -q tests/test_config_secrets.py tests/test_scraper_contract.py tests/test_sweep.py`: `62 passed`
- prova real oficial:
  - `consulta_ssa_print` com `numero_ssa=202602521` e `2026-02-23`: `ok`
  - `aprovacao_cancelamento` com `2026-02-24`: `ok`
  - `reprogramacoes` com `2026-02-23`: `ok`
  - `aprovacao_emissao` com `2026-03-02`: continua bloqueado

## Comportamento validado hoje
- `EXECUTAR_SCRAP_WINDOWS.ps1` suporta:
  - modo unitario
  - modo `both`
  - modo preset
- `-Preset` nao combina com `-Setor` nem `-SetorEmissor`
- `both` com preset gera um JSON por report kind alvo
- `data de emissao` validada hoje para:
  - `executadas`
  - `pendentes`
  - `pendentes_execucao`
  - `consulta_ssa`
  - `consulta_ssa_print`
  - `aprovacao_cancelamento`
  - `reprogramacoes`

## Risco residual
- `data de emissao` ainda nao fecha para todos os `report_kind`
- `aprovacao_emissao` segue com semantica fraca no export
- `derivadas_relacionadas` segue instavel no export
- `demais_*` existe como preset, mas o grupo `demais` segue vazio
- faltam telas adicionais do menu `Relatorios`
- smoke Debian13 real continua dependente de conectividade externa estavel

## Pendente real
1. rodada real de sweep com preset e report kind verde
2. decisao sobre proxima prioridade:
   - completar `data de emissao` nos `report_kind` ainda bloqueados
   - `data de emissao` no sweep
   - novas telas do menu `Relatorios`
3. preenchimento do grupo `demais`
