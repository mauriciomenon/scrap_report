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

## Atualizacao local Windows 2026-04-23, slice 43
- HEAD local confirmado no inicio do slice: `f389671`
- objetivo:
  - fechar higiene local de artefatos temporarios sem tocar runtime
  - validar gates reais completos
  - atualizar demonstrativo REST real de SSAs pendentes para `IEE3`
- mudanca aplicada:
  - `.gitignore` agora ignora `.pytest-local/` e `.pytest-tmp/`
  - artefato local literal `%SystemDrive%/` removido do workspace
- evidencias reais:
  - `py_compile`: ok
  - `ruff`: ok
  - `ty` (`src tests`): ok
  - `pytest -q`: `202 passed`
  - `sam-api-flow` real (`IEE3`):
    - `status=ok`
    - `count=69`
    - `summary.by_emitter={"IEE3": 69}`
    - artifacts:
      - [sam_api_iee3_pendentes_demo_20260423_130409.json](C:\Users\mauri\git\scrap_report\tmp\sam_api_iee3_pendentes_demo_20260423_130409.json)
      - [sam_api_iee3_pendentes_demo_20260423_130409.csv](C:\Users\mauri\git\scrap_report\tmp\sam_api_iee3_pendentes_demo_20260423_130409.csv)
      - [sam_api_iee3_pendentes_demo_20260423_130409.xlsx](C:\Users\mauri\git\scrap_report\tmp\sam_api_iee3_pendentes_demo_20260423_130409.xlsx)
- kluster:
  - `.gitignore`: 1 issue low inicial (`%SystemDrive%/`), corrigido
  - `.gitignore` revalidado: clean

## Atualizacao local Windows 2026-04-23, slice 44
- HEAD local confirmado no inicio do slice: `b3c8be6`
- objetivo:
  - fechar gate cross-platform com evidencia real de Windows11 e Debian13
  - corrigir falha funcional do `smoke_debian13.sh` com patch minimo
- mudanca aplicada:
  - `scripts/smoke_debian13.sh` agora usa `staging/stage_result.json` para ler `staged_path` canonico
  - `ingest-latest` no smoke Debian13 remove senha de argumento e usa fallback transicional por env de processo
  - `platform_label` da evidencia Debian13 ajustado para `debian13`
  - duplicacao de pytest no bloco de evidencia removida
- evidencias reais:
  - Windows11:
    - [smoke_evidence_windows11.json](C:\Users\mauri\git\scrap_report\staging\smoke_evidence_windows11.json)
    - `generated_at_utc=2026-04-23T16:14:20.9295303Z`
    - checks chave: todos `ok`
  - Debian13:
    - [smoke_evidence_debian13.json](C:\Users\mauri\git\scrap_report\staging\smoke_evidence_debian13.json)
    - `generated_at_utc=2026-04-23T17:52:22.288728+00:00`
    - checks chave: todos `ok`
- kluster no script:
  - primeira rodada com findings (high/medium/low), corrigidos no proprio slice
  - rodada final: clean

## Atualizacao local Windows 2026-04-23, slice 45
- objetivo:
  - varredura geral atras de furos grandes
  - hardening do scanner local de secrets e da redacao de logs
- mudanca aplicada:
  - `secret_scan.py` agora varre diretorios recursivamente e evita duplicidade
  - padroes de detecao ajustados para reduzir ruido de fixture curta
  - `cli.py` default de `scan-secrets` ajustado para `src` + `README.md`
  - scripts `smoke_windows11.ps1` e `smoke_debian13.sh` alinhados ao novo escopo
  - `redaction.py` agora mascara atribuicoes sensiveis e bearer token
- evidencia:
  - `uv run --python 3.13 pytest -q`: `208 passed`
  - `uv run --python 3.13 python -m scrap_report.cli scan-secrets`: `status=ok`
  - `uv run --python 3.13 python -m scrap_report.cli scan-secrets --paths src tests README.md`: `status=error`, `findings_count=3` (fixtures de teste)

## Atualizacao local Windows 2026-04-23, slices 46-47
- objetivo:
  - fechar o falso negativo estrutural em `scan-secrets` (diretorios e multiline simples)
  - consolidar padroes sensiveis compartilhados entre scanner e redacao
  - endurecer redacao sem alterar contrato externo da CLI
- mudanca aplicada:
  - novo modulo `src/scrap_report/sensitive_patterns.py` para centralizar keywords/padroes
  - `src/scrap_report/secret_scan.py` com:
    - normalizacao de roots e dedupe de candidatos
    - leitura em stream
    - janela multiline curta (2 linhas) para casos de atribuicao quebrada
  - `src/scrap_report/redaction.py` com:
    - mascaramento de bearer, atribuicao sensivel e keyword standalone
    - validacao iterativa de payload com protecao contra ciclo
  - testes atualizados em `tests/test_secret_scan.py` e `tests/test_redaction.py`
