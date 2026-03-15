# REVIEW_THREAD_TRIAGE

## fix pequeno real (corrigir agora)
- criar pipeline modular com entrada/saida clara para integracao
- remover qualquer credencial hardcoded de fluxo executavel
- garantir move seguro de xlsx para pasta alvo
- criar baseline formal de seguranca (modelo, ameaca, politica)
- implementar provider de segredo e fail-closed no carregamento de credencial
- ampliar providers para Windows/Linux e comando `secret get` sem leak

## falso positivo (justificar tecnicamente)
- nao aplicar ajustes de layout/dashboard: fora do objetivo desta extracao

## refactor amplo sem bug concreto (backlog)
- unificar todos os wrappers de erro herdados dos legados em arquitetura nova
- reescrever parser de colunas para suportar todos os formatos historicos
- redesenhar logging completo com telemetria estruturada end-to-end

## fora de escopo atual (pedir aprovacao)
- criar repo git nesta pasta
- push, PR, branch ou automacoes de CI
- ampliar scraping para todos os tipos de relatorio alem do baseline atual
- validar login real em ambiente SAM antes da janela autorizada
- criar repositorio publico e publicar remote
