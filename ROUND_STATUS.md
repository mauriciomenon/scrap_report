# ROUND_STATUS

## Sessao atual
- data: `2026-04-23`
- pasta: `C:\Users\mauri\git\scrap_report`
- branch: `master`
- baseline runtime no inicio desta rodada: `b3c8be6`
- runtime REST em edicao nesta rodada: concluido
- doc sync pendente nesta rodada: nao

## Snapshot executivo
- repo publico existente: sim
- branch operacional: `master`
- runtime Playwright principal: estavel no baseline anterior
- camada REST sem Playwright: entregue em tres niveis
- release mais recente conhecida antes desta rodada: `v0.1.7`

## Slice 51 - hardening do smoke windows11 + destravamento de gates no shell correto
Escopo:
- endurecer `scripts/smoke_windows11.ps1` com falha cedo de ambiente e remocao de credencial em CLI
- fechar findings HIGH/CRITICAL do kluster no script
- validar gate completo em shell com profile/login

Arquivos alterados:
- `scripts/smoke_windows11.ps1`

Mudanca aplicada:
- adicionado `Invoke-NetworkPrecheck` (socket + DNS)
- adicionado `Read-RequiredJson` para leitura segura de artefatos
- `py_compile` trocado para `compileall -q src tests` em chamada unica
- `pipeline report-only` passou a usar `staged_path` de `stage_result.json` (fonte canonica)
- `ingest-latest`:
  - removido `--password` em linha de comando
  - removido `--allow-transitional-plaintext`
  - adicionado `secret get` preflight + `--secure-required`
- erros de parser e guardas adicionais corrigidos no script

Validacao:
- kluster no script (progressao):
  - `69ebb2b74ea1da958e19cec8`: 1 HIGH + 1 MEDIUM + 1 LOW
  - `69ebb2d08a818de8a3dab292`: 1 MEDIUM
  - `69ebb2f08a818de8a3dab4dc`: 1 MEDIUM
  - `69ebb30850b51ca1da53a919`: 1 MEDIUM
  - `69ebb31d8a818de8a3dab841`: 1 CRITICAL + 1 HIGH + 1 MEDIUM
  - `69ebb34b50b51ca1da53ae29`: 2 MEDIUM
  - `69ebb36d8a818de8a3dabe28`: 1 MEDIUM
  - `69ebb39950b51ca1da53b382`: 1 MEDIUM
  - `69ebb3b68a818de8a3dac34b`: 1 HIGH + 2 MEDIUM + 1 LOW
  - `69ebb3f950b51ca1da53ba11`: 1 MEDIUM
  - `69ebb43d50b51ca1da53be9e`: clean
- gates tecnicos:
  - `uv run --python 3.13 python -m py_compile ...`: ok
  - `uv run --python 3.13 ruff check .`: ok
  - `uv run --python 3.13 ty check src`: ok
  - `uv run --python 3.13 pytest -q` focado: `17 passed`
  - `uv run --python 3.13 pytest -q` completo no shell com login: `216 passed`
- smoke windows11 script:
  - executado via `& scripts/smoke_windows11.ps1`
  - chegou ate `secret get` e falhou com mensagem clara por secret ausente para `smoke_user`
  - comportamento esperado apos endurecimento de seguranca

Risco residual:
- baixo para runtime principal (nenhum arquivo `src/` alterado neste slice)
- baixo para script smoke no ponto de seguranca (sem credencial em CLI)
- medio operacional: execucao de smoke completo depende de secret seguro preexistente para o usuario de teste

## Slice 50 - correcao do HIGH do kluster no multiline scanner
Escopo:
- corrigir issue HIGH apontada pelo kluster em `_iter_line_findings`
- manter patch minimo sem alterar contrato de saida

Arquivos alterados:
- `src/scrap_report/secret_scan.py`

Mudanca aplicada:
- removido dedupe local sem limite em `_iter_line_findings`
- dedupe efetivo mantido em `_record_finding` no nivel de `_scan_file`
- multiline agora calcula `match_line` e `match_excerpt` sem descartar match valido por `boundary`

Validacao:
- kluster:
  - rodada 1 apos slice 49: `Review 69eb799f87f9165e6e4b9cc8` (1 HIGH, 1 MEDIUM, 2 LOW)
  - rodada 2 apos patch: `Review 69eb7a6bab084ce82073baa3` (somente 1 LOW)
- gates tecnicos:
  - `uv run --python 3.13 pytest -q` focado: `17 passed`
  - `uv run --python 3.13 python -m py_compile ...`: ok
  - `uv run --python 3.13 ruff check .`: ok
  - `uv run --python 3.13 ty check src`: ok
  - `uv run --python 3.13 pytest -q` completo:
    - bloqueado por ambiente (`asyncio/_overlapped`, WinError 10106)
- scanner operacional:
  - `scan-secrets` default: `status=ok`, `findings_count=0`
  - `scan-secrets --paths src tests README.md`: `status=error`, `findings_count=6` (fixtures intencionais)

Risco residual:
- baixo no escopo do scanner tocado
- baixo/medio para melhoria estrutural (LOW do kluster)
- medio no gate global ate normalizar ambiente Playwright/asyncio do host

## Slice 49 - reduzir falso negativo multiline sem refatoracao ampla
Escopo:
- ampliar captura multiline do scanner de 2 para ate 4 linhas totais por janela
- manter contrato de saida do `scan-secrets`
- reforcar teste de regressao do comportamento multiline

Arquivos alterados:
- `src/scrap_report/secret_scan.py`
- `tests/test_secret_scan.py`

Mudanca aplicada:
- `secret_scan.py`:
  - adicionado `MAX_MULTILINE_FOLLOWUP_LINES = 3`
  - `_iter_line_findings` agora mantem janelas pendentes para triggers multiline
  - captura multiline evoluiu de 2 para ate 4 linhas sem alterar schema de finding
- `tests/test_secret_scan.py`:
  - adicionado `test_scan_paths_detects_multiline_assignment_across_three_lines`

Validacao:
- kluster (obrigatorio):
  - `kluster review file src/scrap_report/secret_scan.py tests/test_secret_scan.py --mode deep`
  - resultado: bloqueado por DNS
  - erro: `lookup api.kluster.ai: getaddrinfow: A non-recoverable error occurred during a database lookup`
- gates tecnicos:
  - `uv run --python 3.13 python -m py_compile ...`: ok
  - `uv run --python 3.13 ruff check .`: ok
  - `uv run --python 3.13 ty check src`: ok
  - `uv run --python 3.13 pytest -q` focado: `17 passed`
  - `uv run --python 3.13 pytest -q` completo:
    - bloqueado por ambiente (`asyncio/_overlapped`, WinError 10106)
- scanner operacional:
  - `scan-secrets` default: `status=ok`, `findings_count=0`
  - `scan-secrets --paths src tests README.md`: `status=error`, `findings_count=6` (fixtures intencionais)

Risco residual:
- baixo no escopo do scanner tocado
- medio operacional por bloqueio DNS do kluster
- medio no gate global ate normalizar ambiente Playwright/asyncio do host

## Slice 48 - estabilidade deterministica de scanner + cache real em redacao
Escopo:
- reduzir variacao cross-platform do `scan-secrets` com ordem deterministica de arquivos
- remover cache inefetivo em `assert_no_sensitive_fields` sem refatoracao ampla
- manter patch minimo e verificavel

Arquivos alterados:
- `src/scrap_report/redaction.py`
- `src/scrap_report/secret_scan.py`
- `tests/test_secret_scan.py`

Mudanca aplicada:
- `redaction.py`:
  - `_is_effectively_safe_key` movido para escopo de modulo com `@lru_cache(maxsize=512)`
  - removido cache interno por chamada em `assert_no_sensitive_fields`
- `secret_scan.py`:
  - varredura de diretorio agora usa `os.walk` com `dirs.sort()` e `files.sort()` para ordem deterministica
- `tests/test_secret_scan.py`:
  - novo teste `test_scan_paths_is_deterministic_by_path_order`

Validacao:
- kluster (obrigatorio):
  - comando:
    - `kluster review file src/scrap_report/redaction.py src/scrap_report/secret_scan.py --mode deep`
    - `kluster review file src/scrap_report/redaction.py src/scrap_report/secret_scan.py tests/test_secret_scan.py --mode deep`
  - resultado:
    - bloqueado por ambiente em ambas tentativas
    - erro: `lookup api.kluster.ai: getaddrinfow: A non-recoverable error occurred during a database lookup`
- gates tecnicos:
  - `uv run --python 3.13 python -m py_compile ...`: ok
  - `uv run --python 3.13 ruff check .`: ok
  - `uv run --python 3.13 ty check src`: ok
  - `uv run --python 3.13 pytest -q` focado: `16 passed`
  - `uv run --python 3.13 pytest -q` completo:
    - bloqueado por ambiente (`asyncio/_overlapped`, WinError 10106 no host)
  - tentativa fallback `uv run --python 3.12 pytest -q`:
    - bloqueada por DNS para baixar wheel (`numpy`, os error 11003)
- scanner operacional:
  - `scan-secrets` default: `status=ok`, `findings_count=0`
  - `scan-secrets --paths src tests README.md`: `status=error`, `findings_count=6` (fixtures de teste intencionais)

Risco residual:
- baixo para runtime tocado no slice
- medio operacional enquanto DNS externo bloquear kluster e fallback de dependencias
- suite completa continua dependente de resolver ambiente `asyncio` no Python 3.13 deste host

## Slice 47 - hardening final do scanner e redacao de secrets
Escopo:
- fechar o falso negativo estrutural de `scan-secrets` para diretorios e multiline simples
- endurecer `redaction.py` sem refatoracao ampla
- validar novamente com gates tecnicos completos e kluster

Arquivos alterados:
- `src/scrap_report/sensitive_patterns.py` (novo)
- `src/scrap_report/secret_scan.py`
- `src/scrap_report/redaction.py`
- `tests/test_secret_scan.py`
- `tests/test_redaction.py`

Mudanca aplicada:
- scanner com normalizacao de roots, dedupe de candidatos e detecao multiline em janela curta
- leitura de arquivo em stream no scanner, evitando carga integral em memoria
- padroes sensiveis compartilhados em modulo unico
- redacao com cobertura para bearer, atribuicao sensivel e keyword standalone
- validacao de campos sensiveis com travessia iterativa e protecao de ciclo

Validacao:
- kluster (iterativo no slice):
  - rodada inicial: findings `HIGH/MEDIUM/LOW`
  - rodadas intermediarias: `HIGH` eliminado
  - rodada final: findings `MEDIUM/LOW` de qualidade/performance ampla, sem bloqueador funcional confirmado
- gates tecnicos:
  - `uv run --python 3.13 python -m py_compile ...`: ok
  - `uv run --python 3.13 ruff check .`: ok
  - `uv run --python 3.13 ty check src`: ok
  - `uv run --python 3.13 pytest -q` focado: `15 passed`
  - `uv run --python 3.13 pytest -q`: `214 passed`
- scanner operacional:
  - `scan-secrets` default: `status=ok`, `findings_count=0`
  - `scan-secrets --paths src tests README.md`: `status=error`, `findings_count=4` (fixtures de teste intencionais)

Risco residual:
- baixo para runtime principal
- baixo para scanner no modo default
- medio nao bloqueante para melhorias amplas de arquitetura/performance sugeridas pelo kluster
- suporte multiline permanece deliberadamente limitado a janela curta de 2 linhas

## Slice 45 - varredura de furos grandes e hardening de secrets scan
Escopo:
- executar varredura geral de risco alto no codigo e no fluxo operacional
- corrigir falso negativo critico do comando `scan-secrets` em diretorios
- endurecer redacao para evitar vazamento de valor sensivel em logs

