$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

function Invoke-CheckedCommand {
    param(
        [Parameter(Mandatory = $true)][string]$Name,
        [Parameter(Mandatory = $true)][scriptblock]$Command
    )

    & $Command
    if ($LASTEXITCODE -ne 0) {
        throw "[smoke] step failed: $Name (exit_code=$LASTEXITCODE)"
    }
}

New-Item -ItemType Directory -Path staging -Force | Out-Null
New-Item -ItemType Directory -Path downloads -Force | Out-Null

Invoke-CheckedCommand -Name "uv sync" -Command { uv sync }

$pyFiles = @(
    (Get-ChildItem -Path src/scrap_report -Filter *.py).FullName +
    (Get-ChildItem -Path tests -Filter *.py).FullName
)
Invoke-CheckedCommand -Name "py_compile" -Command { uv run --project . python -m py_compile $pyFiles }
Invoke-CheckedCommand -Name "ruff" -Command { uv run --project . ruff check . }
Invoke-CheckedCommand -Name "pytest" -Command {
    uv run --project . --with pytest python -m pytest -q tests/test_contract.py tests/test_cli.py tests/test_pipeline_offline.py tests/test_scraper_contract.py tests/test_file_ops.py tests/test_reporting.py
}

Invoke-CheckedCommand -Name "scan-secrets" -Command {
    uv run --project . python -m scrap_report.cli scan-secrets --paths src tests README.md --output-json staging/scan_secrets.json
}
Invoke-CheckedCommand -Name "validate-contract" -Command {
    uv run --project . python -m scrap_report.cli validate-contract --output-json staging/contract_info.json
}
Invoke-CheckedCommand -Name "secret test" -Command {
    uv run --project . python -m scrap_report.cli secret test
}

Invoke-CheckedCommand -Name "make sample xlsx" -Command {
    uv run --project . --with pandas python -c "import pandas as pd; pd.DataFrame({'Numero da SSA':['1']}).to_excel('downloads/Report.xlsx', index=False)"
}
Invoke-CheckedCommand -Name "stage" -Command {
    uv run --project . python -m scrap_report.cli stage --source downloads/Report.xlsx --staging-dir staging --report-kind pendentes --output-json staging/stage_result.json
}

$LATEST_XLSX = (Get-ChildItem staging -Filter *.xlsx | Sort-Object LastWriteTime -Descending | Select-Object -First 1).FullName
Invoke-CheckedCommand -Name "pipeline report-only" -Command {
    uv run --project . python -m scrap_report.cli pipeline --setor IEE3 --report-kind pendentes --staging-dir staging --report-only --source-excel "$LATEST_XLSX" --output-json staging/pipeline_report_only.json
}

Copy-Item -Path "$LATEST_XLSX" -Destination downloads/Report_latest.xlsx -Force
Invoke-CheckedCommand -Name "ingest-latest" -Command {
    uv run --project . python -m scrap_report.cli ingest-latest --setor IEE3 --report-kind pendentes --download-dir downloads --staging-dir staging --username local_user --password local_pass --output-json staging/ingest_result.json
}

$scan = Get-Content staging/scan_secrets.json -Raw | ConvertFrom-Json
$contract = Get-Content staging/contract_info.json -Raw | ConvertFrom-Json
$stageResult = Get-Content staging/stage_result.json -Raw | ConvertFrom-Json
$reportOnly = Get-Content staging/pipeline_report_only.json -Raw | ConvertFrom-Json
$ingest = Get-Content staging/ingest_result.json -Raw | ConvertFrom-Json

$evidence = [ordered]@{
  platform_label = "windows11_real"
  generated_at_utc = (Get-Date).ToUniversalTime().ToString("o")
  host = $env:COMPUTERNAME
  checks = [ordered]@{
    py_compile = "ok"
    ruff = "ok"
    pytest = "ok"
    scan_secrets = $scan.status
    validate_contract = $contract.status
    stage = $stageResult.status
    pipeline_report_only = $reportOnly.status
    ingest_latest = $ingest.status
  }
  artifacts = [ordered]@{
    scan_secrets_json = "staging/scan_secrets.json"
    contract_info_json = "staging/contract_info.json"
    stage_result_json = "staging/stage_result.json"
    pipeline_report_only_json = "staging/pipeline_report_only.json"
    ingest_result_json = "staging/ingest_result.json"
  }
}

$evidence | ConvertTo-Json -Depth 6 | Out-File -Encoding utf8 staging/smoke_evidence_windows11.json
Write-Host "[smoke] evidence written: staging/smoke_evidence_windows11.json"

Write-Host "smoke_windows11.ps1: done"
