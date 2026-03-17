# PRE_RELEASE_STATUS

## Estado atual
- repo publico: sim
- URL: `https://github.com/mauriciomenon/scrap_report`
- branch operacional: `master`
- commit de referencia desta doc: `3a8da8e`

## O que esta pronto hoje
### Runtime principal
- scraping real do SAM via Playwright
- stage de xlsx e pdf
- reporting derivado para formatos suportados
- wrappers Windows para operador final
- secret seguro por OS com fallback Windows

### Report kinds suportados
- `pendentes`
- `executadas`
- `pendentes_execucao`
- `consulta_ssa`
- `consulta_ssa_print`
- `aprovacao_emissao`
- `aprovacao_cancelamento`
- `derivadas_relacionadas`
- `reprogramacoes`

### Lote
- `FilterSpec`
- `SweepPlan`
- `SweepRunner`
- presets operacionais
- `-Preset` ligado ao launcher Windows oficial

## Evidencia funcional consolidada
### Validado com conteudo real
- `pendentes`
- `executadas`
- `pendentes_execucao`
- `consulta_ssa`
- `consulta_ssa_print`
- `derivadas_relacionadas`

### Estavel com 0 linhas na rodada validada
- `reprogramacoes`
- `aprovacao_emissao`
- `aprovacao_cancelamento`

## Evidencia tecnica recente
### Sweep base
- commit: `ffe2807`
- validacao: `py_compile`, `ruff`, `ty`, `pytest`

### Sweep runner
- commit: `eb924f3`
- validacao: `py_compile`, `ruff`, `ty`, `pytest`

### Presets operacionais
- commit: `571937e`
- validacao: `py_compile`, `ruff`, `ty`, `pytest`

### Launcher Windows com preset
- commit: `3a8da8e`
- validacao:
  - parser PowerShell dos wrappers
  - smoke de encaminhamento com `uv` stub

## Resultado de prontidao
### Pronto para
- uso operacional no Windows pelo launcher atual
- execucao unitaria e `both`
- execucao em lote por preset pelo mesmo launcher
- integracao externa via json de pipeline e manifest de lote

### Ainda nao pronto para
- declarar cobertura total do menu `Relatorios`
- usar `data de emissao` no runtime real de sweep
- agendamento sem definir politica operacional
- fechamento cross-platform final sem nova rodada Debian13 real estavel

## Bloqueios e limites reais
- `data de emissao` ainda nao esta ligada ao runtime real do sweep
- grupo `demais` ainda nao foi preenchido
- ainda faltam telas adicionais do menu `Relatorios`
- smoke Debian13 real continua dependente de conectividade externa estavel

## Proximo gate recomendado
1. executar uma rodada real de `sweep-run` com preset em `pendentes` ou `executadas`
2. validar manifest, bruto staged e derivados ponta a ponta
3. decidir se o proximo slice prioriza:
   - `data de emissao` no sweep
   - novas telas do menu `Relatorios`
