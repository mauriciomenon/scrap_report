# ROUND_STATUS

## Sessao atual
- data: `2026-03-23`
- pasta: `C:\Users\mauri\git\scrap_report`
- branch: `master`
- baseline runtime no inicio desta rodada: `f5c41d7`
- runtime REST em edicao nesta rodada: concluido
- doc sync pendente nesta rodada: sim

## Snapshot executivo
- repo publico existente: sim
- branch operacional: `master`
- runtime Playwright principal: estavel no baseline anterior
- camada REST sem Playwright: entregue em tres niveis
- release mais recente conhecida antes desta rodada: `v0.1.7`

## Current truth do runtime
### Fluxo Playwright
- `numero_ssa` validado para:
  - `consulta_ssa`
  - `consulta_ssa_print`
  - `aprovacao_emissao`
- `data de emissao` validada para:
  - `executadas`
  - `pendentes`
  - `pendentes_execucao`
  - `consulta_ssa`
  - `consulta_ssa_print`
  - `aprovacao_cancelamento`
  - `reprogramacoes`
- `aprovacao_emissao` continua bloqueado para `data de emissao`
- `derivadas_relacionadas` continua bloqueado para `data de emissao`

### Fluxo REST sem Playwright
- nivel 1:
  - API interna reutilizavel em `sam_api.py`
- nivel 2:
  - comando opinativo `sam-api-flow`
- nivel 3:
  - fluxo totalmente independente `sam-api-standalone`
- trilha TLS operacional:
  - `sam-api-cert`
  - `--ca-file`
  - `--rest-ca-file`
- filtros REST atuais:
  - executor
  - emissor
  - localizacao
  - `year_week`
  - `emission_date`
  - lista de SSAs
- exportacao REST atual:
  - `json`
  - `csv`
  - `xlsx`
  - resumo `xlsx`
- o `sweep-run --runtime rest` para `pendentes` nao exige credencial

## Evidencia operacional rodada 2026-03-23
### Quality gates do slice REST atual
Comandos:
```powershell
uv run python -m py_compile src\scrap_report\sam_api.py src\scrap_report\cli.py src\scrap_report\sweep.py tests\test_sam_api.py tests\test_cli.py tests\test_sweep.py
uv run ruff check src\scrap_report\sam_api.py src\scrap_report\cli.py src\scrap_report\sweep.py tests\test_sam_api.py tests\test_cli.py tests\test_sweep.py
uv run ty check src
uv run pytest -q tests\test_sam_api.py tests\test_cli.py tests\test_sweep.py tests\test_reporting.py tests\test_contract.py
```

Resultados:
- `py_compile`: ok
- `ruff`: ok
- `ty`: ok
- `pytest`: `113 passed`

### Exportacao real da CA raiz REST
Comando:
```powershell
uv run --python 3.13 python -m scrap_report.cli sam-api-cert --output tmp/itaipu_root_ca_v2.pem --output-json tmp/sam_api_cert_v2.json
```

Resultado:
- manifest: [tmp\sam_api_cert_v2.json](C:\Users\mauri\git\scrap_report\tmp\sam_api_cert_v2.json)
- `status=ok`
- `subject=CN=Itaipu Binacional Root CA 3`
- `issuer=CN=Itaipu Binacional Root CA 3`
- `certificate_count=2`

### TLS estrito validado com `--ca-file`
Comando:
```powershell
uv run --python 3.13 python -m scrap_report.cli sam-api --ssa-number 202602521 --ca-file tmp/itaipu_root_ca_v2.pem --output-json tmp/sam_api_ca_detail_relative_v2.json
```

Resultado:
- manifest: [tmp\sam_api_ca_detail_relative_v2.json](C:\Users\mauri\git\scrap_report\tmp\sam_api_ca_detail_relative_v2.json)
- `status=ok`
- `verify_tls=true`
- `warnings=["custom_ca_file_configured"]`
- `count=1`

