param(
    [string]$SmokeUsername = $env:SMOKE_USERNAME,
    [switch]$PromptUsername,
    [switch]$SetupSecret,
    [string]$SecretService = "scrap_report.sam"
)

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

function Invoke-NetworkPrecheck {
    param(
        [string[]]$DnsHosts = @(
            "api.kluster.ai",
            "files.pythonhosted.org"
        )
    )

    Write-Host "[smoke] precheck: winsock and dns"

    $socket = $null
    try {
        $socket = [System.Net.Sockets.Socket]::new(
            [System.Net.Sockets.AddressFamily]::InterNetwork,
            [System.Net.Sockets.SocketType]::Stream,
            [System.Net.Sockets.ProtocolType]::Tcp
        )
    }
    catch {
        throw "[smoke] precheck failed: winsock socket init error: $($_.Exception.Message)"
    }
    finally {
        if ($null -ne $socket) {
            $socket.Dispose()
        }
    }

    foreach ($hostName in $DnsHosts) {
        try {
            $addresses = [System.Net.Dns]::GetHostAddresses($hostName)
            if (-not $addresses -or $addresses.Count -eq 0) {
                throw "empty dns answer"
            }
        }
        catch {
            throw "[smoke] precheck failed: dns resolve failed for ${hostName}: $($_.Exception.Message)"
        }
    }
}

function Read-RequiredJson {
    param(
        [Parameter(Mandatory = $true)][string]$Path,
        [Parameter(Mandatory = $true)][string]$Name
    )

    if (-not (Test-Path -LiteralPath $Path)) {
        throw "[smoke] step failed: $Name (missing file: $Path)"
    }
    $parsedJson = Get-Content -LiteralPath $Path -Raw | ConvertFrom-Json
    if ($parsedJson -is [System.Array]) {
        throw "[smoke] step failed: $Name (expected JSON object, got array root)"
    }
    return $parsedJson
}

function Assert-ExistingArtifact {
    param(
        [Parameter(Mandatory = $true)][string]$Path,
        [Parameter(Mandatory = $true)][string]$Name
    )

    if ([string]::IsNullOrWhiteSpace($Path) -or -not (Test-Path -LiteralPath $Path -PathType Leaf)) {
        throw "[smoke] step failed: $Name (missing artifact file: $Path)"
    }
}

function Assert-AvailableArtifacts {
    param(
        [Parameter(Mandatory = $true)]$Payload,
        [Parameter(Mandatory = $true)][string]$Name
    )

    if (-not ($Payload.PSObject.Properties.Name -contains "available_artifacts")) {
        return
    }
    foreach ($property in $Payload.available_artifacts.PSObject.Properties) {
        if ($property.Value -is [string]) {
            Assert-ExistingArtifact -Path $property.Value -Name "$Name available_artifacts.$($property.Name)"
            continue
        }
        if ($null -eq $property.Value) {
            continue
        }
        foreach ($nestedProperty in $property.Value.PSObject.Properties) {
            if ($nestedProperty.Value -is [string]) {
                Assert-ExistingArtifact -Path $nestedProperty.Value -Name "$Name available_artifacts.$($property.Name).$($nestedProperty.Name)"
            }
        }
    }
}

New-Item -ItemType Directory -Path staging -Force | Out-Null
New-Item -ItemType Directory -Path downloads -Force | Out-Null
$SmokeJsonOutputs = @(
    "staging/scan_secrets.json",
    "staging/contract_info.json",
    "staging/stage_result.json",
    "staging/pipeline_report_only.json",
    "staging/ingest_result.json",
    "staging/smoke_evidence_windows11.json"
)
foreach ($jsonPath in $SmokeJsonOutputs) {
    if (Test-Path -LiteralPath $jsonPath) {
        Remove-Item -LiteralPath $jsonPath -Force
    }
}

Invoke-NetworkPrecheck
Invoke-CheckedCommand -Name "uv sync" -Command { uv sync }

$ShouldSetupSecret = $SetupSecret.IsPresent
$setupSecretRaw = $env:SMOKE_SETUP_SECRET
if (-not $ShouldSetupSecret -and -not [string]::IsNullOrWhiteSpace($setupSecretRaw)) {
    $setupSecretValue = $setupSecretRaw.Trim()
    if ($setupSecretValue -in @("1", "true", "TRUE", "yes", "YES", "y", "Y", "on", "ON")) {
        $ShouldSetupSecret = $true
    }
}

if ($PromptUsername.IsPresent -or [string]::IsNullOrWhiteSpace($SmokeUsername)) {
    $inputUsername = Read-Host "smoke username"
    if (-not [string]::IsNullOrWhiteSpace($inputUsername)) {
        $SmokeUsername = $inputUsername.Trim()
    }
}

if ([string]::IsNullOrWhiteSpace($SmokeUsername)) {
    $SmokeUsername = "smoke_user"
}
if ($SmokeUsername -notmatch "^[A-Za-z0-9._-]+$") {
    throw "[smoke] invalid smoke username token: use only letters, numbers, dot, underscore, dash"
}
if ($SecretService -notmatch "^[A-Za-z0-9._:-]+$") {
    throw "[smoke] invalid secret service token: use only letters, numbers, dot, underscore, dash, colon"
}

