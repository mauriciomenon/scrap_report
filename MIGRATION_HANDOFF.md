# MIGRATION_HANDOFF

## Contexto
- origem:
  - /Users/menon/git/SCRAP_SAM
  - /Users/menon/git/scrap_sam_rework
- destino:
  - /Users/menon/git/scrap_report

## Funcionalidade extraida
- fluxo de scraping de relatorios sem UI
- fluxo de staging de xlsx para consumo externo
- geracao de artefatos de apoio para analise local

## O que ficou fora
- dashboard e layout
- refactor amplo de legado
- qualquer operacao de git/repo/PR

## Contrato de integracao (atual)
- entrada:
  - credenciais SAM (args ou env)
  - setor executor
  - tipo de relatorio (`pendentes` ou `executadas`)
  - download_dir
  - staging_dir
- saida:
  - `source_path` do download
  - `staged_path` final
  - paths de artefatos em `staging/reports`

## Risco residual
- sem acesso ao ambiente SAM nesta fase, logo sem prova E2E real
