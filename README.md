# scrap_report

Extracao modular de artefatos do SAM com foco em xlsx e pdf para integracao externa, operacao Windows e varredura em lote.

## Current truth
- branch operacional: `master`
- launcher Windows oficial: `EXECUTAR_SCRAP_WINDOWS.ps1`
- launcher visual para duplo clique: `EXECUTAR_SCRAP_WINDOWS.cmd`
- wrapper legado mantido: `scripts/main_windows.ps1`
- fluxo Windows unitario: `windows-flow`
- fluxo Windows em lote por preset: `sweep-run`
- `data de emissao` validada no runtime para:
  - `executadas`
  - `pendentes`
  - `pendentes_execucao`
  - `consulta_ssa`
  - `consulta_ssa_print`
  - `aprovacao_cancelamento`
  - `reprogramacoes`
- janela padrao operacional: semana atual ate 4 semanas para tras
- exemplo validado em `2026-03-16`: `202608 -> 202612`

## Escopo entregue
- login seguro com secret store do OS e fallback DPAPI no Windows
- navegacao real nas telas do SAM via Playwright
- export de xlsx e pdf conforme a tela
- staging de artefatos com naming estavel
- geracao de relatorios derivados quando o formato for suportado
- varredura em lote por grupos de setores e presets operacionais

## Fora do escopo atual
- dashboard ou GUI propria
- agendamento
- paralelismo no sweep
- criacao de script novo para cada variacao operacional

## Estrutura do projeto
- `src/scrap_report/config.py`: defaults, validacao e grupos de setores
- `src/scrap_report/scraper.py`: automacao Playwright das telas SAM
- `src/scrap_report/file_ops.py`: naming e staging de downloads
- `src/scrap_report/reporting.py`: parser e artefatos derivados
- `src/scrap_report/pipeline.py`: execucao unitaria de scrape + stage + reports
- `src/scrap_report/sweep.py`: planejamento, runner e presets de lote
- `src/scrap_report/cli.py`: comandos operacionais

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
### Fluxos com export e conteudo validado
- `pendentes`
- `executadas`
- `pendentes_execucao`
- `consulta_ssa`
- `consulta_ssa_print`
- `derivadas_relacionadas`
- `aprovacao_cancelamento`
- `reprogramacoes`

### Fluxos estaveis com ausencia real de dados na rodada validada
- `aprovacao_emissao`

## Matriz atual de `data de emissao`

| report_kind | status | formatos validados na tela | motivo do bloqueio quando aplicavel |
| --- | --- | --- | --- |
| `executadas` | suportado | `YYYY-MM-DD` | |
| `pendentes` | suportado | `DD/MM/YYYY`, `YYYY-MM-DD`, `DDMMYYYY` | |
| `pendentes_execucao` | suportado | `DD/MM/YYYY`, `YYYY-MM-DD`, `DDMMYYYY` | |
| `consulta_ssa` | suportado | `DD/MM/YYYY`, `YYYY-MM-DD`, `DDMMYYYY` | |
| `consulta_ssa_print` | suportado | `DD/MM/YYYY` | pdf validado com `numero_ssa + data`; data errada gera sem resultados |
| `aprovacao_cancelamento` | suportado | `DD/MM/YYYY` | |
| `reprogramacoes` | suportado | `DD/MM/YYYY` | |
| `aprovacao_emissao` | bloqueado | nenhum liberado | filtro altera o resultado, mas a semantica do export ainda nao esta forte o bastante para liberar |
| `derivadas_relacionadas` | bloqueado | nenhum liberado | export instavel mesmo sem filtro de data |

Regra global de formato:
- `MM/DD/YYYY` e rejeitado cedo no runtime com erro explicito
- formatos aceitos pelo parser central:
  - `DD/MM/YYYY`
  - `DDMMYYYY`
  - `YYYY-MM-DD`

## Filtros de setor
O sistema suporta quatro modos logicos:
- apenas emissor
- apenas executor
- ambos
- nenhum

Tokens para nao filtrar um lado:
- `ALL`
- `*`
- vazio

Exemplos:
- apenas executor: `--setor MEL4 --setor-emissor ALL`
- apenas emissor: `--setor ALL --setor-emissor IEE3`
- ambos: `--setor MEL4 --setor-emissor IEE3`
- nenhum: `--setor ALL --setor-emissor ALL`

## Grupos de setores atuais
- principal: `IEE3`, `MEL4`, `MEL3`
- segundo_plano: `IEE1`, `IEE2`, `IEE4`
- terceiro_plano: `MEL1`, `MEL2`, `IEQ1`, `IEQ2`, `IEQ3`, `ILA1`, `ILA2`, `ILA3`
- prioritarios: uniao de `principal`, `segundo_plano` e `terceiro_plano`
- demais: reservado para preenchimento futuro

