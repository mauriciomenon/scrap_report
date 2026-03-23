# WINDOWS_AGENT_INSTRUCTIONS

## Current truth
- entrypoint oficial: `EXECUTAR_SCRAP_WINDOWS.ps1`
- launcher visual: `EXECUTAR_SCRAP_WINDOWS.cmd`
- alias legado: `scripts/main_windows.ps1`
- modo unitario: `windows-flow`
- modo lote: `sweep-run`
- branch alvo: `master`
- para recorte multi-setor do mesmo relatorio, o modo recomendado e um pedido unico com expansao automatica por setor

## Uso mais simples
### 1. Sem argumentos
```powershell
.\EXECUTAR_SCRAP_WINDOWS.cmd
```

### 2. Mesmo fluxo em PowerShell
```powershell
.\EXECUTAR_SCRAP_WINDOWS.ps1
```

Comportamento padrao:
- pede `username` se necessario
- pede senha com mascara quando o secret ainda nao existir
- roda `both` por padrao
- gera dois JSONs:
  - `staging/pipeline_online_windows_pendentes.json`
  - `staging/pipeline_online_windows_executadas.json`

## Modo unitario com parametros
### 1. Ambos os filtros
```powershell
.\EXECUTAR_SCRAP_WINDOWS.ps1 -Username "menon" -Setor "MEL4" -SetorEmissor "IEE3" -ReportKind pendentes
```

### 2. Apenas executor
```powershell
.\EXECUTAR_SCRAP_WINDOWS.ps1 -Username "menon" -Setor "MEL4" -SetorEmissor "ALL" -ReportKind pendentes
```

### 3. Apenas emissor
```powershell
.\EXECUTAR_SCRAP_WINDOWS.ps1 -Username "menon" -Setor "ALL" -SetorEmissor "IEE3" -ReportKind pendentes
```

### 4. Sem filtro de setor
```powershell
.\EXECUTAR_SCRAP_WINDOWS.ps1 -Username "menon" -Setor "ALL" -SetorEmissor "ALL" -ReportKind pendentes
```

## Modo lote com preset
### 1. Um report kind
```powershell
.\EXECUTAR_SCRAP_WINDOWS.ps1 -Username "menon" -Preset "principal_executor" -ReportKind pendentes
```

### 2. `both` com preset
```powershell
.\EXECUTAR_SCRAP_WINDOWS.ps1 -Username "menon" -Preset "principal_executor" -ReportKind both
```

Saidas no caso `both` com preset:
- `staging/sweep_windows_pendentes.json`
- `staging/sweep_windows_executadas.json`

## Modo recomendado para varios setores no mesmo relatorio
Quando o objetivo for pedir, por exemplo, `IEE1 IEE2 IEE3 IEE4` para um mesmo relatorio:
- nao repetir o comando quatro vezes
- nao tentar montar um unico campo de tela com varios setores
- usar um pedido unico de lote com varios setores

Comportamento real validado:
- o sistema expande um item por setor
- gera um arquivo por setor
- devolve um unico manifest de controle

Relatorios validados neste modo:
- `pendentes`
- `executadas`
- `pendentes_execucao`
- `reprogramacoes`

Exemplo:
```powershell
uv run --project . python -m scrap_report.cli sweep-run --username "menon" --report-kind pendentes --scope-mode emissor --setores-emissor IEE1 IEE2 IEE3 IEE4 --ignore-https-errors --output-json staging/sweep_iee1_iee4_pendentes_eval.json
```

O que esperar:
- `item_count = 4`
- `success_count = 4` quando todos fecharem
- um staged por setor
- um derivado por setor
- um erro isolado por item se algum setor falhar

## Regras do modo preset
- `-Preset` usa `sweep-run` internamente
- `-Preset` nao pode ser combinado com `-Setor`
- `-Preset` nao pode ser combinado com `-SetorEmissor`
- `-ReportKind` continua obrigatorio no sentido operacional do launcher
- `-ReportKind both` no preset hoje expande para:
  - `pendentes`
  - `executadas`

## Presets disponiveis
### Grupo principal
- `principal_emissor`
- `principal_executor`
- `principal_ambos`

### Segundo plano
- `segundo_plano_emissor`
- `segundo_plano_executor`
- `segundo_plano_ambos`

### Terceiro plano
- `terceiro_plano_emissor`
- `terceiro_plano_executor`
- `terceiro_plano_ambos`

### Prioritarios
- `prioritarios_emissor`
- `prioritarios_executor`
- `prioritarios_ambos`

### Demais
- `demais_emissor`
- `demais_executor`
- `demais_ambos`

