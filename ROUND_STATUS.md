# ROUND_STATUS

## Sessao atual
- data: `2026-03-23`
- pasta: `C:\Users\mauri\git\scrap_report`
- branch: `master`
- baseline runtime no inicio da sessao: `81fb0c6`
- runtime REST integrado ao sweep neste ciclo: `e9460c9`
- doc sync pendente neste ciclo: nao

## Snapshot executivo
- repo publico existente: sim
- branch operacional: `master`
- runtime Playwright principal: estavel no baseline anterior
- camada REST sem Playwright: entregue em tres niveis
- release mais recente conhecida antes deste ciclo: `v0.1.3`

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

## Evidencia operacional rodada 2026-03-23
### Quality gates do slice REST final
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
- `pytest`: `96 passed`

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
- o `sweep-run` agora aceita `--runtime rest` para `report_kind=pendentes`
- o runtime REST do sweep escreve artefatos em `staging/rest_sweep/...`
- o diagnostico de TLS ficou classificado por erro real de cadeia self-signed
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
  - `CERTIFICATE_VERIFY_FAILED`
  - `self-signed certificate in certificate chain`

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

## Commits relevantes da frente REST
- `6129535` `STABILITY_PATCH: adicionar cliente sam api`
- `5511d49` `STABILITY_PATCH: ampliar integracao sam api`
- `81fb0c6` `STABILITY_PATCH: fechar niveis rest api`
- `f1c846a` `STABILITY_PATCH: endurecer operacao rest`
- `e9460c9` `STABILITY_PATCH: integrar rest ao sweep`

## Estado por camada
| camada | status | observacao |
| --- | --- | --- |
| Playwright unitario | verde | fluxo oficial mantido |
| Sweep multi-setor | verde | pedido unico por setor validado |
| REST nivel 1 | verde | API interna reutilizavel |
| REST nivel 2 | verde | `sam-api-flow` operacional |
| REST nivel 3 | verde | `sam-api-standalone` com manifest proprio |

## Risco residual
- a REST API ainda depende de `--ignore-https-errors` no ambiente atual
- o chunking removeu o fail-fast, mas o custo de detalhe continua linear por SSA em lotes grandes
- o `sweep-run` REST ainda esta limitado a `report_kind=pendentes`

## Proximo passo natural
1. decidir se vale:
   - resolver confianca de certificado para a REST
   - reduzir custo linear do detalhe em lote
2. ou voltar para as pendencias do fluxo Playwright
