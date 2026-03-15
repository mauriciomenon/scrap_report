# RECOVERY_BACKLOG

## NAO_BLOQUEANTE_DEFERIDO
- adicionar suporte completo para relatorio de executadas com seletor dedicado
- adicionar validacao de schema para consumo por outro programa via contrato versionado
- incluir teste E2E real com ambiente SAM disponivel
- avaliar retries adaptativos por tipo de falha de rede
- adicionar gate local de scanner de segredos antes de execucao principal
- incluir suite de testes de redacao de logs para excecoes encadeadas
- implementar provider Windows 11 (Credential Manager/DPAPI)
- implementar provider Linux (Secret Service)
- adicionar comando `secret get` com resposta segura (sem valor bruto)
- migrar backend Windows para leitura segura real (DPAPI/CredRead) para eliminar modo presenca
- validar em Windows 11 real com modulo `CredentialManager` instalado
- ampliar redacao para stack traces e pontos adicionais de logging estruturado
- ampliar regras do `scan-secrets` com baseline de falso positivo por caminho
- adicionar health-check DOM e modo strict/adaptive no selector engine
- validar modo strict em ambiente SAM real e ajustar fallback por evidencias
- avaliar exigencia de credencial em `ingest-latest` quando operando somente com arquivo local
