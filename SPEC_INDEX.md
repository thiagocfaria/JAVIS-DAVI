# SPEC_INDEX

## Documento Unico (PLANO_UNICO.md)
1. Como usar este documento (orientacao geral).
2. Estado atual do projeto (codigo) e registro local de instalacoes.
3. Atualizacao: cerebro self-hosted (Qwen2.5-7B, LoRA).
4. Pendencias estruturais ainda nao prontas.
5. Premissas fixas e decisoes globais (orcamento, VPS, modelo base, canal seguro).
6. Separacao honesta PC vs Nuvem (o que roda onde).
7. Regra fixa por item (criterios para marcar checklist como concluido).
8. Gates obrigatorios (policy, kill switch, limites diarios, diagrama atualizado).
9. Criterio de sucesso do MVP.
10. Mapa de fases (0 a 8).
11. Perfis de desenvolvimento (responsabilidades).
12. Fase 0 - Alinhamento e baseline (objetivo, entregaveis, checklists e como fazer).
13. Fase 1 - Infra minima (VPS + canal seguro) com funcoes de VPS, modelo base, memoria VPS, observabilidade e quotas.
14. Fase 1b - Seguranca base (policy, dados, validacao, kill switch) com checklists local/VPS.
15. Fase 2 - Memoria robusta (VPS) com estado atual, entregaveis, funcoes internas e privacidade/backup.
16. Fase 3 - Olhos e maos (Rust) incluindo visao, parser, acoes, grounding, RAG por app e bridge.
17. Fase 4 - Cerebro (VPS) cobrindo modelo base, gate de confianca, pool de APIs externas e telemetria de custo.
18. Fase 5 - Integracao E2E (PC <-> VPS) com fluxos completos.
19. Fase 6 - Pipeline de experimento (suite de testes, benchmarks, aprovacao/relatorio).
20. Fase 7 - Estabilizacao e diagrama (regressao, pesos reais, documentacao, integracoes locais).
21. Fase 8 - Melhorias e refino continuo (47 itens) com checklists local/VPS.

## Outros documentos
- README.md: status rapido, como rodar, modos CLI e painel.
- PROJECT_SPEC.md: especificacao resumida para analise automatica (runtime, entrypoints, testes, deps).
- Documentos/README.md: indice do diretório de documentos e historico.
- Documentos/DIAGRAMA_ARQUITETURA.svg: diagrama de arquitetura (PC/VPS/Servidor GPU).
- Documentos/REGISTRO_IMPLEMENTACAO.md: log de entregas e testes.
