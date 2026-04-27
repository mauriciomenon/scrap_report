# CROSS_PLATFORM_SMOKE

## Objetivo
- validar portabilidade operacional do `scrap_report` em macOS, Debian 13 e Windows 11
- confirmar funcionamento do contrato JSON e dos comandos principais sem depender de scraping online

## Pre-requisitos
- Python 3.11+ instalado
- `uv` instalado
- workspace com acesso a `/Users/menon/git/scrap_report` (ou caminho equivalente na maquina alvo)

## Escopo do smoke
- `validate-contract`
- `scan-secrets`
- `secret test` (backend readiness)
- `stage`
- `pipeline --report-only`
- `ingest-latest` (com arquivo local em `downloads/`)

## Comandos copy/paste - Bash (macOS e Debian 13)
1. preparar ambiente
```bash
uv sync
```

observacao:
- `scripts/smoke_debian13.sh` agora executa preflight automatico de conectividade com `https://pypi.org/simple/wheel/` antes do `uv sync`
- se esse preflight falhar, tratar como bloqueio externo de rede/host, nao como falha do runtime do projeto

2. validacao tecnica minima
```bash
uv run --project . python -m py_compile src/scrap_report/*.py tests/*.py
uv run --project . ruff check .
uv run --project . --with pytest python -m pytest -q tests/test_contract.py tests/test_cli.py tests/test_pipeline_offline.py tests/test_scraper_contract.py tests/test_file_ops.py tests/test_reporting.py
```

3. validar contrato
```bash
mkdir -p staging
uv run --project . python -m scrap_report.cli validate-contract --output-json staging/contract_info.json
```

4. validar scanner de segredo
```bash
uv run --project . python -m scrap_report.cli scan-secrets --paths src tests README.md --output-json staging/scan_secrets.json
```

5. validar backend de segredo
```bash
uv run --project . python -m scrap_report.cli secret test
```

6. smoke `stage`
```bash
mkdir -p downloads staging
uv run --project . --with pandas python -c "import pandas as pd; pd.DataFrame({'Numero da SSA':['1']}).to_excel('downloads/Report.xlsx', index=False)"
uv run --project . python -m scrap_report.cli stage --source downloads/Report.xlsx --staging-dir staging --report-kind pendentes --output-json staging/stage_result.json
```

7. smoke `pipeline --report-only`
```bash
LATEST_XLSX="$(ls -1t staging/*.xlsx | head -1)"
uv run --project . python -m scrap_report.cli pipeline --setor IEE3 --report-kind pendentes --staging-dir staging --report-only --source-excel "$LATEST_XLSX" --output-json staging/pipeline_report_only.json
```

8. smoke `ingest-latest` (modo transicional default)
```bash
cp "$LATEST_XLSX" downloads/Report_latest.xlsx
SMOKE_TRANSITIONAL_PASSWORD="$(date +%s%N)"
SAM_PASSWORD="${SMOKE_TRANSITIONAL_PASSWORD}" uv run --project . python -m scrap_report.cli ingest-latest --setor IEE3 --report-kind pendentes --download-dir downloads --staging-dir staging --username local_user --allow-transitional-plaintext --output-json staging/ingest_result.json
```

8b. smoke `ingest-latest` (modo seguro com usuario valido salvo no cofre)
```bash
SMOKE_USERNAME="menon"
uv run --project . python -m scrap_report.cli secret setup --username "${SMOKE_USERNAME}" --secret-service scrap_report.sam
uv run --project . python -m scrap_report.cli secret get --username "${SMOKE_USERNAME}" --secret-service scrap_report.sam
cp "$LATEST_XLSX" downloads/Report_latest.xlsx
uv run --project . python -m scrap_report.cli ingest-latest --setor IEE3 --report-kind pendentes --download-dir downloads --staging-dir staging --username "${SMOKE_USERNAME}" --secret-service scrap_report.sam --secure-required --output-json staging/ingest_result.json
```

