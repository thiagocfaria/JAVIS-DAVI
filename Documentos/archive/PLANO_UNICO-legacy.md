# Plano Unico - Jarvis (Checklist por Fase e Funcao)

## Como usar este documento
- README.md: estado atual e logica do sistema (o que ja existe no codigo).
- Este documento: backlog completo + checklist por fase (o que falta fazer e como fazer).
- Diagrama: Documentos/DIAGRAMA_ARQUITETURA.svg (mantido separado).
- Os anexos ao final contem o conteudo integral dos documentos originais (exceto README).

## Estado atual do projeto (codigo)
- CLI com loop/texto/voz + preflight.
- Orquestrador local: comando -> plano -> policy -> aprovacao -> execucao -> validacao.
- Roteamento LLM: local (OpenAI-compat) -> browser AI manual -> cloud single-shot; MockLLM fallback.
- Gate de confianca por schema/warnings + self-score opcional do modelo + penalidades por risco/tamanho + budget diario + cache de respostas.
- Automacao desktop (xdotool/wtype/ydotool/pyautogui) e web (Playwright).
- Policy de seguranca + policy do usuario + bloqueios de dados sensiveis.
- Sanitizacao anti prompt injection + redacao automatica + mascara de screenshots.
- Kill switch via arquivo STOP.
- Chat log e chat inbox/UI local.
- Aprendizado por demonstracao integrado ao CLI (comandos demonstrar/parar); pendente teste real.
- Memoria local SQLite + procedimentos + comandos fixar/esquecer; Supabase opcional.
- Rust vision opcional (jarvis_vision) integrado ao validator Python; fallback Python.
- STT/TTS existem (Groq/faster-whisper, Piper/espeak), dependem de libs nativas.
- Protocolo VPS <-> PC em codigo (mensagens/validacao), nao integrado ao fluxo.
- Testes unitarios em testes/ + scripts de benchmark/medicao.

## Pendencias estruturais (nao estao prontas)
- VPS infra (Tailscale, llama.cpp, memoria VPS, rclone/exportacao Drive).
- Wayland portal para captura/input (ScreenCast + RemoteDesktop).
- Rust actions + bridge JSON-RPC (jarvis_actions/jarvis_bridge).
- Memoria robusta no VPS (SQLite + FTS + vetores + RAG).
- Telemetria de custo e baseline de benchmarks.
- Integracao PC <-> VPS (protocolo operando no fluxo).
- Chat UI com atalho/botao.

## Premissas fixas e decisoes globais
- Orcamento mensal: R$ 300-400.
- VPS CPU barato como base (orquestrador + memoria).
- GPU on-demand apenas quando necessario.
- PC local apenas para olhos/maos/policy/confirmacao.
- Memoria longa no VPS + arquivo frio no Drive.
- Wayland e alvo principal (X11 fallback existe, mas nao e foco).
- Linguagens: core local em Rust; orquestrador do MVP em Python; inferencia CPU via llama.cpp.
- Provedor VPS recomendado: Hetzner CX32 (4 vCPU, 16 GB RAM, 160 GB SSD) ou equivalente.
- Provedor GPU on-demand: RunPod.
- Modelo base: Qwen2.5-7B-Instruct quantizado (Q4_K_M).
- API leve paga: gpt-4o-mini (OpenAI oficial).
- API forte: gpt-4o (uso raro, apenas falha total).
- APIs gratuitas opcionais: Gemini e Groq (pool), usar apenas se quota ativa.
- Regra: nunca encadear APIs na mesma tarefa.
- Canal seguro preferido: Tailscale (IP privado).

## Separacao honesta: PC vs nuvem
PC (obrigatorio):
- Captura de tela real, input real (mouse/teclado), AT-SPI.
- Policy, validacao local e confirmacao humana.
- Automacao local exige sessao grafica ativa e desbloqueada.
Nuvem (quando necessario):
- Grounding pesado, modelos de visao, RAG remoto, telemetria agregada.
- Orquestracao remota e memoria principal.

## Regra fixa por item (aplicar a todas as fases)
Cada item do checklist so pode ser marcado como concluido quando TODOS os passos abaixo forem feitos.
Quando nao for aplicavel, documentar o motivo no PLANO_UNICO.md.

1) Implementar a parte (codigo, infra ou documento).
2) Testar funcionamento (unitario/funcional + edge cases).
3) Teste de integracao quando o item toca outros modulos.
4) Otimizar custo de recursos (CPU/RAM/GPU/armazenamento) sem perder qualidade.
5) Revisar linguagem e dependencias: existe opcao mais leve/segura? aplicar se fizer sentido.
6) Verificar duplicidade e coerencia no projeto (nao criar funcao repetida).
7) Endurecer contra falhas (erros, fallback, limites, seguranca).
8) Medir e registrar peso/custo de pior caso.
9) Atualizar PLANO_UNICO.md com status e como foi feito.
10) Atualizar DIAGRAMA_ARQUITETURA.svg e pesos reais.
11) Rodar teste final (cenario real ou E2E quando existir).
12) Revisao cruzada: outro dev valida impacto no projeto.

## Gates obrigatorios (nao passar sem cumprir)
- Policy local valida antes de executar.
- Schema estrito para acoes (sem comandos arbitrarios).
- Kill switch local funcional e testado.
- Limites diarios de custo ativos.
- Medicao de peso registrada para cada modulo.
- Diagrama atualizado e honesto.
- Aprovacao humana antes de mudanca permanente.

## Criterio de sucesso do MVP
- Funciona 6-8h/dia com custo dentro do teto.
- Olhos/maos executam tarefas simples com validacao.
- Memoria recupera contexto de tarefas anteriores.
- Evolucao controlada sem quebrar o sistema.

## Mapa de fases (visao geral)
- Fase 0 - Alinhamento e baseline
- Fase 1 - Infra minima (VPS + canal seguro)
- Fase 1b - Seguranca base (obrigatorio)
- Fase 2 - Memoria robusta (VPS)
- Fase 3 - Olhos e maos (Rust)
- Fase 4 - Cerebro (VPS)
- Fase 5 - Integracao E2E
- Fase 6 - Pipeline de experimento (obrigatorio)
- Fase 7 - Estabilizacao e diagrama
- Fase 8 - Melhorias e refino continuo

## Perfis de desenvolvimento (sugestao de distribuicao)
- Dev Core: orquestrador, LLM, CLI, procedures, integracao local.
- Dev Infra: VPS, deploy, systemd, Tailscale, rclone, observabilidade.
- Dev Rust: vision/actions/bridge, Wayland portal, daemon local.
- Dev Data: memoria, embeddings, FTS/vetores, RAG, exportacao.
- Dev Sec: policy, privacidade, aprovacao, kill switch.
- Dev QA: testes, benchmarks, pesos, baselines.
- Dev UX: chat UI, voz, fluxo de aprovacao e entrada.

## Fase 0 - Alinhamento e baseline
### Objetivo
- Revisar planos, travar decisoes principais e definir metas de latencia/custo/peso.

### Entregaveis da fase
- Metas de latencia/custo/peso definidas.
- Baseline de testes e benchmarks definido.
- Documentacao e registro de implementacao atualizados.

### Funcao: Documentacao e decisoes (Responsavel: Dev Core)
#### Checklist sem servidor (local)
- [ ] Revisar todos os planos e travar decisoes principais.
- [x] Definir metas de latencia, custo e peso (pior caso). (registradas abaixo)
- [x] Diagrama atualizado para refletir o estado atual (ultimo update registrado).
- [x] Registro de implementacao existe (Documentos/REGISTRO_IMPLEMENTACAO.md).
- [ ] Manter REGISTRO_IMPLEMENTACAO.md atualizado a cada mudanca. (ultimo update: 03/01/2026)
- [ ] Atualizar README quando algo mudar. (ultimo update: demonstracao)

Metas definidas (pior caso, antes do VPS):
- Latencia: <= 8s por comando local com OCR full; <= 12s quando usar LLM cloud.
- Custo: <= R$ 12/dia (<= R$ 360/mes), <= R$ 0,50 por comando pago.
- Peso (PC): RSS <= 2.5 GB, CPU p95 <= 2 cores, disco <= 2 GB (logs/cache).

#### Checklist com servidor (VPS)
- (sem itens)

### Funcao: Metricas e pesos (Responsavel: Dev QA)
#### Checklist sem servidor (local)
- [x] Micro-medicoes locais registradas (scripts/measure_local_weights.py + Documentos/PESOS_MEDIDOS.md).
-    - Registro recente: 02/01/2026 às 23:53 (UTC−3); os dados alimentam `Documentos/DIAGRAMA_ARQUITETURA.svg`.
- [ ] Medicoes reais de pior caso (OCR full, automacao, STT/TTS, etc).
- [ ] Reexecutar `scripts/measure_local_weights.py` (e demais benchmarks críticos) e atualizar `Documentos/PESOS_MEDIDOS.md` + `DIAGRAMA_ARQUITETURA.svg` após cada alteração relevante em procedures, memoria ou orquestrador.

#### Checklist com servidor (VPS)
- [ ] Atualizar diagrama com pesos reais medidos (inclui pesos do VPS).

### Funcao: Testes e benchmarks (Responsavel: Dev QA)
#### Checklist sem servidor (local)
- [x] Testes unitarios basicos em testes/.
- [x] Scripts de benchmark existem (scripts/run_benchmarks.sh).
- [ ] Definir suite baseline.
- [ ] Rodar benchmarks e salvar resultados em Documentos/benchmarks/.
- [ ] Comparar com baseline e ajustar limiares.

#### Checklist com servidor (VPS)
- (sem itens)

### Funcao: Ambiente local e preflight (Responsavel: Dev Infra)
#### Checklist sem servidor (local)
- [x] Preflight implementado (python3 -m jarvis.app --preflight).
- [x] Instalar dependencias locais para recursos completos (tesseract, xdotool/wtype/ydotool, portaudio, piper/espeak, tkinter, playwright browsers).
- [x] Script de instalacao automatizado criado (scripts/install_deps.sh).
- [x] Preflight validado sem falhas criticas (10 OK, 3 avisos de configuracao opcional).
- [ ] Registrar resultados do `--preflight-strict`, identificar dependências faltantes (voz, OCR, automação) e confirmar a instalação antes do VPS.
- [ ] Documentar checklist adicional de dependências opcionais (Wayland vs X11, TTS/STT/browsers) e vincular ao `scripts/install_deps.sh` para facilitar a migração.

#### Checklist com servidor (VPS)
- (sem itens)

### Funcao: Procedimentos e aprendizado local (Responsavel: Dev Core)
#### Checklist sem servidor (local)
- [x] ProcedureStore em SQLite (tags, TTL, score por tokens/tags).
- [x] Auto-learn de procedimentos quando ha guidance.
- [ ] Integrar aprendizado por demonstracao (recorder/learner) ao CLI. (implementado: comandos demonstrar/parar)
- [ ] Testar e documentar fluxo de demonstracao. (documentado no README; falta teste real)

#### Checklist com servidor (VPS)
- (sem itens)

### Como fazer
- Ver Anexo: PLANO_MESTRE.md
- Ver Anexo: PLANO_TESTES_BENCHMARKS.md
- Ver Anexo: PESOS_MEDIDOS.md

## Fase 1 - Infra minima (VPS + canal seguro)
### Objetivo
- Subir VPS CPU com modelo base, memoria e canal seguro com o PC local.

### Entregaveis da fase
- VPS online com Tailscale e acesso seguro.
- Servico do modelo base e orquestrador no VPS.
- Memoria base no VPS + exportacao mensal configurada.

### Funcao: VPS e sistema base (Responsavel: Dev Infra)
#### Checklist sem servidor (local)
- [ ] Planejar contas/limites (Hetzner, RunPod, Gemini, Groq, OpenAI) e mapear passos de Tailscale + build llama.cpp conforme anexos antes do deploy.

#### Checklist com servidor (VPS)
- [ ] Criar VPS (4 vCPU/16 GB ou equivalente).
- [ ] SSH por chave, usuario jarvis e firewall (UFW).
- [ ] Atualizar pacotes e instalar dependencias base.
- [ ] Instalar Tailscale no VPS e no PC local.

### Funcao: Modelo base e orquestrador no VPS (Responsavel: Dev Infra)
#### Checklist sem servidor (local)
- (sem itens)

#### Checklist com servidor (VPS)
- [ ] Instalar/compilar llama.cpp e baixar Qwen2.5-7B-Instruct GGUF.
- [ ] Subir servidor do modelo (systemd) ouvindo apenas na interface Tailscale.
- [ ] Subir orquestrador no VPS (systemd) ouvindo apenas na interface Tailscale.

### Funcao: Memoria VPS e arquivo frio (Responsavel: Dev Data)
#### Checklist sem servidor (local)
- (sem itens)

#### Checklist com servidor (VPS)
- [ ] Criar SQLite + sqlite-vec + FTS no VPS.
- [ ] Validar consultas e inserts basicos.
- [ ] Configurar rclone e exportacao mensal para Drive (jsonl.zst + manifesto).
- [ ] Agendar consolidacao/resumos fora do pico.

### Funcao: Observabilidade e custos (Responsavel: Dev Infra)
#### Checklist sem servidor (local)
- (sem itens)

#### Checklist com servidor (VPS)
- [ ] Logs via journalctl + logrotate.
- [ ] Telemetria de custo salva em JSON/CSV.

### Funcao: Contas e quotas (15 dias) (Responsavel: Dev Infra)
#### Checklist sem servidor (local)
- [ ] Criar conta RunPod e definir limite de gasto (GPU).
- [ ] Criar conta Gemini AI Studio (free tier) e gerar API key.
- [ ] Criar conta Groq Cloud (free tier) e gerar API key.
- [ ] Criar conta OpenAI (gpt-4o-mini e gpt-4o) e definir limite diario.
- [ ] Guardar keys em .env seguro no VPS e no PC local.

#### Checklist com servidor (VPS)
- (sem itens)

### Como fazer
- Ver Anexo: PLANO_INFRA_DEPLOY_VPS.md
- Ver Anexo: PLANO_PASSOS_MANUAIS_15_DIAS.md

## Fase 1b - Seguranca base (obrigatorio)
### Objetivo
- Garantir policy local, bloqueios e protecao de dados antes de qualquer execucao real.

### Entregaveis da fase
- Policy ativa com bloqueios e aprovacao humana funcionando.
- Redacao/sanitizacao e kill switch testados.

### Funcao: Policy e aprovacao (Responsavel: Dev Sec)
#### Checklist sem servidor (local)
- [x] Policy imutavel com bloqueios (bancos, contatos fora da allowlist).
- [x] Policy do usuario para bloquear/permitir sites e apps.
- [x] Policy cobre acoes web (web_fill, web_click).
- [x] Aprovacao humana por voz+tecla (ou modo configurado).
- [ ] Atalho de emergencia e stop via systemd (depende de deploy do service local).

#### Checklist com servidor (VPS)
- (sem itens)

### Funcao: Dados e privacidade (Responsavel: Dev Sec)
#### Checklist sem servidor (local)
- [x] Classificacao de dados (publico, sensivel, sigiloso).
- [x] Redacao automatica de dados sensiveis.
- [x] Mascara de privacidade antes de enviar screenshots.
- [x] Bloqueio automatico de envio externo quando ha dados sensiveis (com confirmacao).

#### Checklist com servidor (VPS)
- (sem itens)

### Funcao: Validacao e sanitizacao (Responsavel: Dev Sec)
#### Checklist sem servidor (local)
- [x] Validacao de saida do LLM (schema estrito de acoes).
- [x] Sanitizacao de entradas externas (anti prompt injection).

#### Checklist com servidor (VPS)
- (sem itens)

### Funcao: Kill switch e logs (Responsavel: Dev Sec)
#### Checklist sem servidor (local)
- [x] Kill switch local via arquivo STOP.
- [x] Logs locais auditaveis (eventos + chat log).
- [x] Testar kill switch em todos os ambientes.

#### Checklist com servidor (VPS)
- (sem itens)

### Como fazer
- Ver Anexo: POLITICA_SEGURANCA_PRIVACIDADE.md