Arquivos alterados:
- `src/scrap_report/secret_scan.py`
- `src/scrap_report/redaction.py`
- `src/scrap_report/cli.py`
- `scripts/smoke_windows11.ps1`
- `scripts/smoke_debian13.sh`
- `tests/test_secret_scan.py`
- `tests/test_redaction.py`
- `tests/test_cli.py`

Mudanca aplicada:
- `scan_paths` agora varre diretorios de forma recursiva e evita reprocessar arquivo duplicado
- padroes do scanner endurecidos para reduzir ruido operacional de fixture curta
- `scan-secrets` default ajustado para `src` e `README.md` (evita erro permanente por fixtures de `tests`)
- scripts de smoke W11/Debian13 alinhados para o mesmo escopo de scanner
- `redact_text` agora mascara atribuicoes sensiveis e bearer token antes da redacao por palavra-chave

Validacao:
- gates globais:
  - `uv run --python 3.13 python -m compileall -q src tests scripts`: ok
  - `uv run --python 3.13 ruff check src tests scripts`: ok
  - `uv run --python 3.13 ty check src`: ok
  - `uv run --python 3.13 pytest -q`: `208 passed`
- evidencias focadas:
  - `uv run --python 3.13 python -m scrap_report.cli scan-secrets`: `status=ok, findings_count=0`
  - `uv run --python 3.13 python -m scrap_report.cli scan-secrets --paths src tests README.md`: `status=error, findings_count=3` (fixtures de teste intencionais)

Risco residual:
- baixo para runtime principal
- baixo/medio para uso manual do scanner com `tests` incluido (fixtures intencionais continuam sinalizados)

## Slice 46 - fechamento do falso negativo estrutural + redacao robusta
Escopo:
- corrigir falso negativo estrutural do `scan-secrets` para diretorios
- endurecer redacao para evitar vazamento acidental em atribuicoes sensiveis
- revalidar com kluster e gates locais completos

Arquivos alterados:
- `src/scrap_report/sensitive_patterns.py` (novo)
- `src/scrap_report/secret_scan.py`
- `src/scrap_report/redaction.py`
- `tests/test_secret_scan.py`
- `tests/test_redaction.py`

Mudanca aplicada:
- scanner agora varre diretorio de forma recursiva com leitura em stream, sem depender de leitura integral de arquivo
- padroes sensiveis compartilhados em modulo unico para reduzir drift entre scanner e redacao
- redacao cobre:
  - `Bearer <token>` -> `Bearer ***`
  - `key=value` sensivel -> `key=***`
  - keyword sensivel standalone -> `keyword ***`

Validacao:
- kluster (iterativo no slice):
  - rodada inicial: encontrou issues `HIGH/MEDIUM/LOW`
  - rodadas intermediarias: eliminados `HIGH` e `MEDIUM`
  - rodada final: somente `LOW` nao bloqueantes
- gates tecnicos:
  - `uv run --python 3.13 python -m py_compile ...`: ok
  - `uv run --python 3.13 ruff check ...`: ok
  - `uv run --python 3.13 ty check src`: ok
  - `uv run --python 3.13 pytest -q`: `210 passed`
- scanner operacional:
  - `scan-secrets` default: `status=ok`, `findings_count=0`
  - `scan-secrets --paths src tests README.md`: `status=error`, `findings_count=4` (fixtures de teste intencionais)

Risco residual:
- baixo para runtime atual
- baixo para scanner default
- medio nao bloqueante em qualidade/performance fina apontada por kluster (somente `LOW`)

## Slice 44 - fechamento do smoke cross-platform real
Escopo:
- fechar gate de evidencia real para Windows11 e Debian13
- corrigir falha funcional do roteiro Debian13 sem tocar runtime
- manter patch minimo e verificavel no script operacional

Arquivos alterados:
- `scripts/smoke_debian13.sh`
- `ROUND_STATUS.md`
- `HANDOFF.md`
- `PRE_RELEASE_STATUS.md`
- `CROSS_PLATFORM_SMOKE.md`
- `README.md`

Mudanca aplicada:
- `scripts/smoke_debian13.sh`:
  - selecao do xlsx staged agora le `staging/stage_result.json` em vez de `find|head`
  - validacao explicita de existencia de `staged_path` antes do `pipeline --report-only`
  - `ingest-latest` sem `--password` em linha de comando
  - fallback transicional controlado por `SAM_PASSWORD` em env de processo + `--allow-transitional-plaintext`
  - `platform_label` da evidencia ajustado para `debian13`
  - remocao da duplicacao de pytest no bloco Python de evidencia

Validacao:
- `kluster review file scripts/smoke_debian13.sh`:
  - rodada inicial: 3 issues (1 high + 2 low), corrigidos no mesmo slice
  - rodada intermediaria: 4 issues (medium/low), reduzidos no mesmo slice
  - rodada final: clean
- smoke Windows11 real:
  - `powershell -ExecutionPolicy Bypass -File scripts/smoke_windows11.ps1`
  - resultado: `done`
  - evidencia:
    - [staging\smoke_evidence_windows11.json](C:\Users\mauri\git\scrap_report\staging\smoke_evidence_windows11.json)
    - `generated_at_utc=2026-04-23T16:14:20.9295303Z`
    - checks: `py_compile, ruff, pytest, scan_secrets, validate_contract, stage, pipeline_report_only, ingest_latest = ok`
- smoke Debian13 real (WSL Debian13):
  - `bash scripts/smoke_debian13.sh`
  - tentativa 1: bloqueio externo de DNS no preflight PyPI
  - tentativa 2: `done`
  - evidencia:
    - [staging\smoke_evidence_debian13.json](C:\Users\mauri\git\scrap_report\staging\smoke_evidence_debian13.json)
    - `generated_at_utc=2026-04-23T17:52:22.288728+00:00`
    - checks: `py_compile, ruff, pytest, scan_secrets, validate_contract, stage, pipeline_report_only, ingest_latest = ok`

Risco residual:
- baixo para o patch do script e para a evidencias de smoke
- medio apenas para oscilacao eventual de DNS externo no preflight do PyPI

## Slice 43 - higiene local e demonstrativo REST real `IEE3`
Escopo:
- reduzir ruido local de artefatos temporarios e warnings de status
- validar gates tecnicos reais ponta a ponta apos ajuste de higiene
- executar demonstrativo REST real com lista de SSAs pendentes para `IEE3`
- sincronizar docs para juncao futura com repo `reports`

Arquivos alterados:
- `.gitignore`
- `README.md`
- `ROUND_STATUS.md`
- `HANDOFF.md`
- `PRE_RELEASE_STATUS.md`
- `RECOVERY_BACKLOG.md`

Mudanca aplicada:
- `.gitignore` agora ignora:
  - `.pytest-local/`
  - `.pytest-tmp/`
- removido artefato local literal `%SystemDrive%/` do workspace
- demonstrativo REST real atualizado com artifacts timestampados da `IEE3`

Validacao:
- `kluster review file .gitignore`: 1 issue low inicial (`%SystemDrive%/`), corrigido no mesmo slice
- `kluster review file .gitignore` (re-run): clean
- `uv run --python 3.13 python -c "import pathlib, py_compile ..."`: ok
- `uv run --python 3.13 ruff check .`: ok
- `uv run --python 3.13 ty check src tests`: ok
- `uv run --python 3.13 --with pytest python -m pytest -q`: `202 passed`
- demonstrativo REST real:
  - comando:
    - `uv run --python 3.13 python -m scrap_report.cli sam-api-flow --profile panorama --emitter-sector IEE3 --number-of-years 1 --ca-file tmp/itaipu_root_ca_v2.pem --output-json tmp/sam_api_iee3_pendentes_demo_20260423_130409.json --output-csv tmp/sam_api_iee3_pendentes_demo_20260423_130409.csv --output-xlsx tmp/sam_api_iee3_pendentes_demo_20260423_130409.xlsx`
  - resultado:
    - `status=ok`
    - `count=69`
    - `summary.by_emitter={"IEE3": 69}`
    - primeiros SSAs: `202601253, 202601438, 202602000, 202602187, 202602521, 202603000, 202603208, 202603281, 202603516, 202603522, 202603708, 202603856, 202603857, 202603966, 202603971`
    - artifacts:
      - [tmp\sam_api_iee3_pendentes_demo_20260423_130409.json](C:\Users\mauri\git\scrap_report\tmp\sam_api_iee3_pendentes_demo_20260423_130409.json)
      - [tmp\sam_api_iee3_pendentes_demo_20260423_130409.csv](C:\Users\mauri\git\scrap_report\tmp\sam_api_iee3_pendentes_demo_20260423_130409.csv)
      - [tmp\sam_api_iee3_pendentes_demo_20260423_130409.xlsx](C:\Users\mauri\git\scrap_report\tmp\sam_api_iee3_pendentes_demo_20260423_130409.xlsx)

Risco residual:
- baixo para higiene local e contrato de docs
- medio para fechamento de release cross-platform enquanto Debian13 real e evidencia W11 nao forem fechados

## Slice 41 - gate de integracao com `reports` e higiene de artefatos temporarios
Escopo:
- reduzir ruido local de artefatos temporarios no `git status`
- endurecer prova de consumo externo por import publico leve
- publicar gate rapido de integracao por contrato JSON no README

Arquivos alterados:
- `.gitignore`
- `tests/test_contract.py`
- `README.md`
- `ROUND_STATUS.md`
- `HANDOFF.md`
- `RECOVERY_BACKLOG.md`

Mudanca aplicada:
- `.gitignore` agora ignora artefatos temporarios locais de execucao:
  - `downloads/`
  - `output/`
  - `tmp/`
  - `.backups/`
  - `%SystemDrive%/`
  - `staging/rest_sweep/`
  - `staging/consulta_ssa_print_*.pdf`
- teste novo de contrato:
  - `test_public_import_does_not_load_heavy_runtime_modules`
  - valida em subprocesso que `import scrap_report` nao puxa `playwright`, `pandas` nem `openpyxl`
- README ganhou bloco curto "Gate rapido para integracao com repo `reports`"
  - gera contrato canonico via `validate-contract`
  - lista chaves minimas obrigatorias
  - valida import publico minimo

Validacao:
- `kluster review file tests/test_contract.py README.md`: bloqueado por DNS
  - `lookup api.kluster.ai: getaddrinfow`
- `kluster log`: bloqueado por DNS no mesmo host
- `uv run --python 3.13 --no-sync python -c "import py_compile..."`: ok
- `uv run --python 3.13 --no-sync ruff check .`: ok
- `uv run --python 3.13 --no-sync ty check`: bloqueado
  - `Acesso negado` em `.pytest-local/run` e `.pytest-tmp`
  - ambiente local sem deps resolvidas (`pandas`, `playwright`, `pytest`) com DNS externo indisponivel
- `uv run --python 3.13 --no-sync ty check src/scrap_report/contract.py src/scrap_report/__init__.py`: ok
- `uv run --python 3.13 --no-sync pytest -q tests/test_contract.py`: `10 passed`
- `uv run --python 3.13 --no-sync pytest -q tests/test_contract.py tests/test_cli.py -k "validate_contract or public_package_surface or public_import_does_not_load_heavy_runtime_modules"`: bloqueado por falta de `pandas` no ambiente local sem sync

Risco residual:
- medio
- gate completo de `ty` e `pytest` integrado permanece dependente de ambiente com deps sincronizadas
- Kluster permanece indisponivel enquanto DNS externo para `api.kluster.ai` estiver quebrado

