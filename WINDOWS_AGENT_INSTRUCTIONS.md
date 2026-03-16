# WINDOWS_AGENT_INSTRUCTIONS

## TLDR
1. Fluxo unico recomendado (um comando):
```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/scrape_sam_windows.ps1 -Username "<usuario>" -Setor IEE3 -ReportKind both
```
2. Em `both`, gera duas rodadas no mesmo comando:
   - `staging/pipeline_online_windows_pendentes.json`
   - `staging/pipeline_online_windows_executadas.json`
3. Se o secret ainda nao existir, o comando vai pedir senha com mascara `*****` e gravar no backend seguro.
4. Fluxo CLI equivalente (mantido):
```powershell
uv run --project . python -m scrap_report.cli windows-flow --username "<usuario>" --setor IEE3 --report-kind pendentes --output-json staging/pipeline_online_windows.json
```
5. Alias legado (mantido para compatibilidade):
```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/main_windows.ps1 -Username "<usuario>" -Setor IEE3 -ReportKind pendentes
```
6. Comandos anteriores (mantidos):
```powershell
uv run --project . python -m scrap_report.cli secret setup --username "<usuario>" --secret-service scrap_report.sam
uv run --project . python -m scrap_report.cli secret get --username "<usuario>" --secret-service scrap_report.sam
uv run --project . python -m scrap_report.cli pipeline --username "<usuario>" --setor IEE3 --secure-required --report-kind pendentes --download-dir downloads --staging-dir staging --base-url "https://osprd.itaipu/SAM_SMA/" --output-json staging/pipeline_online_windows.json
```

## Objetivo
- Executar validacao real em host Windows 11 e entregar evidencia consolidada para fechamento do pre-release.

## Pre-requisitos
1. Windows 11
2. PowerShell 5.1+ ou PowerShell 7+
3. Python 3.11+
4. uv instalado
5. Sem instalacao manual extra de modulo de segredo

## Passos obrigatorios
1. Abrir PowerShell na raiz do projeto.
2. (Opcional) validar modulo de segredo:
```powershell
Get-Module -ListAvailable -Name CredentialManager
```
3. Se ausente, NAO precisa instalar. O app usa fallback DPAPI por usuario automaticamente.
```powershell
# nenhum comando adicional necessario
```
4. Rodar smoke completo:
```powershell
powershell -ExecutionPolicy Bypass -File scripts/smoke_windows11.ps1
```

## Resultado esperado
- Arquivo gerado: `staging/smoke_evidence_windows11.json`
- Saida sem leak de segredo
- `status: ok` para checks do JSON consolidado

## Entrega para fechamento
1. Enviar `staging/smoke_evidence_windows11.json`.
2. Se houver falha, enviar tambem o log completo do comando.

## Observacao
- Nao alterar `src/` nem `tests/` durante essa rodada operacional.