## Fase 2 - Memoria robusta (VPS)
### Objetivo
- Memoria de longo prazo com baixo custo, em VPS CPU, com exportacao mensal.

### Estado atual (codigo)
- [x] Memoria local SQLite com FTS + embeddings locais + cache LRU + dedup por hash.
- [x] Comandos fixar/esquecer (FIXED) com redacao antes de salvar.
- [x] Supabase opcional (schema + RPC match_memories externo).
- [ ] RAG completo no VPS (SQLite + FTS + vetores).

### Entregaveis da fase
- Memoria no VPS com FTS+vetores e exportacao mensal.
- Regras de escrita/leitura e consolidacao funcionando.

### Notas de implementacao (Dev Data) - local (feito)
- FTS local + deduplicacao por hash + cache LRU para buscas (texto e vetores).
- Embeddings locais padronizados (dim 384, modelo multilingual-e5-small) e fallback local.
- Busca vetorial local com score hibrido (sim 0.6 + recencia 0.2 + uso 0.2).
- Embeddings salvos em BLOB (float32) no SQLite para reduzir espaco e acelerar leitura.
- Redacao de dados sensiveis antes de salvar episodios, procedures e FIXED (orchestrator).
- Camadas HOT/WARM/COLD/ARCHIVE: acesso promove; decay manual via `HybridMemoryStore.apply_decay`.
- Testes locais: `python3 -m pytest testes/teste_memoria_local.py`.
- Diagrama atualizado: `Documentos/DIAGRAMA_ARQUITETURA.svg`.
- Avaliado aplicar memoria inteligente em `ProcedureStore`/chat log; mantido como esta por baixo volume.
- Pendente: scheduler/rotina de decay, medicao de peso/custo, integracao E2E, revisao cruzada.

### Funcao: Base (Fase 0 interna) (Responsavel: Dev Data)
#### Checklist sem servidor (local)
- [ ] Definir JARVIS_EMBED_DIM=384 fixo. (implementado local; falta passos 3-12 da regra fixa)
- [ ] Padronizar modelo de embeddings (multilingual-e5-small ou similar). (implementado local; falta passos 3-12)
- [ ] Criar estrutura SQLite para texto + vetores + FTS. (implementado local com FTS5 + embeddings BLOB; falta passos 3-12)

#### Checklist com servidor (VPS)
- (sem itens)

### Funcao: Hibrido simples (Fase 1 interna) (Responsavel: Dev Data)
#### Checklist sem servidor (local)
- [ ] Escrita por regras (episodica/procedural/semantica). (parcial: episodico no sucesso, procedural no approve/auto-learn, knowledge em fixar)
- [ ] Deduplicacao por hash. (implementado local; falta passos 3-12)
- [ ] Busca FTS + recencia. (implementado local; falta passos 3-12)

#### Checklist com servidor (VPS)
- (sem itens)

### Funcao: Vetores (Fase 2 interna) (Responsavel: Dev Data)
#### Checklist sem servidor (local)
- [ ] Integrar embeddings locais CPU. (implementado local; falta passos 3-12)
- [ ] Busca vetorial e score hibrido (sim * 0.6 + recencia * 0.2 + sucesso * 0.2). (implementado local; falta passos 3-12)
- [ ] Cache LRU para consultas recentes. (implementado local; falta passos 3-12)

#### Checklist com servidor (VPS)
- (sem itens)

### Funcao: Robustez (Fase 3 interna) (Responsavel: Dev Data)
#### Checklist sem servidor (local)
- [ ] Feedback positivo/negativo com score.
- [ ] Regras de confirmacao por historico.
- [ ] Regras de importancia e consolidacao. (parcial: acesso atualiza HOT/WARM/COLD/ARCHIVE; falta consolidacao)
- [ ] Camadas HOT/WARM/COLD/FIXED/ARCHIVE aplicadas. (parcial: acesso + decay manual; falta scheduler)

#### Checklist com servidor (VPS)
- [ ] Resumo periodico (COLD) com modelo base.
- [ ] Exportacao mensal para Drive (rclone + manifesto).

### Funcao: Privacidade e backup (Responsavel: Dev Sec)
#### Checklist sem servidor (local)
- [ ] Passar PrivacyMasker antes de salvar dados sensiveis. (parcial: redacao de texto com `redact_text`)
- [ ] Criptografia opcional para arquivo frio.

#### Checklist com servidor (VPS)
- [ ] Backup seletivo em Supabase (futuro).

### Como fazer
- Ver Anexo: DOC_MEMORIA_OPENMEMORY.md

## Fase 3 - Olhos e maos (Rust)
### Objetivo
- Reescrever visao e acoes em Rust com baixo peso e loop visual robusto.

### Estado atual (codigo)
- [x] rust/jarvis_vision existe (capture CLI, OCR, mask, compare, detect, validator).
- [x] Validator Python usa jarvis_vision quando disponivel.
- [ ] Wayland portal (ScreenCast/RemoteDesktop) ainda nao implementado.
- [ ] Maos em Rust e bridge JSON-RPC nao existem.

### Entregaveis da fase
- Vision e actions em Rust com bridge JSON-RPC e fallback seguro.
- Loop visual com grounding basico e validacao.

### Funcao: Medicao e baseline (Fase 0 interna) (Responsavel: Dev QA)
#### Checklist sem servidor (local)
- [ ] Definir metrica de peso e cenarios de pior caso.
- [ ] Script de benchmark (OCR, screenshot, click, type, open).
- [ ] Comparar peso Python vs Rust.

#### Checklist com servidor (VPS)
- (sem itens)

### Funcao: Olhos em Rust (Fase 1 interna) (Responsavel: Dev Rust)
#### Checklist sem servidor (local)
- [ ] Captura Wayland via portal (ScreenCast + PipeWire) + fallback. (NOTA: Atualmente usa CLI tools - gnome-screenshot/grim/scrot)
- [x] OCR com leptess (fallback CLI). (FEITO: leptess opcional via feature, fallback CLI tesseract funciona)
- [x] Cache por hash + diff para OCR parcial. (FEITO: cache básico por hash implementado em validator.rs)
- [x] APIs: take_screenshot_png, ocr_text, detect_error_modal, detect_captcha_2fa. (FEITO: todas as APIs existem e funcionam)

#### Checklist com servidor (VPS)
- (sem itens)

### Funcao: Parser estruturado (Fase 1.5 interna) (Responsavel: Dev Rust)
#### Checklist sem servidor (local)
- [ ] Detector de elementos (bbox + texto + role).
- [ ] Integrar AT-SPI/DOM quando existir estrutura nativa.

#### Checklist com servidor (VPS)
- (sem itens)

### Funcao: Maos em Rust (Fase 2 interna) (Responsavel: Dev Rust)
#### Checklist sem servidor (local)
- [ ] Input injection (Wayland portal, wtype/ydotool fallback).
- [ ] Foco de janela, lista de janelas e maximizacao.
- [ ] AT-SPI para buscar elemento por texto/role.
- [ ] APIs: click, type_text, hotkey, open_app, open_url.

#### Checklist com servidor (VPS)
- (sem itens)

### Funcao: Grounding e loop inteligente (Fase 3 interna) (Responsavel: Dev Rust)
#### Checklist sem servidor (local)
- [ ] Loop de controle: AT-SPI -> OCR -> grounding -> LLM.
- [ ] Reflexao e retries com validacao.
- [ ] Speculative multi-action com validacao passo a passo.

#### Checklist com servidor (VPS)
- [ ] Engine de grounding remoto (bbox + confidence).

### Funcao: RAG por app (Fase 3.5 interna) (Responsavel: Dev Data)
#### Checklist sem servidor (local)
- (sem itens)

#### Checklist com servidor (VPS)
- [ ] Indexar docs/demos/traces por app.
- [ ] Cache local LRU + TTL.

### Funcao: Bridge e integracao (Fase 4 interna) (Responsavel: Dev Rust)
#### Checklist sem servidor (local)
- [ ] Daemon Rust JSON-RPC (Unix socket).
- [ ] Integrar chamadas Rust no Python.
- [ ] Fail-safe: se Rust indisponivel, abortar acao.

#### Checklist com servidor (VPS)
- (sem itens)

### Funcao: Pipeline de experimento (Fase 4.5 interna) (Responsavel: Dev QA)
#### Checklist sem servidor (local)
- [ ] Baseline, hipotese, testes em sandbox.
- [ ] Medir tempo/custo/CPU/RAM e comparar com baseline.
- [ ] Relatorio simples (HTML/JSON) e aprovacao humana.

#### Checklist com servidor (VPS)
- (sem itens)

### Funcao: Robustez e performance (Fase 5 interna) (Responsavel: Dev Rust)
#### Checklist sem servidor (local)
- [x] Testes de regressao (captura, OCR, click, hotkey). (FEITO: testes básicos criados em tests/test_basic.rs - testa detect_captcha, detect_error, compare_png, ocr_text)
- [ ] Watchdog e retry com backoff.
- [ ] Empacotamento (binarios + cache modelos).

#### Checklist com servidor (VPS)
- (sem itens)

### Como fazer
- Ver Anexo: PLANO_RUST_OLHOS_MAOS.md

## Fase 4 - Cerebro (VPS)
### Objetivo
- Subir cerebro barato no VPS e aplicar escada de decisao sem explodir custo.

### Estado atual (codigo)
- [x] Roteamento LLM local -> browser manual -> cloud single-shot.
- [x] Budget diario de chamadas/caracteres.
- [x] Gate de confianca heuristico (schema/warnings).
- [ ] Self-score do modelo e penalidades de risco/volume. (implementado no router; calibracao pendente)
- [ ] Pool de APIs gratuitas com quota + circuit breaker.
- [ ] Telemetria de custo em tempo real.
- [ ] LLM base Qwen2.5-7B-Instruct no VPS via llama.cpp.

### Entregaveis da fase
- Modelo base no VPS operando com escada de decisao.
- Gate de confianca calibrado e custo monitorado.

### Funcao: Modelo base e infra (Responsavel: Dev Infra)
#### Checklist sem servidor (local)
- (sem itens)

#### Checklist com servidor (VPS)
- [ ] Servico Qwen2.5-7B-Instruct no VPS (llama.cpp).
- [ ] Escada de decisao (free -> leve -> forte), sem cadeia.

### Funcao: Gate de confianca (Responsavel: Dev Core)
#### Checklist sem servidor (local)
- [ ] Implementar self-score do modelo. (implementado no router; falta calibrar)
- [ ] Penalidades por risco e tamanho do plano. (implementado no validator; falta calibrar)
- [ ] Recalibrar limiares com benchmarks. (pendente)

#### Checklist com servidor (VPS)
- (sem itens)

### Funcao: Pool de APIs gratuitas (Responsavel: Dev Core)
#### Checklist sem servidor (local)
- [ ] Implementar pool (Gemini + Groq) com checagem de quota.
- [ ] Circuit breaker e health-check.

#### Checklist com servidor (VPS)
- (sem itens)

### Funcao: Telemetria de custo (Responsavel: Dev Infra)
#### Checklist sem servidor (local)
- (sem itens)

#### Checklist com servidor (VPS)
- [ ] Medidor de custo (tempo, tokens, GPU).
- [ ] Logs de custo agregados (JSON/CSV).

### Funcao: Privacidade e dados (Responsavel: Dev Sec)
#### Checklist sem servidor (local)
- [x] Regras de classificacao e redacao antes de APIs externas.
- [ ] Politicas refinadas para dados sensiveis na nuvem.

#### Checklist com servidor (VPS)
- (sem itens)

### Como fazer
- Ver Anexo: PLANO_CEREBRO_MAQUINA.md

## Fase 5 - Integracao E2E
### Objetivo
- Conectar VPS (cerebro/memoria) ao executor local com policy ativa.

### Estado atual (codigo)
- [x] Fluxo local: comando -> plano -> policy -> execucao -> validacao.
- [x] Protocolo VPS <-> PC existe em codigo (validacao basica).
- [ ] Cliente/servidor do protocolo integrado ao fluxo principal.

### Entregaveis da fase
- Protocolo ativo entre VPS e PC com autenticacao e retry.
- Fluxo completo PC <-> VPS em funcionamento.

### Funcao: Integracao PC <-> VPS (Responsavel: Dev Core)
#### Checklist sem servidor (local)
- (sem itens)

#### Checklist com servidor (VPS)
- [ ] Implementar cliente/servidor (WebSocket ou gRPC).
- [ ] Autenticacao (token + rotacao) e nonce anti-replay.
- [ ] Idempotencia e retry/backoff.
- [ ] Timeouts e limites por tipo de mensagem.
- [ ] Telemetry_event para VPS.
- [ ] Fallback seguro quando VPS indisponivel.

### Funcao: Fluxo completo (Responsavel: Dev Core)
#### Checklist sem servidor (local)
- [x] Policy local sempre ativa.

#### Checklist com servidor (VPS)
- [ ] Orquestrador chama memoria VPS e executor local.

### Como fazer
- Ver Anexo: PROTOCOLO_VPS_PC.md

## Fase 6 - Pipeline de experimento (obrigatorio)
### Objetivo
- Evolucao controlada com testes, benchmarks e aprovacao humana.

### Estado atual (codigo)
- [x] Testes unitarios basicos em testes/.
- [x] Scripts de medicao/benchmark existem.
- [ ] Baseline formal e resultados registrados.

### Entregaveis da fase
- Baseline formal e relatorio de comparacao.
- Pipeline de aprovacao humana definido.

### Funcao: Suite de testes (Responsavel: Dev QA)
#### Checklist sem servidor (local)
- [ ] Baseline de testes fixos.
- [ ] Regressao visual (OCR fast vs full).

#### Checklist com servidor (VPS)
- [ ] Integracao + E2E com cenarios reais.

### Funcao: Benchmarks (Responsavel: Dev QA)
#### Checklist sem servidor (local)
- [ ] Rodar benchmarks em cenarios de pior caso.
- [ ] Registrar resultados e comparar com baseline.

#### Checklist com servidor (VPS)
- (sem itens)

### Funcao: Aprovacao e relatorio (Responsavel: Dev QA)
#### Checklist sem servidor (local)
- [ ] Relatorio HTML/JSON para revisao.
- [ ] Aprovacao humana antes de merge.

#### Checklist com servidor (VPS)
- (sem itens)

### Como fazer
- Ver Anexo: PLANO_TESTES_BENCHMARKS.md

## Fase 7 - Estabilizacao e diagrama
### Objetivo
- Consolidar estabilidade, pesos reais e documentacao final.

### Entregaveis da fase
- Diagrama com pesos reais + documentacao fiel ao codigo.
- Ambiente local com preflight sem falhas criticas.

### Funcao: Regressao e cenarios reais (Responsavel: Dev QA)
#### Checklist sem servidor (local)
- [ ] Testes de regressao e cenarios reais.

#### Checklist com servidor (VPS)
- (sem itens)

### Funcao: Pesos reais (Responsavel: Dev QA)
#### Checklist sem servidor (local)
- (sem itens)

#### Checklist com servidor (VPS)
- [ ] Atualizar diagrama com pesos reais medidos.
- [ ] Medicao de peso registrada para cada modulo.

### Funcao: Documentacao (Responsavel: Dev Core)
#### Checklist sem servidor (local)
- [ ] Revisar documentacao e README (manter fiel ao codigo).
- [x] Chat local com atalho/botao (UI + inbox ok; atalho implementado via Ctrl+Shift+J com --enable-shortcut).

#### Checklist com servidor (VPS)
- (sem itens)

### Funcao: Integracoes locais (Responsavel: Dev Infra)
#### Checklist sem servidor (local)
- [x] Instalar dependencias locais faltantes e validar preflight sem falhas criticas.

#### Checklist com servidor (VPS)
- (sem itens)

### Como fazer
- Ver Anexo: PLANO_MESTRE.md

## Fase 8 - Melhorias e refino continuo
### Objetivo
- Aplicar melhorias de performance, robustez e manutencao.

### Funcao: Melhorias identificadas (47 itens) (Responsavel: Dev Core)
#### Checklist sem servidor (local)
- Ver Anexo: MELHORIAS_IDENTIFICADAS.md
- Priorizar: alta -> media -> baixa.
- Medir impacto (benchmarks antes/depois) e testar regressao.