## Slice 42 - endurecer bloqueio REST fora de `pendentes`
Escopo:
- manter comportamento atual sem ampliar suporte REST para novos `report_kind`
- remover hardcode solto e centralizar a regra em constante de configuracao
- evitar regressao por divergencia de mensagem/critico em testes

Arquivos alterados:
- `src/scrap_report/config.py`
- `src/scrap_report/sweep.py`
- `tests/test_sweep.py`
- `ROUND_STATUS.md`
- `HANDOFF.md`

Mudanca aplicada:
- nova constante: `REST_SWEEP_SUPPORTED_REPORT_KINDS=("pendentes",)`
- `SweepRunner._run_rest_item` agora usa a constante para validar suporte REST
- mensagem de erro no item do sweep passa a refletir a constante central
- teste de rejeicao para `executadas` atualizado para validar mensagem baseada na constante

Validacao:
- `kluster review file src/scrap_report/config.py`: 5 issues preexistentes, fora de escopo deste slice
- `kluster review file src/scrap_report/config.py src/scrap_report/sweep.py tests/test_sweep.py`: 4 issues preexistentes, fora de escopo deste slice
- `uv run --python 3.13 --no-sync python -c "import py_compile..."`: ok
- `uv run --python 3.13 --no-sync ruff check src/scrap_report/config.py src/scrap_report/sweep.py tests/test_sweep.py`: ok
- `uv run --python 3.13 --no-sync ty check src/scrap_report/config.py src/scrap_report/sweep.py`: ok
- `uv run --python 3.13 --no-sync pytest -q tests/test_sweep.py -k "rest_mode_rejects_unsupported_report_kind or rest_mode_exports_records_for_pendentes"`: bloqueado por ambiente local sem `pandas`

Risco residual:
- baixo para comportamento funcional do slice (regra continua identica)
- medio para gate local de testes enquanto `pandas` nao estiver disponivel no ambiente desta maquina

## Slice 36 - zerar baseline global do `ty`
Escopo:
- corrigir diagnosticos reais do `ty` em provider Windows e testes
- manter runtime intacto e sem refactor transversal
- registrar a verdade do slice nos docs de controle

Arquivos alterados:
- `src/scrap_report/secret_provider.py`
- `tests/test_config_secrets.py`
- `tests/test_scraper_contract.py`
- `tests/test_secret_provider.py`
- `tests/test_sweep.py`
- `uv.lock`
- `PRE_RELEASE_STATUS.md`
- `HANDOFF.md`
- `CONVERSA_MIGRACAO_STATUS.md`
- `ROUND_STATUS.md`

Mudanca aplicada:
- helpers internos adicionados no provider Windows para isolar `ctypes.windll` e `ctypes.WinError`
- testes ajustados para tipos concretos esperados por `ty`
- monkeypatch do teste Windows endurecido para `Path` com separador de host diferente
- lockfile alinhado com a versao atual do pacote (`0.1.17`)

Validacao:
- `uv run --project . python -m py_compile src/scrap_report/*.py tests/*.py`: ok
- `uv run --project . ruff check .`: ok
- `uv run --project . ty check`: ok
- `uv run --project . --with pytest python -m pytest -q`: `201 passed`
- `kluster_code_review_auto`: clean (0 issues), chat_id `rreu0jm276r`

Risco residual:
- medio
- permanece dependente de rodada Debian13 real com rede estavel
- evidencia W11 historica nao esta preservada nesta copia local em `staging/`

## Slice 37 - harden de dependencias `dev`
Escopo:
- corrigir os 2 alertas abertos do GitHub Security com patch minimo
- manter runtime do pacote intacto
- registrar a triagem objetiva como `dev-only`

Arquivos alterados:
- `pyproject.toml`
- `uv.lock`
- `PRE_RELEASE_STATUS.md`
- `HANDOFF.md`
- `CONVERSA_MIGRACAO_STATUS.md`
- `ROUND_STATUS.md`

Mudanca aplicada:
- `pytest` elevado para `>=9.0.3`
- `Pygments` adicionado no grupo `dev` com `>=2.20.0`
- `uv.lock` regenerado com `pytest 9.0.3` e `Pygments 2.20.0`
- docs atualizados com a classificacao `dev-only`

Triagem:
- `BUG_REAL`: `GHSA-6w46-j5rx-g56g` em `pytest < 9.0.3`
- `BUG_REAL`: `GHSA-5239-wwwm-4pmq` em `Pygments < 2.20.0`
- impacto real no repo: grupo `dev`, sem exposicao no runtime publicado

Validacao:
- `uv tree --project . --group dev`: `pytest 9.0.3`, `Pygments 2.20.0`
- `uv run --project . python -m py_compile src/scrap_report/*.py tests/*.py`: ok
- `uv run --project . ruff check .`: ok
- `uv run --project . ty check`: ok
- `uv run --project . --with pytest python -m pytest -q`: `201 passed`
- `kluster_code_review_auto` em `pyproject.toml`: clean
- `kluster_code_review_auto` em `pyproject.toml;uv.lock`: clean

Risco residual:
- baixo para o bloco de dependencias locais
- consulta atual `dependabot/alerts?state=open`: `[]`
- o bloqueio operacional maior continua sendo o smoke Debian13 real

## Slice 40 - confirmar fechamento dos alertas GitHub
Escopo:
- validar se os alertas de Dependabot realmente fecharam no GitHub
- alinhar os docs com o estado atual sem tocar runtime ou dependencias

Arquivos alterados:
- `PRE_RELEASE_STATUS.md`
- `HANDOFF.md`
- `CONVERSA_MIGRACAO_STATUS.md`
- `ROUND_STATUS.md`

Mudanca aplicada:
- docs atualizados para refletir que a API atual de alertas abertos retorna `[]`
- historico preservado com fechamento explicito do item 1

Validacao:
- `gh api ... /dependabot/alerts?state=open`: `[]`
- `uv.lock`: `pytest 9.0.3`, `Pygments 2.20.0`

Risco residual:
- baixo para supply chain
- permanecem abertos apenas os gates Debian13 real e evidencia W11

## Slice 41 - refazer Debian13 real com usuario correto
Escopo:
- rerodar o smoke Debian13 real como `menon`, sem usar `root` para o repo
- confirmar ownership correto dos artefatos e da `.venv`
- remover o clone incorreto criado em `/root/scrap_report`

Arquivos alterados:
- `PRE_RELEASE_STATUS.md`
- `HANDOFF.md`
- `CONVERSA_MIGRACAO_STATUS.md`
- `ROUND_STATUS.md`

Mudanca aplicada:
- docs atualizados para refletir que o Debian13 real foi validado via VMware Fusion como `menon`
- docs atualizados para refletir que o artefato W11 continua ausente nesta copia local

Validacao remota:
- SSH como `menon`: ok
- preflight PyPI: `200`
- `bash scripts/smoke_debian13.sh`: ok
- `pytest`: `108 passed`
- ownership: `.venv`, `staging`, `downloads` -> `menon:menon`
- `sudo rm -rf /root/scrap_report`: ok

Risco residual:
- baixo para Debian13
- permanece aberta apenas a preservacao ou regeneracao da evidencia W11 nesta copia local

## Slice 43 - smoke Debian self-contained e pronto para W11
Escopo:
- corrigir falha real do smoke Debian em ambiente limpo sem `ruff` preinstalado
- revalidar Mac e Debian antes do ciclo W11
- manter build em `/tmp`, sem artefato versionado

Arquivos alterados:
- `scripts/smoke_debian13.sh`
- `CROSS_PLATFORM_SMOKE.md`
- `PRE_RELEASE_STATUS.md`
- `HANDOFF.md`
- `CONVERSA_MIGRACAO_STATUS.md`
- `ROUND_STATUS.md`

Mudanca aplicada:
- `scripts/smoke_debian13.sh` passou a rodar `uv run --project . --with ruff ruff check .`
- docs atualizados para a evidencia Debian final em `2b0b7bd`

Validacao local Mac:
- `bash -n scripts/smoke_debian13.sh`: ok
- `uv run --project . python -m compileall -q src tests`: ok
- `uv run --project . --with ruff ruff check .`: ok
- `uv run --project . --with ty ty check`: ok
- `uv run --project . --with pytest python -m pytest -q`: `216 passed`
- `uv run --project . python -m scrap_report.cli scan-secrets`: `status=ok`, `findings_count=0`
- `uv build --out-dir /tmp/scrap_report_build_mac_after_smoke_fix`: ok

Validacao Debian13 real:
- `git pull --ff-only`: ok em `/home/menon/scrap_report`
- `bash scripts/smoke_debian13.sh`: ok, `108 passed`
- evidencia: `generated_at_utc=2026-04-27T16:09:19.826461+00:00`
- `uv run --project . --with ty ty check`: ok
- `uv run --project . --with pytest python -m pytest -q`: `216 passed`
- `uv run --project . python -m scrap_report.cli scan-secrets`: `status=ok`, `findings_count=0`
- `uv run --project . python -m scrap_report.cli scan-secrets --paths src README.md`: `status=ok`, `findings_count=0`
- `uv build --out-dir /tmp/scrap_report_build_debian_ready`: ok

Risco residual:
- baixo para Mac e Debian
- pendencia real antes de fechar cross-platform: regenerar ou recolocar `staging/smoke_evidence_windows11.json`

## Slice 42 - readiness Debian final antes do W11
Escopo:
- validar a branch atual em Debian13 real apos o merge remoto e o patch de teste Linux
- provar build de pacote sem artefato no repo
- corrigir a verdade documental sobre W11 local ausente

Arquivos alterados:
- `tests/test_secret_provider.py`
- `src/scrap_report.egg-info/PKG-INFO`
- `src/scrap_report.egg-info/SOURCES.txt`
- `CROSS_PLATFORM_SMOKE.md`
- `PRE_RELEASE_STATUS.md`
- `HANDOFF.md`
- `CONVERSA_MIGRACAO_STATUS.md`
- `ROUND_STATUS.md`

Mudanca aplicada:
- teste `test_windows_provider_presence_only` agora mocka a descoberta de executavel PowerShell
- metadata tracked de pacote atualizada por `uv build`
- docs atualizados para Debian13 real validado como `menon` em `0a2d759`
- docs atualizados para W11: rodada historica existe, mas artefato local ainda nao esta presente

Validacao local:
- `uv run --project . python -m compileall -q src tests`: ok
- `uv run --project . ruff check .`: ok
- `uv run --project . ty check`: ok
- `uv run --project . --with pytest python -m pytest -q`: `216 passed`
- `uv run --project . python -m scrap_report.cli scan-secrets`: `status=ok`, `findings_count=0`
- `uv run --project . python -m scrap_report.cli scan-secrets --paths src README.md`: `status=ok`, `findings_count=0`
- `uv build --out-dir /tmp/scrap_report_build_local`: ok

Validacao Debian13 real:
- `git pull --ff-only`: ok em `/home/menon/scrap_report`
- `bash scripts/smoke_debian13.sh`: ok
- `uv run --project . --with ty ty check`: ok
- `uv run --project . --with pytest python -m pytest -q`: `216 passed`
- `uv run --project . python -m scrap_report.cli scan-secrets`: `status=ok`, `findings_count=0`
- `uv run --project . python -m scrap_report.cli scan-secrets --paths src README.md`: `status=ok`, `findings_count=0`
- `uv build --out-dir /tmp/scrap_report_build_debian`: ok

Risco residual:
- baixo para Debian13
- pendencia real antes do W11: regenerar ou recolocar `staging/smoke_evidence_windows11.json`

