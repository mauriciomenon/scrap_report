# ROUND_STATUS

## Sessao atual
- data: `2026-03-22`
- pasta: `C:\Users\mauri\git\scrap_report`
- branch: `master`
- baseline runtime atual: `b893356`
- doc sync pendente neste ciclo: sim

## Snapshot executivo
- repo publico existente: sim
- branch operacional: `master`
- runtime geral: estavel para os `report_kind` principais
- release publicada mais recente antes deste ciclo: `v0.1.1`
- commits reais apos `v0.1.1`:
  - `5436620` `STABILITY_PATCH: explicitar alias aprovacao emissao`
  - `0e109f4` `STABILITY_PATCH: explicitar parser derivadas`
  - `a2ef27c` `STABILITY_PATCH: liberar numero ssa aprovacao`
  - `55ccbe6` `STABILITY_PATCH: explicitar export derivadas`
  - `b893356` `STABILITY_PATCH: explicitar bloqueio emissao`

## Current truth do runtime
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
- modo multi-setor em pedido unico agora esta validado e recomendado para:
  - `pendentes`
  - `executadas`
  - `pendentes_execucao`
  - `reprogramacoes`

## Evidencia operacional rodada 2026-03-22
### Diagnostico de ambiente
- DNS `osprd.itaipu`: `172.17.7.165`
- `uv run python -m scrap_report.cli secret get --username menon`: `status=ok`

### `derivadas_relacionadas`
Comando:
```powershell
uv run python -m scrap_report.cli sweep-run --username menon --report-kind derivadas_relacionadas --scope-mode nenhum --ignore-https-errors --output-json staging/sweep_derivadas_relacionadas_baseline.json
```

Resultado:
- manifest: [staging\sweep_derivadas_relacionadas_baseline.json](C:\Users\mauri\git\scrap_report\staging\sweep_derivadas_relacionadas_baseline.json)
- status: `error`
- erro validado:
  - `report_kind=derivadas_relacionadas nao entregou download no fluxo oficial; tela segue especial por export instavel`

Conclusao:
- o parser especial continua valido
- o gargalo real no fluxo oficial segue sendo export/download, nao parser

### `aprovacao_emissao` baseline
Comando:
```powershell
uv run python -m scrap_report.cli sweep-run --username menon --report-kind aprovacao_emissao --scope-mode nenhum --ignore-https-errors --output-json staging/sweep_aprovacao_emissao_baseline_none.json
```

Resultado:
- manifest: [staging\sweep_aprovacao_emissao_baseline_none.json](C:\Users\mauri\git\scrap_report\staging\sweep_aprovacao_emissao_baseline_none.json)
- status: `ok`
- staged: [aprovacao_emissao_SSAs Pendentes de Aprovação na Emissão_22-03-2026_1114PM_20260322_231441_7571f94e.xlsx](C:\Users\mauri\git\scrap_report\staging\aprovacao_emissao_SSAs%20Pendentes%20de%20Aprova%C3%A7%C3%A3o%20na%20Emiss%C3%A3o_22-03-2026_1114PM_20260322_231441_7571f94e.xlsx)
- derivado: [ssas_dados_20260322_231441_748743.xlsx](C:\Users\mauri\git\scrap_report\staging\reports\ssas_dados_20260322_231441_748743.xlsx)
- linhas no derivado: `87`
- coluna `Emitida Em`:
  - presente
  - `emitida_em_nonnull=1`
  - maioria das linhas inspecionadas veio nula

Conclusao:
- baseline da tela exporta
- `numero_ssa` continua util nesta tela
- `Emitida Em` continua pouco confiavel para liberar `data de emissao`

### `aprovacao_emissao` com `data de emissao`
Comando:
```powershell
uv run python -m scrap_report.cli sweep-run --username menon --report-kind aprovacao_emissao --scope-mode nenhum --emission-date-start 2026-03-22 --emission-date-end 2026-03-22 --ignore-https-errors --output-json staging/sweep_aprovacao_emissao_emission_date_blocked.json
```