#### Checklist com servidor (VPS)
- (sem itens)

## Anexos (conteudo integral)


---

# ANEXO: PLANO_MESTRE.md

# Plano Mestre - Jarvis Davi

Este plano organiza todos os planos existentes em uma sequencia unica, com dependencias
claras e gates de validacao. Ele nao substitui os planos detalhados; ele coordena.

## Objetivo
- Entregar um MVP funcional, leve e barato.
- Manter evolucao controlada (pipeline de experimento + aprovacao humana).
- Preparar base para crescimento (beta e melhorias futuras).

## Status atual (codigo)
- Executor local, policy, aprovacao, validacao, telemetria e chat local existem no repo.
- Orquestracao local funciona; VPS/memoria principal/cloud ainda nao estao integrados.
- Olhos/maos em Rust e Wayland portal ainda nao foram implementados (apenas fallback Python e rust_vision parcial).

## Premissas fixas
- Orcamento mensal: R$ 300-400.
- VPS CPU barato como base (orquestrador + memoria).
- GPU on-demand apenas quando necessario.
- PC local apenas para acoes (olhos/maos/policy/confirmacao).
- Memoria longa no VPS + arquivo frio no Google Drive.
- Wayland exclusivo.

## Documentos base (fonte de verdade)
- `Documentos/PLANO_RUST_OLHOS_MAOS.md`
- `Documentos/PLANO_CEREBRO_MAQUINA.md`
- `Documentos/DOC_MEMORIA_OPENMEMORY.md`
- `Documentos/PLANO_PASSOS_MANUAIS_15_DIAS.md`
- `Documentos/PLANO_INFRA_DEPLOY_VPS.md`
- `Documentos/PROTOCOLO_VPS_PC.md`
- `Documentos/PLANO_TESTES_BENCHMARKS.md`
- `Documentos/POLITICA_SEGURANCA_PRIVACIDADE.md`
- `Documentos/DIAGRAMA_ARQUITETURA.svg`
- `Documentos/README.md`

## Ordem de execucao (fases)
Fase 0 - Alinhamento e baseline
- [ ] Revisar todos os planos e travar decisoes principais.
- [x] Definir metas de latencia, custo e peso (pior caso). (registradas acima)
- [x] Atualizar diagrama para refletir o estado atual.

Fase 1 - Infra minima (VPS + canal seguro)
- [ ] VPS CPU configurado (orquestrador + memoria).
- [ ] Tailscale ou canal seguro entre VPS e PC.
- [x] Limites de custo diarios ativos.
- [ ] Exportacao para Google Drive (arquivo frio) configurada.

Fase 1b - Seguranca base (obrigatorio)
- [x] Policy imutavel com bloqueios (bancos, contatos fora da allowlist).
- [x] Classificacao de dados (publico, sensivel, sigiloso).
- [x] Mascara de privacidade antes de enviar dados para nuvem.
- [x] Validacao de saida do LLM (schema estrito de acoes).
- [x] Sanitizacao de entradas externas (anti prompt injection).
- [x] Kill switch local (arquivo STOP + systemctl --user stop) e modo seguro (dry-run).
- [x] Logs locais auditaveis (eventos por passo).

Fase 2 - Memoria robusta (VPS)
- [ ] SQLite + FTS + vetores (dim 384).
- [ ] Politicas de escrita/leitura e deduplicacao.
- [ ] Feedback positivo/negativo e consolidacao.
- [ ] Comandos "fixar" e "esquecer" memoria.
- [ ] Exportacao mensal para Drive (jsonl.zst + manifesto).

Fase 3 - Olhos e maos (Rust)
- [ ] Captura/OCR/mascara em Rust.
- [ ] Input em Wayland (portal + fallback).
- [ ] Bridge Rust (JSON-RPC) integrada ao Python.
- [ ] Medicao de peso e otimizacao.

Fase 4 - Cerebro (VPS)
- [ ] LLM base Qwen2.5-7B-Instruct via llama.cpp.
- [ ] Escada de decisao (free -> leve -> forte).
- [x] Gate de confianca e budget diario (heuristica por schema/warnings; self-score opcional + penalidades basicas).
- [ ] Telemetria de custo.

Fase 5 - Integracao E2E
- [ ] Orquestrador chama memoria VPS e executor local.
- [x] Policy local sempre ativa.
- [x] Fluxo completo: comando -> plano -> policy -> execucao -> validacao.

Fase 6 - Pipeline de experimento (obrigatorio)
- [ ] Baseline de testes fixos.
- [ ] Comparacao de performance e taxa de sucesso.
- [ ] Aprovacao humana antes de merge.

Fase 7 - Estabilizacao e diagrama
- [ ] Testes de regressao e cenarios reais.
- [ ] Atualizar diagrama com pesos reais medidos (hoje so ha micro-medicoes).
- [ ] Revisar documentacao e README (parcial, README atualizado com demonstracao).
- [ ] Chat local (janela + atalho/botao) para explicar paradas e receber texto. (UI + inbox ok; atalho/botao pendente)

## Gates obrigatorios (nao passar sem cumprir)
- Policy local valida antes de executar.
- Schema estrito para acoes (sem execucao de comandos arbitrarios).
- Kill switch local funcional e testado.
- Limites diarios de custo ativos.
- Medicao de peso registrada para cada modulo.
- Diagrama atualizado e honesto.
- Aprovacao humana antes de mudanca permanente.

## Documentacao complementar
- Todas as politicas criticas ja estao documentadas.

## Criterio de sucesso do MVP
- Funciona 6-8h/dia com custo dentro do teto.
- Olhos/maos executam tarefas simples com validacao.
- Memoria recupera contexto de tarefas anteriores.
- Evolucao controlada sem quebrar o sistema.


---

# ANEXO: PLANO_CEREBRO_MAQUINA.md

# Plano do Cerebro da Maquina (baixo custo)

## Objetivo
Criar um cerebro eficiente e barato para o Jarvis Davi, capaz de planejar tarefas de trabalho por 6-8h/dia, usando o minimo possivel de API paga.

## Status atual (codigo)
- Orquestrador local e roteamento LLM (local -> browser manual -> cloud) estao implementados em `jarvis/cerebro/`.
- Budget diario existe; telemetria de custo nao.
- Nao ha VPS com Qwen/llama.cpp nem pool de APIs gratuitas no fluxo real.

## Decisoes principais (fixas)
- Provedor GPU: RunPod (on-demand).
- Provedor VPS: Hetzner (CX32) ou equivalente 4 vCPU / 16 GB.
- Modelo base: Qwen2.5-7B-Instruct quantizado (VPS CPU como padrao).
- API leve paga: gpt-4o-mini (OpenAI oficial).
- API forte (gpt-4o): uso raro, apenas falha total.
- Regra: nunca escalar em cadeia (nao usar API barata -> media -> forte na mesma tarefa).
- Pool de APIs gratuitas: usar apenas se forem melhores que o modelo base e tiver quota ativa.

## Escolha de linguagens (economia + performance)
- Core do executor (olhos/maos/policy local): Rust.
- Inferencia CPU barata: llama.cpp (C/C++) em vez de reescrever em Rust.
- Orquestrador do MVP: Python (mais rapido para iterar e mais barato agora).
- Meta final: migrar orquestracao para Rust quando o fluxo estiver estavel.
- Scripts e testes: Python (apenas para suporte, nao core).

## Inferencia CPU barata (padrao)
- Stack: llama.cpp + GGUF (quantizacao Q4_K_M).
- VPS minimo recomendado: 4 vCPU + 16 GB RAM.
- Se ficar lento: reduzir contexto, usar Qwen2.5-3B-Instruct como fallback.

## Arquitetura do cerebro (hibrido)
Local (PC):
- Captura/controle, policy, validacao e confirmacao humana.
- Cache minimo de procedimentos (nao e memoria principal).

Servidor barato (CPU/VPS):
- Orquestrador do cerebro (planejamento, heuristicas).
- Modelo base open-source (Qwen2.5-7B-Instruct quantizado via llama.cpp).
- Memoria principal (SQLite + FTS + vetores), embeddings CPU (dim 384).

GPU on-demand (RunPod):
- Grounding/visao pesado apenas quando necessario.

APIs externas:
- Nivel leve: apenas quando a confianca do modelo base for baixa.
- Nivel forte (gpt-4o): somente em falha total e com limite diario.

## Integracao com olhos/maos (executor local)
- O orquestrador no VPS envia planos para o agente local.
- O agente local e o gatekeeper: policy/confirmacao sempre passam localmente.
- Se a rede cair, o agente local entra em modo degradado (regras e procedimentos).
- Executor local assume Wayland.

## Canal seguro entre VPS e PC (baixo custo)
- Padrao: Tailscale (gratis para uso pessoal), comunicacao via IP privado.
- Protocolo: WebSocket ou gRPC com token + timeout + reconexao.
- Fallback: HTTPS com token + mTLS, se Tailscale nao for possivel.

## APIs gratuitas (pool, opcional)
- Google Gemini (AI Studio, free tier com limite diario de requests; verificar limite atual).
- Groq Cloud (free tier rate-limited; verificar quota no console).
Regra: escolher 1 API gratuita disponivel por tarefa (sem cadeia).
Cheque automatico de quota antes de chamar a API gratuita; se nao tiver quota, pular.
Health-check + circuit breaker: se falhar por quota/erro, marcar indisponivel ate reset.

## API leve paga (definida)
- Provedor: OpenAI (oficial).
- Modelo recomendado: `gpt-4o-mini` (baixo custo, rapido).
- Uso: somente quando Qwen ficar abaixo do limiar e API gratuita estiver indisponivel.
- Config: `JARVIS_LLM_MODE=openai`, `JARVIS_LLM_MODEL=gpt-4o-mini` (base_url so se usar proxy).

## Escada de decisao (minimo gasto)
1) Qwen2.5-7B-Instruct no VPS (default).
2) API gratuita (pool) se confianca < limiar e quota disponivel.
3) API leve paga (apenas 1 nivel por tarefa).
4) gpt-4o somente se falhar e a tarefa for critica.
5) Se ainda falhar -> pedir ajuda humana.
Regra: escolher apenas 1 nivel por tarefa; excecao so se a API gratuita falhar por quota antes de gastar tokens.

Status atual: local LLM -> browser manual (sem API) -> cloud single-shot (se configurado). Pool gratuito e VPS nao estao integrados.

## Gate de confianca (limiares)
Definicao: `confidence` em [0,1], calculada a partir de auto-score do modelo com regras de corte.
Regras de calculo:
- `self_score` vem do modelo (0-1). Se nao vier, usar apenas a qualidade do plano.
- `qualidade` vem da validacao (schema/warnings) + penalidades por risco/tamanho.
- `confidence = min(self_score, qualidade)` quando self_score existir.
- Penalizar -0.05 por warning.
- Penalizar por risco: `medium` -0.08, `high` -0.18.
- Penalizar por tamanho: -0.02 por acao acima de 6 (max -0.25).
- Clamp final em [0,1].
Regras:
- Schema invalido ou acao desconhecida = confidence 0.0.
- Qwen >= 0.70: usar Qwen.
- Qwen 0.55-0.69: usar API gratuita (se permitido).
- Qwen < 0.55: usar API leve paga.
- Se API leve < 0.45 e tarefa critica: usar gpt-4o.
- Definicao de tarefa critica: risco alto OU envolve dinheiro/credenciais/dados sigilosos.
- Sem cadeia: so um nivel por tarefa (excecao de quota gratis).
Nota: limiares sao iniciais e devem ser recalibrados com o plano de testes/benchmarks.

Status atual: confidence combina validacao + self_score opcional, com penalidades por risco/tamanho; limiares ainda nao calibrados com benchmarks.

## Limites de custo (teto mensal)
- VPS CPU: R$ 80-120 / mes.
- GPU RunPod: R$ 120-180 / mes (10-15h/mes).
- APIs: R$ 50-100 / mes.
Meta: total <= R$ 400 / mes (ideal <= R$ 300).

## Limites diarios (anti-explosao)
- GPU diario = (teto GPU mensal / 30).
- APIs diarias = (teto API mensal / 30).
- Ao bater o limite: cair para Qwen2.5-7B-Instruct e pedir ajuda humana.

## Privacidade (nao incomodar o usuario)
- Classificar dados: publico, sensivel, sigiloso.
- APIs gratuitas: apenas publico ou texto anonimizado.
- APIs pagas: permitir sensivel, mas com redacao automatica (emails, CPF, chaves).
- Nao pedir confirmacao toda hora; so em tarefas criticas/sensiveis.

## Cold-start de GPU (RunPod)
- Preaquecer na primeira tarefa pesada do dia.
- Manter ligada por janela curta (ex: 15-20 min) e desligar se ocioso.
- Se o cold-start atrasar: fallback para OCR/AT-SPI e pedir confirmacao humana.

## Avaliacao automatica (qualidade real)
- Conjunto de tarefas de teste fixo (scripts + telas salvas).
- Rodar modelos em modo sombra (nao executa acoes).
- Medir: sucesso, tempo, custo e taxa de erro.
- Usar esses dados para ajustar o gate de confianca.

## Memoria e RAG (alinhado com olhos/maos)
- Default: memoria e RAG no VPS para reduzir custo local.
- Embeddings locais no VPS (CPU) com modelo pequeno (dim 384).
- Cache local pequeno no PC apenas para latencia.
- Sempre respeitar policy local ao enviar contexto.
- Arquivo frio no Google Drive (jsonl.zst via rclone), sem custo extra.

## Checklist mestre (execucao em ordem)
Regra fixa para cada item do checklist:
1) Implementar a parte.
2) Testar de forma robusta (teste funcional + edge cases).
3) Otimizar performance sem perder qualidade.
4) Endurecer contra bugs/falhas/seguranca.
5) Medir e registrar custo (tempo, tokens, GPU).
6) Atualizar diagrama se a arquitetura mudar.
7) Marcar no checklist o que foi feito e como foi feito.
8) Atualizar `Documentos/README.md` quando algo mudar.

## Checklist por modulo (MVP)
Formato padrao por item:
- [ ] ITEM (pasta: caminho, local/nuvem)
  - [ ] Implementacao
  - [ ] Teste robusto
  - [ ] Otimizacao
  - [ ] Robustez/seguranca
  - [ ] Medicao de custo
  - [ ] Diagrama atualizado (se necessario)
  - [ ] Registro do que foi feito
  - [ ] README atualizado

Itens MVP (ordem recomendada):
- [x] Orquestrador do cerebro (pasta: jarvis/cerebro/, local hoje)
- [ ] Modelo base Qwen2.5-7B-Instruct (servico no VPS, fora do repo)
- [x] Gate de confianca (pasta: jarvis/cerebro/, local hoje; heuristica com self_score opcional)
- [x] Chamadas de API leve (pasta: jarvis/cerebro/, nuvem; depende de env)
- [x] Chamadas gpt-4o (pasta: jarvis/cerebro/, nuvem; via config de modelo)
- [ ] Memoria principal + RAG (pasta: jarvis/memoria/, VPS CPU)
- [ ] Arquivo frio (Drive) configurado no VPS
- [x] Budget diario/mensal (pasta: jarvis/cerebro/, local hoje)
- [ ] Telemetria de custo (pasta: jarvis/telemetria/, VPS CPU)

## Guardrails obrigatorios
- Nunca usar API em cadeia.
- Sempre respeitar limite diario/mensal.
- Se exceder budget: cair para Qwen2.5-7B-Instruct ou pedir ajuda humana.
- Tarefas criticas exigem confirmacao.
- APIs gratuitas apenas se melhorarem qualidade vs Qwen2.5-7B-Instruct.
- Se API gratuita falhar por quota, pular direto para a paga (sem intermediarios).

## Riscos e mitigacoes
- Modelo base fraco: usar prompt melhor + exemplos + cache.
- Falha de rede: fallback para modo local.
- Custo acima do teto: cortar GPU e API ate normalizar.
- Licencas: uso pessoal, mas sempre respeitar termos do modelo.