## Uso rapido no Windows
### 1. Launcher sem argumentos
```powershell
.\EXECUTAR_SCRAP_WINDOWS.cmd
```

### 2. Launcher PowerShell equivalente
```powershell
.\EXECUTAR_SCRAP_WINDOWS.ps1
```

### 3. Execucao unitaria com filtros explicitos
```powershell
.\EXECUTAR_SCRAP_WINDOWS.ps1 -Username "menon" -Setor "MEL4" -SetorEmissor "IEE3" -ReportKind pendentes
```

### 4. Execucao em lote com preset
```powershell
.\EXECUTAR_SCRAP_WINDOWS.ps1 -Username "menon" -Preset "principal_executor" -ReportKind pendentes
```

### 5. Execucao em lote com preset para os dois relatorios principais
```powershell
.\EXECUTAR_SCRAP_WINDOWS.ps1 -Username "menon" -Preset "principal_executor" -ReportKind both
```

## Presets de lote
Scopes disponiveis por grupo:
- `_emissor`
- `_executor`
- `_ambos`

Grupos disponiveis:
- `principal`
- `segundo_plano`
- `terceiro_plano`
- `prioritarios`
- `demais`

Exemplos validos:
- `principal_emissor`
- `principal_executor`
- `principal_ambos`
- `prioritarios_executor`
- `terceiro_plano_ambos`

Regra importante:
- `-Preset` nao pode ser combinado com `-Setor` nem `-SetorEmissor`

## CLI principal
### windows-flow unitario
```powershell
uv run --project . python -m scrap_report.cli windows-flow --username "menon" --setor MEL4 --setor-emissor IEE3 --report-kind pendentes --output-json staging/pipeline_pendentes.json
```

### sweep-run manual
```powershell
uv run --project . python -m scrap_report.cli sweep-run --username "menon" --report-kind pendentes --scope-mode executor --setores-executor MEL4 MEL3 --year-week-start 202608 --year-week-end 202612 --output-json staging/sweep_manual.json
```

### sweep-run com preset
```powershell
uv run --project . python -m scrap_report.cli sweep-run --username "menon" --report-kind pendentes --preset principal_executor --output-json staging/sweep_principal_executor.json
```

### pipeline report-only
```powershell
uv run --project . python -m scrap_report.cli pipeline --report-only --source-excel staging/pendentes_arquivo.xlsx --report-kind pendentes --staging-dir staging --output-json staging/pipeline_report_only.json
```

## Fluxo de segredo
- comandos com auth resolvem credencial antes da operacao
- ordem de resolucao:
  - `--prompt-password`
  - `--password`
  - secret store do OS
  - fallback DPAPI por usuario no Windows quando necessario
  - `SAM_PASSWORD` apenas em modo transicional permitido
- politica fail-closed mantida quando configurada

Provisionamento recomendado:
```powershell
uv run --project . python -m scrap_report.cli secret setup --username "menon" --secret-service scrap_report.sam
```

## Artefatos gerados
### Fluxo unitario xlsx
- bruto staged: `staging/*.xlsx`
- derivados: `staging/reports/*.xlsx`
- manifest json: caminho informado em `--output-json`

### Fluxo `consulta_ssa_print`
- pdf staged em `staging/*.pdf`
- `reports = {}` por desenho

### Fluxo `derivadas_relacionadas`
- xlsx bruto staged
- xlsx derivado normalizado
- estatisticas

## Ordenacao e preservacao de dados
- a ordem fonte do export SAM e preservada por padrao
- o sweep preserva a ordem de expansao do plano
- falha de um item em lote nao aborta os demais; o manifest final registra `ok`, `partial` ou `error`

## Integracao externa
- o contrato JSON inclui `schema_version`, `generated_at` e `producer`
- o `pipeline` e o `sweep-run` retornam caminhos dos artefatos gerados
- o manifest de lote consolida status por item, filtros aplicados e erros por item

## Limites conhecidos
- `data de emissao` no sweep ainda e parcial por `report_kind`
- `aprovacao_emissao` segue bloqueado por semantica fraca do export
- `derivadas_relacionadas` segue bloqueado por instabilidade de export
- `demais_*` existe como preset, mas hoje depende de preencher o grupo `demais`
- ainda faltam algumas telas adicionais do menu `Relatorios`

## Referencias operacionais
- `WINDOWS_AGENT_INSTRUCTIONS.md`: guia operacional Windows atual
- `HANDOFF.md`: snapshot de estado atual do branch
- `ROUND_STATUS.md`: historico recente por slice
- `RECOVERY_BACKLOG.md`: pendencias reais fora do slice atual
