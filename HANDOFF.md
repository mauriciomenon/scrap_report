# HANDOFF

## Estado atual do branch
- repo local desta copia: `/Users/menon/git/scrap_report`
- repo operacional Windows de referencia: `C:\Users\mauri\git\scrap_report`
- branch: `master`
- remoto: `origin/master`
- HEAD desta copia no momento do sync documental: `6bb3059`
- baseline Playwright antes da trilha REST: `b893356`
- baseline REST em tres niveis: `81fb0c6`
- endurecimento operacional REST: `f1c846a`
- integracao REST no `sweep-run`: `e9460c9`
- otimizacao REST mais recente: `2f61345`

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
- validado para:
  - um setor
  - varios setores
  - geral sem detalhamento
  - geral com detalhamento por `year_week`
  - geral com detalhamento por `emission_date` validado ate `42 dias`
- no runtime REST do sweep, credencial nao e obrigatoria

4. trilha TLS operacional
- `sam-api-cert`
- exporta a CA raiz apresentada pelo host REST
- `--ca-file` e `--rest-ca-file` validados em chamadas reais

## Estado tecnico do slice atual
- baseline anterior do branch: `06761d6`
- gates locais atuais:
  - `py_compile`: ok
  - `ruff`: ok
  - `ty`: ok
  - `pytest`: `201 passed`
- ajuste fechado neste slice:
  - baseline global do `ty check` zerado
  - compatibilidade de testes Windows corrigida para `Path` com separador `/` ou `\\`
- pendencia operacional ainda aberta:
  - smoke Debian13 real com conectividade estavel ao PyPI
- observacao de evidencia:
  - `staging/smoke_evidence_windows11.json` nao esta presente nesta copia local
  - a execucao historica do smoke W11 continua registrada em `CONVERSA_MIGRACAO_STATUS.md`

## Nota de contexto
- os caminhos Windows abaixo sao referencia de operacao e evidencias reais de outra maquina
- a fonte de verdade desta copia de trabalho e o repo local em `/Users/menon/git/scrap_report`
- o branch atual desta copia esta sincronizado com `origin/master`

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
- dedupe de SSA antes do detalhamento
- `ssa_numbers_deduped` exposto quando a entrada repetida e reduzida
- integracao optativa da REST no `sweep-run`
- payload e manifest REST agora incluem:
  - `filters`
  - `warnings`
  - `verify_tls`
  - `timeout_seconds`
- os manifests REST agora compartilham telemetria minima comum no topo:
  - `runtime_mode`
  - `telemetry.record_count`
  - `telemetry.detail_count`
  - `telemetry.without_detail_count`
  - `manifest_json`
- os artefatos Playwright agora tambem expõem aliases canonicos:
  - `dados` -> `data_xlsx`
  - `estatisticas` -> `summary_xlsx`
  - `relatorio_txt` -> `report_txt`
- `validate-contract` agora publica o mapa desses aliases por JSON:
  - `contract.exports.playwright_reports`
  - `contract.exports.rest_reports`
- `validate-contract` agora publica tambem o mapa de consumo por fluxo:
  - `contract.preferred_contracts`
  - `contract.minimum_fields_by_flow`
- isso agora deixa explicito:
  - qual schema consumir por fluxo
  - qual contrato de exports usar por fluxo
  - quais campos minimos o consumidor deve exigir
- o pacote agora tambem esta pronto para import basico por outro projeto:
  - `scrap_report.__version__`
  - `scrap_report.build_contract_catalog()`
  - entrypoint `scrap-report`
- `validate-contract` agora expõe `contract.package` com:
  - `package_name`
  - `package_version`
  - `import_name`
  - `cli_entrypoint`
  - `module_entrypoint`
- `exports` REST agora mantem aliases legados e chaves canonicas:
  - `csv` / `xlsx`
  - `data_csv` / `data_xlsx`
  - `summary_xlsx`, quando existir
  - `manifest_json`, quando houver saida JSON
- o manifest de `sweep-run` agora sai com schema formal validado:
  - `status`
  - `report_kind`
  - `scope_mode`
  - `runtime_mode`
  - `item_count`
  - `success_count`
  - `failure_count`
  - `items`
  - `manifest_json`
- erro TLS agora aponta `--ca-file` ou `--ignore-https-errors`
- `--ca-file` relativo agora e normalizado para caminho absoluto na CLI

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
  - [sam_api_ca_detail_relative_v2.json](C:\Users\mauri\git\scrap_report\tmp\sam_api_ca_detail_relative_v2.json)
- CA exportada:
  - [sam_api_cert_v2.json](C:\Users\mauri\git\scrap_report\tmp\sam_api_cert_v2.json)
- comando opinativo:
  - [sam_api_flow_real_v2.json](C:\Users\mauri\git\scrap_report\tmp\sam_api_flow_real_v2.json)
- fluxo independente:
  - [sam_api_standalone_manifest_v2.json](C:\Users\mauri\git\scrap_report\tmp\sam_api_standalone_manifest_v2.json)
  - [sam_api_detail_ca_v3.json](C:\Users\mauri\git\scrap_report\tmp\sam_api_detail_ca_v3.json)
- chunking real:
  - [sam_api_chunking_manifest.json](C:\Users\mauri\git\scrap_report\tmp\sam_api_chunking_manifest.json)