## Proximos passos
- Definir VPS CPU mais barato e estavel.
- Configurar API leve paga definida e limiares de confianca.
- Criar medidor de custo em tempo real.
- Verificar limites atuais das APIs gratuitas e configurar fallback.
- Configurar rclone e exportacao mensal para Drive.


---

# ANEXO: PLANO_RUST_OLHOS_MAOS.md

# Plano Rust: Olhos + Maos (inspirado no Agent S3)

## Objetivo
Transformar "olhos do sistema" e "maos do sistema" em Rust, mantendo o peso baixo e tornando o loop visual mais inteligente que o Agent S3, sem perder seguranca.

## Status atual (codigo)
- Existe `rust/jarvis_vision` com captura/OCR/mask, opcional no validator Python.
- Captura usa ferramentas CLI (gnome-screenshot/grim/scrot), sem portal Wayland.
- Acoes/maos ainda estao em Python (`jarvis/acoes/desktop.py`); nao ha `rust/jarvis_actions`.
- Bridge Rust/JSON-RPC, grounding, parser e RAG por app ainda nao existem.
- Fallback Python agora tenta grim no Wayland e ydotool para click/scroll (quando daemon ativo).

## O que faz o Agent S3 parecer mais inteligente
- Loop visual passo a passo: a cada acao ele ve a tela de novo e decide o proximo passo.
- Grounding com modelo visual: traduz "clique no botao X" em coordenadas reais.
- OCR + LLM juntos: usa OCR para texto e LLM para entender o contexto da UI.
- Reflexao: se erra, ele critica a acao e tenta corrigir.
- Formato de saida valido: valida que o LLM retornou acao correta.
- Trajetoria curta: limita historico de imagens para nao explodir contexto.
- Code agent: para tarefas de dados ele executa scripts locais (Python/Bash).
- Acao via automacao de GUI: controla mouse/teclado diretamente.

## Qualidades extras (outros repositorios) para superar o Agent S3
- Acoes hibridas GUI + API: usar API nativa quando existe, e clicar so quando precisa.
- Speculative multi-action: prever varios passos em uma chamada, validar ao vivo e reduzir custo.
- Knowledge substrate (RAG): aprender com docs, demos e traces por app.
- Parsing estruturado de tela: elementos com bbox e texto, melhor que OCR puro.
- Sandbox remoto opcional: mover o pesado para VM/servidor e reduzir peso local.
- Separacao de modelos: grounding/visao/acao com modelos diferentes e mais baratos.

## Diretriz de linguagem e performance
- Core em Rust (binarios locais, baixo overhead).
- C/C++ apenas quando a API do SO exigir (FFI), sem logica de alto nivel.
- No MVP, Python pode orquestrar e manter policy/telemetria; em producao final migrar para Rust.
- Processos longos via daemon Rust com JSON-RPC (socket local) para reduzir custo de spawn.
- Pipeline de experimento em Rust (CLI + daemon), scheduler via systemd/cron.
- Wayland obrigatorio:
  - Captura via xdg-desktop-portal (ScreenCast) + PipeWire.
  - Input via xdg-desktop-portal (RemoteDesktop) quando possivel.
  - Funciona apenas com sessao grafica ativa e desbloqueada.
  - Sessao de permissao persistente enquanto o login estiver ativo.
  - Re-solicitar permissao automaticamente se a sessao cair.
- Cloud-first para o pesado:
  - Grounding, parser e RAG preferencialmente em servidor.
  - Local so captura, controle, policy e validacao.
  - Imagens para nuvem sempre passam por mascara de privacidade.
- Execucao continua:
  - Daemon em systemd (user service) com auto-restart.
  - Inicia no login e roda enquanto o PC estiver ligado.
- Kill switch (Wayland-safe):
  - Arquivo `~/.jarvis/STOP` interrompe tudo imediatamente.
  - Comando de emergencia: `systemctl --user stop jarvis-local`.
  - Hotkey e opcional (pode falhar em Wayland).
- Integracao com o cerebro (VPS):
  - Planos chegam do orquestrador remoto via canal seguro.
  - Policy/confirmacao sempre acontecem localmente.

## Como vamos replicar e melhorar (em Rust e com foco em performance)
- Loop visual deterministico + LLM quando precisa:
  - Primeiro tenta regras rapidas (AT-SPI, DOM do navegador, OCR simples).
  - So chama LLM/grounding quando a regra falha.
- Grounding leve:
  - Modo remoto: chamada HTTP para um servidor de grounding (GPU).
  - Modo local: ONNX/TensorRT opcional, somente se a maquina aguentar.
- Parsing estruturado:
  - Detector de elementos (bbox + texto + role) para reduzir OCR e melhorar clique.
  - Cache de layout por app/janela.
- OCR com cache e regioes de interesse:
  - Hash de tela + cache de texto.
  - OCR so em regioes que mudaram (diff visual).
  - Fast pass downscale + fallback full.
- Melhor que Agent S3:
  - Usa arvore de acessibilidade (AT-SPI) antes de CV.
  - Acoes hibridas (API quando possivel, GUI quando necessario).
  - Speculative multi-action para reduzir chamadas ao LLM.
  - RAG com docs/demos/traces por app.
  - Privacidade antes de enviar imagem para nuvem.
  - Politica de seguranca e confirmacao integradas.
  - Telemetria local para medir custo por acao.
- Motor de acao 100% Rust (maos):
  - Wayland: portal RemoteDesktop (preferido), wtype/ydotool como fallback.
  - Fallback controlado: sem pyautogui em producao.

## Arquitetura proposta (modulos Rust)
- rust/jarvis_vision:
  - captura de tela (Wayland/portal)
  - diff + cache + OCR
  - detector de modais/erros/2FA
  - mascara de privacidade
- rust/jarvis_actions:
  - mouse/teclado (Wayland), foco de janela, abrir app/url
  - busca por elemento via AT-SPI (texto, role, atributos)
- rust/jarvis_grounding:
  - cliente para grounding remoto
  - pipeline local opcional (ONNX)
- rust/jarvis_parser:
  - parse de tela (elementos, bbox, texto, hierarquia)
  - integra OCR + visao leve
- rust/jarvis_rag:
  - cliente de memoria/RAG no VPS (sem DB local)
  - cache LRU local de consultas e traces
- rust/jarvis_bridge:
  - daemon com JSON-RPC (Unix socket) para reduzir overhead
  - API unica para Python: take_screenshot, ocr, ground, click, type, etc

## Plano de implementacao (fases)
### Fase 0 - Medicao e base de referencia
- Definir metrica de peso (CPU %, RAM, tempo por acao, p95).
- Definir cenarios de pior caso (resolucao, OCR full, pagina pesada).
- Script de benchmark padrao para:
  - OCR fast vs OCR full
  - screenshot + diff
  - click + type + open app/url
- Resultado: tabela com peso atual do Python e baseline Rust.

### Fase 1 - Olhos em Rust (visao)
- Captura Wayland:
  - xdg-desktop-portal (ScreenCast) + PipeWire
  - fallback: grim (se suportado pelo compositor)
- OCR:
  - leptess (libtesseract) como padrao
  - fallback CLI se lib nao estiver disponivel
- Cache:
  - hash de imagem + texto
  - diff para OCR parcial
- API:
  - take_screenshot_png()
  - ocr_text(png_bytes)
  - detect_error_modal(png_bytes)
  - detect_captcha_or_2fa(png_bytes)

### Fase 1.5 - Parser estruturado de tela
- Integrar detector de elementos (bbox + texto + role).
- Priorizar parser leve (modelo pequeno remoto ou local se possivel).
- Unificar com AT-SPI e DOM quando existir estrutura nativa.

### Fase 2 - Maos em Rust (acoes)
- Input injection:
  - Wayland: RemoteDesktop portal (preferido)
  - Wayland fallback: wtype/ydotool (se permitido)
- Foco e janela:
  - lista de janelas, focar e maximizar
- AT-SPI:
  - buscar elemento por texto/role
  - obter coordenadas para clique preciso
- API:
  - click(x,y), type_text(text), hotkey(combo), open_app(cmd), open_url(url)

### Fase 3 - Grounding e loop inteligente
- Engine de grounding:
  - protocolo simples (request: screenshot + target textual)
  - resposta: bbox + confidence
- Loop de controle:
  - tentar AT-SPI/DOM
  - se falhar -> OCR + heuristica
  - se falhar -> grounding
  - se falhar -> LLM (com imagem e contexto curto)
- Reflexao:
  - se validacao falhar, nova tentativa com ajuste
- Speculative multi-action:
  - gerar lote de acoes, validar cada uma antes de executar a proxima
  - se falhar, voltar ao loop visual
  - cada acao ainda passa por policy/confirmacao antes de executar

### Fase 3.5 - Knowledge substrate (RAG)
- Indexar docs, demos e traces por app.
- Recuperar contexto antes do passo visual.
- Atualizar base quando uma tarefa completa com sucesso.
- Eficiencia:
  - Vetor remoto (nuvem) como default.
  - Cache local pequeno (LRU) por app.
  - TTL e limites de tamanho por app.
  - Resumos compactos para reduzir custo.

### Fase 4 - Integracao com o Jarvis atual
- Substituir chamadas Python por bridge Rust.
- Manter policy/telemetria no Python.
- Falha segura: se Rust indisponivel, logar e abortar acao.

### Fase 4.5 - Pipeline de experimento (MVP obrigatorio)
- Objetivo: permitir evolucao controlada do sistema com aprovacao humana.
- Fluxo padrao:
  1) Capturar baseline (metricas e taxa de sucesso).
  2) Definir hipotese e mudanca pequena (branch isolado).
  3) Rodar testes em sandbox (ou ambiente isolado).
  4) Medir: tempo por acao, taxa de acerto, custo, CPU/RAM.
  5) Comparar com baseline (ex: >3% de melhoria).
  6) Gerar relatorio simples (HTML/JSON) para revisao.
  7) Exigir aprovacao humana antes de aplicar.
  8) Se aprovado, merge; se nao, rollback total.
- Scheduler:
  - Janela de execucao configuravel (horas/dias).
  - Modo economico: rodar a cada X horas.
- Guardrails:
  - Nao altera policy de seguranca automaticamente.
  - Mudancas sempre removiveis e auditadas.
  - Log completo de todas as tentativas.

### Fase 5 - Robustez e performance
- Testes de regressao (captura, OCR, click, hotkey).
- Watchdog para evitar travas.
- Regras de retry com backoff.
- Empacotamento: binarios + cache de modelos.
- Modo sandbox remoto opcional (VM/servidor) para tarefas pesadas.

### Fase 6 - Recursos opcionais (futuro, nao agora)
- Painel/HUD leve (web):
  - Frontend estatico (HTML/CSS/JS) consumindo JSON de telemetria.
  - Hospedagem sugerida: GitHub Pages (mais simples e barato).
  - Alternativa: Vercel (melhor CI e dominio, mas mais complexo).
  - Painel mostra: tempo por acao, custos, erros, status, filas.
- Tell-me-when (monitoramento com economia):
  - Scheduler com intervalo configuravel (min/horas/dias).
  - Modo cloud-first para monitorar 24/7 sem gastar PC local.
  - Notificacoes: email/webhook/telegram (configuravel).
- Plugins/skills (marketplace):
  - Manifesto simples (nome, versao, permissao, comandos).
  - Registry remoto apenas com metadados; plugin roda local.
  - Instalacao reversivel e isolada (facil de remover).
- Sandbox por padrao:
  - Rodar tarefas em VM/contener para seguranca maxima.
  - Local somente se hardware permitir; preferir remoto.
- Multi-device orchestration (nao agora):
  - Maestro que coordena varias VMs/PCs em paralelo.
  - Usar apenas quando houver demanda real e custo justifique.

## Checklist mestre (execucao em ordem)
Regra fixa para cada item do checklist:
1) Implementar a parte.
2) Testar de forma robusta (teste funcional + edge cases).
3) Otimizar performance sem perder qualidade.
4) Endurecer contra bugs/falhas/seguranca.
5) Medir e registrar o peso de pior caso (CPU, RAM, GPU/VRAM, disco temporario e persistente).
6) Atualizar o diagrama (arquitetura honesta do estado atual, com pesos).
7) Revisar o codigo e confirmar que o diagrama representa 100% do sistema.
8) Marcar no checklist o que foi feito e como foi feito.
9) Atualizar `Documentos/README.md` com o que mudou (apenas quando algo for feito).
10) So seguir para o proximo item quando todos os sub-itens estiverem completos.

## Checklist por modulo (MVP)
Formato padrao por item:
- [ ] ITEM (pasta: caminho, local/nuvem)
  - [ ] Implementacao
  - [ ] Teste robusto
  - [ ] Otimizacao
  - [ ] Robustez/seguranca
  - [ ] Medicao de peso (pior caso)
  - [ ] Organizacao por pastas e imports
  - [ ] Separacao PC vs nuvem (documentada e refletida no diagrama)
  - [ ] Diagrama atualizado
  - [ ] Revisao diagrama x codigo
  - [ ] Registro do que foi feito
  - [ ] README atualizado

Itens MVP (ordem recomendada - foco em minimo funcional):
- [ ] Olhos do sistema (pasta: rust/jarvis_vision, local obrigatorio; parcial: modulo existe, sem portal/bridge)
- [ ] Maos do sistema (pasta: rust/jarvis_actions, local obrigatorio)
- [ ] Bridge Rust (pasta: rust/jarvis_bridge, local obrigatorio)
- [ ] Integracao no Python (pasta: jarvis/, local obrigatorio)
- [ ] Pipeline de experimento (pasta: rust/jarvis_experiments, local + nuvem opcional)

Itens pos-MVP (adiar para reduzir escopo):
- [ ] Grounding (pasta: rust/jarvis_grounding, preferir nuvem)
- [ ] Parser estruturado (pasta: rust/jarvis_parser, local ou nuvem)
- [ ] RAG por app (pasta: rust/jarvis_rag, VPS + cache local)

## Separacao honesta: o que deve ficar no PC vs nuvem
PC obrigatorio:
- Captura de tela real, input real (mouse/teclado), AT-SPI.
- Politica de seguranca, validacao local e confirmacao humana.
- Automacao local exige sessao grafica ativa e desbloqueada.

Pode ser nuvem:
- Grounding pesado, modelos de visao, RAG remoto, sandbox.
- Telemetria agregada e painel/HUD.

## Medicao de peso (pior caso) para o diagrama
Para cada balao do diagrama:
- CPU: percentual maximo observado na tarefa mais pesada.
- RAM: pico em MB.
- GPU: percentual maximo (se aplicavel) ou N/A.
- VRAM: pico em MB (se GPU for usada) ou N/A.
- Disco temporario: uso em MB durante execucao.
- Disco persistente: tamanho de modelos/cache em MB.
GPU representa a placa de video; nao duplicar a contagem.
Registrar o cenario de pior caso usado para a medicao.
Para funcoes em nuvem, marcar como "cloud" e medir peso no servidor (nao soma no PC).
Esses valores devem ir no diagrama de forma pequena e clara.

## Mapa de pastas (documentacao viva)
- Para cada item do checklist, documentar o caminho real e o motivo da pasta.
- A descricao deve estar em portugues simples e refletir a organizacao atual.
- Se mover arquivos, registrar o novo caminho e ajustar imports.

## Atualizacao do diagrama e honestidade
- A cada item concluido:
  - Atualizar `Documentos/DIAGRAMA_ARQUITETURA.svg`.
  - Conferir se caminhos e descricoes batem com o codigo atual.
  - Marcar no checklist que a revisao foi feita.

## Registro de conclusao
Ao finalizar cada item:
- Descrever o que foi feito, como foi feito e o que falta.
- Se algo ficou pendente, deixar anotado no item.

## Criterios de sucesso
- Peso visual (OCR full) <= baseline atual e fast pass <= 60.
- Latencia p95 por passo <= 2.5s em tarefas comuns.
- Taxa de acerto em tarefas de UI > 90% em ambiente controlado.
- Nao enviar screenshot sem passar pela mascara de privacidade.

