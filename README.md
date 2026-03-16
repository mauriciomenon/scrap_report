# scrap_report

Extracao modular de relatorio SAM para entregar arquivos xlsx para integracao externa.

## Escopo deste ciclo
- abrir pagina em headless
- navegar para tela de relatorio
- preencher filtros
- baixar xlsx
- mover xlsx para pasta de staging
- gerar artefatos locais (dados, estatisticas, txt)

## Nao esta no escopo
- dashboard/ui/layout
- criacao de repo git, branch ou PR
- validacao E2E online (sem acesso ao ambiente SAM nesta fase)

## Estrutura
- `src/scrap_report/config.py`: configuracao e validacao de entrada
- `src/scrap_report/scraper.py`: fluxo Playwright
- `src/scrap_report/file_ops.py`: staging e naming de arquivos
- `src/scrap_report/reporting.py`: geracao de artefatos
- `src/scrap_report/pipeline.py`: orquestracao completa
- `src/scrap_report/cli.py`: comandos de execucao

## Uso rapido

## Fluxo de segredo (quando pede credencial)
0. Ponto de partida recomendado no Windows (um comando):
```bash
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/scrape_sam_windows.ps1 \
  -Username "<usuario>" \
  -Setor IEE3 \
  -ReportKind both
```
Esse wrapper executa `windows-flow` internamente.
Em `both`, ele gera:
- `staging/pipeline_online_windows_pendentes.json`
- `staging/pipeline_online_windows_executadas.json`

Alias legado ainda disponivel:
```bash
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/main_windows.ps1 \
  -Username "<usuario>" \
  -Setor IEE3 \
  -ReportKind pendentes
```

0.1 Fluxo CLI equivalente (sequencial):
```bash
uv run python -m scrap_report.cli windows-flow \
  --username "<usuario>" \
  --setor IEE3 \
  --report-kind pendentes \
  --output-json staging/pipeline_online_windows.json
```
Se o secret nao existir, o comando pede senha com mascara e grava no backend seguro.

1. Comandos que resolvem credencial antes da operacao: `windows-flow`, `scrape`, `pipeline` (sem `--report-only`) e `ingest-latest`.
2. Aviso de seguranca e emitido em `stderr` no inicio desses comandos.
3. Ordem de resolucao de senha:
  - `--prompt-password` (entrada interativa sem eco)
  - `--password` (entrada explicita da execucao atual)
  - secret store do OS (`Keychain`, `Credential Manager`, `Secret Service`)
  - no Windows, se `CredentialManager` nao estiver funcional, fallback automatico para cofre local DPAPI por usuario
  - `SAM_PASSWORD` somente em modo transicional permitido
4. Politica fail-closed:
  - se `--secure-required` estiver ativo, sem secret seguro a execucao para com erro limpo
  - se `--allow-transitional-plaintext` estiver desabilitado, sem secret seguro a execucao para
5. Comando recomendado para provisionar secret sem exibir valor:
```bash
uv run python -m scrap_report.cli secret setup \
  --username "<usuario>" \
  --secret-service scrap_report.sam
```

### 1) somente scraping
```bash
uv run python -m scrap_report.cli scrape \
  --username "$SAM_USERNAME" \
  --setor IEE3 \
  --secure-required \
  --report-kind pendentes
```

### 2) pipeline completo (scrape + stage + relatorios)
```bash
uv run python -m scrap_report.cli pipeline \
  --username "$SAM_USERNAME" \
  --setor IEE3 \
  --secure-required \
  --report-kind pendentes \
  --download-dir downloads \
  --staging-dir staging \
  --output-json staging/pipeline_result.json
```

### 3) pipeline em modo report-only (sem scraping)
```bash
uv run python -m scrap_report.cli pipeline \
  --setor IEE3 \
  --report-kind pendentes \
  --staging-dir staging \
  --report-only \
  --source-excel staging/pendentes_arquivo.xlsx \
  --output-json staging/pipeline_report_only.json
```

### 4) ingestao local (sem acessar o site)
```bash
uv run python -m scrap_report.cli ingest-latest \
  --setor IEE3 \
  --report-kind pendentes \
  --download-dir downloads \
  --staging-dir staging \
  --output-json staging/ingest_result.json
```

### 5) gerar artefatos a partir de um excel ja baixado
```bash
uv run python -m scrap_report.cli report-from-excel \
  --excel staging/pendentes_arquivo.xlsx \
  --output-dir staging/reports
```

### 6) validar contrato JSON
```bash
uv run python -m scrap_report.cli validate-contract \
  --output-json staging/contract_info.json
```

## Integracao com outro programa
- o arquivo principal para consumo fica em `staging/*.xlsx`
- os artefatos adicionais ficam em `staging/reports/`
- os comandos retornam json com `schema_version` para contrato estavel de integracao
- os comandos retornam tambem `generated_at` (UTC) e `producer`
- o comando `pipeline` retorna json com caminhos finais para integracao automatica

## Politica de versao do contrato
- `schema_version` segue semver (`MAJOR.MINOR.PATCH`)
- bump MAJOR: mudanca incompativel de campo, remocao ou rename
- bump MINOR: campo novo opcional, comando novo sem quebra
- bump PATCH: ajuste interno sem mudanca estrutural do payload
