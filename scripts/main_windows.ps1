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

$entrypoint = Join-Path $PSScriptRoot "scrape_sam_windows.ps1"
if (-not (Test-Path $entrypoint)) {
    throw "entrypoint nao encontrado: $entrypoint"
}

$forward = @{
    Username = $Username
    Preset = $Preset
    ReportKind = $ReportKind
    BaseUrl = $BaseUrl
    OutputJson = $OutputJson
    SecretService = $SecretService
}
if (-not $Preset) {
    $forward.Setor = $Setor
    $forward.SetorEmissor = $SetorEmissor
}
if ($Headed) {
    $forward.Headed = $true
}
if ($StrictCert) {
    $forward.StrictCert = $true
}

Write-Host "[main_windows] alias legado. use scripts/scrape_sam_windows.ps1"
& $entrypoint @forward
exit $LASTEXITCODE