## Riscos e mitigacoes
- Wayland sem permissao: portal obrigatorio, re-solicitar automaticamente, fallback seguro.
- Wayland sem sessao ativa/desbloqueada: pausar tarefas e reabrir sessao.
- Wayland sem lista de janelas: usar AT-SPI/heuristica e pedir ajuda humana.
- RemoteDesktop portal ausente no compositor: fallback wtype/ydotool e aviso claro.
- AT-SPI incompleto: usar hibrido AT-SPI + DOM + OCR + grounding.
- Input em Wayland: preferir portal; fallback wtype/ydotool quando permitido.
- Modelo de grounding pesado: default remoto + cache agressivo.
- Falhas de OCR: combinar OCR + AT-SPI + DOM.
- Falhas de input: fallback entre drivers, mas sem pyautogui em producao.
- Custo de nuvem: limitar chamadas, usar modelos menores e cache agressivo.
- Queda de rede: degradar para OCR local e pedir confirmacao humana.

## Proximos passos imediatos
- Validar quais APIs de Wayland estao disponiveis no Pop!_OS atual.
- Definir protocolo JSON-RPC do daemon Rust.
- Escolher modelo de grounding (remoto vs local) e custo.


---

# ANEXO: DOC_MEMORIA_OPENMEMORY.md

# Plano de Memoria Robusta (baixo custo)

Este plano define a melhor memoria possivel dentro do orcamento do projeto (R$ 300-400/mes),
com foco em robustez, baixo custo, privacidade e integracao com os outros planos.

## 1) Objetivo e restricoes
- Memoria de longo prazo com alto recall e baixo custo.
- Rodar bem em VPS CPU barata (4 vCPU + 16 GB RAM).
- Nao depender de API paga para embeddings.
- Integrar com o plano do cerebro (orquestrador no VPS) e com o plano de olhos/maos.

## Status atual (codigo)
- Existe memoria local (SQLite) e FIXED (comandos fixar/esquecer) em `jarvis/memoria/`.
- Existe integracao opcional com Supabase, mas sem sqlite-vec/FTS no VPS.
- Nao ha RAG completo, nem exportacao mensal para Drive.

## 2) Decisao principal
Escolha: **motor proprio no VPS** (nao usar OpenMemory como base no MVP).

Motivos:
- Custo e controle: evita infra extra e depende menos de API paga.
- Baixa latencia: mesma VPS do orquestrador.
- Integracao simples: reaproveita `jarvis/memoria/*` e `ProcedureStore`.

OpenMemory, Zep, Letta e similares ficam como opcao futura quando houver budget extra.

## 3) Arquitetura (alinhada aos outros planos)
Local (PC):
- Apenas cache de procedimentos aprovados e validacao local.
- Nao salva memoria completa no PC.

VPS CPU (principal):
- Banco de memoria (texto + vetores).
- Embeddings locais (CPU).
- RAG e resumo periodico (usando modelo base do cerebro).

Arquivo frio (Google Drive 1 TB):
- Historico de longo prazo (transcricoes, fatos e resumos).
- Nao participa do loop principal; usado apenas quando necessario.
- Drive ja pago (sem custo adicional).

Backup opcional (futuro):
- Supabase somente para memorias FIXED ou backups compactos.

## 4) Tecnologias escolhidas (baixo custo)
- Banco: SQLite no VPS (arquivo unico, simples e barato).
- Vetores: sqlite-vec (ou SQLite + tabela vetorial equivalente).
- Busca hibrida: FTS5 + vetores + score de recencia.
- Embeddings: modelo pequeno e multilingue (dim 384).
  - Preferencia: `multilingual-e5-small` (CPU ok).
  - Alternativa: `paraphrase-multilingual-MiniLM-L12-v2`.
- Resumos: modelo base do cerebro (Qwen2.5-7B-Instruct) em tarefas agendadas.
- Arquivo frio: exportacao em `.jsonl.zst` para Google Drive (via rclone).

## 5) Estrutura de dados (minimo necessario)
Memoria (tabela principal):
- id, kind, text, metadata, ts, layer, app, source, hash
- success_count, fail_count, feedback_score, last_feedback_ts

Vetores:
- id, embedding (dim 384), kind, app, ts

FTS:
- index de `text` + campos chave (app, kind, tags)

Procedimentos (ja existe):
- `~/.jarvis/procedures.db` (SQLite) no lado do orquestrador.
- A memoria nao duplica os passos; guarda apenas referencia/estatisticas se necessario.

Arquivo frio (Drive):
- pacotes mensais: `mem_YYYY_MM.jsonl.zst`
- manifesto: `manifest.jsonl` com id, ts, kind, hash, arquivo

## 6) Politicas de escrita (para nao inflar custo)
- Episodica: salvar apenas sucesso relevante ou erro importante.
- Procedural: salvar apenas quando usuario aprova.
- Semantica: salvar apenas quando confirmado (preferencias, fatos estaveis).
- Deduplicacao: hash + similaridade > limiar -> nao gravar.
- Arquivo frio: exportar apenas texto limpo e metadados essenciais.

## 7) Politicas de leitura (recall alto, custo baixo)
- Busca hibrida:
  - FTS para texto exato.
  - Vetor para semantica.
  - Score final = sim * 0.6 + recencia * 0.2 + sucesso * 0.2.
- Limites por app e por tipo para evitar lixo.
- Cache LRU de ultimas memorias usadas.
- Fallback: se a memoria local nao achar, consultar o manifesto do Drive.

## 8) Memoria humana (curto, medio, longo prazo)
- Curto prazo (HOT): cache em memoria + procedimentos recentes.
- Medio prazo (WARM): episodica recente no banco (dias/semanas).
- Longo prazo (COLD + FIXED): resumos consolidados + memorias fixadas.
- Arquivo frio (ARCHIVE): historico completo no Drive (anos).
- Fixar/Esquecer:
  - Comando "fixar memoria": envia item para FIXED (nao expira).
  - Comando "esquecer memoria": remove item (ou move para COLD).
  - Implementado no MVP local via `jarvis/cerebro/orchestrator.py` + `jarvis/memoria/memory.py`.

## 9) Consolidacao sem custo extra
- Resumo automatico com o **mesmo** modelo base do VPS (Qwen2.5-7B-Instruct).
- Rodar em horario ocioso (ex: madrugada).
- Salvar apenas o resumo no COLD e limpar detalhes redundantes.
- Regras de importancia: salvar mais o que teve sucesso ou foi marcado como importante.
- Exportacao mensal para Drive (texto compactado).

## 10) Feedback negativo/positivo (robustez)
- Quando usuario diz "aprovado": success_count++ e sobe prioridade.
- Quando usuario diz "errado"/"reprovado": fail_count++ e cai prioridade.
- Se fail_count alto: exigir confirmacao antes de reutilizar.
- Penalizar procedimentos com historico de falhas.

## 11) Decaimento e memoria longa
- HOT: recentes e usados com sucesso (cache).
- WARM: episodica recente (default).
- COLD: episodica antiga, resumida periodicamente.
- FIXED: memorias marcadas como permanentes (nunca expiram).
- ARCHIVE: historico completo no Drive (texto compactado).

Resumo automatico:
- Rodar a cada X dias/semana.
- Resumo grava em COLD e remove detalhes antigos.

## 12) Privacidade e seguranca
- Passar `PrivacyMasker` antes de salvar.
- Nunca enviar dados sensiveis para APIs externas.
- Memoria sensivel so fica no VPS (nao sai para nuvem publica).
- Opcional: criptografar arquivos do Drive com chave local.

## 13) Integracao com os planos existentes
Plano do cerebro:
- Orquestrador no VPS acessa a memoria local (SQLite + vetores).
- RAG roda no VPS para reduzir custo local.

Plano de olhos/maos:
- Memoria ajuda na validacao de UI e passos repetidos.
- Procedimentos aprovados ficam no livro; memoria procedural so referencia e contexto.

## 14) Plano de implementacao (checklist)
Fase 0 - Base
- [ ] Definir `JARVIS_EMBED_DIM=384` fixo.
- [ ] Padronizar modelo de embeddings.
- [ ] Criar estrutura SQLite para texto + vetores + FTS.

Fase 1 - Hibrido simples
- [ ] Escrita por regras (episodica/procedural/semantica).
- [ ] Deduplicacao por hash.
- [ ] Busca FTS + recencia.

Fase 2 - Vetores
- [ ] Integrar embeddings locais CPU.
- [ ] Busca vetorial e score hibrido.
- [ ] Cache LRU para consultas recentes.

Fase 3 - Robustez
- [ ] Feedback positivo/negativo com score.
- [ ] Regras de confirmacao por historico.
- [ ] Resumo periodico (COLD).
- [x] Comandos "fixar memoria" e "esquecer memoria" (implementado local, sem VPS).
- [ ] Regras de importancia e consolidacao.
- [ ] Exportacao mensal para Drive (rclone + manifesto).

Fase 4 - Opcional futuro
- [ ] Backup seletivo em Supabase.
- [ ] Avaliar OpenMemory/Zep/Letta se houver budget.

## 15) Alternativas open-source (avaliadas)
- OpenMemory: robusto, mas mais pesado e exige integracao extra.
- Zep: bom historico, mas servidor extra.
- Letta/MemGPT: potente, mas pesado e mais complexo.

Conclusao: para este orcamento, o motor proprio no VPS e o melhor custo-beneficio.


---

# ANEXO: PLANO_INFRA_DEPLOY_VPS.md

# Plano de Infra/Deploy VPS (CPU)

## Objetivo
Subir a infraestrutura minima no VPS para o cerebro, memoria e modelo base, mantendo custo baixo
e seguranca adequada para o MVP.

## Status atual (codigo)
- Nenhuma etapa de VPS/Tailscale/llama.cpp foi executada neste repo.
- Infra continua como plano; apenas protocolo e orquestrador local existem.

## Premissas
- VPS CPU e obrigatorio (orquestrador + memoria + modelo base).
- PC local fica apenas com olhos/maos/policy/confirmacao.
- Wayland-only no PC local.
- Orcamento mensal: R$ 300-400.

## Provedor recomendado (decisao final)
- **Hetzner** (melhor custo/beneficio para CPU).
- Plano sugerido: **CX32** (4 vCPU, 16 GB RAM, 160 GB SSD).
- Se Hetzner nao estiver disponivel: usar VPS equivalente (4 vCPU/16 GB).

## Especificacao minima recomendada
- 4 vCPU + 16 GB RAM (Qwen2.5-7B-Instruct quantizado Q4).
- 80-120 GB SSD.
- Se nao caber no custo: usar Qwen2.5-3B-Instruct (quantizado) e 8 GB RAM.

## Stack base no VPS
- Ubuntu 24.04 LTS.
- Python 3.11, git, build-essential.
- llama.cpp (server) + modelo GGUF.
- SQLite + sqlite-vec (memoria e vetores).
- rclone (arquivo frio no Drive).
- Tailscale (canal privado com PC local).

## Passo a passo (resumo)
1) Criar VPS com specs minimas e cobranca por hora (se possivel).
2) Configurar SSH por chave (sem senha) e criar usuario `jarvis`.
3) Atualizar pacotes e instalar dependencias base.
4) Configurar firewall (UFW) e limitar portas publicas.
5) Instalar Tailscale e conectar VPS + PC local.
6) Clonar o repositorio e instalar dependencias do orquestrador no VPS.
7) Instalar/compilar llama.cpp e baixar modelo GGUF (Qwen2.5-7B-Instruct Q4).
8) Subir servidor do modelo (systemd) ouvindo apenas na interface Tailscale.
9) Criar banco SQLite + sqlite-vec para memoria.
10) Validar compatibilidade do sqlite-vec no VPS (consulta e insert simples).
11) Agendar consolidacao/resumos fora do pico (ex: madrugada).
12) Configurar rclone para Drive e exportacao mensal (jsonl.zst + manifesto).
13) Criar `.env` seguro com chaves e limites de custo.
14) Subir orquestrador no VPS (systemd) expondo apenas na interface Tailscale.
15) Validar latencia e resposta do modelo base no VPS.

## Seguranca minima
- SSH por chave, sem login root.
- Firewall liberando apenas SSH e trafego Tailscale.
- Servicos expostos apenas na rede Tailscale.
- Logs locais com rotacao.

## Observabilidade
- Logs do orquestrador e do servidor do modelo em `journalctl`.
- Logrotate para evitar crescimento infinito.
- Telemetria de custo salva em arquivo JSON/CSV.

## Checklist de entrega
- [ ] VPS ativo e acessivel por SSH.
- [ ] Tailscale conectado entre VPS e PC.
- [ ] LLM base respondendo rapido no VPS.
- [ ] Memoria SQLite + sqlite-vec criada.
- [ ] Exportacao mensal para Drive configurada.
- [ ] Limites diarios de custo ativos.

## Falhas comuns e mitigacoes
- Latencia alta: reduzir contexto, trocar para Qwen2.5-3B-Instruct.
- RAM insuficiente: aumentar swap ou reduzir modelo.
- Queda de conexao: manter reconexao automatica no protocolo VPS <-> PC.


---

# ANEXO: PLANO_PASSOS_MANUAIS_15_DIAS.md

# Plano de Passos Manuais (15 dias de teste)

## Estado atual
Ate agora so existem planos e documentacao. Nenhum servidor, GPU ou API foi configurado.

Nota: o codigo local (orquestrador/policy/validacao) existe no repo, mas a infra do VPS nao foi feita.

## Orcamento alvo (15 dias)
Meta: R$ 150-200 para 15 dias (equivalente a R$ 300-400/mes).
Observacao: prefira provedores com cobranca por hora para pagar apenas os 15 dias.
Se o VPS cobrar mensal, ele pode consumir quase todo o orcamento de 15 dias.

Tabela de tetos (nao ultrapassar):
Recurso | Teto 15 dias | Observacao
VPS CPU | R$ 60-90 | Se for mensal, pode custar o mes inteiro
GPU sob demanda | R$ 40-70 | Limitar horas de uso
APIs pagas | R$ 10-30 | Uso so em falha total

Drive 1 TB: ja pago (sem custo adicional no MVP).

## Passos manuais (ordem recomendada)
1) Criar VPS CPU (Hetzner CX32 ou equivalente 4 vCPU + 16 GB RAM).
2) Instalar Ubuntu, configurar firewall basico e SSH.
3) Instalar Tailscale no VPS e no seu PC para canal privado seguro.
4) Subir o servidor do modelo base (llama.cpp + Qwen2.5-7B-Instruct GGUF).
5) Instalar sqlite-vec e criar o banco de memoria (SQLite + FTS + vetores).
6) Validar sqlite-vec (consulta e insert simples) e agendar resumos fora do pico.
7) Configurar rclone com o Google Drive (1 TB) e a exportacao mensal.
8) Criar conta RunPod e definir limite de gasto para 15 dias.
9) Criar template GPU (on-demand) e configurar auto-desligar.
10) Definir pre-aquecimento diario da GPU (evitar cold-start).
11) Criar conta no Gemini AI Studio (free tier) e gerar API key.
12) Criar conta na Groq Cloud (free tier) e gerar API key.
13) Criar conta na API leve paga (OpenAI, gpt-4o-mini) e definir limite diario.
14) Criar conta na API paga forte (gpt-4o) e definir limite diario.
15) Subir o orquestrador no VPS e validar comunicacao com o PC local.
16) Guardar todas as keys em um `.env` seguro no VPS e no PC local.
17) Configurar limites diarios de GPU e API no sistema.
18) Rodar testes com logs de custo por 15 dias.

## APIs gratuitas e contas extras
Nao recomendo criar varias contas para burlar limites gratuitos; isso pode violar termos e derrubar o acesso.
Se o provedor permitir varias contas por usuario, use com cautela e sempre respeite os termos.
Mais seguro: usar dois provedores diferentes (Gemini + Groq).

## Regras de uso (para nao estourar custo)
1) Qwen2.5-7B-Instruct no VPS e sempre o default.
2) API gratuita so se a confianca for baixa e quota ativa.
3) API paga leve (gpt-4o-mini) se a gratuita estiver indisponivel ou com qualidade insuficiente.
4) gpt-4o somente se tarefa for critica e o gate indicar necessidade.
5) Sem cadeia de APIs na mesma tarefa (escolher 1 nivel por tarefa).
Excecao: se a API gratuita falhar por quota antes de gastar tokens, pular direto para a paga.