- evidencias reais:
  - `uv run --python 3.13 python -m py_compile ...`: ok
  - `uv run --python 3.13 ruff check .`: ok
  - `uv run --python 3.13 ty check src`: ok
  - `uv run --python 3.13 pytest -q` (focado): `15 passed`
  - `uv run --python 3.13 pytest -q`: `214 passed`
  - `uv run --python 3.13 python -m scrap_report.cli scan-secrets`: `status=ok`, `findings_count=0`
  - `uv run --python 3.13 python -m scrap_report.cli scan-secrets --paths src tests README.md`: `status=error`, `findings_count=4` (fixtures de teste)
- kluster:
  - ciclo iterativo com eliminacao de findings `HIGH`
  - ultimo estado ainda com findings `MEDIUM/LOW` de qualidade/performance ampla, sem bloqueador funcional confirmado
- risco residual:
  - scanner multiline limitado a janela de 2 linhas (tradeoff explicito)
  - backlog de melhoria estrutural de performance/arquitetura permanece nao bloqueante

## Atualizacao local Windows 2026-04-24, slice 48
- objetivo:
  - deixar `scan-secrets` com ordem deterministica de varredura entre ambientes
  - transformar cache de validacao de chave sensivel em cache real de modulo
- mudanca aplicada:
  - `src/scrap_report/redaction.py`:
    - `_is_effectively_safe_key` movido para modulo com `@lru_cache(maxsize=512)`
    - removido cache recriado a cada chamada
  - `src/scrap_report/secret_scan.py`:
    - troca de `rglob` para `os.walk` com `dirs/files` ordenados
  - `tests/test_secret_scan.py`:
    - adicionado `test_scan_paths_is_deterministic_by_path_order`
- validacao:
  - `uv run --python 3.13 python -m py_compile ...`: ok
  - `uv run --python 3.13 ruff check .`: ok
  - `uv run --python 3.13 ty check src`: ok
  - `uv run --python 3.13 pytest -q` focado: `16 passed`
  - `uv run --python 3.13 pytest -q` completo: bloqueado por ambiente (`asyncio/_overlapped`, WinError 10106)
  - fallback `uv run --python 3.12 pytest -q`: bloqueado por DNS (`numpy` wheel, os error 11003)
  - `uv run --python 3.13 python -m scrap_report.cli scan-secrets`: `status=ok`, `findings_count=0`
  - `uv run --python 3.13 python -m scrap_report.cli scan-secrets --paths src tests README.md`: `status=error`, `findings_count=6` (fixtures)
- kluster:
  - duas tentativas no slice, ambas bloqueadas por DNS
  - erro objetivo: `lookup api.kluster.ai: getaddrinfow: A non-recoverable error occurred during a database lookup`
- risco residual:
  - medio operacional enquanto DNS externo impedir kluster e fallback de deps
  - sem indicio de regressao funcional no escopo alterado

## Atualizacao local Windows 2026-04-24, slice 49
- objetivo:
  - reduzir falso negativo multiline no scanner sem ampliar escopo de arquitetura
- mudanca aplicada:
  - `src/scrap_report/secret_scan.py`:
    - janela multiline ampliada para ate 4 linhas totais por trigger
  - `tests/test_secret_scan.py`:
    - novo teste de regressao em 3 linhas
- validacao:
  - `uv run --python 3.13 python -m py_compile ...`: ok
  - `uv run --python 3.13 ruff check .`: ok
  - `uv run --python 3.13 ty check src`: ok
  - `uv run --python 3.13 pytest -q` focado: `17 passed`
  - `uv run --python 3.13 pytest -q` completo: bloqueado por ambiente (`asyncio/_overlapped`, WinError 10106)
  - `uv run --python 3.13 python -m scrap_report.cli scan-secrets`: `status=ok`, `findings_count=0`
  - `uv run --python 3.13 python -m scrap_report.cli scan-secrets --paths src tests README.md`: `status=error`, `findings_count=6` (fixtures)
- kluster:
  - `kluster review file src/scrap_report/secret_scan.py tests/test_secret_scan.py --mode deep`
  - bloqueado por DNS: `lookup api.kluster.ai: getaddrinfow: A non-recoverable error occurred during a database lookup`
- risco residual:
  - baixo para runtime tocado
  - medio operacional por indisponibilidade de kluster via DNS