### Fluxo independente detalhado com `--ca-file`
Comando:
```powershell
uv run --python 3.13 python -m scrap_report.cli sam-api-standalone --profile detail-lote --ssa-number 202602521 --ssa-number 202600001 --ca-file C:/Users/mauri/git/scrap_report/tmp/itaipu_root_ca_v2.pem --output-dir tmp/sam_api_detail_ca_v3 --output-json tmp/sam_api_detail_ca_v3.json
```

Resultado:
- manifest: [tmp\sam_api_detail_ca_v3.json](C:\Users\mauri\git\scrap_report\tmp\sam_api_detail_ca_v3.json)
- `status=ok`
- `verify_tls=true`
- `count=2`

### `sweep-run` REST sem credencial, um setor
Comando:
```powershell
uv run --python 3.13 python -m scrap_report.cli sweep-run --report-kind pendentes --scope-mode emissor --setores-emissor IEE3 --year-week-start 202608 --year-week-end 202612 --runtime rest --rest-ca-file C:/Users/mauri/git/scrap_report/tmp/itaipu_root_ca_v2.pem --output-json tmp/sweep_rest_one_ca_v3.json
```

Resultado:
- manifest: [tmp\sweep_rest_one_ca_v3.json](C:\Users\mauri\git\scrap_report\tmp\sweep_rest_one_ca_v3.json)
- `status=ok`
- `runtime_mode=rest`
- `item_count=1`
- `success_count=1`

### `sweep-run` REST sem credencial, varios setores
Comando:
```powershell
uv run --python 3.13 python -m scrap_report.cli sweep-run --report-kind pendentes --scope-mode emissor --setores-emissor IEE1 IEE3 --year-week-start 202608 --year-week-end 202612 --runtime rest --rest-ca-file C:/Users/mauri/git/scrap_report/tmp/itaipu_root_ca_v2.pem --output-json tmp/sweep_rest_multi_ca_v3.json
```

Resultado:
- manifest: [tmp\sweep_rest_multi_ca_v3.json](C:\Users\mauri\git\scrap_report\tmp\sweep_rest_multi_ca_v3.json)
- `status=ok`
- `item_count=2`
- `success_count=2`

### `sweep-run` REST sem credencial, geral sem detalhamento
Comando:
```powershell
uv run --python 3.13 python -m scrap_report.cli sweep-run --report-kind pendentes --scope-mode nenhum --runtime rest --rest-ca-file tmp/itaipu_root_ca_v2.pem --output-json tmp/sweep_rest_all_ca_relative_v2.json
```

Resultado:
- manifest: [tmp\sweep_rest_all_ca_relative_v2.json](C:\Users\mauri\git\scrap_report\tmp\sweep_rest_all_ca_relative_v2.json)
- `status=ok`
- `item_count=1`
- `success_count=1`
- item unico:
  - `record_count=6262`
  - `detail_count=0`
  - `without_detail_count=6262`

### `sweep-run` REST sem credencial, geral com detalhamento por `year_week`
Comando:
```powershell
uv run --python 3.13 python -m scrap_report.cli sweep-run --report-kind pendentes --scope-mode nenhum --year-week-start 202608 --year-week-end 202612 --runtime rest --rest-ca-file tmp/itaipu_root_ca_v2.pem --output-json tmp/sweep_rest_all_yearweek_ca_v4.json
```

Resultado:
- manifest: [tmp\sweep_rest_all_yearweek_ca_v4.json](C:\Users\mauri\git\scrap_report\tmp\sweep_rest_all_yearweek_ca_v4.json)
- `status=ok`
- `item_count=1`
- `success_count=1`
- item unico:
  - `record_count=1193`
  - `detail_count=1193`
  - `without_detail_count=0`
- observacao:
  - o wrapper do terminal marcou timeout, mas o processo concluiu e gravou manifest e artefatos validos

### `sweep-run` REST sem credencial, geral com detalhamento por `emission_date`, 1 dia
Comando:
```powershell
uv run --python 3.13 python -m scrap_report.cli sweep-run --report-kind pendentes --scope-mode nenhum --emission-date-start 2026-02-23 --emission-date-end 2026-02-23 --runtime rest --rest-ca-file tmp/itaipu_root_ca_v2.pem --output-json tmp/sweep_rest_all_emission_date_day_v3.json
```