## Deposito inicial (para 15 dias)
Sugestao conservadora:
1) VPS: escolher plano por hora; se for mensal, manter <= R$ 90.
2) GPU RunPod: colocar credito de R$ 40-70.
3) API paga (leve + forte): colocar credito total de R$ 10-30.

## Verificacao final antes de testar
1) Tailscale conectado entre VPS e PC.
2) Modelo base respondendo rapido no VPS.
3) Limites diarios configurados.
4) Quotas gratuitas detectadas automaticamente.
5) Logs de custo ativos.


---

# ANEXO: PLANO_TESTES_BENCHMARKS.md

# Plano de Testes e Benchmarks

## Objetivo
Garantir que cada modulo funcione, medir performance real e evitar regressao.

## Status atual (codigo)
- Testes unitarios existem em `testes/` (policy, orcamento, procedures, memoria, etc).
- Scripts de medicao existem (`scripts/measure_local_weights.py`, `scripts/run_benchmarks.sh`).
- Nao ha baseline formal nem resultados registrados em `Documentos/benchmarks/`.

## Premissas
- Wayland-only no PC local.
- Testes devem rodar em maquina real (sem navegador aberto, se possivel).
- Benchmarks sempre com cenarios de pior caso definidos.

## Tipos de testes
1) **Unitarios**
   - Parser de acoes, policy, validacao de schema.
2) **Integracao**
   - Orquestrador + policy + executor (dry-run).
   - Memoria (insert/search) no VPS.
3) **E2E**
   - Tarefas reais curtas (abrir app, digitar, clicar, validar).
4) **Regressao visual**
   - OCR fast vs OCR full.
   - Captura de tela + diff.

## Benchmarks obrigatorios (pior caso)
- **Olhos (vision)**
  - Screenshot + OCR completo.
  - OCR fast + fallback.
  - Detector de erro/captcha.
- **Maos (actions)**
  - click(x,y), type_text, hotkey.
  - Latencia total por acao.
- **Memoria**
  - Insercao (episodio) e busca (top-k).
  - p95 de consulta no VPS.
- **Cerebro**
  - Tempo medio por plano (Qwen2.5-7B-Instruct).
  - Taxa de erro do parser de plano.

## Metricas a registrar
- Latencia media e p95 por acao.
- CPU/RAM pico (PC local e VPS).
- GPU/VRAM (se usado).
- Taxa de sucesso (%).
- Custo por tarefa (tokens + tempo GPU).

## Criterios minimos de sucesso
- Latencia p95 por passo <= 2.5s em tarefas comuns.
- Taxa de acerto > 90% em cenarios controlados.
- Peso do vision (OCR full) <= baseline atual.

## Procedimento de execucao
1) Definir cenario (texto, tela, app).
2) Rodar 5 vezes (1 warm-up + 4 medicoes).
3) Salvar logs em `Documentos/benchmarks/` (JSON/CSV).
4) Comparar com baseline anterior.
5) Se piorar > 3%, bloquear merge.
6) Ajustar limiares de confianca com base nos resultados.

## Automacao sugerida
- Script unico: `scripts/run_benchmarks.sh`.
- Relatorio simples HTML/JSON para revisao humana.

## Checklist por etapa
- [ ] Definir suite de testes baseline.
- [x] Criar scripts de execucao (scripts/run_benchmarks.sh).
- [ ] Rodar benchmarks e salvar resultados.
- [ ] Calibrar limiares com 2-3 tarefas reais.
- [ ] Ajustar limiares se necessario.


---

# ANEXO: POLITICA_SEGURANCA_PRIVACIDADE.md

# Politica de Seguranca e Privacidade

## Objetivo
Definir regras claras para execucao segura, protecao de dados e uso de nuvem.
Esta politica e obrigatoria para qualquer execucao em producao.

## Principios
- **Local e o gatekeeper**: policy e confirmacao sempre no PC local.
- **Menor privilegio**: executar apenas o necessario.
- **Dados sensiveis nao saem**: redacao e mascaras antes de enviar para nuvem.
- **Fail-safe**: em duvida, abortar ou pedir ajuda humana.

## Classificacao de dados
1) **Publico**: conteudo sem risco (ex: instrucoes genericas).
2) **Sensivel**: emails, contatos, documentos pessoais, dados financeiros.
3) **Sigiloso**: senhas, chaves, tokens, dados bancarios, documentos legais.

Regras:
- Publico pode ir para VPS e APIs.
- Sensivel pode ir para VPS, mas **nao** para APIs externas sem confirmacao.
- Sigiloso **nunca** vai para APIs; deve ser redigido ou bloqueado.
Nota: palavras-chave de sensivel podem ser habilitadas via `JARVIS_SENSITIVE_KEYWORDS_STRICT`.

## Mascaramento e redacao
- Usar `PrivacyMasker` antes de enviar imagens ou texto para nuvem.
- Blacklist de apps e dominios sempre bloqueia envio.
- Redigir CPF/CNPJ, email, telefone, dados bancarios e senhas.

## Prompt injection (anti-injecao)
- Nunca executar comandos vindos de pagina web como instrucoes.
- Separar "dados observados" de "instrucoes do sistema".
- Validar schema de acoes antes de executar.
- Se detectar dado sensivel, perguntar antes de enviar para IA externa.

## Execucao e aprovacao
- Acoes de risco exigem confirmacao humana.
- Modo `dry-run` habilitavel como padrao em ambiente novo.
- Sem policy valida: nenhuma acao e executada.

## Kill switch (obrigatorio)
- Deve existir um mecanismo de parada imediata.
- Preferir duas opcoes:
  1) **Arquivo STOP**: se `~/.jarvis/STOP` existir, abortar tudo.
  2) **systemctl --user stop jarvis-local** (parada imediata do daemon).
- Atalho local e opcional (Wayland pode falhar).
- Kill switch deve ser testado em todos os ambientes.

## Logs e auditoria
- Logs locais com redacao de dados sensiveis.
- Guardar: timestamp, acao, resultado, risco, custo.
- Nao registrar capturas completas de tela sem necessidade.
- Log de paradas com motivo e resumo do que foi feito (chat local).

## Retencao e backup
- Memoria principal no VPS (SQLite + vetores).
- Exportacao mensal para Drive (jsonl.zst + manifesto).
- Opcional: criptografar arquivo frio com chave local.

## Checklist minimo de seguranca (antes de produzir)
- [x] Policy ativa e validando todas as acoes (codigo).
- [x] Kill switch funcionando (arquivo STOP).
- [x] Redacao de dados sensiveis ativa (sanitizacao).
- [x] Bloqueio de apps/dominios sensiveis ativo (policy + policy usuario).
- [x] Logs auditaveis sem dados sigilosos (telemetria + chat log).


---

# ANEXO: PROTOCOLO_VPS_PC.md

# Protocolo VPS <-> PC (baixo custo)

## Objetivo
Definir a comunicacao entre o VPS (cerebro/memoria) e o PC local (executor) de forma segura,
simples e barata.

## Status atual (codigo)
- O protocolo esta implementado em `jarvis/comunicacao/protocolo.py`.
- Ainda nao existe cliente/servidor conectado ao fluxo principal.

## Premissas
- PC local e o gatekeeper: policy/confirmacao sempre locais.
- VPS nunca executa acao direta no PC sem validacao local.
- Canal privado via Tailscale sempre que possivel.
- Wayland-only no PC local.

## Topologia
- PC local inicia a conexao com o VPS (evita problemas de NAT).
- Transporte: WebSocket (JSON) ou gRPC (protobuf).
- Porta exposta apenas na interface Tailscale.

## Autenticacao
Camadas recomendadas:
1) Tailscale (IP privado).
2) Token compartilhado (JWT simples ou HMAC).
3) Opcional: mTLS se nao usar Tailscale.

## Rotacao de token
- Rotacionar token a cada X dias (ex: 30).
- Incluir `token_id` no payload para facilitar revogacao.
- Rejeitar tokens expirados ou revogados.

## Formato de mensagem (JSON)
Campos base:
- `version`: versao do protocolo (ex: "1.0").
- `type`: string (ex: "hello", "plan_request", "plan_response").
- `id`: UUID da mensagem.
- `ts`: timestamp unix ms.
- `nonce`: valor unico por mensagem (anti-replay).
- `session_id`: id da sessao.
- `payload`: objeto com dados.

## Tipos de mensagem (minimo)
- `hello` (PC -> VPS): capabilities, versao, session_id.
- `heartbeat` (ambos): health + uptime + load.
- `plan_request` (PC -> VPS): comando do usuario + contexto permitido.
- `plan_response` (VPS -> PC): plano + confidence + risco.
- `action_result` (PC -> VPS): resultado da execucao.
- `telemetry_event` (PC -> VPS): custo/latencia/erros agregados.
- `error` (ambos): erro padrao + codigo.

## Fluxo principal
1) PC abre conexao e envia `hello`.
2) VPS responde com `heartbeat` e confirma sessao.
3) PC envia `plan_request` com texto e contexto permitido.
4) VPS devolve `plan_response`.
5) PC aplica policy/confirmacao, executa e retorna `action_result`.
6) PC envia `telemetry_event` resumido.

## Timeouts e retry
- `plan_request`: timeout 10-20s (depende do modelo).
- Retry com backoff exponencial (2s, 5s, 10s).
- Se exceder 3 tentativas: abortar e pedir ajuda humana.

## Idempotencia
- Toda mensagem tem `id`.
- VPS ignora `plan_request` repetido com mesmo `id`.
- PC ignora `plan_response` repetido.

## Regras de seguranca
- Nunca enviar dados sigilosos para o VPS se policy local bloquear.
- Sempre mascarar imagens antes de enviar (quando houver).
- Logs de auditoria locais e no VPS (sem dados sensiveis).

## Falhas e degradacao
- Sem conexao VPS: PC entra em modo degradado (regras locais + procedimentos).
- Sem aprovacao humana: abortar acoes de risco.
- Sem policy: nao executar nada.

## Observacoes
- Implementar primeiro o protocolo simples (WebSocket + JSON).
- Migrar para gRPC apenas se houver necessidade real.


---

# ANEXO: REGISTRO_IMPLEMENTACAO.md

# Registro de Implementacao (inicio)

## O que foi feito
- Gate de confianca do plano: validacao de schema e `confidence` em `jarvis/validacao/plano.py`.
- Orcamento diario para LLM: limites por chamadas e caracteres em `jarvis/cerebro/orcamento.py`.
- Integracao no LLM Router: valida plano, aplica gate e registra consumo.
- Orquestrador valida plano antes de executar (bloqueia schema invalido).
- Orquestrador agora para quando a validacao retorna `failed`.
- Policy agora cobre `web_fill` e `web_click` (mesmas regras de seguranca).
- Screenshots salvos passam por mascara de privacidade quando ativada.
- Loop de falhas: depois de N falhas, pede explicacao e tenta com guidance.
- Policy do usuario em arquivo (bloquear/permitir sites e apps).
- Removidos logs de debug ruidosos do fluxo principal.
- Protocolo VPS <-> PC em codigo: mensagens e validacao basica em `jarvis/comunicacao/protocolo.py`.
- `ActionPlan` agora carrega `confidence`.
- Cerebro local configuravel (OpenAI-compat) antes da nuvem.
- Escada em camadas: local -> browser AI manual -> cloud single-shot.
- Auto-aprendizado de procedimentos ao concluir com guidance.
- Sanitizacao de respostas externas (anti prompt injection) com redacao automatica.
- Classificacao de dados (publico/sensivel/sigiloso) para redacao externa.
- Kill switch local via arquivo STOP (com aviso no preflight).
- Comandos "fixar memoria" e "esquecer memoria" (com deduplicacao local).
- Chat log local com motivo das paradas e resumo do que foi feito.
- Bloqueio de envio externo quando ha dados sensiveis (com confirmacao).
- Cooldown do LLM local quando o servidor falha.
- SQLite em modo WAL para memoria/procedures (latencia menor).
- Cache de OCR no validator Python (hash da tela).
- Chat UI local com inbox de comandos.
- Classificacao sensivel menos rigida (keywords opcionais via env).
- Chat auto-open agora tem cooldown para evitar abrir varias vezes.
- Tratamento de erro para sounddevice/pyautogui quando libs nativas faltam.
- Dependencias Python instaladas em `.venv` (Playwright, Supabase, OCR, STT, etc).
- Wayland: click via ydotool (daemon) e scroll via PageUp/PageDown quando necessario.
- Validator Python agora tenta grim no Wayland antes de outros fallbacks.

## Como foi feito
- `jarvis/cerebro/llm.py` agora calcula `confidence` e aplica gate antes de aceitar um plano.
- `jarvis/cerebro/orchestrator.py` cria o orcamento diario e passa para o LLM.
- `jarvis/cerebro/orchestrator.py` valida o plano antes de executar.
- `jarvis/seguranca/policy.py` ganhou suporte para acoes web (`web_fill`, `web_click`).
- `jarvis/validacao/validator.py` mascara screenshots salvas quando `JARVIS_MASK_SCREENSHOTS=true`.
- `jarvis/seguranca/policy_usuario.py` guarda bloqueios do usuario.
- `jarvis/cerebro/orchestrator.py` aplica comandos de policy e tenta guidance em falhas.
- Novas variaveis de ambiente em `jarvis/cerebro/config.py`.
- `jarvis/cerebro/llm.py` ganhou `LocalLLMRouter` e `SingleShotLLMRouter` (sem cadeia de APIs).
- `jarvis/cerebro/orchestrator.py` tenta cerebro local, pede ajuda via navegador e so depois usa cloud.
- Guidance agora pode ser JSON direto e salva procedimentos quando habilitado.
- Prompt de ajuda inclui erro observado, tentativas anteriores e instrucao de colagem (<COLAR>).
- Diagrama atualizado com cerebro local e IA no navegador.
- Procedimentos agora preferem planos mais simples (menos acoes).
- Livro de procedimentos em SQLite com tags, indice e limites.
- Novas variaveis: `JARVIS_PROCEDURES_PATH`, `JARVIS_PROCEDURES_MAX_TOTAL`, `JARVIS_PROCEDURES_MAX_PER_TAG`, `JARVIS_PROCEDURES_TTL_DAYS`.
- Match de procedimentos agora usa score (token/tag) para reduzir ambiguidade.
- Diagrama ajustado: legenda movida para nao cobrir baloes.
- Nova sanitizacao em `jarvis/seguranca/sanitizacao.py` e kill switch em `jarvis/seguranca/kill_switch.py`.
- Orquestrador aplica sanitizacao em guidance e redacao antes de chamar LLM paga.
- Memoria local ganhou `add_fixed_knowledge` e `forget` com dedup e delete local.
- Preflight avisa quando STOP esta ativo.
- Chat log em `jarvis/comunicacao/chat_log.py` e comandos `abrir chat`/`--open-chat`.
- Chat UI em `jarvis/entrada/chat_ui.py` e inbox em `jarvis/comunicacao/chat_inbox.py`.
- Orquestrador registra paradas no chat com motivo e resumo.
- Guardrail: bloqueia IA externa quando texto e sensivel (com pergunta ao usuario).
- Local LLM tem cooldown configuravel.
- SQLite com WAL/NORMAL e OCR cache configuravel no validator Python.
- Medicao local basica em `scripts/measure_local_weights.py` (pesos micro).
- Import de sounddevice/pyautogui agora tolera erro de libs nativas.
- Ambiente Python via `.venv` para contornar PEP 668.
- Preflight agora avisa se ydotoold nao esta ativo (Wayland).

## Testes adicionados
Pasta dedicada: `testes/`
- `testes/teste_validacao_plano.py`
- `testes/teste_orcamento_diario.py`
- `testes/teste_policy_usuario.py`
- `testes/teste_llm_roteamento.py`
- `testes/teste_procedures_store.py`
- `testes/teste_sanitizacao.py`
- `testes/teste_memoria_local.py`
- `testes/teste_kill_switch.py`
- `testes/teste_chat_log.py`
- `testes/teste_chat_inbox.py`