## Atualizacao local Windows 2026-04-24, slice 50
- objetivo:
  - fechar issue HIGH do kluster no caminho multiline de `secret_scan.py`
- mudanca aplicada:
  - removido `seen_findings` local de `_iter_line_findings` (crescimento sem limite)
  - dedupe mantido no nivel de `_scan_file` com `_record_finding`
  - ajuste de `match_excerpt` para linha real do match multiline
- validacao:
  - kluster antes do patch:
    - `Review 69eb799f87f9165e6e4b9cc8`
    - 1 HIGH + 1 MEDIUM + 2 LOW
  - kluster apos o patch:
    - `Review 69eb7a6bab084ce82073baa3`
    - somente 1 LOW
  - `uv run --python 3.13 pytest -q` focado: `17 passed`
  - `uv run --python 3.13 python -m py_compile ...`: ok
  - `uv run --python 3.13 ruff check .`: ok
  - `uv run --python 3.13 ty check src`: ok
  - `uv run --python 3.13 pytest -q` completo: bloqueado por ambiente (`asyncio/_overlapped`, WinError 10106)
  - `scan-secrets` default: `status=ok`, `findings_count=0`
  - `scan-secrets --paths src tests README.md`: `status=error`, `findings_count=6` (fixtures)
- risco residual:
  - sem HIGH/MEDIUM no kluster para o escopo alterado
  - permanece LOW de qualidade estrutural no gerador multiline

## Atualizacao local Windows 2026-04-24, slice 51
- objetivo:
  - endurecer `smoke_windows11.ps1` para precheck real de ambiente e seguranca de credencial
  - fechar findings HIGH/CRITICAL do kluster no script
- mudanca aplicada:
  - adicionado `Invoke-NetworkPrecheck` (socket + DNS)
  - adicionado `Read-RequiredJson` com guarda de arquivo obrigatorio
  - `py_compile` migrado para `compileall -q src tests`
  - `LATEST_XLSX` agora vem de `stage_result.json` (`staged_path`)
  - removido uso de `--password` e de `--allow-transitional-plaintext` no `ingest-latest`
  - adicionado `secret get --username "$SmokeUsername"` antes de `ingest-latest`
  - `ingest-latest` agora usa `--secure-required`
- validacao:
  - kluster no script terminou clean:
    - `Review 69ebb43d50b51ca1da53be9e` -> sem issues
  - `uv run --python 3.13 pytest -q` focado: `17 passed`
  - `uv run --python 3.13 pytest -q` completo em shell com login: `216 passed`
  - `& scripts/smoke_windows11.ps1`:
    - precheck rodou
    - fluxo chegou ate `secret get`
    - falha clara por secret ausente para `smoke_user` (esperado com `--secure-required`)
- licao operacional importante:
  - no host atual, o contexto de shell impacta os erros de rede/socket.
  - com shell sem login foram observados erros intermitentes de DNS/socket.
  - com shell de login (profile carregado), os gates completos ficaram estaveis nesta rodada.

## Atualizacao local Windows 2026-04-23
- HEAD local confirmado: `afdee46`
- estado local nesta sessao:
  - mudancas nao commitadas em `.gitignore`, docs e `tests/test_contract.py`
- ajuste de higiene local:
  - `.gitignore` cobre artefatos temporarios de execucao e backups locais
- gate de integracao com repo `reports` endurecido:
  - README com bloco curto de validacao por `validate-contract`
  - teste novo para garantir import publico leve do pacote (`scrap_report`) sem carregar runtime pesado
- evidencia de validacao desta sessao:
  - `py_compile`: ok
  - `ruff`: ok
  - `ty` completo: bloqueado por ambiente local sem deps sincronizadas e erro de permissao em dirs locais
  - `ty` focado em contrato/public surface: ok
  - `pytest` focado `tests/test_contract.py`: `10 passed`
  - `kluster`: bloqueado por DNS externo (`api.kluster.ai`)

## Atualizacao local Windows 2026-04-23, slice REST 42
- objetivo:
  - endurecer o bloqueio intencional do `sweep-run --runtime rest` fora de `pendentes`
- mudanca:
  - regra de suporte REST no sweep saiu de hardcode e foi centralizada em `REST_SWEEP_SUPPORTED_REPORT_KINDS`
  - `sweep.py` e teste de rejeicao em `tests/test_sweep.py` agora leem a mesma fonte de verdade
- comportamento:
  - permanece igual ao baseline: somente `report_kind=pendentes` no runtime REST do sweep