Resultado:
- manifest: [staging\sweep_aprovacao_emissao_emission_date_blocked.json](C:\Users\mauri\git\scrap_report\staging\sweep_aprovacao_emissao_emission_date_blocked.json)
- status: `error`
- erro validado:
  - `report_kind=aprovacao_emissao nao suporta filtro por data de emissao validado; export atual nao entrega Emitida Em confiavel`

Conclusao:
- bloqueio continua correto
- mensagem operacional agora reflete o motivo real

### Pedido unico multi-setor `IEE1 IEE2 IEE3 IEE4`
Objetivo:
- validar que um unico pedido consegue gerar um arquivo por setor automaticamente

#### `pendentes`
- manifest: [staging\sweep_iee1_iee4_pendentes_eval.json](C:\Users\mauri\git\scrap_report\staging\sweep_iee1_iee4_pendentes_eval.json)
- resultado:
  - `status=ok`
  - `item_count=4`
  - `success_count=4`

#### `executadas`
- manifest: [staging\sweep_iee1_iee4_executadas_eval.json](C:\Users\mauri\git\scrap_report\staging\sweep_iee1_iee4_executadas_eval.json)
- resultado:
  - `status=ok`
  - `item_count=4`
  - `success_count=4`

#### `pendentes_execucao`
- manifest: [staging\sweep_iee1_iee4_pendentes_execucao_eval.json](C:\Users\mauri\git\scrap_report\staging\sweep_iee1_iee4_pendentes_execucao_eval.json)
- resultado:
  - `status=ok`
  - `item_count=4`
  - `success_count=4`

#### `reprogramacoes`
- manifest: [staging\sweep_iee1_iee4_reprogramacoes_eval.json](C:\Users\mauri\git\scrap_report\staging\sweep_iee1_iee4_reprogramacoes_eval.json)
- resultado:
  - `status=ok`
  - `item_count=4`
  - `success_count=4`

Conclusao:
- o sistema ja suporta pedido unico multi-setor
- o comportamento recomendado e:
  - um pedido
  - um item por setor
  - um arquivo por setor
  - um manifest unico de controle
- nao ha evidencia ainda de um unico export do SAM com varios setores no mesmo campo

## Quality gates deste ciclo
Comandos:
```powershell
uv run python -m py_compile src\scrap_report\scraper.py src\scrap_report\sweep.py tests\test_scraper_contract.py tests\test_sweep.py
uv run ruff check src\scrap_report\scraper.py src\scrap_report\sweep.py tests\test_scraper_contract.py tests\test_sweep.py
uv run ty check src
uv run pytest -q tests\test_scraper_contract.py tests\test_sweep.py tests\test_config_secrets.py tests\test_reporting.py tests\test_pipeline_offline.py
```

Resultados:
- `py_compile`: ok
- `ruff`: ok
- `ty`: ok
- `pytest`: `86 passed`

## Estado por report kind
| report_kind | runtime geral | `numero_ssa` | `emission_year_week` | `emission_date` | observacao |
| --- | --- | --- | --- | --- | --- |
| `pendentes` | sim | nao | sim | sim | verde |
| `executadas` | sim | nao | sim | sim | verde |
| `pendentes_execucao` | sim | nao | sim | sim | verde |
| `consulta_ssa` | sim | sim | sim | sim | verde |
| `consulta_ssa_print` | parcial | sim | sim | sim | PDF proprio |
| `aprovacao_emissao` | parcial | sim | sim | nao | alias de executor e export com `Emitida Em` pouco confiavel |
| `aprovacao_cancelamento` | sim | nao | sim | sim | verde |
| `derivadas_relacionadas` | parcial | nao | sim | nao | parser especial e export oficial instavel |
| `reprogramacoes` | sim | nao | sim | sim | verde |

## Risco residual
- `derivadas_relacionadas` continua sendo o ultimo gargalo real de export oficial
- `aprovacao_emissao` continua sem base para liberar `data de emissao`
- `demais_*` continua dependente de preencher o grupo `demais`
- faltam telas adicionais do menu `Relatorios`

## Proximo passo natural
1. sincronizar docs ativos com o modo multi-setor recomendado
2. criar release incremental nova com essa documentacao
3. decidir se a proxima frente de codigo sera export de `derivadas_relacionadas` ou fonte confiavel de `Emitida Em` em `aprovacao_emissao`
