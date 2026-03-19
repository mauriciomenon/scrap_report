# SSA Consulta Rapida AGENTS Guide


## Baseline V1.1 Frozen

- Canonical frozen snapshot: `docs/POLICY_BASELINE_V1_1_FROZEN.md`
- Previous snapshot retained: `docs/POLICY_BASELINE_V1_FROZEN.md`
- Change rule: do not edit frozen baseline files; create a new version file when policy evolves.
- Update only with explicit user command and DOC_SYNC commit.


## Current Truth

- Active baseline is the current `dev` branch state unless user defines another target.
- Recovery/hardening history is context only; active follow-up backlog is `docs/RECOVERY_BACKLOG.md`.
- Stable behavior from previous golden/release-candidate cycles must be preserved.

## Objetivo

- Estabilizar codigo.
- Evitar refatoracoes amplas.

## Regras De Conduta (Criticas)

- NUNCA criar branch novo nem PR novo sem autorizacao explicita (nao inferir por `continue`).
- Nao criar worktree/pasta sem aprovacao.
- NUNCA fechar/abrir PR sem pedido explicito.
- Nao editar nada antes de aprovar plano.
- Nao alterar arquivo preexistente sem listar impacto antes.
- Nao misturar idiomas: comunicacao tecnica em PT-BR. Codigo/comentarios em ASCII.
- Sem acentos/cedilha/emojis/emdash em codigo e mensagens tecnicas.
- Nao fazer mudancas fora do escopo; se algo parecer necessario, parar e pedir confirmacao.
- Nada de try/except vazio, nada de suppress que esconda erro real, nada de self-healing silencioso.
- Evitar mudanca de layout/posicionamento na GUI (a menos que seja pedido explicitamente).
- Nao alterar nada fora do escopo do sprint a menos que explicitamente solicitado.
- Nao adicionar wrappers/mixins/helpers extras desnecessarios.
- Nao usar `git reset --hard` ou comandos destrutivos.
- Nao quebrar usabilidade entre ciclos; cada ciclo so fecha com estabilidade e usabilidade.

## Controle De Escopo E Intencao

Antes de qualquer edicao, registrar em 3 linhas:
1. Objetivo do slice.
2. Arquivos que podem mudar.
3. Arquivos proibidos no slice.

Se aparecer necessidade fora do escopo: parar e pedir aprovacao.

## Protocolo De Confirmacao Explicita

1. Nao inferir permissao para mudanca com respostas genericas como `continue`, `segue`, `ok`.
2. Mudanca de layout so com pedido explicito (`alterar layout`, `ajustar alinhamento`, `reverter layout`) ou lista direta de itens.
3. Nunca executar rollback de qualquer funcao sem comando explicito com `reverter` e escopo definido.
4. Se houver ambiguidade, parar e pedir confirmacao binaria (`sim`/`nao`) com checklist objetivo antes de editar.
5. Default em ambiguidade: rodar apenas diagnostico/testes, sem editar.

## Processo (XP Curto + SDLC)

### SDLC base (ordem obrigatoria)
Requirements -> Development -> Review -> Testing -> Data -> Deployment -> Operations

### XP em slices (dentro do SDLC)
0. Commits atomicos e rollback facil por feature.
1. Diagnosticar e isolar o problema (evidencia: arquivo/linha/log/repro).
2. Propor plano curto + diff previsto antes de editar (menor patch possivel).
3. Implementar em slice pequeno.
4. Validar localmente: `python -m py_compile` + `ruff check` + `ty check` + `pytest` focado.
5. Commit atomico (um por slice), push, checar bots/checks.
6. Itens nao bloqueantes: registrar em `docs/RECOVERY_BACKLOG.md` (sem arrumar tudo agora).
7. Priorizar risco real; evitar refatoracao transversal fora de escopo.
8. Quando alterar config, fazer backup com timestamp.
9. Responder comentarios de PR: corrigidos e nao corrigidos com status claro.

## Contrato De Slices (Obrigatorio)