Rodar:
```bash
python3 -m unittest discover -s testes
```

Resultado (no ambiente atual - 2026-01-02):
```text
.venv/bin/python -m unittest discover -s testes
Ran 22 tests in 0.198s
OK
```

Pesos micro (ambiente atual - 2026-01-02):
```json
{
  "policy_check": {
    "latency_ms": 1.9638200028566644,
    "cpu_pct": 99.38701088494611,
    "rss_mb": 95.6640625
  },
  "sanitizacao": {
    "latency_ms": 1.3838570012012497,
    "cpu_pct": 99.63276755601463,
    "rss_mb": 95.6640625
  },
  "chat_log_append": {
    "latency_ms": 1.6590319937677123,
    "cpu_pct": 99.39761414886605,
    "rss_mb": 95.6640625
  },
  "procedures_match": {
    "latency_ms": 123.5993279988179,
    "cpu_pct": 15.534655395498579,
    "rss_mb": 96.07421875
  },
  "memory_add_search": {
    "latency_ms": 15.544519003015012,
    "cpu_pct": 58.782484404078076,
    "rss_mb": 96.08203125
  },
  "orchestrator_dry_run": {
    "latency_ms": 61.51155399857089,
    "cpu_pct": 11.952448234666315,
    "rss_mb": 96.09765625
  },
  "validator_check": {
    "latency_ms": 5575.390452002466,
    "cpu_pct": 11.888790026569902,
    "rss_mb": 104.67578125
  }
}
```

Preflight (ambiente atual - 2026-01-02):
- [OK] LLM local configurado (via .env).
- [OK] TTS, Chat UI, OCR e Aprendizado disponiveis.
- [OK] Acoes web: Playwright pronto.
- [OK] Acoes desktop: ydotool socket detectado.
- [FAIL] STT: local sem faster-whisper.
- [WARN] LLM cloud em modo mock (sem Groq/OpenAI compat).
- [WARN] Memoria cloud: Supabase nao configurado.

## Observacoes
- O consumo de tokens e aproximado por caracteres do comando.
- O protocolo VPS ainda nao esta conectado ao fluxo principal (so estrutura).
- Orcamento diario fica em `~/.jarvis/orcamento.json` (ou `JARVIS_DATA_DIR`).
- O passo de browser AI e manual (usuario cola a resposta).
- O cerebro local exige servidor OpenAI-compat configurado.
- Medicao rapida do validator:
```text
python3 scripts/measure_validator_weight.py --runs 3 --no-cache
mode=rust
median_s=0.0000
suggested_weight=1
```


---

# ANEXO: PESOS_MEDIDOS.md

# Pesos medidos (micro) - Jarvis

Este arquivo registra **medicoes micro** feitas localmente com `scripts/measure_local_weights.py`.
Elas medem latencia, CPU (%) e RSS do **processo atual**, nao representam carga real de producao
com automacao, OCR real, STT/TTS ou drivers externos.

Rodar:
```bash
python3 scripts/measure_local_weights.py
```

## Medicoes micro (ambiente atual - 2026-01-02)
```json
{
  "policy_check": {
    "latency_ms": 1.9638200028566644,
    "cpu_pct": 99.38701088494611,
    "rss_mb": 95.6640625
  },
  "sanitizacao": {
    "latency_ms": 1.3838570012012497,
    "cpu_pct": 99.63276755601463,
    "rss_mb": 95.6640625
  },
  "chat_log_append": {
    "latency_ms": 1.6590319937677123,
    "cpu_pct": 99.39761414886605,
    "rss_mb": 95.6640625
  },
  "procedures_match": {
    "latency_ms": 123.5993279988179,
    "cpu_pct": 15.534655395498579,
    "rss_mb": 96.07421875
  },
  "memory_add_search": {
    "latency_ms": 15.544519003015012,
    "cpu_pct": 58.782484404078076,
    "rss_mb": 96.08203125
  },
  "orchestrator_dry_run": {
    "latency_ms": 61.51155399857089,
    "cpu_pct": 11.952448234666315,
    "rss_mb": 96.09765625
  },
  "validator_check": {
    "latency_ms": 5575.390452002466,
    "cpu_pct": 11.888790026569902,
    "rss_mb": 104.67578125
  }
}
```

## Dependencias faltantes no ambiente atual (preflight - 2026-01-02)
- `faster-whisper` (STT local)
- LLM cloud nao configurado (`JARVIS_GROQ_API_KEY` ou OpenAI compat)
- Supabase nao configurado (`JARVIS_SUPABASE_URL`/`JARVIS_SUPABASE_KEY`)

## Dependencias instaladas no venv
- Python deps via `.venv`: numpy, sounddevice, Pillow, pytesseract, pynput, Playwright, Supabase, pytest etc.
- Playwright Chromium instalado via `.venv/bin/python -m playwright install chromium`.
 - TTS local (`espeak-ng`), OCR (`tesseract`) e UI (`tkinter`) instalados no sistema.
 - Wayland input: `wtype` + `ydotool` (requer `ydotoold` ativo).

## Itens ainda estimados (sem medicao real)
- STT/TTS (depende de drivers/servicos)
- Automacao desktop/web (depende de apps e compositor)
- Vision/OCR real (depende de tesseract/portal)
- LLM local em producao (depende de modelo e hardware)
- VPS/Cloud (depende de infra real)

## Observacoes
- CPU % em micro-medicoes pode parecer alto por causa da duracao curta.
- Use estas metricas apenas como baseline leve; valores reais devem ser medidos em workload real.
- O validator ficou lento neste ambiente por causa de captura via fallback (Wayland sem portal).


---

# ANEXO: MELHORIAS_IDENTIFICADAS.md

# Melhorias Identificadas no Codigo

## Resumo Executivo

Foram identificadas **47 melhorias potenciais** em 8 categorias:
- **Performance**: 12 melhorias
- **Codigo Duplicado**: 8 melhorias
- **Cache/Memoizacao**: 6 melhorias
- **Validacao/Seguranca**: 7 melhorias
- **UX/Erros**: 5 melhorias
- **Manutenibilidade**: 5 melhorias
- **Otimizacoes de I/O**: 4 melhorias

---

##  PERFORMANCE (12 melhorias)

### 1. **Normalizacao de Texto Repetida**

**Problema:**
- `text.strip().lower()` aparece 23 vezes no codigo
- Cada chamada cria nova string

**Localizacao:**
- `orchestrator.py`: 5 ocorrencias
- `policy.py`: 4 ocorrencias
- `sanitizacao.py`: 1 ocorrencia
- Outros: 13 ocorrencias

**Solucao:**
```python
# Criar funcao helper
def normalize_text(text: str) -> str:
    """Normalize text for comparison."""
    return text.strip().lower()

# Usar em todos os lugares
if normalize_text(spoken) == normalize_text(voice_phrase):
    ...
```

**Impacto:**  Reduz alocacoes de memoria, codigo mais limpo

---

### 2. **Cache de Regex Compiladas**

**Problema:**
- Regex sao recompiladas a cada uso
- `_INJECTION_RE`, `_EMAIL_RE`, etc. sao compiladas toda vez

**Localizacao:**
- `sanitizacao.py`: multiplas regex
- `policy.py`: regex para validacao
- `procedures.py`: regex para matching

**Solucao:**
```python
# Compilar uma vez no modulo
_INJECTION_PATTERNS = [...]
_INJECTION_RE = re.compile("|".join(_INJECTION_PATTERNS), re.IGNORECASE)

# Ja esta feito, mas verificar se todas estao compiladas
```

**Impacto:**  Reduz overhead de compilacao

---

### 3. **Otimizar Loop de Matching de Procedimentos**

**Problema:**
- `match()` compila regex para cada candidato
- `template_to_regex()` e chamado repetidamente

**Localizacao:**
- `procedures.py:256-281`

**Solucao:**
```python
# Cache de regex compiladas por template
def match(self, command: str) -> Optional[Tuple[ActionPlan, Dict[str, str]]]:
    candidates = self._candidates_for_command(command)
    best: Optional[Tuple[ProcedureRecord, Dict[str, str]]] = None
    best_score = -1.0

    # Compilar regex uma vez por template (cache)
    for proc in candidates:
        pattern = self._get_cached_regex(proc.template)  # Cache aqui
        match = pattern.match(command, flags=re.IGNORECASE)
        ...
```

**Impacto:**  Reduz tempo de matching em 50-70%

---

### 4. **Evitar Rebuild de Indice Desnecessario**

**Problema:**
- `_rebuild_index()` e chamado apos cada `_delete()`
- Pode ser custoso com muitos procedimentos

**Localizacao:**
- `procedures.py:337-338`

**Solucao:**
```python
def _delete(self, proc: ProcedureRecord) -> None:
    # ... deletar do DB ...
    self._procedures = [p for p in self._procedures if p.id != proc.id]
    # Rebuild apenas se necessario (lazy)
    self._index_dirty = True

def _ensure_index(self) -> None:
    if self._index_dirty:
        self._rebuild_index()
        self._index_dirty = False
```

**Impacto:**  Reduz operacoes de rebuild em 80%
**Status:** ✅ Implementado em `jarvis/memoria/procedures.py` e coberto pelo benchmark `scripts/measure_local_weights.py`.

---

### 5. **Otimizar Busca de Memoria**

**Problema:**
- Busca hibrida pode ser lenta sem indices adequados
- FTS + vetores + score pode ser otimizado

**Localizacao:**
- `memory.py`: metodos de busca

**Solucao:**
```python
# Adicionar indices compostos
conn.execute("""
    CREATE INDEX IF NOT EXISTS idx_memories_search
    ON memories(kind, layer, ts DESC)
""")

# Usar LIMIT mais cedo na query
# Buscar apenas top N, nao todos
```

**Impacto:**  Reduz tempo de busca em 60-80%

---

### 6. **Batch de Operacoes de I/O**

**Problema:**
- Multiplas escritas em arquivo JSON
- Cada `json.dumps()` e uma operacao separada

**Localizacao:**
- `telemetry.py`: uma linha por evento
- `chat_log.py`: append linha a linha
- `orcamento.py`: reescreve arquivo inteiro

**Solucao:**
```python
# Buffer de escrita
class BufferedTelemetry:
    def __init__(self, log_path: Path, buffer_size: int = 10):
        self._buffer = []
        self._buffer_size = buffer_size

    def log_event(self, event_type: str, data: dict):
        self._buffer.append({"type": event_type, "data": data, "ts": time.time()})
        if len(self._buffer) >= self._buffer_size:
            self._flush()

    def _flush(self):
        # Escrever todas de uma vez
        ...
```

**Impacto:**  Reduz I/O em 70-90%

---

### 7. **Cache de Embeddings Mais Agressivo**

**Problema:**
- Embeddings sao recalculados mesmo para textos similares
- Cache atual pode nao ser suficiente

**Localizacao:**
- `embeddings.py`: `EmbeddingCache`

**Solucao:**
```python
# Adicionar cache de similaridade
# Se texto e muito similar (90%+), reusar embedding
def _similarity_cache_key(self, text: str) -> Optional[str]:
    # Hash de palavras-chave
    words = set(text.lower().split())
    key = hashlib.md5(" ".join(sorted(words)).encode()).hexdigest()
    return self._similarity_cache.get(key)
```

**Impacto:**  Reduz chamadas de embedding em 30-50%

---

### 8. **Lazy Loading de Modulos Pesados**

**Problema:**
- Alguns modulos sao importados mesmo quando nao usados
- PIL, pytesseract, etc. sao pesados

**Localizacao:**
- Multiplos arquivos com imports no topo

**Solucao:**
```python
# Ja esta feito com try/except, mas pode melhorar
# Usar importlib para carregar sob demanda
def _lazy_import_pil():
    if not hasattr(_lazy_import_pil, '_module'):
        from PIL import Image
        _lazy_import_pil._module = Image
    return _lazy_import_pil._module
```

**Impacto:**  Reduz tempo de inicializacao em 20-30%

---

### 9. **Otimizar Validacao de Planos**

**Problema:**
- `validar_plano()` e chamado multiplas vezes
- Pode ser cacheado para planos identicos

**Localizacao:**
- `orchestrator.py`: validacao antes de executar
- `llm.py`: validacao apos gerar plano

**Solucao:**
```python
# Cache de validacao por hash do plano
_validation_cache: Dict[str, QualidadePlano] = {}

def validar_plano_cached(plan: ActionPlan) -> QualidadePlano:
    plan_hash = hashlib.md5(json.dumps(plan.to_dict()).encode()).hexdigest()
    if plan_hash in _validation_cache:
        return _validation_cache[plan_hash]
    result = validar_plano(plan)
    _validation_cache[plan_hash] = result
    return result
```

**Impacto:**  Reduz validacoes duplicadas

---

### 10. **Reduzir Sleeps Desnecessarios**

**Problema:**
- `time.sleep(0.5)` no loop de voz pode ser reduzido
- `time.sleep(0.1)` no recorder pode ser otimizado

**Localizacao:**
- `entrada/app.py:81`
- `recorder.py:318`

**Solucao:**
```python
# Usar eventos ao inves de polling
import threading

class VoiceLoop:
    def __init__(self):
        self._event = threading.Event()

    def wait_for_voice(self, timeout: float = 5.0):
        return self._event.wait(timeout)
```

**Impacto:**  Reduz latencia e CPU

---

### 11. **Otimizar Serializacao JSON**

**Problema:**
- `json.dumps()` e chamado multiplas vezes
- Pode usar `orjson` para melhor performance

**Localizacao:**
- 29 ocorrencias de `json.dumps/json.loads`

**Solucao:**
```python
# Usar orjson (mais rapido)
try:
    import orjson as json
    json.dumps = lambda obj, **kw: orjson.dumps(obj).decode()
    json.loads = lambda s, **kw: orjson.loads(s)
except ImportError:
    import json  # Fallback
```

**Impacto:**  Reduz tempo de serializacao em 50-70%

---

### 12. **Pool de Conexoes SQLite**

**Problema:**
- Cada operacao abre/fecha conexao
- Pode reusar conexoes

**Localizacao:**
- `memory.py`: multiplas conexoes
- `procedures.py`: multiplas conexoes

**Solucao:**
```python
# Connection pool (thread-local)
import threading

_local_conn = threading.local()

def get_connection(db_path: Path) -> sqlite3.Connection:
    if not hasattr(_local_conn, 'connection'):
        _local_conn.connection = sqlite3.connect(db_path)
    return _local_conn.connection
```

**Impacto:**  Reduz overhead de conexao em 60-80%

---

##  CODIGO DUPLICADO (8 melhorias)

### 13. **Funcao Helper para Normalizacao**

**Problema:**
- `text.strip().lower()` repetido 23 vezes

**Solucao:**
```python
# jarvis/utils/text.py
def normalize_text(text: str) -> str:
    """Normalize text for comparison."""
    return text.strip().lower()
```

---

### 14. **Helper para Verificacao de Ambiente**

**Problema:**
- Logica de `_env_bool()` repetida em varios lugares

**Localizacao:**
- `config.py:23-28`
- `sanitizacao.py:70` (similar)

**Solucao:**
```python
# Centralizar em utils
def env_bool(key: str, default: bool = False) -> bool:
    value = os.environ.get(key)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}
```

---

### 15. **Helper para Parsing de JSON Seguro**

**Problema:**
- `_safe_json_loads()` existe mas pode ser melhorado
- Logica de parsing repetida

**Localizacao:**
- `llm.py:835-843`

**Solucao:**
```python
# Melhorar funcao existente
def safe_json_loads(text: str, default: Optional[dict] = None) -> Optional[dict]:
    """Safely parse JSON from text."""
    try:
        # Tentar extrair JSON de texto
        match = re.search(r'\{[^{}]*\}', text, re.DOTALL)
        if match:
            return json.loads(match.group(0))
        return json.loads(text)
    except Exception:
        return default
```

---

### 16. **Helper para Redacao de Texto**

**Problema:**
- Logica de redacao pode ser reutilizada

