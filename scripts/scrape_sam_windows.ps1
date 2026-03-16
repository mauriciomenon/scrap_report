param(
    [string]$Username = "",
    [string]$Setor = "IEE3",
    [ValidateSet("pendentes", "executadas", "both")]
    [string]$ReportKind = "pendentes",
    [string]$BaseUrl = "https://osprd.itaipu/SAM_SMA/",
    [string]$OutputJson = "staging/pipeline_online_windows.json",
    [string]$SecretService = "scrap_report.sam",
    [switch]$Headed
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

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

$outputDir = Split-Path -Parent $OutputJson
if (-not $outputDir) {
    $outputDir = "."
}
New-Item -ItemType Directory -Path $outputDir -Force | Out-Null

function Invoke-WindowsFlow {
    param(
        [Parameter(Mandatory = $true)][string]$Kind,
        [Parameter(Mandatory = $true)][string]$OutFile
    )

    $args = @(
        "run", "--project", ".", "python", "-m", "scrap_report.cli", "windows-flow",
        "--username", $Username,
        "--setor", $Setor,
        "--report-kind", $Kind,
        "--base-url", $BaseUrl,
        "--secret-service", $SecretService,
        "--output-json", $OutFile
    )

    if ($Headed) {
        $args += "--headed"
    }

    Write-Host "[scrape_sam_windows] iniciando report_kind=$Kind"
    uv @args
    if ($LASTEXITCODE -ne 0) {
        throw "[scrape_sam_windows] falha no windows-flow para report_kind=$Kind (exit_code=$LASTEXITCODE)"
    }

    if (Test-Path $OutFile) {
        try {
            $result = Get-Content $OutFile -Raw | ConvertFrom-Json
            if ($result.status) {
                Write-Host "[scrape_sam_windows] status=$($result.status) report_kind=$Kind"
            }
            if ($result.staged_path) {
                Write-Host "[scrape_sam_windows] staged_path=$($result.staged_path)"
            }
        } catch {
            Write-Host "[scrape_sam_windows] aviso: json invalido em $OutFile"
        }
    }
}

if ($ReportKind -eq "both") {
    $baseName = [System.IO.Path]::GetFileNameWithoutExtension($OutputJson)
    $extension = [System.IO.Path]::GetExtension($OutputJson)
    if (-not $extension) {
        $extension = ".json"
    }
    $dirName = Split-Path -Parent $OutputJson
    if (-not $dirName) {
        $dirName = "."
    }

    $outPendentes = Join-Path $dirName ($baseName + "_pendentes" + $extension)
    $outExecutadas = Join-Path $dirName ($baseName + "_executadas" + $extension)

    Invoke-WindowsFlow -Kind "pendentes" -OutFile $outPendentes
    Invoke-WindowsFlow -Kind "executadas" -OutFile $outExecutadas

    Write-Host "[scrape_sam_windows] concluido both"
    Write-Host "[scrape_sam_windows] saidas:"
    Write-Host "  $outPendentes"
    Write-Host "  $outExecutadas"
    exit 0
}

Invoke-WindowsFlow -Kind $ReportKind -OutFile $OutputJson
Write-Host "[scrape_sam_windows] concluido com sucesso"