## Slice 38 - endurecer o smoke Debian13
Escopo:
- falhar cedo quando o host nao tiver conectividade minima com o PyPI
- registrar essa regra no runbook cross-platform
- manter a leitura correta: evidencias locais nao substituem host Debian13 real

Arquivos alterados:
- `scripts/smoke_debian13.sh`
- `CROSS_PLATFORM_SMOKE.md`
- `PRE_RELEASE_STATUS.md`
- `HANDOFF.md`
- `CONVERSA_MIGRACAO_STATUS.md`
- `ROUND_STATUS.md`

Mudanca aplicada:
- preflight HTTP para `https://pypi.org/simple/wheel/` antes do `uv sync`
- mensagem de erro objetiva para bloqueio de rede/host
- documentacao ajustada para diferenciar validacao local do gate Debian13 real

Validacao:
- `bash -n scripts/smoke_debian13.sh`: ok
- `bash scripts/smoke_debian13.sh`: ok neste host atual
- evidencia gerada: `staging/smoke_evidence_debian13.json`
- `kluster_code_review_auto` em `scripts/smoke_debian13.sh`: clean
- `kluster_code_review_auto` em `CROSS_PLATFORM_SMOKE.md`: clean

Risco residual:
- medio
- o gate Debian13 continua aberto enquanto nao houver execucao em host Debian13 real

## Slice 39 - fechar a verdade da evidencia W11
Escopo:
- confirmar se `smoke_evidence_windows11.json` ainda existe em algum local recuperavel
- evitar qualquer fabricacao manual de evidencia
- deixar a instrucao operacional explicita para regeneracao no host W11

Arquivos alterados:
- `WINDOWS11_READINESS.md`
- `WINDOWS_AGENT_INSTRUCTIONS.md`
- `CROSS_PLATFORM_SMOKE.md`
- `PRE_RELEASE_STATUS.md`
- `HANDOFF.md`
- `CONVERSA_MIGRACAO_STATUS.md`
- `ROUND_STATUS.md`

Mudanca aplicada:
- runbooks atualizados para exigir o retorno do artefato real `staging/smoke_evidence_windows11.json`
- docs de controle atualizados para refletir que o arquivo nao esta nesta copia local

Diagnostico:
- busca local no repo: sem arquivo
- busca em `~/git`: sem arquivo
- busca em `~/Downloads`: sem arquivo

Validacao:
- nenhuma edicao de runtime
- integridade de status preservada: sem JSON fabricado

Risco residual:
- medio
- a rodada W11 continua aberta ate o artefato ser regenerado ou recolocado

## Slice DOC_SYNC - verdade atual dos docs de controle
Escopo:
- alinhar `PRE_RELEASE_STATUS.md`, `HANDOFF.md` e `CONVERSA_MIGRACAO_STATUS.md` ao estado atual do repo
- explicitar que caminhos Windows em handoff sao contexto operacional, nao raiz universal desta copia
- neutralizar contradicoes antigas sobre criacao do repo publico

Arquivos alterados:
- `PRE_RELEASE_STATUS.md`
- `HANDOFF.md`
- `CONVERSA_MIGRACAO_STATUS.md`
- `ROUND_STATUS.md`

Mudanca aplicada:
- `PRE_RELEASE_STATUS.md` agora referencia `6bb3059` e sync com `origin/master`
- `HANDOFF.md` agora separa repo local desta copia de referencias Windows
- `CONVERSA_MIGRACAO_STATUS.md` agora abre com bloco `Current truth` e marca o restante como historico

Validacao:
- `uv run --project . python -m py_compile src/scrap_report/*.py tests/*.py`: ok
- `uv run --project . ruff check .`: ok
- `uv run --project . ty check`: baseline vermelho fora do slice
  - `ctypes.windll` e `ctypes.WinError` em `secret_provider.py`
  - contratos de tipo em `tests/test_scraper_contract.py`, `tests/test_sweep.py` e `tests/test_config_secrets.py`
- `uv run --project . --with pytest python -m pytest -q tests/test_contract.py tests/test_cli.py tests/test_pipeline_offline.py tests/test_scraper_contract.py tests/test_file_ops.py tests/test_reporting.py`: `107 passed`
- `kluster_code_review_auto`: clean (0 issues), chat_id `rreu0jm276r`

## Current truth do runtime
### Fluxo Playwright
- `numero_ssa` validado para:
  - `consulta_ssa`
  - `consulta_ssa_print`
  - `aprovacao_emissao`
- `data de emissao` validada para:
  - `executadas`
  - `pendentes`
  - `pendentes_execucao`
  - `consulta_ssa`
  - `consulta_ssa_print`
  - `aprovacao_cancelamento`
  - `reprogramacoes`
- `aprovacao_emissao` continua bloqueado para `data de emissao`
- `derivadas_relacionadas` continua bloqueado para `data de emissao`

### Fluxo REST sem Playwright
- nivel 1:
  - API interna reutilizavel em `sam_api.py`
- nivel 2:
  - comando opinativo `sam-api-flow`
- nivel 3:
  - fluxo totalmente independente `sam-api-standalone`
- trilha TLS operacional:
  - `sam-api-cert`
  - `--ca-file`
  - `--rest-ca-file`
- filtros REST atuais:
  - executor
  - emissor
  - localizacao
  - `year_week`
  - `emission_date`
  - lista de SSAs
- exportacao REST atual:
  - `json`
  - `csv`
  - `xlsx`
  - resumo `xlsx`
- o `sweep-run --runtime rest` para `pendentes` nao exige credencial

## Evidencia operacional rodada 2026-03-23
### Slice atual: pacote importavel para outros projetos
Escopo:
- alinhar metadados de pacote e entrypoint instalavel
- expor discovery programatico por import
- remover dependencia de Playwright na carga inicial de `scrap_report.cli`

Mudanca aplicada:
- `pyproject.toml` agora declara:
  - `version = 0.1.17`
  - `readme = README.md`
  - script `scrap-report = scrap_report.cli:main`
- `scrap_report` agora expõe:
  - `__version__`
  - `build_contract_catalog()`
  - `validate_contract_definition()`
  - `validate_payload_schema()`
- `validate-contract` agora publica tambem:
  - `contract.package.package_name`
  - `contract.package.package_version`
  - `contract.package.import_name`
  - `contract.package.cli_entrypoint`
  - `contract.package.module_entrypoint`
- `scrap_report.cli` passou a usar wrappers lazy para os caminhos que antes puxavam Playwright na importacao

Quality gates do slice:
```powershell
C:\Users\mauri\.pyenv\pyenv-win\versions\3.13.9\python.exe -m py_compile src\scrap_report\__init__.py src\scrap_report\contract.py src\scrap_report\cli.py tests\test_contract.py tests\test_cli.py
C:\Users\mauri\.local\bin\ruff.exe check src\scrap_report\__init__.py src\scrap_report\contract.py src\scrap_report\cli.py tests\test_contract.py tests\test_cli.py
C:\Users\mauri\.local\bin\ty.exe check --python C:\Users\mauri\.pyenv\pyenv-win\versions\3.13.9\python.exe src\scrap_report\__init__.py src\scrap_report\contract.py src\scrap_report\cli.py
C:\Users\mauri\.pyenv\pyenv-win\versions\3.13.9\python.exe -m pytest -q tests\test_contract.py -p no:cacheprovider
```

Resultados:
- `py_compile`: ok
- `ruff`: ok
- `ty` focado nos arquivos alterados: ok
- `pytest tests/test_contract.py`: `9 passed`
- `pytest tests/test_cli.py`: bloqueado por `PermissionError` do sandbox no `tmp_path`
- `ty check src`: bloqueado por baseline anterior em `reporting.py`, fora deste slice

Smokes reais deste slice:
```powershell
$env:PYTHONPATH='src'; C:\Users\mauri\.pyenv\pyenv-win\versions\3.13.9\python.exe -c "import scrap_report; import scrap_report.cli; print(scrap_report.__version__)"
$env:PYTHONPATH='src'; C:\Users\mauri\.pyenv\pyenv-win\versions\3.13.9\python.exe -m scrap_report.cli validate-contract --output-json tmp\contract_package_v1.json
```

Resultados reais:
- `import scrap_report`: ok
- `import scrap_report.cli`: ok
- `scrap_report.__version__ = 0.1.17`
- `validate-contract`: ok
- artefato:
  - `tmp\contract_package_v1.json`
- tooling de review:
  - `kluster_code_review_auto` no lote completo: timeout apos 120s
  - retry menor em `cli.py`: erro `502`

### Quality gates do slice REST atual
Comandos:
```powershell
uv run python -m py_compile src\scrap_report\sam_api.py src\scrap_report\cli.py src\scrap_report\sweep.py tests\test_sam_api.py tests\test_cli.py tests\test_sweep.py
uv run ruff check src\scrap_report\sam_api.py src\scrap_report\cli.py src\scrap_report\sweep.py tests\test_sam_api.py tests\test_cli.py tests\test_sweep.py
uv run ty check src
uv run pytest -q tests\test_sam_api.py tests\test_cli.py tests\test_sweep.py tests\test_reporting.py tests\test_contract.py
```

Resultados:
- `py_compile`: ok
- `ruff`: ok
- `ty`: ok
- `pytest`: `113 passed`

### Slice atual: telemetria minima unificada para manifests REST
Escopo:
- alinhar `sam-api`, `sam-api-flow` e `sam-api-standalone` ao contrato minimo ja usado no sweep
- manter aliases legados sem quebrar consumo atual

Mudanca aplicada:
- payloads REST agora expõem no topo:
  - `runtime_mode`
  - `telemetry`
  - `manifest_json`

Campos de `telemetry` neste slice:
- `record_count`
- `detail_count`
- `without_detail_count`

Quality gates do slice:
```powershell
uv run python -m py_compile src\scrap_report\contract.py src\scrap_report\cli.py tests\test_contract.py tests\test_cli.py
uv run ruff check src\scrap_report\contract.py src\scrap_report\cli.py tests\test_contract.py tests\test_cli.py
uv run ty check src
uv run pytest -q tests\test_contract.py tests\test_cli.py tests\test_sweep.py tests\test_reporting.py tests\test_sam_api.py
```

Resultados:
- `py_compile`: ok
- `ruff`: ok
- `ty`: ok
- `pytest`: `115 passed`

Smokes reais deste slice:
```powershell
uv run --python 3.13 python -m scrap_report.cli sam-api-flow --profile panorama --emitter-sector IEE3 --number-of-years 1 --ca-file tmp\itaipu_root_ca_v2.pem --output-json tmp\sam_api_iee3_contract_demo_v4.json --output-csv tmp\sam_api_iee3_contract_demo_v4.csv --output-xlsx tmp\sam_api_iee3_contract_demo_v4.xlsx
uv run --python 3.13 python -m scrap_report.cli sam-api-standalone --profile detail-lote --ssa-number 202602521 --ca-file tmp\itaipu_root_ca_v2.pem --output-dir tmp\sam_api_contract_detail_v1 --output-json tmp\sam_api_contract_detail_v1.json
uv run --python 3.13 python -m scrap_report.cli sweep-run --report-kind pendentes --scope-mode emissor --setores-emissor IEE3 --year-week-start 202608 --year-week-end 202612 --runtime rest --rest-ca-file tmp\itaipu_root_ca_v2.pem --output-json tmp\sweep_rest_iee3_contract_v3.json
```

Resultados reais:
- `sam-api-flow`:
  - `status=ok`
  - `runtime_mode=rest`
  - `telemetry.record_count=39`
  - `telemetry.detail_count=0`
  - `telemetry.without_detail_count=39`
  - `manifest_json=tmp\\sam_api_iee3_contract_demo_v4.json`