**Solucao:**
```python
# Criar funcao generica
def redact_sensitive(text: str, patterns: List[re.Pattern]) -> Tuple[str, List[str]]:
    """Generic redaction function."""
    redactions = []
    result = text
    for pattern, token in patterns:
        if pattern.search(result):
            result = pattern.sub(token, result)
            redactions.append(token)
    return result, redactions
```

---

### 17. **Helper para Validacao de Planos**

**Problema:**
- Validacao repetida em multiplos lugares

**Solucao:**
```python
# Criar wrapper que cacheia
def validate_plan_cached(plan: ActionPlan) -> QualidadePlano:
    """Validate plan with caching."""
    # ... implementacao com cache ...
```

---

### 18. **Helper para Logging de Eventos**

**Problema:**
- Padrao de logging repetido

**Solucao:**
```python
# Criar decorator ou helper
def log_event(event_type: str, data: dict, telemetry: Telemetry):
    """Log event with consistent format."""
    telemetry.log_event(event_type, {
        "timestamp": time.time(),
        **data
    })
```

---

### 19. **Helper para Tratamento de Erros**

**Problema:**
- Padrao try/except repetido

**Solucao:**
```python
# Criar context manager
@contextmanager
def handle_errors(telemetry: Telemetry, context: str):
    try:
        yield
    except Exception as e:
        telemetry.log_event(f"{context}_error", {"error": str(e)})
        raise
```

---

### 20. **Helper para Cache de Resultados**

**Problema:**
- Logica de cache repetida

**Solucao:**
```python
# Criar decorator generico
def cached(ttl: int = 3600, max_size: int = 100):
    def decorator(func):
        cache = {}
        def wrapper(*args, **kwargs):
            key = hashlib.md5(str(args + tuple(kwargs.items())).encode()).hexdigest()
            if key in cache:
                entry = cache[key]
                if time.time() - entry['ts'] < ttl:
                    return entry['value']
            result = func(*args, **kwargs)
            cache[key] = {'value': result, 'ts': time.time()}
            if len(cache) > max_size:
                # Evict oldest
                ...
            return result
        return wrapper
    return decorator
```

---

##  CACHE/MEMOIZACAO (6 melhorias)

### 21. **Cache de Validacao de Planos**

**Ja mencionado em #9**, mas detalhar:

```python
# Cache por hash do plano
_plan_validation_cache: Dict[str, QualidadePlano] = {}
CACHE_TTL = 3600  # 1 hora

def validar_plano_cached(plan: ActionPlan) -> QualidadePlano:
    plan_dict = plan.to_dict()
    plan_hash = hashlib.md5(json.dumps(plan_dict, sort_keys=True).encode()).hexdigest()

    if plan_hash in _plan_validation_cache:
        cached = _plan_validation_cache[plan_hash]
        if time.time() - cached['ts'] < CACHE_TTL:
            return cached['result']

    result = validar_plano(plan)
    _plan_validation_cache[plan_hash] = {'result': result, 'ts': time.time()}

    # Limpar cache antigo
    if len(_plan_validation_cache) > 1000:
        _plan_validation_cache.clear()

    return result
```

---

### 22. **Cache de Regex Compiladas**

**Ja mencionado em #2**, mas implementar:

```python
# Cache de regex por template
_regex_cache: Dict[str, re.Pattern] = {}

def template_to_regex_cached(template: str) -> Tuple[re.Pattern, List[str]]:
    if template in _regex_cache:
        pattern, slots = _regex_cache[template]
        return pattern, slots

    pattern, slots = template_to_regex(template)
    _regex_cache[template] = (pattern, slots)
    return pattern, slots
```

---

### 23. **Cache de Classificacao de Texto**

**Problema:**
- `classify_text()` pode ser cacheado

**Solucao:**
```python
_text_classification_cache: Dict[str, str] = {}

def classify_text_cached(text: str) -> str:
    text_hash = hashlib.md5(text.encode()).hexdigest()
    if text_hash in _text_classification_cache:
        return _text_classification_cache[text_hash]

    result = classify_text(text)
    _text_classification_cache[text_hash] = result
    return result
```

---

### 24. **Cache de Busca de Memoria**

**Problema:**
- Buscas similares podem ser cacheadas

**Solucao:**
```python
# Cache de resultados de busca
_memory_search_cache: Dict[str, List[SearchResult]] = {}
CACHE_TTL = 300  # 5 minutos

def search_memory_cached(query: str, **kwargs) -> List[SearchResult]:
    cache_key = hashlib.md5(f"{query}:{kwargs}".encode()).hexdigest()
    if cache_key in _memory_search_cache:
        return _memory_search_cache[cache_key]

    results = search_memory(query, **kwargs)
    _memory_search_cache[cache_key] = results
    return results
```

---

### 25. **Cache de Embeddings por Similaridade**

**Ja mencionado em #7**, mas detalhar:

```python
# Cache de embeddings similares
def get_embedding_cached(text: str) -> List[float]:
    # Hash de palavras-chave
    words = set(text.lower().split())
    key = hashlib.md5(" ".join(sorted(words)).encode()).hexdigest()

    # Verificar cache de similaridade
    if key in _similarity_cache:
        return _similarity_cache[key]

    embedding = get_embedding(text)
    _similarity_cache[key] = embedding
    return embedding
```

---

### 26. **Cache de Screenshots**

**Problema:**
- Screenshots podem ser reusados se tela nao mudou

**Solucao:**
```python
# Cache de screenshot por hash
_last_screenshot: Optional[Tuple[bytes, Image.Image]] = None

def take_screenshot_cached() -> Optional[Image.Image]:
    screenshot = take_screenshot()
    if screenshot is None:
        return None

    png_bytes = _image_to_png_bytes(screenshot)
    screenshot_hash = hashlib.md5(png_bytes).hexdigest()

    if _last_screenshot and _last_screenshot[0] == screenshot_hash:
        return _last_screenshot[1]

    _last_screenshot = (screenshot_hash, screenshot)
    return screenshot
```

---

##  VALIDACAO/SEGURANCA (7 melhorias)

### 27. **Validacao Mais Estrita de Planos**

**Problema:**
- Validacao pode ser melhorada

**Solucao:**
```python
# Adicionar validacoes extras
def validar_plano_estrito(plan: ActionPlan) -> QualidadePlano:
    errors = []
    warnings = []

    # Validar numero maximo de acoes
    if len(plan.actions) > 20:
        errors.append("too_many_actions")

    # Validar acoes perigosas
    dangerous_actions = ["delete", "rm", "format"]
    for action in plan.actions:
        if any(danger in str(action.params).lower() for danger in dangerous_actions):
            errors.append("dangerous_action")

    # ... outras validacoes ...

    return QualidadePlano(errors=errors, warnings=warnings, confidence=...)
```

---

### 28. **Sanitizacao Mais Agressiva**

**Problema:**
- Pode detectar mais padroes de injection

**Solucao:**
```python
# Adicionar mais padroes
_MORE_INJECTION_PATTERNS = [
    r"override\s+system",
    r"bypass\s+security",
    r"disable\s+policy",
    # ... mais padroes ...
]
```

---

### 29. **Validacao de URLs**

**Problema:**
- URLs podem nao ser validadas adequadamente

**Solucao:**
```python
def validate_url(url: str) -> bool:
    """Validate URL format and safety."""
    try:
        result = urlparse(url)
        if not result.scheme in {"http", "https"}:
            return False
        # Verificar dominios bloqueados
        if result.netloc in BLOCKED_DOMAINS:
            return False
        return True
    except Exception:
        return False
```

---

### 30. **Validacao de Comandos de Sistema**

**Problema:**
- Comandos podem ser perigosos

**Solucao:**
```python
DANGEROUS_COMMANDS = ["rm", "delete", "format", "dd", "mkfs"]

def validate_command(command: str) -> bool:
    """Validate system command safety."""
    parts = command.split()
    if not parts:
        return False
    cmd = parts[0].lower()
    return cmd not in DANGEROUS_COMMANDS
```

---

### 31. **Rate Limiting de Aprovacoes**

**Problema:**
- Muitas aprovacoes podem ser spam

**Solucao:**
```python
# Rate limiting
_approval_times: List[float] = []
MAX_APPROVALS_PER_MINUTE = 10

def can_request_approval() -> bool:
    now = time.time()
    _approval_times[:] = [t for t in _approval_times if now - t < 60]
    return len(_approval_times) < MAX_APPROVALS_PER_MINUTE
```

---

### 32. **Validacao de Tamanho de Entrada**

**Problema:**
- Entradas muito grandes podem causar problemas

**Solucao:**
```python
MAX_INPUT_SIZE = 10000  # caracteres

def validate_input_size(text: str) -> bool:
    """Validate input size."""
    return len(text) <= MAX_INPUT_SIZE
```

---

### 33. **Validacao de Tipos Mais Estrita**

**Problema:**
- Type hints podem ser melhorados

**Solucao:**
```python
# Usar TypedDict para estruturas
from typing import TypedDict

class ActionParams(TypedDict, total=False):
    text: str
    url: str
    app: str
    combo: str
    # ... outros campos ...
```

---

##  UX/ERROS (5 melhorias)

### 34. **Mensagens de Erro Mais Claras**

**Problema:**
- Erros podem ser mais informativos

**Solucao:**
```python
# Melhorar mensagens
def _say_error(self, error: str, context: str = ""):
    """Say error with context."""
    messages = {
        "plan_invalid": "Nao consegui criar um plano valido.",
        "policy_blocked": f"Bloqueado por politica de seguranca: {context}",
        # ... mais mensagens ...
    }
    message = messages.get(error, f"Erro: {error}")
    self._say(message)
```

---

### 35. **Progresso Visual**

**Problema:**
- Usuario nao sabe o que esta acontecendo

**Solucao:**
```python
# Adicionar indicadores de progresso
def _show_progress(self, step: int, total: int, message: str):
    """Show progress indicator."""
    percent = int((step / total) * 100)
    bar = "=" * (percent // 2)
    print(f"\r[{bar:<50}] {percent}% - {message}", end="", flush=True)
```

---

### 36. **Timeout Configuravel por Operacao**

**Problema:**
- Timeouts podem ser muito curtos/longos

**Solucao:**
```python
# Timeouts especificos
TIMEOUTS = {
    "llm": 30,
    "stt": 10,
    "ocr": 15,
    "screenshot": 5,
}
```

---

### 37. **Retry com Backoff Exponencial**

**Problema:**
- Retries podem ser melhorados

**Solucao:**
```python
def retry_with_backoff(func, max_retries=3, base_delay=1):
    """Retry with exponential backoff."""
    for attempt in range(max_retries):
        try:
            return func()
        except Exception as e:
            if attempt == max_retries - 1:
                raise
            delay = base_delay * (2 ** attempt)
            time.sleep(delay)
```

---

### 38. **Logging Mais Detalhado**

**Problema:**
- Logs podem ser mais informativos

**Solucao:**
```python
# Adicionar niveis de log
import logging

logger = logging.getLogger("jarvis")
logger.setLevel(logging.DEBUG)

# Log estruturado
logger.info("plan_generated", extra={
    "source": "groq",
    "actions_count": len(plan.actions),
    "confidence": plan.confidence,
})
```

---

##  MANUTENIBILIDADE (5 melhorias)

### 39. **Documentacao de Funcoes**

**Problema:**
- Algumas funcoes nao tem docstrings

**Solucao:**
```python
# Adicionar docstrings completas
def normalize_text(text: str) -> str:
    """
    Normalize text for comparison.

    Args:
        text: Text to normalize

    Returns:
        Normalized text (lowercase, stripped)

    Example:
        >>> normalize_text("  Hello World  ")
        'hello world'
    """
    return text.strip().lower()
```

---

### 40. **Type Hints Completos**

**Problema:**
- Alguns tipos podem ser mais especificos

**Solucao:**
```python
# Usar tipos mais especificos
from typing import Literal, Union

ApprovalMode = Literal["voice_and_key", "voice_or_key", "key_only"]
LLMMode = Literal["groq", "openai", "auto", "mock"]
```

---

### 41. **Constantes Centralizadas**

**Problema:**
- Valores magicos espalhados

**Solucao:**
```python
# jarvis/constants.py
MAX_ACTIONS_PER_PLAN = 20
MAX_INPUT_SIZE = 10000
CACHE_TTL_DEFAULT = 3600
MAX_CACHE_SIZE = 100
```

---

### 42. **Testes Unitarios**

**Problema:**
- Cobertura de testes pode ser melhorada

**Solucao:**
```python
# Adicionar mais testes
def test_normalize_text():
    assert normalize_text("  Hello  ") == "hello"
    assert normalize_text("WORLD") == "world"

def test_validate_plan():
    plan = ActionPlan(actions=[], risk_level="low")
    result = validar_plano(plan)
    assert result.errors == []
```

---

### 43. **Refatoracao de Funcoes Longas**

**Problema:**
- Algumas funcoes sao muito longas

**Solucao:**
```python
# Quebrar em funcoes menores
def handle_text(self, text: str) -> None:
    """Handle text command."""
    if not self._should_process(text):
        return

    plan = self._generate_plan(text)
    if not plan:
        return

    self._execute_plan_safely(plan)
```

---

##  OTIMIZACOES DE I/O (4 melhorias)

### 44. **Escrita Assincrona de Logs**

**Problema:**
- Logs bloqueiam execucao

**Solucao:**
```python
# Usar queue para logs assincronos
import queue
import threading

_log_queue = queue.Queue()
_log_thread = None

def start_log_thread():
    global _log_thread
    if _log_thread is None:
        _log_thread = threading.Thread(target=_log_worker, daemon=True)
        _log_thread.start()

def _log_worker():
    while True:
        record = _log_queue.get()
        if record is None:
            break
        _write_log(record)
```

---

### 45. **Compressao de Dados Antigos**

**Problema:**
- Arquivos podem crescer muito

**Solucao:**
```python
# Comprimir logs antigos
import gzip

def compress_old_logs(log_path: Path, days: int = 30):
    """Compress logs older than N days."""
    cutoff = time.time() - (days * 86400)
    # ... comprimir arquivos antigos ...
```

---

### 46. **Leitura Lazy de Arquivos Grandes**

**Problema:**
- Arquivos grandes sao carregados inteiros

**Solucao:**
```python
# Ler linha por linha
def read_jsonl_lazy(path: Path):
    """Read JSONL file lazily."""
    with open(path) as f:
        for line in f:
            yield json.loads(line)
```

---

### 47. **Cache de Arquivos de Configuracao**

**Problema:**
- Config e lido multiplas vezes

**Solucao:**
```python
# Cache de config
_config_cache: Optional[Config] = None
_config_mtime: float = 0

def load_config_cached() -> Config:
    """Load config with caching."""
    global _config_cache, _config_mtime
    config_path = Path("~/.jarvis/config.json")
    mtime = config_path.stat().st_mtime if config_path.exists() else 0

    if _config_cache and mtime == _config_mtime:
        return _config_cache

    _config_cache = load_config()
    _config_mtime = mtime
    return _config_cache
```

---

##  PRIORIZACAO

### Alta Prioridade (Impacto Alto, Esforco Baixo)
1. [x] #1: Normalizacao de texto (funcao helper)
2. [x] #13: Helper para normalizacao
3. [x] #21: Cache de validacao de planos
4. [x] #44: Escrita assincrona de logs

### Media Prioridade (Impacto Medio, Esforco Medio)
5. [x] #3: Otimizar loop de matching
6. [x] #6: Batch de I/O
7. [x] #11: Otimizar serializacao JSON
8. [x] #12: Pool de conexoes SQLite

### Baixa Prioridade (Impacto Baixo ou Esforco Alto)
9. [x] #10: Reduzir sleeps (refatoracao maior)
10. [x] #42: Testes unitarios (trabalho continuo)

---

##  PROXIMOS PASSOS

1. **Implementar melhorias de alta prioridade**
2. **Medir impacto** (benchmarks antes/depois)
3. **Documentar** mudancas
4. **Testar** regressoes
5. **Iterar** com melhorias de media prioridade

---

**Data da Analise:** 2025-01-27
**Total de Melhorias:** 47
**Categorias:** 8
