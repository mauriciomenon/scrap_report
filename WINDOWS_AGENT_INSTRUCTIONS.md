# WINDOWS_AGENT_INSTRUCTIONS

## Current truth
- entrypoint oficial: `EXECUTAR_SCRAP_WINDOWS.ps1`
- launcher visual: `EXECUTAR_SCRAP_WINDOWS.cmd`
- alias legado: `scripts/main_windows.ps1`
- modo unitario: `windows-flow`
- modo lote: `sweep-run`
- branch alvo: `master`
- para recorte multi-setor do mesmo relatorio, o modo recomendado e um pedido unico com expansao automatica por setor
- existe uma camada REST sem Playwright para consultas diretas a `SAM_SMA_API`
- o `sweep-run` agora aceita `--runtime rest` para `pendentes`
- o caminho REST do sweep ja esta validado para:
  - um setor
  - varios setores
  - geral sem detalhamento
  - geral com detalhamento por `year_week`
  - geral com detalhamento por `emission_date` validado ate `42 dias`
- no runtime REST do sweep, `username` e `password` nao sao obrigatorios
- existe um comando dedicado para exportar a CA raiz do host REST:
  - `sam-api-cert`

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

### sweep-run com runtime REST
```powershell
uv run --project . python -m scrap_report.cli sweep-run --report-kind pendentes --scope-mode emissor --setores-emissor IEE3 --year-week-start 202608 --year-week-end 202612 --runtime rest --rest-ca-file tmp/itaipu_root_ca_v2.pem --output-json staging/sweep_rest_pendentes.json
```

### sweep-run REST com varios setores
```powershell
uv run --project . python -m scrap_report.cli sweep-run --report-kind pendentes --scope-mode emissor --setores-emissor IEE1 IEE3 --year-week-start 202608 --year-week-end 202612 --runtime rest --rest-ca-file tmp/itaipu_root_ca_v2.pem --output-json staging/sweep_rest_varios_setores.json
```

### sweep-run REST geral sem detalhamento
```powershell
uv run --project . python -m scrap_report.cli sweep-run --report-kind pendentes --scope-mode nenhum --runtime rest --rest-ca-file tmp/itaipu_root_ca_v2.pem --output-json staging/sweep_rest_geral_sem_detalhe.json
```

## Fluxos REST sem Playwright
Estes comandos sao independentes do launcher Windows principal:
- nao usam navegador
- nao fazem login
- nao usam `windows-flow`
- `sam-api` e `sam-api-flow` nao usam `sweep-run`
- `sweep-run --runtime rest` ja usa a mesma camada REST em um caso operacional concreto

### 1. Comando tecnico
```powershell
uv run --project . python -m scrap_report.cli sam-api --start-localization-code A000A000 --end-localization-code Z999Z999 --number-of-years 1 --executor-sector MAM1 --limit 20 --ca-file tmp/itaipu_root_ca_v2.pem --output-json tmp/sam_api_search.json
```

### 2. Comando opinativo
```powershell
uv run --project . python -m scrap_report.cli sam-api-flow --profile panorama --executor-sector MAM1 --number-of-years 1 --limit 20 --ca-file tmp/itaipu_root_ca_v2.pem --output-json tmp/sam_api_flow.json --output-csv tmp/sam_api_flow.csv --output-xlsx tmp/sam_api_flow.xlsx
```

### 3. Fluxo totalmente independente
```powershell
uv run --project . python -m scrap_report.cli sam-api-standalone --profile detail-lote --ssa-number 202602521 --ca-file tmp/itaipu_root_ca_v2.pem --output-dir tmp/sam_api_standalone --output-json tmp/sam_api_standalone_manifest.json
```

### 4. Exportar a CA raiz do host REST
```powershell
uv run --project . python -m scrap_report.cli sam-api-cert --output tmp/itaipu_root_ca_v2.pem --output-json tmp/sam_api_cert_v2.json
```

