# Plano Pessoal do Projeto (Dev Infra)

**Data:** 02/01/2026 23:56 (UTC−3)
**Responsável:** Dev Infra (eu)

## Contexto
- Antes da VPS, foco em garantir que o ambiente local está completo, documentado e com métricas sólidas.
- Os pontos de bloqueio identificados foram esquema dos procedimentos, colunas de memória local e falta de um registro confiável das medições.

## Checklist pessoal
- [x] Corrigir `ProcedureStore` para rebuild lazy do índice (`_ensure_index` + flag `_index_dirty`).
- [x] Garantir que `LocalMemoryCache` adiciona colunas extras antes de criar índices (sem quebrar banco existente).
- [x] Rodar `scripts/measure_local_weights.py` com configuração mock/dry-run e registrar os resultados em `Documentos/PESOS_MEDIDOS.md`.
- [x] Atualizar o diagrama (`Documentos/DIAGRAMA_ARQUITETURA.svg`) para citar o arquivo de pesos medidos.
- [x] Criar `Documentos/REGISTRO_IMPLEMENTACAO.md` refletindo mudanças e próximos passos.
- [ ] Validar o pré-flight estrito (`python3 -m jarvis.app --preflight --preflight-strict`), documentar resultados/avisos e listar dependências faltantes antes de tocar VPS.
- [ ] Valorizar e documentar dependências adicionais de sistema (Wayland/X11, TTS, STT, browsers) em um checklist separado para o ambiente local.
- [ ] Registrar logs/medições e atestar que o ambiente está pronto antes de provisionar contas VPS/Tailscale; manter esse registro em `Documentos/REGISTRO_IMPLEMENTACAO.md`.
- [ ] Preencher os dados do checklist remoto no `Documentos/PLANO_UNICO.md` com prazos ou comentários (quando tiver mais execuções).
- [ ] Planejar próximos passos de Dev Infra (preflight estrito, contas na nuvem, telemetria) e anotar no plano pessoal.

## Próximos passos imediatos
1. Escrever um mini plano de dependências locais e arranjos para o VPS (manter em `Documentos/PLANO_PESSOAL_DO PROJETO.md`).
2. Estudar o `Documentos/PLANO_INFRA_DEPLOY_VPS.md` (quando disponível) e alinhar recursos necessários.
3. Reexecutar os benchmarks sempre que houver alteração significativa no executador ou nos scripts de automação.
4. Preparar a Fase 1 de infra: listar contas (Hetzner, RunPod, Gemini, Groq, OpenAI), validar limites/gastos e planejar instalação Tailscale + llama.cpp conforme anexos existentes.
5. Atualizar `Documentos/DIAGRAMA_ARQUITETURA.svg` e `Documentos/PESOS_MEDIDOS.md` após qualquer mudança crítica em procedures/memória/orquestrador ou automação local para manter pesos consistentes.