Cada slice deve declarar:
- Entrada: bug/risco alvo + evidencia.
- Saida: comportamento esperado mensuravel.
- Nao muda: lista explicita do que nao sera alterado.
- Testes: comandos e resultado esperado.
- Evidencia: commit e resposta no PR.

## Categorias De Mudanca (Obrigatorio Em Todo Commit)

- `HOTFIX_BLOCKER`: corrige falha funcional/risco alto.
- `STABILITY_PATCH`: corrige regressao sem alterar arquitetura.
- `DOC_SYNC`: sincroniza docs/handoff/backlog sem runtime.
- `DEFERRED_NOTE`: anotacao de pendencia com motivo.

## Categorias De Falha (Obrigatorio Na Triagem)

- `BUG_REAL`: reproduzivel e com risco funcional/seguranca.
- `DECISAO_INTENCIONAL`: comportamento mantido por politica aprovada.
- `NAO_BLOQUEANTE_DEFERIDO`: melhora valida, mas fora do escopo atual.
- `FALSO_POSITIVO`: comentario sem evidencia tecnica aplicavel ao contexto atual.

## Politica De Comentarios De PR

- Todo comentario deve receber resposta.
- Se corrigido: responder com commit hash e arquivo/linha.
- Se nao corrigido agora: responder com motivo + item no `docs/RECOVERY_BACKLOG.md`.
- Nao deixar comentario sem status.
- Quando houver melhoria percebida durante o ciclo, atualizar tambem a descricao do PR.

## Politica De Git Operacional

- Proibido rodar commits em paralelo (evitar `index.lock`).
- Ao trocar de branch com arquivos locais:
  - criar stash nomeado com timestamp e motivo;
  - registrar stash id no handoff da conversa;
  - planejar aplicacao/revisao do stash (nao esquecer destash/recuperacao).
- Stash gigante e sinal de risco: pausar, auditar conteudo e confirmar estrategia antes de seguir.
- Nao fechar ciclo sem push confirmado no branch alvo.
- No fechamento da sessao, orientar explicitamente destino do stash (aplicar/manter/descartar) com justificativa.

## Higiene De Workspace (Importante)

- Rodar `git status --short` no inicio.
- Certificar pasta e branch de trabalho.
- Arquivos locais/fora de escopo nao devem ser commitados sem confirmacao:
  - `.envrc`, `.python-version`, segredos em `config/*`, ajustes locais de shell.
- Se aparecer mudanca em `.gitignore*` fora do pedido: parar e perguntar.
- Estabilizar import/startup e pontos de concorrencia (race/deadlock/cancel/locks/IO) com mudancas minimas verificaveis.
- Otimizar carregamento e desempenho da GUI com mudancas minimas e sem excesso defensivo.
- Sugerir mudancas de layout minimas apenas com ganho claro e aprovacao explicita.
- Verificar status e condicoes de loops.

## Error Handling E Performance

- Tratamento de erro deve existir por bloco funcional relevante, nao a cada poucas linhas.
- Evitar excesso de condicionais e `try/except` fragmentado.
- Proibido `try/except` vazio e proibido esconder falha real.
- Cada tratamento deve ter saida clara: log objetivo e retorno/acao coerente.
- Em qualquer fix, validar que a solucao nao cria custo alto desnecessario.
- Quando houver tradeoff real, parar e pedir permissao com 2 opcoes objetivas.
- Busca ampla (`rg`, `find` etc.) com timeout 60s por padrao; para mudar timeout, perguntar.

## Politica De Derivadas E Import

- Startup: sem import automatico.
- Import incremental: nao roda sync automatico de derivadas.
- Sync derivadas: apenas full rescan ou botao manual dedicado.
- Se sync de derivadas for pulado por politica, log explicito obrigatorio.
- Full rescan deve recriar banco do zero por regra.

## Politica De Docs De Migracao

- Manter um unico bloco `CURRENT TRUTH` nos docs ativos.
- Blocos antigos devem ser marcados como `HISTORICAL SNAPSHOT`.
- Release baseline atual deve aparecer no topo dos docs ativos.
- Nao manter blocos conflitantes com status de fonte de verdade.

