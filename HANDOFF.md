# HANDOFF

## Estado atual do branch
- repo: `C:\Users\mauri\git\scrap_report`
- branch: `master`
- remoto: `origin/master`
- baseline Playwright antes da trilha REST: `b893356`
- baseline REST em tres niveis: `81fb0c6`
- endurecimento operacional REST: `f1c846a`

## Current truth
O projeto agora tem duas frentes operacionais distintas:
1. fluxo oficial com Playwright
- `windows-flow`
- `sweep-run`
- staging e derivados tradicionais

2. fluxo REST sem Playwright
- API interna reutilizavel
- `sam-api-flow`
- `sam-api-standalone`

## REST, resumo curto
### Nivel 1
- `sam_api.py`
- funcoes reutilizaveis para busca, detalhe, lote, filtros e sumario

### Nivel 2
- `sam-api-flow`
- comando opinativo para operacao humana direta

### Nivel 3
- `sam-api-standalone`
- manifest proprio
- `csv`
- `xlsx`
- resumo `xlsx`
- sem staging do pipeline antigo

## Mitigacoes novas ja aplicadas
- limite operacional explicito para detalhe em lote
- falha cedo quando a consulta tenta detalhar acima do limite
- payload e manifest REST agora incluem:
  - `filters`
  - `warnings`
  - `verify_tls`
  - `timeout_seconds`

## Estado validado
### Playwright
- mantido estavel conforme rodada anterior

### REST
- nivel 1: verde
- nivel 2: verde
- nivel 3: verde

## Evidencia recente
- comando tecnico:
  - [sam_api_search_real_v2.json](C:\Users\mauri\git\scrap_report\tmp\sam_api_search_real_v2.json)
- comando opinativo:
  - [sam_api_flow_real_v2.json](C:\Users\mauri\git\scrap_report\tmp\sam_api_flow_real_v2.json)
- fluxo independente:
  - [sam_api_standalone_manifest_v2.json](C:\Users\mauri\git\scrap_report\tmp\sam_api_standalone_manifest_v2.json)

## Riscos residuais reais
- a REST API ainda depende de `--ignore-https-errors` no ambiente atual
- ainda nao existe chunking controlado para detalhamento acima do limite operacional
- `derivadas_relacionadas` continua com export oficial instavel no fluxo Playwright
- `aprovacao_emissao` continua sem base para liberar `emission_date`

## Proximos passos naturais
1. decidir se o proximo alvo tecnico sera:
   - confianca TLS para a REST
   - chunking controlado para lote grande
   - ou voltar para as pendencias do fluxo Playwright