Resultado:
- manifest: [tmp\sweep_rest_all_emission_date_day_v3.json](C:\Users\mauri\git\scrap_report\tmp\sweep_rest_all_emission_date_day_v3.json)
- `status=ok`
- `item_count=1`
- `success_count=1`
- item unico:
  - `record_count=41`
  - `detail_count=41`
  - `without_detail_count=0`

### `sweep-run` REST sem credencial, geral com detalhamento por `emission_date`, 3 dias
Comando:
```powershell
uv run --python 3.13 python -m scrap_report.cli sweep-run --report-kind pendentes --scope-mode nenhum --emission-date-start 2026-02-23 --emission-date-end 2026-02-25 --runtime rest --rest-ca-file tmp/itaipu_root_ca_v2.pem --output-json tmp/sweep_rest_all_emission_date_range_v3.json
```

Resultado:
- manifest: [tmp\sweep_rest_all_emission_date_range_v3.json](C:\Users\mauri\git\scrap_report\tmp\sweep_rest_all_emission_date_range_v3.json)
- `status=ok`
- `item_count=1`
- `success_count=1`
- item unico:
  - `record_count=109`
  - `detail_count=109`
  - `without_detail_count=0`

### `sweep-run` REST sem credencial, geral com detalhamento por `emission_date`, 7 dias
Comando:
```powershell
uv run --python 3.13 python -m scrap_report.cli sweep-run --report-kind pendentes --scope-mode nenhum --emission-date-start 2026-02-23 --emission-date-end 2026-03-01 --runtime rest --rest-ca-file tmp/itaipu_root_ca_v2.pem --output-json tmp/sweep_rest_all_emission_date_week_v1.json
```

Resultado:
- manifest: [tmp\sweep_rest_all_emission_date_week_v1.json](C:\Users\mauri\git\scrap_report\tmp\sweep_rest_all_emission_date_week_v1.json)
- `status=ok`
- `item_count=1`
- `success_count=1`
- item unico:
  - `record_count=240`
  - `detail_count=240`
  - `without_detail_count=0`

### `sweep-run` REST sem credencial, geral com detalhamento por `emission_date`, 14 dias
Comando:
```powershell
uv run --python 3.13 python -m scrap_report.cli sweep-run --report-kind pendentes --scope-mode nenhum --emission-date-start 2026-02-23 --emission-date-end 2026-03-08 --runtime rest --rest-ca-file tmp/itaipu_root_ca_v2.pem --output-json tmp/sweep_rest_all_emission_date_14d_v1.json
```

Resultado:
- manifest: [tmp\sweep_rest_all_emission_date_14d_v1.json](C:\Users\mauri\git\scrap_report\tmp\sweep_rest_all_emission_date_14d_v1.json)
- `status=ok`
- `item_count=1`
- `success_count=1`
- item unico:
  - `record_count=494`
  - `detail_count=494`
  - `without_detail_count=0`
- observacao:
  - o wrapper do terminal marcou timeout, mas o processo concluiu e gravou manifest e artefatos validos

### `sweep-run` REST sem credencial, geral com detalhamento por `emission_date`, 21 dias
Comando:
```powershell
uv run --python 3.13 python -m scrap_report.cli sweep-run --report-kind pendentes --scope-mode nenhum --emission-date-start 2026-02-23 --emission-date-end 2026-03-15 --runtime rest --rest-ca-file tmp/itaipu_root_ca_v2.pem --output-json tmp/sweep_rest_all_emission_date_21d_v1.json
```

Resultado:
- manifest: [tmp\sweep_rest_all_emission_date_21d_v1.json](C:\Users\mauri\git\scrap_report\tmp\sweep_rest_all_emission_date_21d_v1.json)
- `status=ok`
- `item_count=1`
- `success_count=1`
- item unico:
  - `record_count=730`
  - `detail_count=730`
  - `without_detail_count=0`
- observacao:
  - concluiu dentro de timeout de shell maior