- `sam-api-standalone`:
  - `status=ok`
  - `runtime_mode=rest`
  - `telemetry.record_count=1`
  - `telemetry.detail_count=1`
  - `telemetry.without_detail_count=0`
  - `manifest_json=tmp\\sam_api_contract_detail_v1.json`
- `sweep-run --runtime rest`:
  - `status=ok`
  - `runtime_mode=rest`
  - `item_count=1`
  - `success_count=1`
  - `manifest_json=tmp\\sweep_rest_iee3_contract_v3.json`
  - `items[0].telemetry.record_count=26`
  - `items[0].telemetry.detail_count=26`
  - `items[0].telemetry.without_detail_count=0`

### Slice atual: aliases canonicos de artefatos e descoberta por `validate-contract`
Escopo:
- alinhar os artefatos Playwright ao mesmo modelo canonico de consumo
- publicar o mapa de aliases por JSON em `validate-contract`

Mudanca aplicada:
- `reporting.artifacts_to_dict()` agora mantem:
  - `dados`
  - `estatisticas`
  - `relatorio_txt`
- e tambem expõe:
  - `data_xlsx`
  - `summary_xlsx`
  - `report_txt`
- `validate-contract` agora publica:
  - `contract.exports.playwright_reports`
  - `contract.exports.rest_reports`

Quality gates do slice:
```powershell
uv run python -m py_compile src\scrap_report\contract.py src\scrap_report\cli.py src\scrap_report\reporting.py tests\test_contract.py tests\test_cli.py tests\test_reporting.py
uv run ruff check src\scrap_report\contract.py src\scrap_report\cli.py src\scrap_report\reporting.py tests\test_contract.py tests\test_cli.py tests\test_reporting.py
uv run ty check src
uv run pytest -q tests\test_contract.py tests\test_cli.py tests\test_reporting.py tests\test_sam_api.py tests\test_sweep.py
```

Resultados:
- `py_compile`: ok
- `ruff`: ok
- `ty`: ok
- `pytest`: `115 passed`

Smokes reais deste slice:
```powershell
uv run --python 3.13 python -m scrap_report.cli validate-contract --output-json tmp\contract_v2.json
uv run --python 3.13 python -m scrap_report.cli report-from-excel --excel tmp\report_contract_input.xlsx --output-dir tmp\report_contract_out --report-kind pendentes --output-json tmp\report_contract_out.json
uv run --python 3.13 python -m scrap_report.cli sam-api-flow --profile panorama --emitter-sector IEE3 --number-of-years 1 --ca-file tmp\itaipu_root_ca_v2.pem --output-json tmp\sam_api_iee3_contract_demo_v5.json --output-csv tmp\sam_api_iee3_contract_demo_v5.csv --output-xlsx tmp\sam_api_iee3_contract_demo_v5.xlsx
```

Resultados reais:
- `validate-contract`:
  - `status=ok`
  - `contract.exports.playwright_reports.dados=data_xlsx`
  - `contract.exports.playwright_reports.estatisticas=summary_xlsx`
  - `contract.exports.rest_reports.csv=data_csv`
- `report-from-excel`:
  - `status=ok`
  - `reports.dados` presente
  - `reports.estatisticas` presente
  - `reports.relatorio_txt` presente
  - `reports.data_xlsx` presente
  - `reports.summary_xlsx` presente
  - `reports.report_txt` presente
- `sam-api-flow`:
  - `status=ok`
  - `runtime_mode=rest`
  - `telemetry.record_count=39`
  - `exports.data_csv` presente
  - `exports.data_xlsx` presente
  - `manifest_json` presente

### Slice atual: contrato descobrivel por fluxo para o repo de reports
Escopo:
- publicar em `validate-contract` qual schema cada fluxo deve usar
- publicar os campos minimos que o consumidor deve esperar por fluxo

Mudanca aplicada:
- `validate-contract` agora expõe:
  - `contract.preferred_contracts`
  - `contract.minimum_fields_by_flow`

Quality gates do slice:
```powershell
uv run python -m py_compile src\scrap_report\contract.py src\scrap_report\cli.py tests\test_contract.py tests\test_cli.py
uv run ruff check src\scrap_report\contract.py src\scrap_report\cli.py tests\test_contract.py tests\test_cli.py
uv run ty check src
uv run pytest -q tests\test_contract.py tests\test_cli.py tests\test_reporting.py tests\test_sam_api.py tests\test_sweep.py
```

Resultados:
- `py_compile`: ok
- `ruff`: ok
- `ty`: ok
- `pytest`: `115 passed`

Smokes reais deste slice:
```powershell
uv run --python 3.13 python -m scrap_report.cli validate-contract --output-json tmp\contract_v3.json
uv run --python 3.13 python -m scrap_report.cli sam-api-flow --profile panorama --emitter-sector IEE3 --number-of-years 1 --ca-file tmp\itaipu_root_ca_v2.pem --output-json tmp\sam_api_iee3_contract_demo_v6.json --output-csv tmp\sam_api_iee3_contract_demo_v6.csv --output-xlsx tmp\sam_api_iee3_contract_demo_v6.xlsx
```

Resultados reais:
- `validate-contract`:
  - `status=ok`
  - `contract.preferred_contracts.sam_api_flow.schema=sam_api_result`
  - `contract.preferred_contracts.sam_api_standalone.schema=sam_api_flow_result`
  - `contract.preferred_contracts.sweep_run_rest.schema=sweep_result`
  - `contract.minimum_fields_by_flow.sam_api_flow` presente
  - `contract.minimum_fields_by_flow.sweep_run_rest` presente
- `sam-api-flow`:
  - `status=ok`
  - continua compatível com o contrato publicado
  - `runtime_mode=rest`
  - `manifest_json` presente

### Slice atual: recomendacao de consumo por caso
Escopo:
- publicar em `validate-contract` qual fluxo o consumidor deve usar e quais campos minimos deve ler

Mudanca aplicada:
- `validate-contract` agora expõe:
  - `contract.preferred_contracts`
  - `contract.minimum_fields_by_flow`

Quality gates do slice:
```powershell
uv run python -m py_compile src\scrap_report\contract.py src\scrap_report\cli.py tests\test_contract.py tests\test_cli.py
uv run ruff check src\scrap_report\contract.py src\scrap_report\cli.py tests\test_contract.py tests\test_cli.py
uv run ty check src
uv run pytest -q tests\test_contract.py tests\test_cli.py tests\test_reporting.py tests\test_sam_api.py tests\test_sweep.py
```

Resultados:
- `py_compile`: ok
- `ruff`: ok
- `ty`: ok
- `pytest`: `115 passed`

Smokes reais deste slice:
```powershell
uv run --python 3.13 python -m scrap_report.cli validate-contract --output-json tmp\contract_v3.json
uv run --python 3.13 python -m scrap_report.cli sam-api-flow --profile panorama --emitter-sector IEE3 --number-of-years 1 --ca-file tmp\itaipu_root_ca_v2.pem --output-json tmp\sam_api_iee3_contract_demo_v6.json --output-csv tmp\sam_api_iee3_contract_demo_v6.csv --output-xlsx tmp\sam_api_iee3_contract_demo_v6.xlsx
```

Resultados reais:
- `validate-contract`:
  - `status=ok`
  - `contract.preferred_contracts.sam_api.schema=sam_api_result`
  - `contract.preferred_contracts.sam_api_standalone.schema=sam_api_flow_result`
  - `contract.preferred_contracts.sweep_run_rest.schema=sweep_result`
  - `contract.minimum_fields_by_flow.sam_api_flow` presente
  - `contract.minimum_fields_by_flow.sweep_run_rest` presente
- `sam-api-flow`:
  - `status=ok`
  - `runtime_mode=rest`
  - `manifest_json` presente
  - continua coerente com o discovery publicado

### Exportacao real da CA raiz REST
Comando:
```powershell
uv run --python 3.13 python -m scrap_report.cli sam-api-cert --output tmp/itaipu_root_ca_v2.pem --output-json tmp/sam_api_cert_v2.json
```

Resultado:
- manifest: [tmp\sam_api_cert_v2.json](C:\Users\mauri\git\scrap_report\tmp\sam_api_cert_v2.json)
- `status=ok`
- `subject=CN=Itaipu Binacional Root CA 3`
- `issuer=CN=Itaipu Binacional Root CA 3`
- `certificate_count=2`

### TLS estrito validado com `--ca-file`
Comando:
```powershell
uv run --python 3.13 python -m scrap_report.cli sam-api --ssa-number 202602521 --ca-file tmp/itaipu_root_ca_v2.pem --output-json tmp/sam_api_ca_detail_relative_v2.json
```

Resultado:
- manifest: [tmp\sam_api_ca_detail_relative_v2.json](C:\Users\mauri\git\scrap_report\tmp\sam_api_ca_detail_relative_v2.json)
- `status=ok`
- `verify_tls=true`
- `warnings=["custom_ca_file_configured"]`
- `count=1`

### Fluxo independente detalhado com `--ca-file`
Comando:
```powershell
uv run --python 3.13 python -m scrap_report.cli sam-api-standalone --profile detail-lote --ssa-number 202602521 --ssa-number 202600001 --ca-file C:/Users/mauri/git/scrap_report/tmp/itaipu_root_ca_v2.pem --output-dir tmp/sam_api_detail_ca_v3 --output-json tmp/sam_api_detail_ca_v3.json
```

Resultado:
- manifest: [tmp\sam_api_detail_ca_v3.json](C:\Users\mauri\git\scrap_report\tmp\sam_api_detail_ca_v3.json)
- `status=ok`
- `verify_tls=true`
- `count=2`

### `sweep-run` REST sem credencial, um setor
Comando:
```powershell
uv run --python 3.13 python -m scrap_report.cli sweep-run --report-kind pendentes --scope-mode emissor --setores-emissor IEE3 --year-week-start 202608 --year-week-end 202612 --runtime rest --rest-ca-file C:/Users/mauri/git/scrap_report/tmp/itaipu_root_ca_v2.pem --output-json tmp/sweep_rest_one_ca_v3.json
```

Resultado:
- manifest: [tmp\sweep_rest_one_ca_v3.json](C:\Users\mauri\git\scrap_report\tmp\sweep_rest_one_ca_v3.json)
- `status=ok`
- `runtime_mode=rest`
- `item_count=1`
- `success_count=1`

### `sweep-run` REST sem credencial, varios setores
Comando:
```powershell
uv run --python 3.13 python -m scrap_report.cli sweep-run --report-kind pendentes --scope-mode emissor --setores-emissor IEE1 IEE3 --year-week-start 202608 --year-week-end 202612 --runtime rest --rest-ca-file C:/Users/mauri/git/scrap_report/tmp/itaipu_root_ca_v2.pem --output-json tmp/sweep_rest_multi_ca_v3.json
```

Resultado:
- manifest: [tmp\sweep_rest_multi_ca_v3.json](C:\Users\mauri\git\scrap_report\tmp\sweep_rest_multi_ca_v3.json)
- `status=ok`
- `item_count=2`
- `success_count=2`

### `sweep-run` REST sem credencial, geral sem detalhamento
Comando:
```powershell
uv run --python 3.13 python -m scrap_report.cli sweep-run --report-kind pendentes --scope-mode nenhum --runtime rest --rest-ca-file tmp/itaipu_root_ca_v2.pem --output-json tmp/sweep_rest_all_ca_relative_v2.json
```