## Grupos de setores atuais
- principal: `IEE3`, `MEL4`, `MEL3`
- segundo_plano: `IEE1`, `IEE2`, `IEE4`
- terceiro_plano: `MEL1`, `MEL2`, `IEQ1`, `IEQ2`, `IEQ3`, `ILA1`, `ILA2`, `ILA3`
- prioritarios: uniao dos tres grupos acima
- demais: reservado para preenchimento futuro

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
- `both` apenas no wrapper PowerShell

## Estado validado em ambiente real
### Com conteudo validado
- `pendentes`
- `executadas`
- `pendentes_execucao`
- `consulta_ssa`
- `consulta_ssa_print`
- `aprovacao_emissao` baseline com `numero_ssa`
- `aprovacao_cancelamento`
- `reprogramacoes`

### Casos especiais explicitados
- `aprovacao_emissao`
  - `numero_ssa` validado
  - `setor_executor` e alias de runtime para `divisao_emissora`
  - `emission_date` segue bloqueado porque o export atual nao entrega `Emitida Em` confiavel
- `derivadas_relacionadas`
  - parser derivado proprio validado
  - export oficial segue instavel no fluxo Playwright

## Matriz atual de `data de emissao`
Suportado hoje no runtime:
- `executadas`
- `pendentes`
- `pendentes_execucao`
- `consulta_ssa`
- `consulta_ssa_print`
- `aprovacao_cancelamento`
- `reprogramacoes`

Bloqueado hoje no runtime:
- `aprovacao_emissao`
- `derivadas_relacionadas`

Filtros gerais adicionais validados:
- `numero_ssa`:
  - `consulta_ssa`
  - `consulta_ssa_print`
  - `aprovacao_emissao`

Formato aceito pelo parser:
- `DD/MM/YYYY`
- `DDMMYYYY`
- `YYYY-MM-DD`

Formato rejeitado cedo:
- `MM/DD/YYYY`

Exemplos unitarios validos:
```powershell
.\EXECUTAR_SCRAP_WINDOWS.ps1 -Username "menon" -Setor "ALL" -SetorEmissor "ALL" -ReportKind reprogramacoes
uv run --project . python -m scrap_report.cli sweep-run --username "menon" --report-kind consulta_ssa --scope-mode nenhum --numero-ssa 202602521 --emission-date-start 2026-02-23 --emission-date-end 2026-02-23 --ignore-https-errors --output-json staging/sweep_emission_date_consulta_ssa_20260223.json
```

## Janela temporal atual
- padrao operacional: semana atual ate 4 semanas para tras
- exemplo validado em `2026-03-16`: `202608 -> 202612`

## Certificado HTTPS
Padrao atual:
- launcher usa `ignore https errors`
- isso existe por causa do ambiente interno com cert nao confiavel no browser automatizado

Modo estrito:
```powershell
.\EXECUTAR_SCRAP_WINDOWS.ps1 -StrictCert
```

## Secret e credencial
Provisionamento recomendado:
```powershell
uv run --project . python -m scrap_report.cli secret setup --username "menon" --secret-service scrap_report.sam
```

Fluxo de resolucao:
- `--prompt-password`
- `--password`
- secret store do OS
- fallback DPAPI por usuario no Windows
- `SAM_PASSWORD` apenas em modo transicional permitido

## Artefatos gerados
### Unitario xlsx
- bruto staged em `staging\*.xlsx`
- derivados em `staging\reports\*.xlsx`
- JSON no caminho informado em `-OutputJson`

### `consulta_ssa_print`
- pdf staged em `staging\*.pdf`
- sem `reports` derivados

### Sweep por preset
- manifest JSON por execucao
- em `both`, um JSON por report kind

## Fluxos CLI equivalentes
### windows-flow unitario
```powershell
uv run --project . python -m scrap_report.cli windows-flow --username "menon" --setor MEL4 --setor-emissor IEE3 --report-kind pendentes --output-json staging/pipeline_pendentes.json
```

### sweep-run com preset
```powershell
uv run --project . python -m scrap_report.cli sweep-run --username "menon" --report-kind pendentes --preset principal_executor --output-json staging/sweep_principal_executor.json
```

## Observacoes operacionais
- o alias `scripts/main_windows.ps1` existe apenas para compatibilidade
- nao ha necessidade de instalar modulo extra para secret no Windows atual
- o launcher nao cria script novo para variacoes; lote e unitario passam pelo mesmo caminho oficial
- para panorama multi-setor, preferir pedido unico com varios setores em vez de repetir chamadas manuais
- `derivadas_relacionadas` nao deve ser tratada como fluxo geral estavel enquanto o export oficial continuar intermitente
- `aprovacao_emissao` nao deve anunciar `data de emissao` enquanto `Emitida Em` seguir pouco confiavel no export
