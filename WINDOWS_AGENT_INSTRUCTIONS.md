# WINDOWS_AGENT_INSTRUCTIONS

## Objetivo
- Executar validacao real em host Windows 11 e entregar evidencia consolidada para fechamento do pre-release.

## Pre-requisitos
1. Windows 11
2. PowerShell 5.1+ ou PowerShell 7+
3. Python 3.11+
4. uv instalado
5. Modulo CredentialManager instalado

## Passos obrigatorios
1. Abrir PowerShell na raiz do projeto.
2. Validar modulo de segredo:
```powershell
Get-Module -ListAvailable -Name CredentialManager
```
3. Se ausente, instalar:
```powershell
Install-Module CredentialManager -Scope CurrentUser -Force
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