Resultado:
- manifest: [tmp\sweep_rest_all_ca_relative_v2.json](C:\Users\mauri\git\scrap_report\tmp\sweep_rest_all_ca_relative_v2.json)
- `status=ok`
- `item_count=1`
- `success_count=1`
- item unico:
  - `record_count=6262`
  - `detail_count=0`
  - `without_detail_count=6262`

### `sweep-run` REST sem credencial, geral com detalhamento por `year_week`
Comando:
```powershell
uv run --python 3.13 python -m scrap_report.cli sweep-run --report-kind pendentes --scope-mode nenhum --year-week-start 202608 --year-week-end 202612 --runtime rest --rest-ca-file tmp/itaipu_root_ca_v2.pem --output-json tmp/sweep_rest_all_yearweek_ca_v4.json
```

Resultado:
- manifest: [tmp\sweep_rest_all_yearweek_ca_v4.json](C:\Users\mauri\git\scrap_report\tmp\sweep_rest_all_yearweek_ca_v4.json)
- `status=ok`
- `item_count=1`
- `success_count=1`
- item unico:
  - `record_count=1193`
  - `detail_count=1193`
  - `without_detail_count=0`
- observacao:
  - o wrapper do terminal marcou timeout, mas o processo concluiu e gravou manifest e artefatos validos

### `sweep-run` REST sem credencial, geral com detalhamento por `emission_date`, 1 dia
Comando:
```powershell
uv run --python 3.13 python -m scrap_report.cli sweep-run --report-kind pendentes --scope-mode nenhum --emission-date-start 2026-02-23 --emission-date-end 2026-02-23 --runtime rest --rest-ca-file tmp/itaipu_root_ca_v2.pem --output-json tmp/sweep_rest_all_emission_date_day_v3.json
```

Resultado:
- manifest: [tmp\sweep_rest_all_emission_date_day_v3.json](C:\Users\mauri\git\scrap_report\tmp\sweep_rest_all_emission_date_day_v3.json)
- `status=ok`
- `item_count=1`
- `success_count=1`
- item unico:
  - `record_count=41`
  - `detail_count=41`
  - `without_detail_count=0`

### `sweep-run` REST sem credencial, geral com detalhamento por `emission_date`, 3 dias
Comando:
```powershell
uv run --python 3.13 python -m scrap_report.cli sweep-run --report-kind pendentes --scope-mode nenhum --emission-date-start 2026-02-23 --emission-date-end 2026-02-25 --runtime rest --rest-ca-file tmp/itaipu_root_ca_v2.pem --output-json tmp/sweep_rest_all_emission_date_range_v3.json
```

Resultado:
- manifest: [tmp\sweep_rest_all_emission_date_range_v3.json](C:\Users\mauri\git\scrap_report\tmp\sweep_rest_all_emission_date_range_v3.json)
- `status=ok`
- `item_count=1`
- `success_count=1`
- item unico:
  - `record_count=109`
  - `detail_count=109`
  - `without_detail_count=0`

### `sweep-run` REST sem credencial, geral com detalhamento por `emission_date`, 7 dias
Comando:
```powershell
uv run --python 3.13 python -m scrap_report.cli sweep-run --report-kind pendentes --scope-mode nenhum --emission-date-start 2026-02-23 --emission-date-end 2026-03-01 --runtime rest --rest-ca-file tmp/itaipu_root_ca_v2.pem --output-json tmp/sweep_rest_all_emission_date_week_v1.json
```

Resultado:
- manifest: [tmp\sweep_rest_all_emission_date_week_v1.json](C:\Users\mauri\git\scrap_report\tmp\sweep_rest_all_emission_date_week_v1.json)
- `status=ok`
- `item_count=1`
- `success_count=1`
- item unico:
  - `record_count=240`
  - `detail_count=240`
  - `without_detail_count=0`

### `sweep-run` REST sem credencial, geral com detalhamento por `emission_date`, 14 dias
Comando:
```powershell
uv run --python 3.13 python -m scrap_report.cli sweep-run --report-kind pendentes --scope-mode nenhum --emission-date-start 2026-02-23 --emission-date-end 2026-03-08 --runtime rest --rest-ca-file tmp/itaipu_root_ca_v2.pem --output-json tmp/sweep_rest_all_emission_date_14d_v1.json
```

Resultado:
- manifest: [tmp\sweep_rest_all_emission_date_14d_v1.json](C:\Users\mauri\git\scrap_report\tmp\sweep_rest_all_emission_date_14d_v1.json)
- `status=ok`
- `item_count=1`
- `success_count=1`
- item unico:
  - `record_count=494`
  - `detail_count=494`
  - `without_detail_count=0`
- observacao:
  - o wrapper do terminal marcou timeout, mas o processo concluiu e gravou manifest e artefatos validos

### `sweep-run` REST sem credencial, geral com detalhamento por `emission_date`, 21 dias
Comando:
```powershell
uv run --python 3.13 python -m scrap_report.cli sweep-run --report-kind pendentes --scope-mode nenhum --emission-date-start 2026-02-23 --emission-date-end 2026-03-15 --runtime rest --rest-ca-file tmp/itaipu_root_ca_v2.pem --output-json tmp/sweep_rest_all_emission_date_21d_v1.json
```

Resultado:
- manifest: [tmp\sweep_rest_all_emission_date_21d_v1.json](C:\Users\mauri\git\scrap_report\tmp\sweep_rest_all_emission_date_21d_v1.json)
- `status=ok`
- `item_count=1`
- `success_count=1`
- item unico:
  - `record_count=730`
  - `detail_count=730`
  - `without_detail_count=0`
- observacao:
  - concluiu dentro de timeout de shell maior

### `sweep-run` REST sem credencial, geral com detalhamento por `emission_date`, 28 dias
Comando:
```powershell
uv run --python 3.13 python -m scrap_report.cli sweep-run --report-kind pendentes --scope-mode nenhum --emission-date-start 2026-02-23 --emission-date-end 2026-03-22 --runtime rest --rest-ca-file tmp/itaipu_root_ca_v2.pem --output-json tmp/sweep_rest_all_emission_date_28d_v1.json
```

Resultado:
- manifest: [tmp\sweep_rest_all_emission_date_28d_v1.json](C:\Users\mauri\git\scrap_report\tmp\sweep_rest_all_emission_date_28d_v1.json)
- `status=ok`
- `item_count=1`
- `success_count=1`
- item unico:
  - `record_count=1103`
  - `detail_count=1103`
  - `without_detail_count=0`
- observacao:
  - concluiu dentro de timeout de shell maior

### `sweep-run` REST sem credencial, geral com detalhamento por `emission_date`, 35 dias
Comando:
```powershell
uv run --python 3.13 python -m scrap_report.cli sweep-run --report-kind pendentes --scope-mode nenhum --emission-date-start 2026-02-23 --emission-date-end 2026-03-29 --runtime rest --rest-ca-file tmp/itaipu_root_ca_v2.pem --output-json tmp/sweep_rest_all_emission_date_35d_v1.json
```

Resultado:
- manifest: [tmp\sweep_rest_all_emission_date_35d_v1.json](C:\Users\mauri\git\scrap_report\tmp\sweep_rest_all_emission_date_35d_v1.json)
- `status=ok`
- `item_count=1`
- `success_count=1`
- item unico:
  - `record_count=1205`
  - `detail_count=1205`
  - `without_detail_count=0`
- observacao:
  - concluiu dentro de timeout de shell maior

### `sweep-run` REST sem credencial, geral com detalhamento por `emission_date`, 42 dias
Comando:
```powershell
uv run --python 3.13 python -m scrap_report.cli sweep-run --report-kind pendentes --scope-mode nenhum --emission-date-start 2026-02-23 --emission-date-end 2026-04-05 --runtime rest --rest-ca-file tmp/itaipu_root_ca_v2.pem --output-json tmp/sweep_rest_all_emission_date_42d_v1.json
```

Resultado:
- manifest: [tmp\sweep_rest_all_emission_date_42d_v1.json](C:\Users\mauri\git\scrap_report\tmp\sweep_rest_all_emission_date_42d_v1.json)
- `status=ok`
- `item_count=1`
- `success_count=1`
- item unico:
  - `record_count=1205`
  - `detail_count=1205`
  - `without_detail_count=0`
- observacao:
  - concluiu dentro de timeout de shell maior

### Demonstrativo REST, panorama de SSAs pendentes para `IEE3`
Comando:
```powershell
uv run --python 3.13 python -m scrap_report.cli sam-api-flow --profile panorama --emitter-sector IEE3 --number-of-years 1 --ca-file tmp/itaipu_root_ca_v2.pem --output-json tmp/sam_api_iee3_pendentes_demo.json --output-csv tmp/sam_api_iee3_pendentes_demo.csv --output-xlsx tmp/sam_api_iee3_pendentes_demo.xlsx
```

Resultado:
- manifest: [tmp\sam_api_iee3_pendentes_demo.json](C:\Users\mauri\git\scrap_report\tmp\sam_api_iee3_pendentes_demo.json)
- `status=ok`
- `count=39`
- `summary.by_emitter={"IEE3": 39}`
- `summary.by_executor={"IMA0": 1, "MEL3": 8, "MEL4": 30}`
- exemplos de SSA:
  - `202601024`
  - `202601253`
  - `202601438`
  - `202602000`
  - `202602187`
- exportacoes:
  - [tmp\sam_api_iee3_pendentes_demo.csv](C:\Users\mauri\git\scrap_report\tmp\sam_api_iee3_pendentes_demo.csv)
  - [tmp\sam_api_iee3_pendentes_demo.xlsx](C:\Users\mauri\git\scrap_report\tmp\sam_api_iee3_pendentes_demo.xlsx)

### Demonstrativo REST, detalhe em lote de amostra da `IEE3`
Comando:
```powershell
uv run --python 3.13 python -m scrap_report.cli sam-api-standalone --profile detail-lote --ca-file tmp/itaipu_root_ca_v2.pem --output-dir tmp/sam_api_iee3_detail_demo --output-json tmp/sam_api_iee3_detail_demo.json --ssa-number 202601024 --ssa-number 202601253 --ssa-number 202601438 --ssa-number 202602000 --ssa-number 202602187
```

Resultado:
- manifest: [tmp\sam_api_iee3_detail_demo.json](C:\Users\mauri\git\scrap_report\tmp\sam_api_iee3_detail_demo.json)
- `status=ok`
- `count=5`
- `summary.by_emitter={"IEE3": 5}`
- `summary.by_executor={"IMA0": 1, "MEL4": 4}`
- exportacoes:
  - [sam_api_detail-lote_dados_20260323_163945_358349.csv](C:\Users\mauri\git\scrap_report\tmp\sam_api_iee3_detail_demo\sam_api_detail-lote_dados_20260323_163945_358349.csv)
  - [sam_api_detail-lote_dados_20260323_163945_358349.xlsx](C:\Users\mauri\git\scrap_report\tmp\sam_api_iee3_detail_demo\sam_api_detail-lote_dados_20260323_163945_358349.xlsx)
  - [sam_api_detail-lote_resumo_20260323_163945_358349.xlsx](C:\Users\mauri\git\scrap_report\tmp\sam_api_iee3_detail_demo\sam_api_detail-lote_resumo_20260323_163945_358349.xlsx)

### Padronizacao de `exports` para futura juncao com repo de reports
Mudanca:
- `sam-api` e `sam-api-flow` agora expõem tanto:
  - `csv` / `xlsx`
  - quanto `data_csv` / `data_xlsx`
- quando ha `output_json`, o payload passa a registrar tambem:
  - `manifest_json`
- o `sam-api-standalone` e o `sweep-run --runtime rest` passam a expor os aliases legados junto das chaves canonicas