## Politica Para Ferramentas Auxiliares

- Se ferramenta auxiliar entrar em loop, contradizer pedido, ou sugerir acao fora de escopo:
  - informar o usuario imediatamente;
  - oferecer opcoes objetivas:
    1) continuar tentativa ate estabilizar,
    2) aplicar solucao forcada minima,
    3) deferir para backlog com risco documentado.
- Decisao final sempre do usuario.

## Timestamp De Sessao (Obrigatorio)

- Em cada rodada/sessao de trabalho:
  - registrar timestamp inicial no console;
  - registrar timestamp final no console;
  - incluir no handoff curto quando aplicavel.

## Tooling E Validacao

- Python: usar `uv` para `python`/`python3`/`pip`.
- Prioridade runtime: `uv run --python 3.13 ...`; fallback para 3.12/3.11/3.10 quando necessario.
- Rodar sempre: `python -m py_compile`, `ruff check`, `ty check`, `pytest` focado (incluindo derivadas: unit + integracao + CLI quando tocar no fluxo).
- Evitar testes viciados; preferir testes que peguem regressao real (concorrencia/cancel/IO/locks).
- Incluir novos testes quando houver omissao clara.
- Para aplicacao node: usar exclusivamente `pnpm` e `node`.

## Tooling Rules Especificas

- Qwen e ferramenta de apoio para tarefas repetitivas operacionais por slice.
- Decisao tecnica final, review do patch e validacao final permanecem no agente principal.
- Regras Kluster sao obrigatorias e NAO devem ser alteradas por este documento.

## Kluster Rules (Auto-generated)
<kluster.ai mandaroty rules>

## 1. Automatic Code Review (kluster_code_review_auto)

### MANDATORY EXECUTION
- WHEN TO RUN: Execute after ANY file creation, modification, or code change
- New code generation
- Existing code updates
- File modifications or changes
- File creation
- Applied fixes
- Applies to ALL file types, not just code files
- ALWAYS execute regardless of size, complexity, or perceived risk level
- ZERO EXCEPTIONS POLICY: NO change is too small or low-risk to skip verification
- After any kluster_code_review_auto analysis, ALWAYS tell the user what issues were found and what you're about to fix BEFORE making any changes. Never fix silently, announce first, then fix.

### KLUSTER PURPOSE CLARIFICATION
- Kluster is NOT a traditional testing, syntax checking, or build verification tool
- Do NOT use kluster as a substitute for or alongside classic testing tools (jest, pytest, etc.)
- Do NOT use kluster as a syntax checker or linting replacement
- Do NOT run builds, compile code, or execute applications before calling kluster
- Kluster performs security, quality, and compliance verification on code changes
- Call kluster immediately after file modification, NO prerequisites required

### STRICT COMPLIANCE
Follow kluster_code_review_auto field descriptions exactly

---

## 2. Manual Code Review (kluster_code_review_manual)

### WHEN TO RUN
Only when explicitly requested by user

### TRIGGER PHRASES
- verify with kluster
- verify this file
- verify project
- check for bugs
- check security
- Similar manual verification requests

---

## 3. Dependency Validation (kluster_dependency_check)

### WHEN TO RUN
Before package management operations:
- Adding new packages or libraries
- Running package managers (npm, gradle, pip, etc.)
- Generating or updating package list files (package.json, requirements.txt, etc.)

---

## 4. Chat ID Management

### FIRST CALL
- Do not include chat_id field for the very first kluster tool call in a conversation

### SUBSEQUENT CALLS
- MANDATORY: Always include chat_id field with the EXACT value returned by any previous kluster tool call
- SESSION TRACKING: The chat_id maintains context across all kluster calls
- CRITICAL: Missing chat_id on subsequent calls creates new isolated sessions instead of maintaining conversation context