### `sweep-run` REST sem credencial, geral com detalhamento por `emission_date`, 28 dias
Comando:
```powershell
uv run --python 3.13 python -m scrap_report.cli sweep-run --report-kind pendentes --scope-mode nenhum --emission-date-start 2026-02-23 --emission-date-end 2026-03-22 --runtime rest --rest-ca-file tmp/itaipu_root_ca_v2.pem --output-json tmp/sweep_rest_all_emission_date_28d_v1.json
```

Resultado:
- manifest: [tmp\sweep_rest_all_emission_date_28d_v1.json](C:\Users\mauri\git\scrap_report\tmp\sweep_rest_all_emission_date_28d_v1.json)
- `status=ok`
- `item_count=1`
- `success_count=1`
- item unico:
  - `record_count=1103`
  - `detail_count=1103`
  - `without_detail_count=0`
- observacao:
  - concluiu dentro de timeout de shell maior

### `sweep-run` REST sem credencial, geral com detalhamento por `emission_date`, 35 dias
Comando:
```powershell
uv run --python 3.13 python -m scrap_report.cli sweep-run --report-kind pendentes --scope-mode nenhum --emission-date-start 2026-02-23 --emission-date-end 2026-03-29 --runtime rest --rest-ca-file tmp/itaipu_root_ca_v2.pem --output-json tmp/sweep_rest_all_emission_date_35d_v1.json
```

Resultado:
- manifest: [tmp\sweep_rest_all_emission_date_35d_v1.json](C:\Users\mauri\git\scrap_report\tmp\sweep_rest_all_emission_date_35d_v1.json)
- `status=ok`
- `item_count=1`
- `success_count=1`
- item unico:
  - `record_count=1205`
  - `detail_count=1205`
  - `without_detail_count=0`
- observacao:
  - concluiu dentro de timeout de shell maior

### `sweep-run` REST sem credencial, geral com detalhamento por `emission_date`, 42 dias
Comando:
```powershell
uv run --python 3.13 python -m scrap_report.cli sweep-run --report-kind pendentes --scope-mode nenhum --emission-date-start 2026-02-23 --emission-date-end 2026-04-05 --runtime rest --rest-ca-file tmp/itaipu_root_ca_v2.pem --output-json tmp/sweep_rest_all_emission_date_42d_v1.json
```

Resultado:
- manifest: [tmp\sweep_rest_all_emission_date_42d_v1.json](C:\Users\mauri\git\scrap_report\tmp\sweep_rest_all_emission_date_42d_v1.json)
- `status=ok`
- `item_count=1`
- `success_count=1`
- item unico:
  - `record_count=1205`
  - `detail_count=1205`
  - `without_detail_count=0`
- observacao:
  - concluiu dentro de timeout de shell maior

### Demonstrativo REST, panorama de SSAs pendentes para `IEE3`
Comando:
```powershell
uv run --python 3.13 python -m scrap_report.cli sam-api-flow --profile panorama --emitter-sector IEE3 --number-of-years 1 --ca-file tmp/itaipu_root_ca_v2.pem --output-json tmp/sam_api_iee3_pendentes_demo.json --output-csv tmp/sam_api_iee3_pendentes_demo.csv --output-xlsx tmp/sam_api_iee3_pendentes_demo.xlsx
```

Resultado:
- manifest: [tmp\sam_api_iee3_pendentes_demo.json](C:\Users\mauri\git\scrap_report\tmp\sam_api_iee3_pendentes_demo.json)
- `status=ok`
- `count=39`
- `summary.by_emitter={"IEE3": 39}`
- `summary.by_executor={"IMA0": 1, "MEL3": 8, "MEL4": 30}`
- exemplos de SSA:
  - `202601024`
  - `202601253`
  - `202601438`
  - `202602000`
  - `202602187`
- exportacoes:
  - [tmp\sam_api_iee3_pendentes_demo.csv](C:\Users\mauri\git\scrap_report\tmp\sam_api_iee3_pendentes_demo.csv)
  - [tmp\sam_api_iee3_pendentes_demo.xlsx](C:\Users\mauri\git\scrap_report\tmp\sam_api_iee3_pendentes_demo.xlsx)