Smoke real:
```powershell
uv run --python 3.13 python -m scrap_report.cli sam-api-flow --profile panorama --emitter-sector IEE3 --number-of-years 1 --ca-file tmp/itaipu_root_ca_v2.pem --output-json tmp/sam_api_iee3_contract_demo_v2.json --output-csv tmp/sam_api_iee3_contract_demo_v2.csv --output-xlsx tmp/sam_api_iee3_contract_demo_v2.xlsx
uv run --python 3.13 python -m scrap_report.cli sweep-run --report-kind pendentes --scope-mode emissor --setores-emissor IEE3 --year-week-start 202608 --year-week-end 202612 --runtime rest --rest-ca-file tmp/itaipu_root_ca_v2.pem --output-json tmp/sweep_rest_iee3_contract_v1.json
```

Resultado:
- [tmp\sam_api_iee3_contract_demo_v2.json](C:\Users\mauri\git\scrap_report\tmp\sam_api_iee3_contract_demo_v2.json)
  - `exports.csv`
  - `exports.xlsx`
  - `exports.data_csv`
  - `exports.data_xlsx`
  - `exports.manifest_json`
- [tmp\sweep_rest_iee3_contract_v1.json](C:\Users\mauri\git\scrap_report\tmp\sweep_rest_iee3_contract_v1.json)
  - `items[0].reports.csv`
  - `items[0].reports.xlsx`
  - `items[0].reports.data_csv`
  - `items[0].reports.data_xlsx`
  - `items[0].reports.summary_xlsx`

### Formalizacao de schema para `sweep-run`
Mudanca:
- o manifest de `sweep-run` deixou de ser emitido sem schema formal
- a CLI agora valida o payload como `sweep_result`
- o payload final registra tambem:
  - `manifest_json`
  - `runtime_mode`

Smoke real:
```powershell
uv run --python 3.13 python -m scrap_report.cli sweep-run --report-kind pendentes --scope-mode emissor --setores-emissor IEE3 --year-week-start 202608 --year-week-end 202612 --runtime rest --rest-ca-file tmp/itaipu_root_ca_v2.pem --output-json tmp/sweep_rest_iee3_contract_v2.json
```

Resultado:
- [tmp\sweep_rest_iee3_contract_v2.json](C:\Users\mauri\git\scrap_report\tmp\sweep_rest_iee3_contract_v2.json)
  - `schema_version=1.0.0`
  - `producer=scrap_report.cli`
  - `runtime_mode=rest`
  - `manifest_json=tmp\\sweep_rest_iee3_contract_v2.json`
  - `items[0].telemetry.record_count=26`

### Correcao de bug no `emission_date` do sweep REST
- o `sweep-run --runtime rest` falhava cedo ao inferir `number_of_years` quando `emission_date` vinha em `YYYY-MM-DD`
- causa real:
  - extracao de ano com `[-4:]` em string ISO
- status:
  - corrigido nesta rodada
  - coberto por teste focado

### Exploracao de endpoint REST para outros `report_kind`
Comandos tentados:
- `GetExecutedSSAsByLocalizationRange`
- `GetExecutedSSAs`
- `GetPendingExecutionSSAsByLocalizationRange`
- `GetSSAsPendingExecutionByLocalizationRange`

Resultado:
- todos retornaram `HTTP 404`
- conclusao operacional:
  - a API REST atualmente comprovada continua sendo:
    - consulta geral de pendentes
    - detalhe por numero de SSA

### Nivel 1, API interna
Comando:
```powershell
uv run --python 3.13 python -
```

Fluxo:
- `SAMApiClient`
- `query_sam_api_records(...)`
- `executor_sectors=("MAM1",)`
- `limit=2`

Resultado:
- `mode=search`
- `count=2`
- primeiro item:
  - `ssa_number=202600001`
  - `executor_sector=MAM1`
  - `emitter_sector=OUO6`

### Nivel 2, comando opinativo
Comando:
```powershell
uv run --python 3.13 python -m scrap_report.cli sam-api-flow --profile panorama --start-localization-code A000A000 --end-localization-code Z999Z999 --number-of-years 1 --executor-sector MAM1 --limit 2 --ignore-https-errors --output-json tmp/sam_api_flow_real_v2.json --output-csv tmp/sam_api_flow_real_v2.csv --output-xlsx tmp/sam_api_flow_real_v2.xlsx
```

Resultado:
- manifest: [tmp\sam_api_flow_real_v2.json](C:\Users\mauri\git\scrap_report\tmp\sam_api_flow_real_v2.json)
- `status=ok`
- `profile=panorama`
- `mode=search`
- `count=2`
- `verify_tls=false`
- `warnings=["tls_verification_disabled"]`
- exportacoes:
  - [tmp\sam_api_flow_real_v2.csv](C:\Users\mauri\git\scrap_report\tmp\sam_api_flow_real_v2.csv)
  - [tmp\sam_api_flow_real_v2.xlsx](C:\Users\mauri\git\scrap_report\tmp\sam_api_flow_real_v2.xlsx)

### Nivel 3, fluxo independente
Comando:
```powershell
uv run --python 3.13 python -m scrap_report.cli sam-api-standalone --profile detail-lote --ssa-number 202602521 --ignore-https-errors --output-dir tmp/sam_api_standalone_real_v2 --output-json tmp/sam_api_standalone_manifest_v2.json
```

Resultado:
- manifest: [tmp\sam_api_standalone_manifest_v2.json](C:\Users\mauri\git\scrap_report\tmp\sam_api_standalone_manifest_v2.json)
- `status=ok`
- `profile=detail-lote`
- `mode=detail`
- `count=1`
- `verify_tls=false`
- `warnings=["tls_verification_disabled"]`
- artefatos:
  - [sam_api_detail-lote_dados_20260323_123504_358529.csv](C:\Users\mauri\git\scrap_report\tmp\sam_api_standalone_real_v2\sam_api_detail-lote_dados_20260323_123504_358529.csv)
  - [sam_api_detail-lote_dados_20260323_123504_358529.xlsx](C:\Users\mauri\git\scrap_report\tmp\sam_api_standalone_real_v2\sam_api_detail-lote_dados_20260323_123504_358529.xlsx)
  - [sam_api_detail-lote_resumo_20260323_123504_358529.xlsx](C:\Users\mauri\git\scrap_report\tmp\sam_api_standalone_real_v2\sam_api_detail-lote_resumo_20260323_123504_358529.xlsx)

### Mitigacoes novas nesta rodada
- detalhe em lote agora usa chunking controlado acima do limite por bloco
- o payload publica `detail_batch_chunked` quando a consulta passa desse limite
- SSAs repetidas agora sao deduplicadas antes do detalhamento
- o payload publica `ssa_numbers_deduped` quando a entrada repetida e reduzida
- o `sweep-run` agora aceita `--runtime rest` para `report_kind=pendentes`
- o runtime REST do sweep escreve artefatos em `staging/rest_sweep/...`
- o diagnostico de TLS ficou classificado por erro real de cadeia self-signed
- a mensagem de erro TLS agora aponta `--ca-file` ou `--ignore-https-errors`
- o payload REST agora inclui:
  - `filters`
  - `warnings`
  - `verify_tls`
  - `timeout_seconds`
- o schema JSON da REST foi endurecido para exigir esse contexto minimo

### Diagnostico TLS real
Comando:
```powershell
uv run --python 3.13 python -m scrap_report.cli sam-api --ssa-number 202602521 --output-json tmp/sam_api_tls_diag.json
```

Resultado:
- falha real com `verify_tls=true`
- erro:
  - `falha ao consultar GetSSABySSANumber: TLS nao confiavel (self-signed certificate in certificate chain); forneca --ca-file ou use --ignore-https-errors quando permitido`

### Chunking real em lote REST
Comando:
```powershell
uv run --python 3.13 python -m scrap_report.cli sam-api-standalone --profile detail-lote --ssa-number-file tmp/sam_api_chunk_input.txt --ignore-https-errors --output-dir tmp/sam_api_chunking_real --output-json tmp/sam_api_chunking_manifest.json
```

Resultado:
- manifest: [tmp\sam_api_chunking_manifest.json](C:\Users\mauri\git\scrap_report\tmp\sam_api_chunking_manifest.json)
- `status=ok`
- `warnings=["tls_verification_disabled", "detail_batch_chunked"]`
- artefatos:
  - [sam_api_detail-lote_dados_20260323_125657_039283.csv](C:\Users\mauri\git\scrap_report\tmp\sam_api_chunking_real\sam_api_detail-lote_dados_20260323_125657_039283.csv)
  - [sam_api_detail-lote_dados_20260323_125657_039283.xlsx](C:\Users\mauri\git\scrap_report\tmp\sam_api_chunking_real\sam_api_detail-lote_dados_20260323_125657_039283.xlsx)
  - [sam_api_detail-lote_resumo_20260323_125657_039283.xlsx](C:\Users\mauri\git\scrap_report\tmp\sam_api_chunking_real\sam_api_detail-lote_resumo_20260323_125657_039283.xlsx)

### Dedupe real em lote REST
Comando:
```powershell
uv run --python 3.13 python -m scrap_report.cli sam-api-standalone --profile detail-lote --ssa-number-file tmp/sam_api_dedupe_input_v2.txt --ignore-https-errors --output-dir tmp/sam_api_dedupe_real_v2 --output-json tmp/sam_api_dedupe_manifest_v2.json
```

Resultado:
- manifest: [tmp\sam_api_dedupe_manifest_v2.json](C:\Users\mauri\git\scrap_report\tmp\sam_api_dedupe_manifest_v2.json)
- `status=ok`
- `count=1`
- `warnings=["tls_verification_disabled", "ssa_numbers_deduped"]`
- `filters.ssa_numbers=["202602521"]`

### `sweep-run` com runtime REST
Comando:
```powershell
uv run --python 3.13 python -m scrap_report.cli sweep-run --username menon --report-kind pendentes --scope-mode emissor --setores-emissor IEE3 --year-week-start 202608 --year-week-end 202612 --runtime rest --ignore-https-errors --output-json tmp/sweep_rest_pendentes.json
```

Resultado:
- manifest: [tmp\sweep_rest_pendentes.json](C:\Users\mauri\git\scrap_report\tmp\sweep_rest_pendentes.json)
- `status=ok`
- `runtime_mode=rest`
- `item_count=1`
- `success_count=1`
- artefatos:
  - [pendentes_001_dados_20260323_125722_571938.csv](C:\Users\mauri\git\scrap_report\staging\rest_sweep\pendentes\item_001\pendentes_001_dados_20260323_125722_571938.csv)
  - [pendentes_001_dados_20260323_125722_571938.xlsx](C:\Users\mauri\git\scrap_report\staging\rest_sweep\pendentes\item_001\pendentes_001_dados_20260323_125722_571938.xlsx)
  - [pendentes_001_resumo_20260323_125722_571938.xlsx](C:\Users\mauri\git\scrap_report\staging\rest_sweep\pendentes\item_001\pendentes_001_resumo_20260323_125722_571938.xlsx)

### `sweep-run` REST com varios setores
Comando:
```powershell
uv run --python 3.13 python -m scrap_report.cli sweep-run --username menon --report-kind pendentes --scope-mode emissor --setores-emissor IEE1 IEE3 --year-week-start 202608 --year-week-end 202612 --runtime rest --ignore-https-errors --output-json tmp/sweep_rest_varios_setores_v2.json
```

Resultado:
- manifest: [tmp\sweep_rest_varios_setores_v2.json](C:\Users\mauri\git\scrap_report\tmp\sweep_rest_varios_setores_v2.json)
- `status=ok`
- `runtime_mode=rest`
- `item_count=2`
- `success_count=2`