### IMPLEMENTATION
- After receiving any kluster tool response, immediately note the chat_id value
- Include this chat_id in ALL subsequent kluster tool calls
- Never generate or modify the chat_id value, always use the exact returned value
- APPLIES TO: all kluster tools (kluster_code_review_auto, kluster_code_review_manual, kluster_dependency_check)

---

## 5. Agent Todo List Management

### EXECUTION
- Always execute and strictly follow agent_todo_list from any kluster tool response

### COMPLETION
- Do not stop until all items in agent_todo_list are completed

### WORKFLOW
- Complete all fixes from agent_todo_list before running kluster_code_review_auto again

## 6. End of chat session - kluster summary
- WHEN TO EXECUTE: MANDATORY at the end of ANY conversation where kluster tools were used, right before the final user-facing response, EXCEPT when Clarification Handling is active (see Clarification Handling section). If any kluster response in the current turn contains CLARIFICATION actions, do NOT generate this summary, show the clarification prompt instead.
- TRIGGER: If any kluster_code_review_auto, kluster_code_review_manual, or kluster_dependency_check tools were called during the conversation AND no CLARIFICATION actions are present in any response, ALWAYS generate this summary.
- SCOPE: The summary MUST include ALL kluster tool calls made after the most recent user request, not just the last tool call. This includes the initial verification and ALL subsequent re-verifications after fixes.

### KLUSTER SUMMARY STRUCTURE
Generate short report capturing the COMPLETE verification journey from ALL kluster tool calls after the last user request:

- kluster feedback: MUST summarize ALL issues found across ALL kluster tool calls (kluster_code_review_auto, kluster_code_review_manual, or kluster_dependency_check) after the last user request.
- CRITICAL: Analyze ALL tool call results from the verification cycle, NOT just the final verification result
- Example: If kluster found 3 issues initially, then 1 issue after fixes, then 0 issues, report total of 4 issues found (3 + 1)
 - Include:
   - Total number of issues found across ALL verification runs since the last user request, grouped by severity in a structured format:
     - Use bullet points or line breaks to clearly separate severity levels
       - Reflect the complete verification journey (example: Initially found 3 issues, after fixes found 1 more issue, final verification clean)
- For case when kluster returned includedExternalKnowledge data, include short summary from includedExternalKnowledge field on what knowledge sources were used during code review. This should be displayed at the END of the kluster summary section, after all other sections, as a separate line formatted as: External knowledge used: [short summary of includedExternalKnowledge]

- Issues found and fixed: Document summary of ALL changes applied to resolve issues found by kluster across the ENTIRE verification cycle since the last user request.
- Do not include this section if NO issues were found in any verification run since the last user request
- Include:
  - What fixes were implemented following kluster tool recommendations, a short 1-2 lines summary covering ALL fixes since the last user request
  - What would have happened without these fixes, how it could affect the application, show this as a separate paragraph/section, NOT as a bullet point within Issues found and fixed. Start this text from Impact Assessment:

### Formatting requirements
- Use markdown bold text with line breaks for title: kluster.ai Review Summary followed by a blank line
- Use emoji and/or bullet points for better formatting
- Always reflect the FULL journey of verification, not just the end state
- Show progression when multiple verification cycles occurred (example: 3 issues -> 1 issue -> clean)

### ENFORCEMENT
- If you complete a conversation without providing this summary when kluster tools were used AND no clarifications were requested, you have violated this rule
- Always check before final response: Did I use any kluster tools? If yes, did any response contain CLARIFICATION actions? If clarification is present, show ONLY the clarification prompt and do NOT generate the kluster summary, these two are mutually exclusive. If no clarification, provide the verification summary covering ALL tool calls since the last user request.

</kluster.ai mandaroty rules>

## Definition Of Done

1. Objetivo principal e criterios de aceite atendidos.
2. Sem regressao confirmada em fluxos sensiveis tocados.
3. Validacoes tecnicas do slice verdes.
4. PR sem bloqueadores tecnicos pendentes.
5. Backlog atualizado com pendencias nao bloqueantes.

## Landing The Plane (Session Completion)

