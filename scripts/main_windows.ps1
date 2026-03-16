param(
    [string]$Username = "",
    [string]$Setor = "IEE3",
    [ValidateSet("pendentes", "executadas", "both")]
    [string]$ReportKind = "both",
    [string]$BaseUrl = "https://osprd.itaipu/SAM_SMA/",
    [string]$OutputJson = "staging/pipeline_online_windows.json",
    [string]$SecretService = "scrap_report.sam",
    [switch]$Headed
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$entrypoint = Join-Path $PSScriptRoot "scrape_sam_windows.ps1"
if (-not (Test-Path $entrypoint)) {
    throw "entrypoint nao encontrado: $entrypoint"
}

$forward = @{
    Username = $Username
    Setor = $Setor
    ReportKind = $ReportKind
    BaseUrl = $BaseUrl
    OutputJson = $OutputJson
    SecretService = $SecretService
}
if ($Headed) {
    $forward.Headed = $true
}

Write-Host "[main_windows] alias legado. use scripts/scrape_sam_windows.ps1"
& $entrypoint @forward
exit $LASTEXITCODE