### `sweep-run` REST geral sem detalhamento
Comando:
```powershell
uv run --python 3.13 python -m scrap_report.cli sweep-run --username menon --report-kind pendentes --scope-mode nenhum --runtime rest --ignore-https-errors --output-json tmp/sweep_rest_geral_sem_detalhe.json
```

Resultado:
- manifest: [tmp\sweep_rest_geral_sem_detalhe.json](C:\Users\mauri\git\scrap_report\tmp\sweep_rest_geral_sem_detalhe.json)
- `status=ok`
- `runtime_mode=rest`
- `item_count=1`
- `success_count=1`
- item unico:
  - `record_count=6284`
  - `detail_count=0`
  - `without_detail_count=6284`

### `sweep-run` REST geral com detalhamento temporal
Comando:
```powershell
uv run --python 3.13 python -m scrap_report.cli sweep-run --username menon --report-kind pendentes --scope-mode nenhum --year-week-start 202608 --year-week-end 202612 --runtime rest --ignore-https-errors --output-json tmp/sweep_rest_geral_v2.json
```

Resultado:
- nao ficou verde nesta rodada
- o wrapper do terminal estourou timeout com detalhamento amplo
- conclusao operacional:
  - geral simples: verde
  - geral com detalhamento temporal amplo: ainda caro e nao liberado como fluxo estavel

## Commits relevantes da frente REST
- `6129535` `STABILITY_PATCH: adicionar cliente sam api`
- `5511d49` `STABILITY_PATCH: ampliar integracao sam api`
- `81fb0c6` `STABILITY_PATCH: fechar niveis rest api`
- `f1c846a` `STABILITY_PATCH: endurecer operacao rest`
- `e9460c9` `STABILITY_PATCH: integrar rest ao sweep`
- `a3bddb9` `STABILITY_PATCH: otimizar rest detalhado`
- `f5c41d7` `STABILITY_PATCH: otimizar prefilter rest year week`
- `2f61345` `STABILITY_PATCH: ampliar emission date rest`

## Estado por camada
| camada | status | observacao |
| --- | --- | --- |
| Playwright unitario | verde | fluxo oficial mantido |
| Sweep multi-setor | verde | pedido unico por setor validado |
| REST nivel 1 | verde | API interna reutilizavel |
| REST nivel 2 | verde | `sam-api-flow` operacional |
| REST nivel 3 | verde | `sam-api-standalone` com manifest proprio |

## Risco residual
- a REST API nao depende mais exclusivamente de `--ignore-https-errors`; o caminho com CA exportada ficou validado
- o chunking removeu a falha seca, o dedupe removeu repeticao inutil e o cache por execucao evita reconsulta da mesma SSA, mas o custo de detalhe continua linear por SSA unica em lotes grandes
- o `sweep-run` REST ainda esta limitado a `report_kind=pendentes`
- `emission_date` geral agora esta verde ate 42 dias
- o modo geral com detalhamento amplo por `emission_date` continua caro para janelas acima de 42 dias

## Proximo passo natural
1. decidir se vale:
   - resolver confianca de certificado para a REST
   - reduzir custo linear do detalhe em lote
2. ou voltar para as pendencias do fluxo Playwright

## Slice 52 - smoke com username valido e opcao de salvar secret
Timestamp inicio: 2026-04-24T15:38:00-03:00

Objetivo:
- habilitar caminho operacional para digitar usuario valido e salvar secret nos scripts de smoke
- manter caminho default atual sem quebrar automacao existente
- atualizar docs com comandos e evidencia REST real mais recente

Arquivos alterados:
- `scripts/smoke_windows11.ps1`
- `scripts/smoke_debian13.sh`
- `CROSS_PLATFORM_SMOKE.md`
- `README.md`

Mudancas aplicadas:
- `smoke_windows11.ps1`:
  - novos parametros: `-SmokeUsername`, `-PromptUsername`, `-SetupSecret`, `-SecretService`
  - leitura opcional de `SMOKE_SETUP_SECRET` com variavel booleana interna (`ShouldSetupSecret`)
  - validacao de tokens para `SmokeUsername` e `SecretService`
  - `secret setup` opcional e `secret get` condicional quando setup for solicitado
  - evidencia JSON agora inclui `inputs.smoke_username`, `inputs.secret_service`, `inputs.setup_secret`
  - `Read-RequiredJson` endurecido para rejeitar raiz JSON em array
- `smoke_debian13.sh`:
  - novas flags: `--smoke-username`, `--prompt-username`, `--setup-secret`, `--secret-service`
  - modo seguro opcional: `secret setup/get` + `ingest-latest --secure-required`
  - modo default preservado: fallback transicional com `--allow-transitional-plaintext`
  - `py_compile` trocado por `compileall -q src tests`
  - evidencia JSON passou a ler `inputs` via env vars para evitar interpolacao shell no bloco Python
- docs:
  - `CROSS_PLATFORM_SMOKE.md` atualizado com comandos dos dois modos (transicional e seguro)
  - `README.md` atualizado com comandos de smoke para usuario valido e demonstrativo REST de 2026-04-24

Evidencia REST real do dia:
- `sam-api-cert`: `status=ok`, cadeia exportada para `tmp/itaipu_root_ca_v2.pem`
- `sam-api-flow` IEE3:
  - comando: `uv run --python 3.13 python -m scrap_report.cli sam-api-flow --profile panorama --emitter-sector IEE3 --number-of-years 2 --limit 50 --ca-file tmp/itaipu_root_ca_v2.pem --output-json tmp/sam_api_flow_iee3_live_20260424_152745.json --output-csv tmp/sam_api_flow_iee3_live_20260424_152745.csv --output-xlsx tmp/sam_api_flow_iee3_live_20260424_152745.xlsx`
  - `status=ok`, `count=50`
- `sweep-run` REST IEE3 pendentes:
  - comando: `uv run --python 3.13 python -m scrap_report.cli sweep-run --runtime rest --report-kind pendentes --scope-mode emissor --setores-emissor IEE3 --rest-ca-file tmp/itaipu_root_ca_v2.pem --output-json tmp/sweep_rest_iee3_pendentes_live_20260424_152745.json`
  - `status=ok`, `item_count=1`, `success_count=1`, `record_count=119`

Kluster (obrigatorio apos edicao):
- `Review: 69ebc3064ea1da958e1ac9a2`
  - 5 achados
  - corrigidos no slice: inconsistencia de gate de secret e robustez de compilacao no Debian
- `Review: 69ebc33e50b51ca1da54a24b`
  - 4 achados
  - corrigidos no slice: bug de atribuicao em parametro switch no PowerShell e endurecimento de parse JSON
- `Review: 69ebc3624ea1da958e1ace56`
  - 6 achados
  - corrigidos no slice: sanitizacao de tokens PowerShell, robustez de env var setup e remocao de interpolacao shell em bloco Python
- `Review: 69ebc3934ea1da958e1ad0c9`
  - 5 achados restantes
  - nao bloqueantes neste slice:
    - recomendacoes de refatoracao ampla/monolitica dos scripts
    - observacao sobre fallback transicional no Debian (ja documentado como modo default legado)
    - observacao de precheck de socket (sem impacto funcional imediato no fluxo atual)

Risco residual:
- baixo: fallback transicional Debian continua disponivel por compatibilidade operacional
- medio: debt estrutural de duplicacao entre scripts (fora do escopo deste slice)

Timestamp fim: pendente

## Slice 53 - validacao de artefatos acionaveis
Timestamp inicio: 2026-05-05T12:51:39-03:00
Timestamp fim: 2026-05-05T13:24:42-03:00

Objetivo:
- impedir que caminhos antigos ou inexistentes sejam oferecidos como artefatos acionaveis
- manter campos historicos existentes sem quebrar consumidores atuais
- evitar reaproveitamento de JSON stale nos smokes

Arquivos alterados:
- `src/scrap_report/file_ops.py`
- `src/scrap_report/cli.py`
- `src/scrap_report/sweep.py`
- `scripts/smoke_windows11.ps1`
- `scripts/smoke_debian13.sh`
- `tests/test_file_ops.py`
- `tests/test_cli.py`
- `tests/test_sweep.py`

Mudancas aplicadas:
- `available_artifacts` passou a ser calculado por fonte unica em `file_ops.py`
- `cli.py` enriquece payloads no emissor comum, sem remover `source_path`, `staged_path`, `reports` ou `exports`
- `sweep.py` calcula `available_artifacts` uma vez ao fechar cada item, evitando I/O durante serializacao
- smokes Windows e Debian removem JSONs fixos antigos no inicio da rodada
- smokes validam que artefatos listados em `available_artifacts` existem como arquivos antes da evidencia final

Validacoes executadas:
- `uv run --python 3.13 python -m compileall -q src tests`: ok
- `uv run --python 3.13 --with ruff ruff check .`: ok
- `uv run --python 3.13 --with ty ty check src`: ok
- `uv run --python 3.13 --with pytest python -m pytest -q tests/test_file_ops.py tests/test_cli.py tests/test_sweep.py`: 83 passed
- `uv run --python 3.13 --with pytest python -m pytest -q`: 233 passed
- `bash -n scripts/smoke_debian13.sh`: ok
- `pwsh Parser.ParseFile scripts/smoke_windows11.ps1`: ok
- `uv run --python 3.13 python -m scrap_report.cli scan-secrets --paths src README.md`: ok, 0 findings

Kluster:
- achados durante o ciclo:
  - 1 medio: acoplamento inicial em `_emit_json`
  - 1 medio: I/O em `SweepItemResult.to_payload`
  - 1 alto: `dict(None)` possivel em `SweepRunner._run_item`
  - 3 achados finais intermediarios: centralizacao, duplicacao e `manifest_json` antes da escrita
- todos corrigidos
- revisao final do conjunto alterado: limpa

Risco residual:
- baixo: `source_path` historico continua podendo apontar para origem ja movida por staging, mas nao entra em `available_artifacts` quando nao existe
- baixo: `manifest_json` nao e auto-oferecido dentro do proprio payload porque a validacao ocorre antes da escrita do arquivo de manifest

Proximo passo natural:
1. rodar smoke real Windows 11 e Debian no ambiente alvo para confirmar evidencias de plataforma

## Slice 54 - excluir manifest stale de artefatos acionaveis
Timestamp inicio: 2026-05-05T13:28:56-03:00
Timestamp fim: 2026-05-05T13:33:13-03:00

Objetivo:
- impedir que `exports.manifest_json` antigo seja listado em `available_artifacts`
- manter `manifest_json` historico no payload normal
- limitar o patch ao helper compartilhado e ao teste focado

Arquivos alterados:
- `src/scrap_report/file_ops.py`
- `tests/test_file_ops.py`

Mudancas aplicadas:
- `DEFAULT_NON_PATH_ARTIFACT_KEYS` renomeado para `DEFAULT_EXCLUDED_ARTIFACT_KEYS`
- `manifest_json` passou a ser chave excluida de mapas de artefatos acionaveis
- teste cobre `exports.manifest_json` apontando para arquivo existente antigo e confirma que ele nao entra em `available_artifacts`

Validacoes previstas:
- `compileall`
- `ruff` focado
- `ty`
- `pytest` focado em `test_file_ops`, `test_cli`, `test_sweep`
- `scan-secrets`

Kluster:
- achados durante o ciclo:
  - 2 baixos: nomes imprecisos de constante e teste
- corrigidos antes das validacoes locais
- revisao do patch de codigo/teste: limpa

Risco residual:
- baixo: `manifest_json` continua disponivel como campo historico, mas nao como acao pronta em `available_artifacts`