if ($ShouldSetupSecret) {
    Invoke-CheckedCommand -Name "secret setup" -Command {
        uv run --project . python -m scrap_report.cli secret setup --username "$SmokeUsername" --secret-service "$SecretService"
    }
}

Invoke-CheckedCommand -Name "py_compile" -Command {
    uv run --project . python -m compileall -q src tests
}
Invoke-CheckedCommand -Name "ruff" -Command { uv run --project . ruff check . }
Invoke-CheckedCommand -Name "pytest" -Command {
    uv run --project . --with pytest python -m pytest -q tests/test_contract.py tests/test_cli.py tests/test_pipeline_offline.py tests/test_scraper_contract.py tests/test_file_ops.py tests/test_reporting.py
}

Invoke-CheckedCommand -Name "scan-secrets" -Command {
    uv run --project . python -m scrap_report.cli scan-secrets --paths src README.md --output-json staging/scan_secrets.json
}
Invoke-CheckedCommand -Name "validate-contract" -Command {
    uv run --project . python -m scrap_report.cli validate-contract --output-json staging/contract_info.json
}
Invoke-CheckedCommand -Name "secret test" -Command {
    uv run --project . python -m scrap_report.cli secret test
}
if ($ShouldSetupSecret) {
    Invoke-CheckedCommand -Name "secret get" -Command {
        uv run --project . python -m scrap_report.cli secret get --username "$SmokeUsername" --secret-service "$SecretService"
    }
}
else {
    Write-Host "[smoke] secret setup nao solicitado; ingest-latest usara senha transicional apenas no processo"
}

Invoke-CheckedCommand -Name "make sample xlsx" -Command {
    uv run --project . --with pandas python -c "import pandas as pd; pd.DataFrame({'Numero da SSA':['1']}).to_excel('downloads/Report.xlsx', index=False)"
}
Invoke-CheckedCommand -Name "stage" -Command {
    uv run --project . python -m scrap_report.cli stage --source downloads/Report.xlsx --staging-dir staging --report-kind pendentes --output-json staging/stage_result.json
}

$StageInfo = Read-RequiredJson -Path "staging/stage_result.json" -Name "stage output"
$LATEST_XLSX = $StageInfo.staged_path
if ([string]::IsNullOrWhiteSpace($LATEST_XLSX) -or -not (Test-Path -LiteralPath $LATEST_XLSX)) {
    throw "[smoke] step failed: pipeline report-only (invalid staged_path from stage output)"
}
Invoke-CheckedCommand -Name "pipeline report-only" -Command {
    uv run --project . python -m scrap_report.cli pipeline --setor IEE3 --report-kind pendentes --staging-dir staging --report-only --source-excel "$LATEST_XLSX" --output-json staging/pipeline_report_only.json
}

Copy-Item -Path "$LATEST_XLSX" -Destination downloads/Report_latest.xlsx -Force
if ($ShouldSetupSecret) {
    Invoke-CheckedCommand -Name "ingest-latest" -Command {
        uv run --project . python -m scrap_report.cli ingest-latest --setor IEE3 --report-kind pendentes --download-dir downloads --staging-dir staging --username "$SmokeUsername" --secret-service "$SecretService" --secure-required --output-json staging/ingest_result.json
    }
}
else {
    Invoke-CheckedCommand -Name "ingest-latest" -Command {
        $env:SAM_PASSWORD = [guid]::NewGuid().ToString("N")
        try {
            uv run --project . python -m scrap_report.cli ingest-latest --setor IEE3 --report-kind pendentes --download-dir downloads --staging-dir staging --username "$SmokeUsername" --allow-transitional-plaintext --output-json staging/ingest_result.json
        }
        finally {
            Remove-Item Env:SAM_PASSWORD -ErrorAction SilentlyContinue
        }
    }
}

$scan = Read-RequiredJson -Path "staging/scan_secrets.json" -Name "scan-secrets output"
$contract = Read-RequiredJson -Path "staging/contract_info.json" -Name "validate-contract output"
$stageResult = $StageInfo
$reportOnly = Read-RequiredJson -Path "staging/pipeline_report_only.json" -Name "pipeline report-only output"
$ingest = Read-RequiredJson -Path "staging/ingest_result.json" -Name "ingest-latest output"
foreach ($artifactPath in $SmokeJsonOutputs) {
    if ($artifactPath -eq "staging/smoke_evidence_windows11.json") {
        continue
    }
    Assert-ExistingArtifact -Path $artifactPath -Name "smoke evidence input"
}
Assert-AvailableArtifacts -Payload $stageResult -Name "stage output"
Assert-AvailableArtifacts -Payload $reportOnly -Name "pipeline report-only output"
Assert-AvailableArtifacts -Payload $ingest -Name "ingest-latest output"

$evidence = [ordered]@{
  platform_label = "windows11_real"
  generated_at_utc = (Get-Date).ToUniversalTime().ToString("o")
  host = $env:COMPUTERNAME
  inputs = [ordered]@{
    smoke_username = $SmokeUsername
    secret_service = $SecretService
    setup_secret = $ShouldSetupSecret
  }
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