### O que sai no fluxo independente
- manifest JSON proprio
- `csv` de dados
- `xlsx` de dados
- `xlsx` de resumo

Contrato atual de `exports` na frente REST:
- compatibilidade mantida com:
  - `csv`
  - `xlsx`
- chaves canonicas para integracao com outro consumidor:
  - `data_csv`
  - `data_xlsx`
  - `summary_xlsx`, quando existir
  - `manifest_json`, quando houver saida JSON

Contrato do manifest de `sweep-run`:
- schema validado na saida final
- campos obrigatorios:
  - `status`
  - `report_kind`
  - `scope_mode`
  - `runtime_mode`
  - `item_count`
  - `success_count`
  - `failure_count`
  - `items`
  - `manifest_json`

Telemetria minima comum nos manifests REST:
- `runtime_mode`
- `telemetry.record_count`
- `telemetry.detail_count`
- `telemetry.without_detail_count`
- `manifest_json`

Isto agora vale para:
- `sam-api`
- `sam-api-flow`
- `sam-api-standalone`
- `sweep-run --runtime rest`

Aliases canonicos para artefatos Playwright e `report-from-excel`:
- legados mantidos:
  - `dados`
  - `estatisticas`
  - `relatorio_txt`
- aliases canonicos:
  - `data_xlsx`
  - `summary_xlsx`
  - `report_txt`

Descoberta automatica de contrato:
- `validate-contract` agora publica em JSON:
  - `contract.schemas`
  - `contract.exports.playwright_reports`
  - `contract.exports.rest_reports`
  - `contract.preferred_contracts`
  - `contract.minimum_fields_by_flow`

### Limites operacionais REST
- detalhe em lote usa chunking controlado acima de `500` SSAs por bloco
- o payload publica `detail_batch_chunked` quando esse caminho for usado
- SSAs repetidas agora sao deduplicadas antes do detalhamento
- o payload publica `ssa_numbers_deduped` quando a entrada repetida e reduzida
- a saida JSON segue registrando `warnings`, `verify_tls` e `timeout_seconds`
- o custo de detalhe continua linear por SSA unica, entao lote grande ainda exige criterio operacional
- o gargalo que continua aberto hoje e o modo geral com detalhamento amplo por `emission_date`
- janelas ate `42 dias` agora estao validadas no `sweep-run --runtime rest`
- acima disso, o risco remanescente passa a ser custo e latencia, nao falha funcional ja provada

### Certificado REST
- com verificacao TLS ligada, a falha real observada foi:
  - `CERTIFICATE_VERIFY_FAILED`
  - `self-signed certificate in certificate chain`
- o caminho recomendado agora e:
  1. exportar a CA raiz com `sam-api-cert`
  2. usar o PEM resultante em `--ca-file` ou `--rest-ca-file`
- isso ja foi validado em chamadas reais
- `--ignore-https-errors` continua existindo como fallback
- a mensagem operacional agora indica:
  - `forneca --ca-file ou use --ignore-https-errors quando permitido`
- com `--ca-file` ou `--rest-ca-file`, o payload passa a indicar:
  - `warnings=["custom_ca_file_configured"]`
  - `verify_tls=true`

## Observacoes operacionais
- o alias `scripts/main_windows.ps1` existe apenas para compatibilidade
- nao ha necessidade de instalar modulo extra para secret no Windows atual
- o launcher nao cria script novo para variacoes; lote e unitario passam pelo mesmo caminho oficial
- para panorama multi-setor, preferir pedido unico com varios setores em vez de repetir chamadas manuais
- para consulta REST direta, preferir `sam-api-flow` quando o objetivo for operacao e `sam-api-standalone` quando o objetivo for artefato independente
- `derivadas_relacionadas` nao deve ser tratada como fluxo geral estavel enquanto o export oficial continuar intermitente
- `aprovacao_emissao` nao deve anunciar `data de emissao` enquanto `Emitida Em` seguir pouco confiavel no export
