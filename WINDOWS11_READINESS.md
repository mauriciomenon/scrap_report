# WINDOWS11_READINESS

## Objetivo
- preparar execucao segura em Windows 11 antes da validacao real em maquina alvo
- garantir backend de segredo funcional e fluxo CLI sem vazamento

## Pre-requisitos
1. Windows 11 atualizado
2. PowerShell 5.1+ ou PowerShell 7+
3. Python 3.11+
4. `uv` instalado
5. Modulo PowerShell `CredentialManager` instalado

## Setup do backend de segredo
1. verificar modulo:
```powershell
Get-Module -ListAvailable -Name CredentialManager
```
2. instalar modulo (se ausente):
```powershell
Install-Module CredentialManager -Scope CurrentUser -Force
```
3. validar backend:
```powershell
uv run --project . python -m scrap_report.cli secret test
```

## Fluxo minimo de segredo
1. gravar segredo:
```powershell
uv run --project . python -m scrap_report.cli secret set --username USER_EXEMPLO --password SENHA_EXEMPLO --secret-service scrap_report.sam
```
2. validar presenca/leitura sem expor valor:
```powershell
uv run --project . python -m scrap_report.cli secret get --username USER_EXEMPLO --secret-service scrap_report.sam
```

## Fluxo de smoke local
1. sync e gate tecnico:
```powershell
uv sync
uv run --project . python -m py_compile src/scrap_report/*.py tests/*.py
uv run --project . ruff check .
uv run --project . --with pytest python -m pytest -q tests/test_contract.py tests/test_cli.py tests/test_pipeline_offline.py tests/test_scraper_contract.py tests/test_file_ops.py tests/test_reporting.py
```
2. scanner de segredo:
```powershell
uv run --project . python -m scrap_report.cli scan-secrets --paths src tests README.md --output-json staging/scan_secrets.json
```
3. contrato:
```powershell
uv run --project . python -m scrap_report.cli validate-contract --output-json staging/contract_info.json
```

4. execucao automatizada opcional:
```powershell
powershell -ExecutionPolicy Bypass -File scripts/smoke_windows11.ps1
```

5. preservar a evidencia nesta copia do repo:
```powershell
Get-Content staging/smoke_evidence_windows11.json -Raw
```
- se o arquivo existir no host W11, copiar `staging/smoke_evidence_windows11.json` de volta para esta copia local do repo
- nao substituir por JSON manual ou aproximado; somente pelo artefato gerado pelo script oficial

## Criterios de aceite W11
1. `secret test` retorna `status: ok`
2. `secret get` retorna `secret_found: true` sem mostrar segredo
3. scanner com `findings_count: 0`
4. pytest focado verde
5. contrato JSON gerado com `schema_version`, `generated_at`, `producer`
6. comandos com auth (`scrape`, `pipeline`, `ingest-latest`) exibem aviso de seguranca em `stderr` sem quebrar JSON em `stdout`

## Evidencia esperada
1. saida dos comandos acima
2. arquivos:
  - `staging/scan_secrets.json`
  - `staging/contract_info.json`
  - `staging/smoke_evidence_windows11.json`
3. data/hora e versao de Python/uv
