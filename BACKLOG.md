# BACKLOG

- [ ] Inventariar/automatizar VPS self-hosted (Tailscale + llama.cpp/vLLM + rclone) com playbook em `ops/`; **validar** rodando playbook em VM e verificando servicos via `systemctl status`.
- [ ] Implementar portal Wayland + ponte Rust (captura/input + JSON-RPC) com fallback X11; **validar** gravando screencast e executando click/teclado em sessao Wayland real.
- [ ] Subir endpoints S3 de grounding/visao self-hosted e configurar URLs no `.env`; **validar** rodando `python -m jarvis.app --s3 "abrir navegador"` com logs apontando para endpoints locais.
- [ ] Finalizar memoria remota (VPS) com FTS/vetores e cache local; **validar** via testes de integracao push/search e latencia registrada em `~/.jarvis/events.jsonl`.
- [ ] Adicionar telemetria de custo/peso com benchmarks automatizados (`scripts/run_benchmarks.sh`); **validar** gerando relatorio atualizado em `Documentos/archive/benchmarks/`.
- [ ] Integrar protocolo PC <-> VPS ao orquestrador com sincronizacao de memoria/eventos; **validar** fluxo end-to-end `--loop` delegando ao VPS e retornando resposta.
- [ ] Empacotar atalho/botao de chat (launcher) e guias de aprovacao rapida; **validar** instalacao via `scripts/install_launcher.sh` e abertura do painel pelo menu/dock.
- [ ] Completar gate de confianca (self-score, penalidades) e testes de demonstracao/parar; **validar** pytest dedicado e cenario manual com bloqueio esperado.
