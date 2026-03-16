Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

param(
    [string]$Username = "",
    [string]$Setor = "IEE3",
    [ValidateSet("pendentes", "executadas")]
    [string]$ReportKind = "pendentes",
    [string]$BaseUrl = "https://osprd.itaipu/SAM_SMA/",
    [string]$OutputJson = "staging/pipeline_online_windows.json",
    [string]$SecretService = "scrap_report.sam",
    [switch]$Headed
)

$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    throw "uv nao encontrado no PATH"
}

if (-not $Username) {
    if ($env:SAM_USERNAME) {
        $Username = $env:SAM_USERNAME
    } else {
        $Username = Read-Host "username"
    }
}

if (-not $Username) {
    throw "username obrigatorio"
}

$args = @(
    "run", "--project", ".", "python", "-m", "scrap_report.cli", "windows-flow",
    "--username", $Username,
    "--setor", $Setor,
    "--report-kind", $ReportKind,
    "--base-url", $BaseUrl,
    "--secret-service", $SecretService,
    "--output-json", $OutputJson
)

if ($Headed) {
    $args += "--headed"
}

Write-Host "[main_windows] iniciando fluxo unico..."
Write-Host "[main_windows] usuario=$Username setor=$Setor report_kind=$ReportKind"
Write-Host "[main_windows] output_json=$OutputJson"

uv @args

if ($LASTEXITCODE -ne 0) {
    throw "[main_windows] falha no windows-flow (exit_code=$LASTEXITCODE)"
}

if (Test-Path $OutputJson) {
    try {
        $result = Get-Content $OutputJson -Raw | ConvertFrom-Json
        if ($result.status) {
            Write-Host "[main_windows] status=$($result.status)"
        }
        if ($result.source_path) {
            Write-Host "[main_windows] source_path=$($result.source_path)"
        }
        if ($result.staged_path) {
            Write-Host "[main_windows] staged_path=$($result.staged_path)"
        }
    } catch {
        Write-Host "[main_windows] aviso: nao foi possivel parsear output_json"
    }
}

Write-Host "[main_windows] concluido com sucesso"