1. Registrar pendencias de follow-up.
2. Executar quality gates do escopo alterado.
3. Atualizar status de itens/PR.
4. Fazer push e confirmar branch sincronizado com remoto.
5. Limpar residuos locais apenas com seguranca.
6. Entregar handoff curto com escopo entregue, riscos e pendencias.

## Registro De Evidencias E Contexto

- Regras operacionais, contrato de slice e politicas ficam versionadas neste `AGENTS.md`.
- Evidencia de execucao por slice deve ficar em commit atomico + resposta em PR.
- Historico detalhado de decisoes e iteracoes tambem permanece na conversa (chat log).

## Execution Style Contract (obrigatorio)

Objetivo:
- manter padrao de ciclo longo com qualidade alta e risco baixo.
- priorizar estabilidade, rastreabilidade e rollback facil.

### A. Planejamento e comunicacao
1. Antes de qualquer edicao, publicar plano numerado detalhado.
2. Plano deve ter no minimo 15 passos quando a tarefa for media/grande.
3. Cada passo deve indicar: objetivo, arquivo(s), risco, validacao.
4. Nao executar edicao sem aprovacao explicita do plano.
5. Durante execucao, publicar status curto a cada slice.
6. Ao fim de cada slice, publicar resumo "feito x pendente x risco residual".

### B. Triage real de comentarios
7. Separar comentarios em 4 grupos:
   - fix pequeno real (corrigir agora)
   - falso positivo (justificar tecnicamente)
   - refactor amplo sem bug concreto (backlog)
   - fora de escopo atual (pedir aprovacao)
8. Nunca fechar thread sem evidencia objetiva (commit/teste/linha).
9. Nunca varrer comentario para baixo do tapete.
10. Manter arquivo de triage atualizado (ex: REVIEW_THREAD_TRIAGE.md).

### C. Escopo e risco
11. Aplicar patch minimo por problema.
12. Evitar refactor transversal em ciclo curto.
13. Se houver tradeoff significativo, parar e perguntar com 2 opcoes objetivas.
14. Nao alterar layout/posicao de UI sem pedido explicito.
15. Nao alterar comportamento funcional sem teste focado.

### D. Validacao obrigatoria por slice
16. Python: py_compile + ruff + pytest focado.
17. JS/launcher/script: lint/syntax check focado.
18. Sempre registrar comando e resultado em ROUND_STATUS.md.
19. Se teste nao puder rodar, declarar bloqueio explicitamente.
20. Nunca declarar "resolvido" sem validacao local minima.

### E. Commits e controle
21. 1 commit atomico por slice.
22. Mensagem de commit curta, objetiva e rastreavel.
23. Push apos cada slice validado.
24. Atualizar HANDOFF.md ao final de cada slice relevante.
25. Registrar backlog nao bloqueante em RECOVERY_BACKLOG.md.

### F. Regras de seguranca e confiabilidade
26. Proibido try/except vazio.
27. Proibido esconder erro real sem log objetivo.
28. Mensagem publica deve ser segura (sem leak de detalhe interno).
29. Em caso de erro interno, log detalhado no servidor e mensagem limpa ao operador.
30. Evitar custo alto desnecessario (loops redundantes/reprocessamento).

### G. Protocolo de ambiguidade
31. Se pedido estiver ambiguo, parar e pedir confirmacao binaria (sim/nao).
32. Sem confirmacao, rodar apenas diagnostico e testes (sem editar).
33. Nao inferir permissao de "continue", "ok", "segue".

### H. Padrao de saida final
34. Entregar resultado final em lista numerada:
   - o que mudou
   - validacoes executadas
   - aberto x resolvido
   - risco residual
35. Incluir sempre proximos passos naturais (1..N) quando aplicavel.

## Planning Quality Gate

Antes de editar, o plano precisa conter:
1. inventario de arquivos impactados
2. criterio de aceite por item
3. criterio de rollback
4. matriz de risco (baixo/medio/alto)
5. estrategia de teste por arquivo alterado
6. ordem de execucao por prioridade
7. definicao clara de "bloqueante real"
8. itens explicitamente fora de escopo

