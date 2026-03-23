# HANDOFF

## Estado atual do branch
- repo: `C:\Users\mauri\git\scrap_report`
- branch: `master`
- remoto: `origin/master`
- baseline Playwright antes da trilha REST: `b893356`
- baseline REST em tres niveis: `81fb0c6`
- endurecimento operacional REST: `f1c846a`
- integracao REST no `sweep-run`: `e9460c9`

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

3. fluxo de produto com REST optativo
- `sweep-run --runtime rest`
- suportado neste ciclo para `report_kind=pendentes`

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
- chunking controlado no detalhe em lote
- `detail_batch_chunked` exposto no payload quando aplicavel
- integracao optativa da REST no `sweep-run`
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
- chunking real:
  - [sam_api_chunking_manifest.json](C:\Users\mauri\git\scrap_report\tmp\sam_api_chunking_manifest.json)
- `sweep-run` REST:
  - [sweep_rest_pendentes.json](C:\Users\mauri\git\scrap_report\tmp\sweep_rest_pendentes.json)

## Riscos residuais reais
- a REST API ainda depende de `--ignore-https-errors` no ambiente atual
- o chunking removeu a falha seca, mas o custo do detalhe continua linear por SSA em lotes grandes
- o `sweep-run` REST ainda esta limitado a `report_kind=pendentes`
- `derivadas_relacionadas` continua com export oficial instavel no fluxo Playwright
- `aprovacao_emissao` continua sem base para liberar `emission_date`

## Proximos passos naturais
1. decidir se o proximo alvo tecnico sera:
   - confianca TLS para a REST
   - reducao de custo do detalhe em lote REST
   - ampliacao do `sweep-run` REST para outros `report_kind`
   - ou voltar para as pendencias do fluxo Playwright