- evidencias do slice:
  - `py_compile`: ok
  - `ruff`: ok
  - `ty` focado (`config.py`, `sweep.py`): ok
  - `pytest` focado de sweep: bloqueado por falta de `pandas` no ambiente local
  - `kluster`: executou e apontou apenas itens preexistentes fora do escopo do slice

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
- baseline anterior do branch: `f389671`
- gates locais atuais:
  - `py_compile`: ok
  - `ruff`: ok
  - `ty`: ok
  - `pytest`: `202 passed`
- ajuste fechado neste slice:
  - baseline global do `ty check` zerado
  - compatibilidade de testes Windows corrigida para `Path` com separador `/` ou `\\`
- pendencia operacional ainda aberta:
  - preservar ou regenerar `staging/smoke_evidence_windows11.json` nesta copia local
- observacao de evidencia:
  - `staging/smoke_evidence_windows11.json` ausente nesta copia local; existe apenas referencia historica da rodada W11
  - `staging/smoke_evidence_debian13.json` presente e validado

## Harden de dependencias mais recente
- baseline anterior do branch: `ce76125`
- triagem objetiva:
  - alerta medium em `pytest` e alerta low em `Pygments`
  - ambos restritos ao grupo `dev`
  - sem impacto no runtime distribuido
- mitigacao aplicada:
  - `pytest` atualizado para `9.0.3`
  - `Pygments` atualizado para `2.20.0`
- validacao:
  - `py_compile`: ok
  - `ruff`: ok
  - `ty`: ok
  - `pytest`: `201 passed`
- observacao:
  - consulta atual `dependabot/alerts?state=open`: `[]`
  - item de seguranca GitHub considerado fechado neste momento

## Slice Debian13 mais recente
- baseline anterior do branch: `b3c8be6`
- mudanca aplicada:
  - rerun completo em Debian13 real via VMware Fusion como usuario `menon`
  - ownership correto confirmado para `.venv`, `staging` e `downloads`
  - clone errado em `/root/scrap_report` removido
- validacao em Debian13 real:
  - `bash scripts/smoke_debian13.sh`: ok
  - evidencia gerada: `staging/smoke_evidence_debian13.json`
  - `generated_at_utc=2026-04-27T15:57:38.424833+00:00`
  - checks: `py_compile, ruff, pytest, scan_secrets, validate_contract, stage, pipeline_report_only, ingest_latest = ok`
- validacao adicional:
  - `uv run --project . --with ty ty check`: ok
  - `uv run --project . --with pytest python -m pytest -q`: `216 passed`
  - `uv build --out-dir /tmp/scrap_report_build_debian`: ok
  - stash temporario remoto de `egg-info` gerado antes do pull foi removido

## Estado atual da evidencia W11
- resultado atual:
  - `staging/smoke_evidence_windows11.json` nao esta nesta copia local
  - a rodada historica W11 continua documentada
- leitura correta:
  - o gate operacional W11 ja foi exercitado historicamente
  - o artefato precisa ser regenerado ou recolocado para voltar a ficar presente nesta copia local

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

## Atualizacao local Windows 2026-04-24, slice 52
- objetivo:
  - habilitar fluxo de smoke com entrada de usuario valido e opcao de salvar secret
  - manter comportamento default atual sem quebra
  - atualizar docs com comandos operacionais e evidencia REST do dia
- arquivos alterados:
  - `scripts/smoke_windows11.ps1`
  - `scripts/smoke_debian13.sh`
  - `CROSS_PLATFORM_SMOKE.md`
  - `README.md`
  - `ROUND_STATUS.md`
  - `HANDOFF.md`
- mudancas:
  - Windows smoke agora aceita:
    - `-SmokeUsername`
    - `-PromptUsername`
    - `-SetupSecret`
    - `-SecretService`
  - Debian smoke agora aceita:
    - `--smoke-username`
    - `--prompt-username`
    - `--setup-secret`
    - `--secret-service`
  - ambos preservam modo default
  - ambos suportam modo seguro com secret store via setup explicito
  - evidencia dos smokes agora inclui bloco `inputs`
  - Debian trocou `py_compile` por `compileall -q src tests`
- evidencias REST reais atualizadas:
  - `tmp/sam_api_flow_iee3_live_20260424_152745.json` (`status=ok`, `count=50`)
  - `tmp/sweep_rest_iee3_pendentes_live_20260424_152745.json` (`status=ok`, `record_count=119`)
- kluster (apos edicao):
  - revisoes executadas:
    - `69ebc3064ea1da958e1ac9a2`
    - `69ebc33e50b51ca1da54a24b`
    - `69ebc3624ea1da958e1ace56`
    - `69ebc3934ea1da958e1ad0c9`
  - itens de alto/medio com patch minimo foram tratados no proprio slice
  - restaram apenas itens de refatoracao ampla e aviso do fallback transicional Debian