## Codex Custom Instructions (Global)

Sempre operar em ciclo:
1) diagnosticar
2) propor plano numerado detalhado
3) aguardar aprovacao
4) executar em slices minimos
5) validar localmente
6) commitar atomico
7) reportar aberto x resolvido com evidencias

Regras fixas:
- nunca pular validacao local minima.
- nunca fechar comentario/thread sem evidencia.
- nunca misturar bug real com sugestao generica de refactor.
- sempre separar "fix agora" vs "backlog".
- sempre priorizar risco real de seguranca/correcao.
- usar ferramentas e subagente leve para economizar contexto/tokens.
- manter comunicacao tecnica em PT-BR ASCII.
- respostas finais com lista numerada e status claro.

## Template De Resposta Padrao

Formato obrigatorio da resposta final:
1. Escopo executado
2. Arquivos alterados
3. Validacoes executadas
4. Resultado por comentario/thread (resolvido, falso positivo, backlog)
5. Risco residual
6. Proximos passos (numerados)

## Kluster Timeout and Retrieval Addendum

This addendum defines operational behavior when kluster analysis becomes unstable due to API timeout or long-running checks.

### Scope
- Applies to this repository only.
- Complements existing kluster rules and does not replace mandatory verification requirements.

### Timeout Handling
1. If `kluster` CLI review requests fail with `context deadline exceeded` or remain stuck near completion, treat it as tooling instability, not a code pass.
2. Increase local runner wait time first (longer session/PTY wait), but do not assume this changes server-side timeout limits.
3. If `deep` mode keeps timing out, reduce review scope (file-by-file or small groups) before widening scope again.

### Fallback Execution Order
1. Primary path: `kluster_code_review_auto` via MCP on the modified file set.
2. Secondary path: split MCP checks by smaller file batches if needed.
3. Tertiary path: CLI review for targeted files only when MCP is unavailable.
4. Do not mark a slice as fully verified if all kluster paths timed out.

### Review Retrieval Policy
1. Use `kluster log` to list available review IDs in repositories with review history.
2. Use `kluster show <review-id>` to fetch detailed findings for evidence and triage.
3. If current repo has no history or is not yet a git repo, document the blocker in `ROUND_STATUS.md` and continue with MCP evidence.

### Evidence and Reporting
1. Every timeout event must be recorded with command, scope, and exact error string.
2. When fallback is used, record which path succeeded (MCP or CLI) and why.
3. Keep triage objective: timeout is an operational blocker, not an issue dismissal.

### Cost and Token Discipline
1. Use lightweight models/tools for side tasks when appropriate (for example `qwen` or `glm_coding`) to reduce token cost.
2. Keep final technical validation and approval decisions in the main execution flow.

## Licoes Aprendidas Recentes

1. Nao inferir suporte a filtro apenas porque um seletor candidato existe no DOM.
2. Nao inferir que `fill()` funcionou so porque a chamada nao falhou.
3. Nao inferir que o filtro foi aplicado apenas porque a busca terminou sem erro.
4. Nao inferir que o export respeitou o filtro apenas porque o arquivo foi gerado.
5. Nao generalizar comportamento de uma tela para outra sem evidencia propria por `report_kind`.
6. Nao generalizar comportamento de um caso positivo isolado para todos os formatos de entrada.
7. Teste de wiring, parser e contrato interno nao substitui validacao funcional real no artefato final.
8. Em filtros sensiveis, principalmente data e numero de SSA, o criterio de verdade e o resultado exportado, nao a suposicao do agente.
9. Quando a evidencia for parcial, a linguagem publica deve refletir isso. Usar "tentativa de preenchimento", "seletor candidato", "valor persistido ou nao", "busca coerente ou nao", "export coerente ou nao".
10. Se houver duvida entre problema de formato, problema de UI, problema de busca e problema de export, nao liberar suporte ate separar essas camadas com evidencia.

## Metodologia De Validacao De Filtros Variaveis