### Demonstrativo REST, detalhe em lote de amostra da `IEE3`
Comando:
```powershell
uv run --python 3.13 python -m scrap_report.cli sam-api-standalone --profile detail-lote --ca-file tmp/itaipu_root_ca_v2.pem --output-dir tmp/sam_api_iee3_detail_demo --output-json tmp/sam_api_iee3_detail_demo.json --ssa-number 202601024 --ssa-number 202601253 --ssa-number 202601438 --ssa-number 202602000 --ssa-number 202602187
```

Resultado:
- manifest: [tmp\sam_api_iee3_detail_demo.json](C:\Users\mauri\git\scrap_report\tmp\sam_api_iee3_detail_demo.json)
- `status=ok`
- `count=5`
- `summary.by_emitter={"IEE3": 5}`
- `summary.by_executor={"IMA0": 1, "MEL4": 4}`
- exportacoes:
  - [sam_api_detail-lote_dados_20260323_163945_358349.csv](C:\Users\mauri\git\scrap_report\tmp\sam_api_iee3_detail_demo\sam_api_detail-lote_dados_20260323_163945_358349.csv)
  - [sam_api_detail-lote_dados_20260323_163945_358349.xlsx](C:\Users\mauri\git\scrap_report\tmp\sam_api_iee3_detail_demo\sam_api_detail-lote_dados_20260323_163945_358349.xlsx)
  - [sam_api_detail-lote_resumo_20260323_163945_358349.xlsx](C:\Users\mauri\git\scrap_report\tmp\sam_api_iee3_detail_demo\sam_api_detail-lote_resumo_20260323_163945_358349.xlsx)

### Padronizacao de `exports` para futura juncao com repo de reports
Mudanca:
- `sam-api` e `sam-api-flow` agora expõem tanto:
  - `csv` / `xlsx`
  - quanto `data_csv` / `data_xlsx`
- quando ha `output_json`, o payload passa a registrar tambem:
  - `manifest_json`
- o `sam-api-standalone` e o `sweep-run --runtime rest` passam a expor os aliases legados junto das chaves canonicas

Smoke real:
```powershell
uv run --python 3.13 python -m scrap_report.cli sam-api-flow --profile panorama --emitter-sector IEE3 --number-of-years 1 --ca-file tmp/itaipu_root_ca_v2.pem --output-json tmp/sam_api_iee3_contract_demo_v2.json --output-csv tmp/sam_api_iee3_contract_demo_v2.csv --output-xlsx tmp/sam_api_iee3_contract_demo_v2.xlsx
uv run --python 3.13 python -m scrap_report.cli sweep-run --report-kind pendentes --scope-mode emissor --setores-emissor IEE3 --year-week-start 202608 --year-week-end 202612 --runtime rest --rest-ca-file tmp/itaipu_root_ca_v2.pem --output-json tmp/sweep_rest_iee3_contract_v1.json
```

Resultado:
- [tmp\sam_api_iee3_contract_demo_v2.json](C:\Users\mauri\git\scrap_report\tmp\sam_api_iee3_contract_demo_v2.json)
  - `exports.csv`
  - `exports.xlsx`
  - `exports.data_csv`
  - `exports.data_xlsx`
  - `exports.manifest_json`
- [tmp\sweep_rest_iee3_contract_v1.json](C:\Users\mauri\git\scrap_report\tmp\sweep_rest_iee3_contract_v1.json)
  - `items[0].reports.csv`
  - `items[0].reports.xlsx`
  - `items[0].reports.data_csv`
  - `items[0].reports.data_xlsx`
  - `items[0].reports.summary_xlsx`

### Correcao de bug no `emission_date` do sweep REST
- o `sweep-run --runtime rest` falhava cedo ao inferir `number_of_years` quando `emission_date` vinha em `YYYY-MM-DD`
- causa real:
  - extracao de ano com `[-4:]` em string ISO
- status:
  - corrigido nesta rodada
  - coberto por teste focado