- `sweep-run` REST:
  - [sweep_rest_pendentes.json](C:\Users\mauri\git\scrap_report\tmp\sweep_rest_pendentes.json)
  - [sweep_rest_varios_setores_v2.json](C:\Users\mauri\git\scrap_report\tmp\sweep_rest_varios_setores_v2.json)
  - [sweep_rest_geral_sem_detalhe.json](C:\Users\mauri\git\scrap_report\tmp\sweep_rest_geral_sem_detalhe.json)
  - [sweep_rest_one_ca_v3.json](C:\Users\mauri\git\scrap_report\tmp\sweep_rest_one_ca_v3.json)
  - [sweep_rest_multi_ca_v3.json](C:\Users\mauri\git\scrap_report\tmp\sweep_rest_multi_ca_v3.json)
  - [sweep_rest_all_ca_relative_v2.json](C:\Users\mauri\git\scrap_report\tmp\sweep_rest_all_ca_relative_v2.json)
  - [sweep_rest_all_yearweek_ca_v4.json](C:\Users\mauri\git\scrap_report\tmp\sweep_rest_all_yearweek_ca_v4.json)
  - [sweep_rest_all_emission_date_day_v3.json](C:\Users\mauri\git\scrap_report\tmp\sweep_rest_all_emission_date_day_v3.json)
  - [sweep_rest_all_emission_date_range_v3.json](C:\Users\mauri\git\scrap_report\tmp\sweep_rest_all_emission_date_range_v3.json)
  - [sweep_rest_all_emission_date_week_v1.json](C:\Users\mauri\git\scrap_report\tmp\sweep_rest_all_emission_date_week_v1.json)
  - [sweep_rest_all_emission_date_14d_v1.json](C:\Users\mauri\git\scrap_report\tmp\sweep_rest_all_emission_date_14d_v1.json)
  - [sweep_rest_all_emission_date_21d_v1.json](C:\Users\mauri\git\scrap_report\tmp\sweep_rest_all_emission_date_21d_v1.json)
  - [sweep_rest_all_emission_date_28d_v1.json](C:\Users\mauri\git\scrap_report\tmp\sweep_rest_all_emission_date_28d_v1.json)
  - [sweep_rest_all_emission_date_35d_v1.json](C:\Users\mauri\git\scrap_report\tmp\sweep_rest_all_emission_date_35d_v1.json)
  - [sweep_rest_all_emission_date_42d_v1.json](C:\Users\mauri\git\scrap_report\tmp\sweep_rest_all_emission_date_42d_v1.json)
  - [sam_api_iee3_pendentes_demo.json](C:\Users\mauri\git\scrap_report\tmp\sam_api_iee3_pendentes_demo.json)
  - [sam_api_iee3_detail_demo.json](C:\Users\mauri\git\scrap_report\tmp\sam_api_iee3_detail_demo.json)
  - [sam_api_iee3_contract_demo_v4.json](C:\Users\mauri\git\scrap_report\tmp\sam_api_iee3_contract_demo_v4.json)
  - [sam_api_contract_detail_v1.json](C:\Users\mauri\git\scrap_report\tmp\sam_api_contract_detail_v1.json)
  - [sweep_rest_iee3_contract_v3.json](C:\Users\mauri\git\scrap_report\tmp\sweep_rest_iee3_contract_v3.json)
  - [contract_v2.json](C:\Users\mauri\git\scrap_report\tmp\contract_v2.json)
  - [contract_v3.json](C:\Users\mauri\git\scrap_report\tmp\contract_v3.json)
  - [report_contract_out.json](C:\Users\mauri\git\scrap_report\tmp\report_contract_out.json)
  - [sam_api_iee3_contract_demo_v5.json](C:\Users\mauri\git\scrap_report\tmp\sam_api_iee3_contract_demo_v5.json)
  - [sam_api_iee3_contract_demo_v6.json](C:\Users\mauri\git\scrap_report\tmp\sam_api_iee3_contract_demo_v6.json)

## Riscos residuais reais
- a REST API nao depende mais exclusivamente de `--ignore-https-errors`; o caminho com CA exportada ficou validado
- o chunking removeu a falha seca e o dedupe removeu repeticao inutil, mas o custo do detalhe continua linear por SSA unica em lotes grandes
- o `sweep-run` REST ainda esta limitado a `report_kind=pendentes`
- `emission_date` geral agora esta verde ate 42 dias
- acima de 42 dias, o modo geral com detalhamento amplo por `emission_date` continua caro e ainda sem teto operacional provado
- a camada REST ja demonstrou panorama e detalhe em lote usando a lista real de pendentes da `IEE3`
- o contrato minimo comum de manifest REST agora esta alinhado para consumo futuro no repo de reports
- o contrato de aliases de artefatos agora tambem esta publicavel por JSON, sem depender de parse de README
- o contrato agora tambem declara por JSON qual schema cada fluxo deve usar e quais campos minimos o consumidor deve ler
- com isso, o repo de reports ja pode decidir consumo por JSON sem precisar inferir pelo nome do comando
- a importacao de `scrap_report` ficou leve e a importacao de `scrap_report.cli` deixou de depender do caminho Playwright na carga inicial
- `derivadas_relacionadas` continua com export oficial instavel no fluxo Playwright
- `aprovacao_emissao` continua sem base para liberar `emission_date`

## Proximos passos naturais
1. decidir se o proximo alvo tecnico sera:
   - reducao de custo do detalhe em lote REST
   - ampliacao do `sweep-run` REST para outros `report_kind`
   - operacionalizar rotacao/manutencao da CA exportada
   - ou voltar para as pendencias do fluxo Playwright