### Objetivo

- Validar filtros com evidencia de ponta a ponta e impedir inferencia fraca.

### Regra De Ouro

- Um filtro so pode ser declarado como suportado quando houver evidencia suficiente nas quatro camadas abaixo:
  1. seletor certo
  2. valor persistido
  3. busca coerente
  4. export coerente

### Quatro Camadas De Prova

1. Seletor certo
- Identificar o campo candidato e registrar qual seletor foi usado.
- Nao assumir que o nome do campo implica suporte funcional.

2. Valor persistido
- Preencher o valor.
- Reler o valor imediatamente apos `fill()`.
- Reler o valor apos `blur`, `tab` ou evento equivalente.
- Reler o valor apos clicar em buscar.
- Se o valor sumir, for reformatado, truncado ou limpo, isso precisa ser registrado.

3. Busca coerente
- Verificar se o grid, cards ou mensagem de resultado ficou coerente com o filtro.
- Ausencia de erro nao prova aplicacao correta.
- Se necessario, comparar com uma busca sem filtro ou com filtro alternativo para confirmar sensibilidade.

4. Export coerente
- O artefato final precisa respeitar a mesma restricao observada na busca.
- Se o grid parecer correto mas o export ignorar o filtro, o suporte nao esta validado.
- O export final e parte obrigatoria da definicao de suporte.

### Regras Especificas Para Filtros De Data

1. Nao confundir formato aceito com filtro suportado.
- Uma tela pode aceitar `DD/MM/YYYY`, `YYYY-MM-DD` ou normalizar entrada, e ainda assim nao respeitar semanticamente o filtro.

2. Testar matriz minima de formatos quando houver risco de locale, mascara ou parser ambiguo.
- Exemplos minimos:
  - `DD/MM/YY`
  - `DD/MM/YYYY`
  - `MM/DD/YY`
  - `MM/DD/YYYY`
  - `YYYYMMDD`
  - `YYYY-MM-DD`

3. Para cada formato testado, registrar:
- valor digitado
- valor lido apos `fill()`
- valor lido apos `blur/tab`
- valor lido apos busca
- resultado do grid
- resultado do export

4. Nao concluir que o problema e de formato sem antes provar:
- se a UI alterou o valor
- se a busca manteve o valor
- se o export respeitou o mesmo valor

### Regras Especificas Para Numero De SSA E Filtros Diretos

1. Nao basta retornar poucas linhas. E preciso provar que o numero alvo esta presente e que numeros indevidos nao foram incluidos.
2. Quando possivel, validar no derivado e no bruto staged.
3. Se o bruto for dificil de ler por cabecalho ou layout, a validacao pode usar o derivado, mas isso deve ser declarado.

### Linguagem Obrigatoria De Status

- Em vez de "filtro preenchido corretamente", usar categorias observaveis:
  - `selector_found`
  - `input_persisted`
  - `search_respected`
  - `export_respected`

- Em resposta tecnica ao usuario, traduzir isso em PT-BR ASCII:
  - seletor encontrado
  - valor persistido
  - busca coerente
  - export coerente

### Proibicoes

1. Proibido liberar suporte por heuristica baseada apenas em DOM.
2. Proibido liberar suporte por um unico caso positivo sem revalidar formato e export.
3. Proibido escrever teste apenas para confirmar o wiring do proprio patch sem tentar derrubar a hipotese principal.
4. Proibido afirmar certeza operacional quando a evidencia disponivel for apenas parcial.

### Criterio De Liberacao

- Um filtro entra em runtime validado apenas quando:
  1. as quatro camadas de prova fecharem
  2. o comportamento for coerente no `report_kind` especifico
  3. o artefato final confirmar a restricao pedida
  4. houver pelo menos uma validacao real registrada no fluxo oficial

### Criterio De Bloqueio

- Se qualquer camada falhar, o filtro deve:
  1. permanecer desabilitado para aquela tela
  2. falhar cedo com erro explicito
  3. nao ser anunciado como suportado