9. execucao automatizada opcional
```bash
bash scripts/smoke_debian13.sh
bash scripts/smoke_debian13.sh --smoke-username menon --setup-secret
bash scripts/smoke_debian13.sh --prompt-username --setup-secret
```
10. evidencia consolidada gerada automaticamente
```bash
cat staging/smoke_evidence_debian13.json
```

## Comandos copy/paste - PowerShell (Windows 11)
0. preparar backend de segredo (CredentialManager)
```powershell
Get-Module -ListAvailable -Name CredentialManager
Install-Module CredentialManager -Scope CurrentUser -Force
```

1. preparar ambiente
```powershell
uv sync
```

2. validacao tecnica minima
```powershell
uv run --project . python -m py_compile src/scrap_report/*.py tests/*.py
uv run --project . ruff check .
uv run --project . --with pytest python -m pytest -q tests/test_contract.py tests/test_cli.py tests/test_pipeline_offline.py tests/test_scraper_contract.py tests/test_file_ops.py tests/test_reporting.py
```

3. validar contrato
```powershell
New-Item -ItemType Directory -Path staging -Force | Out-Null
uv run --project . python -m scrap_report.cli validate-contract --output-json staging/contract_info.json
```

4. validar scanner de segredo
```powershell
uv run --project . python -m scrap_report.cli scan-secrets --paths src tests README.md --output-json staging/scan_secrets.json
```

5. validar backend de segredo
```powershell
uv run --project . python -m scrap_report.cli secret test
```

6. smoke `stage`
```powershell
New-Item -ItemType Directory -Path downloads -Force | Out-Null
New-Item -ItemType Directory -Path staging -Force | Out-Null
uv run --project . --with pandas python -c "import pandas as pd; pd.DataFrame({'Numero da SSA':['1']}).to_excel('downloads/Report.xlsx', index=False)"
uv run --project . python -m scrap_report.cli stage --source downloads/Report.xlsx --staging-dir staging --report-kind pendentes --output-json staging/stage_result.json
```

7. smoke `pipeline --report-only`
```powershell
$LATEST_XLSX = (Get-ChildItem staging -Filter *.xlsx | Sort-Object LastWriteTime -Descending | Select-Object -First 1).FullName
uv run --project . python -m scrap_report.cli pipeline --setor IEE3 --report-kind pendentes --staging-dir staging --report-only --source-excel "$LATEST_XLSX" --output-json staging/pipeline_report_only.json
```

8. smoke `ingest-latest` (modo transicional default)
```powershell
Copy-Item -Path "$LATEST_XLSX" -Destination downloads/Report_latest.xlsx -Force
$env:SAM_PASSWORD = [guid]::NewGuid().ToString("N")
uv run --project . python -m scrap_report.cli ingest-latest --setor IEE3 --report-kind pendentes --download-dir downloads --staging-dir staging --username local_user --allow-transitional-plaintext --output-json staging/ingest_result.json
Remove-Item Env:SAM_PASSWORD
```

8b. smoke `ingest-latest` (modo seguro com usuario valido salvo no cofre)
```powershell
$SMOKE_USERNAME = "menon"
uv run --project . python -m scrap_report.cli secret setup --username "$SMOKE_USERNAME" --secret-service scrap_report.sam
uv run --project . python -m scrap_report.cli secret get --username "$SMOKE_USERNAME" --secret-service scrap_report.sam
Copy-Item -Path "$LATEST_XLSX" -Destination downloads/Report_latest.xlsx -Force
uv run --project . python -m scrap_report.cli ingest-latest --setor IEE3 --report-kind pendentes --download-dir downloads --staging-dir staging --username "$SMOKE_USERNAME" --secret-service scrap_report.sam --secure-required --output-json staging/ingest_result.json
```