### Exploracao de endpoint REST para outros `report_kind`
Comandos tentados:
- `GetExecutedSSAsByLocalizationRange`
- `GetExecutedSSAs`
- `GetPendingExecutionSSAsByLocalizationRange`
- `GetSSAsPendingExecutionByLocalizationRange`

Resultado:
- todos retornaram `HTTP 404`
- conclusao operacional:
  - a API REST atualmente comprovada continua sendo:
    - consulta geral de pendentes
    - detalhe por numero de SSA

### Nivel 1, API interna
Comando:
```powershell
uv run --python 3.13 python -
```

Fluxo:
- `SAMApiClient`
- `query_sam_api_records(...)`
- `executor_sectors=("MAM1",)`
- `limit=2`

Resultado:
- `mode=search`
- `count=2`
- primeiro item:
  - `ssa_number=202600001`
  - `executor_sector=MAM1`
  - `emitter_sector=OUO6`

### Nivel 2, comando opinativo
Comando:
```powershell
uv run --python 3.13 python -m scrap_report.cli sam-api-flow --profile panorama --start-localization-code A000A000 --end-localization-code Z999Z999 --number-of-years 1 --executor-sector MAM1 --limit 2 --ignore-https-errors --output-json tmp/sam_api_flow_real_v2.json --output-csv tmp/sam_api_flow_real_v2.csv --output-xlsx tmp/sam_api_flow_real_v2.xlsx
```

Resultado:
- manifest: [tmp\sam_api_flow_real_v2.json](C:\Users\mauri\git\scrap_report\tmp\sam_api_flow_real_v2.json)
- `status=ok`
- `profile=panorama`
- `mode=search`
- `count=2`
- `verify_tls=false`
- `warnings=["tls_verification_disabled"]`
- exportacoes:
  - [tmp\sam_api_flow_real_v2.csv](C:\Users\mauri\git\scrap_report\tmp\sam_api_flow_real_v2.csv)
  - [tmp\sam_api_flow_real_v2.xlsx](C:\Users\mauri\git\scrap_report\tmp\sam_api_flow_real_v2.xlsx)

### Nivel 3, fluxo independente
Comando:
```powershell
uv run --python 3.13 python -m scrap_report.cli sam-api-standalone --profile detail-lote --ssa-number 202602521 --ignore-https-errors --output-dir tmp/sam_api_standalone_real_v2 --output-json tmp/sam_api_standalone_manifest_v2.json
```

Resultado:
- manifest: [tmp\sam_api_standalone_manifest_v2.json](C:\Users\mauri\git\scrap_report\tmp\sam_api_standalone_manifest_v2.json)
- `status=ok`
- `profile=detail-lote`
- `mode=detail`
- `count=1`
- `verify_tls=false`
- `warnings=["tls_verification_disabled"]`
- artefatos:
  - [sam_api_detail-lote_dados_20260323_123504_358529.csv](C:\Users\mauri\git\scrap_report\tmp\sam_api_standalone_real_v2\sam_api_detail-lote_dados_20260323_123504_358529.csv)
  - [sam_api_detail-lote_dados_20260323_123504_358529.xlsx](C:\Users\mauri\git\scrap_report\tmp\sam_api_standalone_real_v2\sam_api_detail-lote_dados_20260323_123504_358529.xlsx)
  - [sam_api_detail-lote_resumo_20260323_123504_358529.xlsx](C:\Users\mauri\git\scrap_report\tmp\sam_api_standalone_real_v2\sam_api_detail-lote_resumo_20260323_123504_358529.xlsx)

### Mitigacoes novas nesta rodada
- detalhe em lote agora usa chunking controlado acima do limite por bloco
- o payload publica `detail_batch_chunked` quando a consulta passa desse limite
- SSAs repetidas agora sao deduplicadas antes do detalhamento
- o payload publica `ssa_numbers_deduped` quando a entrada repetida e reduzida
- o `sweep-run` agora aceita `--runtime rest` para `report_kind=pendentes`
- o runtime REST do sweep escreve artefatos em `staging/rest_sweep/...`
- o diagnostico de TLS ficou classificado por erro real de cadeia self-signed
- a mensagem de erro TLS agora aponta `--ca-file` ou `--ignore-https-errors`
- o payload REST agora inclui:
  - `filters`
  - `warnings`
  - `verify_tls`
  - `timeout_seconds`
