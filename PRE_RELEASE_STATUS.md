# PRE_RELEASE_STATUS

## Estado atual
- repo publico: sim
- URL: `https://github.com/mauriciomenon/scrap_report`
- branch operacional: `master`
- baseline antes do slice atual: `b3c8be6`
- status de sync no inicio do slice atual: `master` alinhado com `origin/master`

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

### Baseline global de tipagem
- baseline anterior do slice: `06761d6`
- validacao:
  - `py_compile`: ok
  - `ruff`: ok
  - `ty`: ok
  - `pytest`: `201 passed`

### Harden de dependencias de desenvolvimento
- baseline anterior do slice: `ce76125`
- vulnerabilidades tratadas:
  - `pytest < 9.0.3` (`GHSA-6w46-j5rx-g56g`, medium)
  - `Pygments < 2.20.0` (`GHSA-5239-wwwm-4pmq`, low)
- escopo real:
  - grupo `dev`
  - sem impacto no runtime publicado do pacote
- mitigacao aplicada:
  - `pytest>=9.0.3`
  - `Pygments>=2.20.0`
- validacao:
  - `py_compile`: ok
  - `ruff`: ok
  - `ty`: ok
  - `pytest`: `201 passed`
  - `dependabot/alerts?state=open`: `[]`

### Higiene local e demonstrativo REST real `IEE3`
- baseline anterior do slice: `f389671`
- ajuste de higiene:
  - `.gitignore` passou a ignorar `.pytest-local/` e `.pytest-tmp/`
  - artefato local `%SystemDrive%/` removido do workspace
- validacao:
  - `py_compile`: ok
  - `ruff`: ok
  - `ty` (`src tests`): ok
  - `pytest`: `202 passed`
  - `sam-api-flow` panorama (`IEE3`): `status=ok`, `count=69`
  - artifacts:
    - [sam_api_iee3_pendentes_demo_20260423_130409.json](C:\Users\mauri\git\scrap_report\tmp\sam_api_iee3_pendentes_demo_20260423_130409.json)
    - [sam_api_iee3_pendentes_demo_20260423_130409.csv](C:\Users\mauri\git\scrap_report\tmp\sam_api_iee3_pendentes_demo_20260423_130409.csv)
    - [sam_api_iee3_pendentes_demo_20260423_130409.xlsx](C:\Users\mauri\git\scrap_report\tmp\sam_api_iee3_pendentes_demo_20260423_130409.xlsx)

### Smoke cross-platform real (Windows11 + Debian13)
- baseline anterior do slice: `b3c8be6`
- smoke W11:
  - `powershell -ExecutionPolicy Bypass -File scripts/smoke_windows11.ps1`: ok
  - evidencia: [smoke_evidence_windows11.json](C:\Users\mauri\git\scrap_report\staging\smoke_evidence_windows11.json)
  - `generated_at_utc=2026-04-23T16:14:20.9295303Z`
- smoke Debian13:
  - `bash scripts/smoke_debian13.sh`: ok
  - evidencia: [smoke_evidence_debian13.json](C:\Users\mauri\git\scrap_report\staging\smoke_evidence_debian13.json)
  - `generated_at_utc=2026-04-23T17:52:22.288728+00:00`
- checks confirmados nas duas evidencias:
  - `py_compile, ruff, pytest, scan_secrets, validate_contract, stage, pipeline_report_only, ingest_latest = ok`

## Resultado de prontidao
### Pronto para
- uso operacional no Windows pelo launcher atual
- execucao unitaria e `both`
- execucao em lote por preset pelo mesmo launcher
- integracao externa via json de pipeline e manifest de lote
- consumo externo como pacote Python com:
  - `scrap_report.__version__`
  - `scrap_report.build_contract_catalog()`
  - entrypoint `scrap-report`
- demonstrativo REST real de `pendentes` para `IEE3` atualizado em `2026-04-23` com 69 SSAs

### Ainda nao pronto para
- declarar cobertura total do menu `Relatorios`
- usar `data de emissao` no runtime real de sweep
- agendamento sem definir politica operacional

## Bloqueios e limites reais
- `data de emissao` ainda nao esta ligada ao runtime real do sweep
- grupo `demais` ainda nao foi preenchido
- ainda faltam telas adicionais do menu `Relatorios`

## Proximo gate recomendado
1. executar uma rodada real de `sweep-run` com preset em `pendentes` ou `executadas`
2. validar manifest, bruto staged e derivados ponta a ponta
3. decidir se o proximo slice prioriza:
   - `data de emissao` no sweep
   - novas telas do menu `Relatorios`