9. execucao automatizada opcional
```powershell
powershell -ExecutionPolicy Bypass -File scripts/smoke_windows11.ps1
powershell -ExecutionPolicy Bypass -File scripts/smoke_windows11.ps1 -SmokeUsername menon -SetupSecret
powershell -ExecutionPolicy Bypass -File scripts/smoke_windows11.ps1 -PromptUsername -SetupSecret
```
10. evidencia consolidada gerada automaticamente
```powershell
Get-Content staging/smoke_evidence_windows11.json -Raw
```

## Criterios de aceite por plataforma
- todos os comandos retornam exit code 0
- existe arquivo `staging/contract_info.json` com `schema_version`, `generated_at`, `producer`
- scanner de segredo com `status: ok` e `findings_count: 0`
- `ruff` sem erro
- pytest focado verde
- comandos CLI geram JSON valido com `status: ok`
- arquivo consolidado de evidencia existe:
  - Linux/macOS: `staging/smoke_evidence_debian13.json`
  - Windows11: `staging/smoke_evidence_windows11.json`

## Registro de evidencia

### macOS
- data/hora: `2026-03-15T16:54:28-0300`
- py_compile: ok (via script)
- ruff: ok
- pytest: ok (32 passed no roteiro do script)
- validate-contract: ok (`status: ok`)
- scan-secrets: ok (`status: ok`, `findings_count: 0`)
- secret test: ok (`backend_ready: true`)
- stage: ok (`status: ok`)
- pipeline --report-only: ok (`status: ok`, `telemetry` presente)
- ingest-latest: ok (`status: ok`, `telemetry` presente)
- observacoes:
  - aviso de seguranca de credencial apareceu em `stderr` no `ingest-latest`
  - `stdout` permaneceu JSON valido
  - execucao realizada em host local macOS

### Debian 13
- data/hora: `2026-04-27T16:09:19.826461+00:00`
- py_compile: ok
- ruff: ok
- pytest: ok (`108 passed` no smoke; `216 passed` na suite completa)
- validate-contract: ok (`status: ok`)
- scan-secrets: ok (`status: ok`, `findings_count: 0`)
- secret test: ok (`backend_ready: true`)
- stage: ok (`status: ok`)
- pipeline --report-only: ok (`status: ok`, `telemetry` presente)
- ingest-latest: ok (`status: ok`, `telemetry` presente)
- ty: ok
- package build: ok (`scrap_report-0.1.17-py3-none-any.whl` e `scrap_report-0.1.17.tar.gz`)
- evidencia:
  - `staging/smoke_evidence_debian13.json`
- observacoes:
  - validado em Debian GNU/Linux 13 (trixie) via VMware Fusion
  - executado como usuario `menon`, sem workspace de repo em `root`
  - preflight de PyPI ok (`HTTP 200`)
  - smoke Debian13 corrigido em `2b0b7bd` para usar `uv --with ruff` e nao depender de `ruff` preinstalado

### Windows 11
- data/hora: `2026-04-23T16:14:20.9295303Z`
- py_compile: ok
- ruff: ok
- pytest: ok (`108 passed`)
- validate-contract: ok (`status: ok`)
- scan-secrets: ok (`status: ok`, `findings_count: 0`)
- secret test: ok (`backend_ready: true`)
- stage: ok (`status: ok`)
- pipeline --report-only: ok (`status: ok`, `telemetry` presente)
- ingest-latest: ok (`status: ok`, `telemetry` presente)
- evidencia:
  - `staging/smoke_evidence_windows11.json`
- observacoes:
  - rodada historica W11 documentada
  - artefato `staging/smoke_evidence_windows11.json` ainda precisa ser regenerado ou recolocado nesta copia local

## Notas
- o E2E com acesso SAM nao faz parte deste smoke de portabilidade
- qualquer falha deve ser registrada com comando e erro completo
- detalhes de readiness W11: `WINDOWS11_READINESS.md`
- para envio de evidencia de maquina remota, compartilhar o arquivo `smoke_evidence_*.json` junto com logs de erro quando houver falha