- o schema JSON da REST foi endurecido para exigir esse contexto minimo

### Diagnostico TLS real
Comando:
```powershell
uv run --python 3.13 python -m scrap_report.cli sam-api --ssa-number 202602521 --output-json tmp/sam_api_tls_diag.json
```

Resultado:
- falha real com `verify_tls=true`
- erro:
  - `falha ao consultar GetSSABySSANumber: TLS nao confiavel (self-signed certificate in certificate chain); forneca --ca-file ou use --ignore-https-errors quando permitido`

### Chunking real em lote REST
Comando:
```powershell
uv run --python 3.13 python -m scrap_report.cli sam-api-standalone --profile detail-lote --ssa-number-file tmp/sam_api_chunk_input.txt --ignore-https-errors --output-dir tmp/sam_api_chunking_real --output-json tmp/sam_api_chunking_manifest.json
```

Resultado:
- manifest: [tmp\sam_api_chunking_manifest.json](C:\Users\mauri\git\scrap_report\tmp\sam_api_chunking_manifest.json)
- `status=ok`
- `warnings=["tls_verification_disabled", "detail_batch_chunked"]`
- artefatos:
  - [sam_api_detail-lote_dados_20260323_125657_039283.csv](C:\Users\mauri\git\scrap_report\tmp\sam_api_chunking_real\sam_api_detail-lote_dados_20260323_125657_039283.csv)
  - [sam_api_detail-lote_dados_20260323_125657_039283.xlsx](C:\Users\mauri\git\scrap_report\tmp\sam_api_chunking_real\sam_api_detail-lote_dados_20260323_125657_039283.xlsx)
  - [sam_api_detail-lote_resumo_20260323_125657_039283.xlsx](C:\Users\mauri\git\scrap_report\tmp\sam_api_chunking_real\sam_api_detail-lote_resumo_20260323_125657_039283.xlsx)

### Dedupe real em lote REST
Comando:
```powershell
uv run --python 3.13 python -m scrap_report.cli sam-api-standalone --profile detail-lote --ssa-number-file tmp/sam_api_dedupe_input_v2.txt --ignore-https-errors --output-dir tmp/sam_api_dedupe_real_v2 --output-json tmp/sam_api_dedupe_manifest_v2.json
```

Resultado:
- manifest: [tmp\sam_api_dedupe_manifest_v2.json](C:\Users\mauri\git\scrap_report\tmp\sam_api_dedupe_manifest_v2.json)
- `status=ok`
- `count=1`
- `warnings=["tls_verification_disabled", "ssa_numbers_deduped"]`
- `filters.ssa_numbers=["202602521"]`

### `sweep-run` com runtime REST
Comando:
```powershell
uv run --python 3.13 python -m scrap_report.cli sweep-run --username menon --report-kind pendentes --scope-mode emissor --setores-emissor IEE3 --year-week-start 202608 --year-week-end 202612 --runtime rest --ignore-https-errors --output-json tmp/sweep_rest_pendentes.json
```

Resultado:
- manifest: [tmp\sweep_rest_pendentes.json](C:\Users\mauri\git\scrap_report\tmp\sweep_rest_pendentes.json)
- `status=ok`
- `runtime_mode=rest`
- `item_count=1`
- `success_count=1`
- artefatos:
  - [pendentes_001_dados_20260323_125722_571938.csv](C:\Users\mauri\git\scrap_report\staging\rest_sweep\pendentes\item_001\pendentes_001_dados_20260323_125722_571938.csv)
  - [pendentes_001_dados_20260323_125722_571938.xlsx](C:\Users\mauri\git\scrap_report\staging\rest_sweep\pendentes\item_001\pendentes_001_dados_20260323_125722_571938.xlsx)
  - [pendentes_001_resumo_20260323_125722_571938.xlsx](C:\Users\mauri\git\scrap_report\staging\rest_sweep\pendentes\item_001\pendentes_001_resumo_20260323_125722_571938.xlsx)

