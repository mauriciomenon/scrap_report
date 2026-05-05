param(
    [string]$Username = "",
    [string]$Setor = "MEL4",
    [string]$SetorEmissor = "IEE3",
    [string]$Preset = "",
    [ValidateSet("pendentes", "executadas", "pendentes_execucao", "consulta_ssa", "consulta_ssa_print", "aprovacao_emissao", "aprovacao_cancelamento", "derivadas_relacionadas", "reprogramacoes", "both")]
    [string]$ReportKind = "both",
    [string]$BaseUrl = "https://osprd.itaipu/SAM_SMA/",
    [string]$OutputJson = "staging/pipeline_online_windows.json",
    [string]$SecretService = "scrap_report.sam",
    [switch]$Headed,
    [switch]$StrictCert
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

if ($Preset -and -not $PSBoundParameters.ContainsKey("OutputJson")) {
    $OutputJson = "staging/sweep_windows.json"
}

if ($Preset) {
    if ($PSBoundParameters.ContainsKey("Setor") -or $PSBoundParameters.ContainsKey("SetorEmissor")) {
        throw "[scrape_sam_windows] preset nao pode ser combinado com Setor ou SetorEmissor"
    }
}

$outputDir = Split-Path -Parent $OutputJson
if (-not $outputDir) {
    $outputDir = "."
}
New-Item -ItemType Directory -Path $outputDir -Force | Out-Null

function Read-RequiredFlowJson {
    param(
        [Parameter(Mandatory = $true)][string]$Path,
        [Parameter(Mandatory = $true)][string]$StepName
    )

    if (-not (Test-Path -LiteralPath $Path)) {
        throw "[scrape_sam_windows] $StepName terminou sem JSON de saida: $Path"
    }
    try {
        $result = Get-Content -LiteralPath $Path -Raw | ConvertFrom-Json
    } catch {
        throw "[scrape_sam_windows] $StepName gravou JSON invalido: $Path"
    }
    if (-not $result.status) {
        throw "[scrape_sam_windows] $StepName gravou JSON sem status: $Path"
    }
    return $result
}

function Invoke-RequiredFlowJsonCommand {
    param(
        [Parameter(Mandatory = $true)][string]$StepName,
        [Parameter(Mandatory = $true)][string]$Context,
        [Parameter(Mandatory = $true)][string]$OutFile,
        [Parameter(Mandatory = $true)][string[]]$CommandArgs
    )

    uv @CommandArgs
    $exitCode = $LASTEXITCODE
    $result = $null
    if (Test-Path -LiteralPath $OutFile) {
        $result = Read-RequiredFlowJson -Path $OutFile -StepName $StepName
    }
    if ($exitCode -ne 0) {
        if ($null -ne $result) {
            $detail = ""
            if (
                ($result.PSObject.Properties.Name -contains "message") -and
                (-not [string]::IsNullOrWhiteSpace($result.message))
            ) {
                $detail = ": $($result.message)"
            }
            throw "[scrape_sam_windows] $StepName retornou status=$($result.status) para $Context (exit_code=$exitCode)$detail"
        }
        throw "[scrape_sam_windows] falha no $StepName para $Context (exit_code=$exitCode)"
    }
    if ($null -eq $result) {
        $result = Read-RequiredFlowJson -Path $OutFile -StepName $StepName
    }
    return $result
}

function Invoke-WindowsFlow {
    param(
        [Parameter(Mandatory = $true)][string]$Kind,
        [Parameter(Mandatory = $true)][string]$OutFile
    )

    $cmdArgs = @(
        "run", "--project", ".", "python", "-m", "scrap_report.cli", "windows-flow",
        "--username", $Username,
        "--setor", $Setor,
        "--setor-emissor", $SetorEmissor,
        "--report-kind", $Kind,
        "--base-url", $BaseUrl,
        "--secret-service", $SecretService,
        "--output-json", $OutFile
    )

    if ($Headed) {
        $cmdArgs += "--headed"
    }
    if (-not $StrictCert) {
        $cmdArgs += "--ignore-https-errors"
    }

    Write-Host "[scrape_sam_windows] iniciando report_kind=$Kind"
    $result = Invoke-RequiredFlowJsonCommand -StepName "windows-flow" -Context "report_kind=$Kind" -OutFile $OutFile -CommandArgs $cmdArgs
    Write-Host "[scrape_sam_windows] status=$($result.status) report_kind=$Kind"
    if ($result.staged_path) {
        Write-Host "[scrape_sam_windows] staged_path=$($result.staged_path)"
    }
}

function Invoke-SweepRun {
    param(
        [Parameter(Mandatory = $true)][string]$Kind,
        [Parameter(Mandatory = $true)][string]$OutFile
    )

    $cmdArgs = @(
        "run", "--project", ".", "python", "-m", "scrap_report.cli", "sweep-run",
        "--username", $Username,
        "--report-kind", $Kind,
        "--preset", $Preset,
        "--base-url", $BaseUrl,
        "--secret-service", $SecretService,
        "--output-json", $OutFile
    )

    if ($Headed) {
        $cmdArgs += "--headed"
    }
    if (-not $StrictCert) {
        $cmdArgs += "--ignore-https-errors"
    }

    Write-Host "[scrape_sam_windows] iniciando preset=$Preset report_kind=$Kind"
    $result = Invoke-RequiredFlowJsonCommand -StepName "sweep-run" -Context "preset=$Preset report_kind=$Kind" -OutFile $OutFile -CommandArgs $cmdArgs
    Write-Host "[scrape_sam_windows] status=$($result.status) preset=$Preset report_kind=$Kind"
}

function Resolve-BatchOutputPath {
    param(
        [Parameter(Mandatory = $true)][string]$BasePath,
        [Parameter(Mandatory = $true)][string]$Suffix
    )

    $baseName = [System.IO.Path]::GetFileNameWithoutExtension($BasePath)
    $extension = [System.IO.Path]::GetExtension($BasePath)
    if (-not $extension) {
        $extension = ".json"
    }
    $dirName = Split-Path -Parent $BasePath
    if (-not $dirName) {
        $dirName = "."
    }
    return (Join-Path $dirName ($baseName + "_" + $Suffix + $extension))
}

if ($Preset) {
    if ($ReportKind -eq "both") {
        $outPendentes = Resolve-BatchOutputPath -BasePath $OutputJson -Suffix "pendentes"
        $outExecutadas = Resolve-BatchOutputPath -BasePath $OutputJson -Suffix "executadas"

        Invoke-SweepRun -Kind "pendentes" -OutFile $outPendentes
        Invoke-SweepRun -Kind "executadas" -OutFile $outExecutadas

        Write-Host "[scrape_sam_windows] concluido preset both"
        Write-Host "[scrape_sam_windows] saidas:"
        Write-Host "  $outPendentes"
        Write-Host "  $outExecutadas"
        exit 0
    }

    Invoke-SweepRun -Kind $ReportKind -OutFile $OutputJson
    Write-Host "[scrape_sam_windows] concluido preset com sucesso"
    exit 0
}

if ($ReportKind -eq "both") {
    $outPendentes = Resolve-BatchOutputPath -BasePath $OutputJson -Suffix "pendentes"
    $outExecutadas = Resolve-BatchOutputPath -BasePath $OutputJson -Suffix "executadas"

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