### `sweep-run` REST com varios setores
Comando:
```powershell
uv run --python 3.13 python -m scrap_report.cli sweep-run --username menon --report-kind pendentes --scope-mode emissor --setores-emissor IEE1 IEE3 --year-week-start 202608 --year-week-end 202612 --runtime rest --ignore-https-errors --output-json tmp/sweep_rest_varios_setores_v2.json
```

Resultado:
- manifest: [tmp\sweep_rest_varios_setores_v2.json](C:\Users\mauri\git\scrap_report\tmp\sweep_rest_varios_setores_v2.json)
- `status=ok`
- `runtime_mode=rest`
- `item_count=2`
- `success_count=2`

### `sweep-run` REST geral sem detalhamento
Comando:
```powershell
uv run --python 3.13 python -m scrap_report.cli sweep-run --username menon --report-kind pendentes --scope-mode nenhum --runtime rest --ignore-https-errors --output-json tmp/sweep_rest_geral_sem_detalhe.json
```

Resultado:
- manifest: [tmp\sweep_rest_geral_sem_detalhe.json](C:\Users\mauri\git\scrap_report\tmp\sweep_rest_geral_sem_detalhe.json)
- `status=ok`
- `runtime_mode=rest`
- `item_count=1`
- `success_count=1`
- item unico:
  - `record_count=6284`
  - `detail_count=0`
  - `without_detail_count=6284`

### `sweep-run` REST geral com detalhamento temporal
Comando:
```powershell
uv run --python 3.13 python -m scrap_report.cli sweep-run --username menon --report-kind pendentes --scope-mode nenhum --year-week-start 202608 --year-week-end 202612 --runtime rest --ignore-https-errors --output-json tmp/sweep_rest_geral_v2.json
```

Resultado:
- nao ficou verde nesta rodada
- o wrapper do terminal estourou timeout com detalhamento amplo
- conclusao operacional:
  - geral simples: verde
  - geral com detalhamento temporal amplo: ainda caro e nao liberado como fluxo estavel

## Commits relevantes da frente REST
- `6129535` `STABILITY_PATCH: adicionar cliente sam api`
- `5511d49` `STABILITY_PATCH: ampliar integracao sam api`
- `81fb0c6` `STABILITY_PATCH: fechar niveis rest api`
- `f1c846a` `STABILITY_PATCH: endurecer operacao rest`
- `e9460c9` `STABILITY_PATCH: integrar rest ao sweep`
- `a3bddb9` `STABILITY_PATCH: otimizar rest detalhado`
- `f5c41d7` `STABILITY_PATCH: otimizar prefilter rest year week`
- `2f61345` `STABILITY_PATCH: ampliar emission date rest`

## Estado por camada
| camada | status | observacao |
| --- | --- | --- |
| Playwright unitario | verde | fluxo oficial mantido |
| Sweep multi-setor | verde | pedido unico por setor validado |
| REST nivel 1 | verde | API interna reutilizavel |
| REST nivel 2 | verde | `sam-api-flow` operacional |
| REST nivel 3 | verde | `sam-api-standalone` com manifest proprio |

## Risco residual
- a REST API nao depende mais exclusivamente de `--ignore-https-errors`; o caminho com CA exportada ficou validado
- o chunking removeu a falha seca, o dedupe removeu repeticao inutil e o cache por execucao evita reconsulta da mesma SSA, mas o custo de detalhe continua linear por SSA unica em lotes grandes
- o `sweep-run` REST ainda esta limitado a `report_kind=pendentes`
- `emission_date` geral agora esta verde ate 42 dias
- o modo geral com detalhamento amplo por `emission_date` continua caro para janelas acima de 42 dias

## Proximo passo natural
1. decidir se vale:
   - resolver confianca de certificado para a REST
   - reduzir custo linear do detalhe em lote
2. ou voltar para as pendencias do fluxo Playwright
