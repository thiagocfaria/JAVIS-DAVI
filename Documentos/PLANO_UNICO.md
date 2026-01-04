# Plano Unico - Jarvis (Checklist por Fase e Funcao)

## Como usar este documento
- README.md: estado atual e logica do sistema (o que ja existe no codigo).
- Este documento: backlog completo + checklist por fase (o que falta fazer e como fazer).
- Diagrama: Documentos/DIAGRAMA_ARQUITETURA.svg (mantido separado).
- Os anexos antigos estao em `Documentos/archive/` se precisar revisitar historico.

## Estado atual do projeto (codigo)
- CLI com loop/texto/voz + preflight.
- Orquestrador local: comando -> plano -> policy -> aprovacao -> execucao -> validacao.
- Roteamento LLM: local (OpenAI-compat) + MockLLM fallback; guidance manual via navegador (sem usar APIs externas).
- Gate de confianca por schema/warnings + cache de respostas; ainda sem self-score, penalidades de risco/tamanho ou orcamento integrado.
- Automacao desktop (xdotool/wtype/ydotool/pyautogui) e web (Playwright).
- Agent S3 integrado como motor de GUI (modulo `jarvis/agent_s3`) com loop visual e CLI `--s3`.
- Automacao desktop ampliada (drag, clicks com botao/hold, type com overwrite/enter) para suportar o S3.
- Policy de seguranca + policy do usuario + bloqueios de dados sensiveis.
- Sanitizacao anti prompt injection + redacao automatica + mascara de screenshots.
- Kill switch via arquivo STOP.
- Chat log e chat inbox/UI local.
- Aprendizado por demonstracao integrado ao CLI (comandos demonstrar/parar); pendente teste real.
- Memoria local SQLite + procedimentos + comandos fixar/esquecer; Supabase ainda nao implementado.
- Rust vision opcional (jarvis_vision) integrado ao validator Python; fallback Python.
- STT/TTS locais (faster-whisper, Piper/espeak), dependem de libs nativas.
- Configuracao carrega `.env` automaticamente (se existir).
- Protocolo VPS <-> PC em codigo (mensagens/validacao), nao integrado ao fluxo.
- Testes unitarios em testes/ + scripts de benchmark/medicao.
- Manifesto de dependencias versionado (requirements.txt) alinhado com scripts de setup.

### Registro local (instalacoes recentes neste PC)
- `pip install sentence-transformers` (puxou `torch`, `transformers`, `scikit-learn`, `scipy`, `triton` e libs nvidia-cu12).
- `python -m playwright install chromium` (fallback build para ubuntu24.04-x64).
- `scripts/install_deps.sh` tentou instalar tudo, mas travou na etapa `pip` por causa do download pesado do `torch`; finalizado manualmente via `pip install sentence-transformers`.

### Atualizacao: cerebro self-hosted (Qwen2.5-7B, LoRA)
- Objetivo: rodar LLM aberto (Qwen2.5-7B-Instruct) no VPS via llama.cpp/vLLM, com API OpenAI-compat usada pelo Jarvis.
- Quantizacao: GGUF (Q4/Q5) para reduzir RAM; alternar nivel conforme tarefa.
- LoRA/QLoRA: treinos leves com dados reais (logs aprovados) para afinar respostas sem tocar pesos originais; versionar e aplicar sob demanda.
- Pipeline: dados -> curadoria -> validacao offline -> LoRA -> deploy com rollback; registrar latencia/custo e checkpoints.

## Pendencias estruturais (nao estao prontas)
- VPS infra (Tailscale, llama.cpp, memoria VPS, rclone/exportacao Drive).
- Wayland portal para captura/input (ScreenCast + RemoteDesktop).
- Rust actions + bridge JSON-RPC (jarvis_actions/jarvis_bridge).
- Endpoints self-hosted de modelo visual/grounding para o S3 ainda nao configurados.
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
- Sem uso de APIs externas de IA (nem pagas nem gratuitas); apenas cerebro self-hosted (Qwen2.5-7B quantizado) no VPS.
- Regra: manter 100% self-hosted para inferencia.
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
- [ ] Definir metas de latencia, custo e peso (pior caso). (registradas abaixo)
- [ ] Diagrama atualizado para refletir o estado atual (ultimo update registrado).
- [x] Registro de implementacao existe (Documentos/REGISTRO_IMPLEMENTACAO.md).
- [x] Manter REGISTRO_IMPLEMENTACAO.md atualizado a cada mudanca. (ultimo update: 05/01/2026)
- [ ] Atualizar README quando algo mudar. (ultimo update: demonstracao)

Metas definidas (pior caso, antes do VPS):
- Latencia: <= 8s por comando local com OCR full; <= 12s quando usar LLM cloud.
- Custo: <= R$ 12/dia (<= R$ 360/mes), <= R$ 0,50 por comando pago.
- Peso (PC): RSS <= 2.5 GB, CPU p95 <= 2 cores, disco <= 2 GB (logs/cache).

#### Checklist com servidor (VPS)
- (sem itens)

### Funcao: Metricas e pesos (Responsavel: Dev QA)
#### Checklist sem servidor (local)
- [ ] Micro-medicoes locais registradas (scripts/measure_local_weights.py + Documentos/PESOS_MEDIDOS.md).
- [ ] Medicoes reais de pior caso (OCR full, automacao, STT/TTS, etc).
- [ ] Reexecutar benchmarks apos mudancas e atualizar PESOS_MEDIDOS + DIAGRAMA.

#### Checklist com servidor (VPS)
- [ ] Atualizar diagrama com pesos reais medidos (inclui VPS).

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
- [x] Manifesto de dependencias versionado (requirements.txt) para que os scripts nao quebrem.
- [ ] Preflight validado sem falhas criticas (10 OK, 3 avisos de configuracao opcional).
- [ ] Registrar resultados do `--preflight-strict`, listar dependencias faltantes (voz, OCR, automacao) e confirmar instalacao antes do VPS.
- [x] Documentar checklist adicional de dependencias opcionais (Wayland vs X11, TTS/STT/browsers) e vincular ao scripts/install_deps.sh.

#### Checklist com servidor (VPS)
- (sem itens)

### Funcao: Procedimentos e aprendizado local (Responsavel: Dev Core)
#### Checklist sem servidor (local)
- [x] ProcedureStore em SQLite (tags, TTL, score por tokens/tags).
- [x] Auto-learn de procedimentos quando ha guidance.
- [x] Integrar aprendizado por demonstracao (recorder/learner) ao CLI (comandos demonstrar/parar).
- [ ] Testar e documentar fluxo de demonstracao (falta teste real).

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
- [ ] Criar conta RunPod e definir limite de gasto (GPU on-demand, se precisar treinar/rodar modelo maior).
- [ ] Criar conta Hetzner/fornecedor VPS e registrar limites de custo.

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
- [ ] Atalho de emergencia e stop via systemd (depende de deploy local/daemon).

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
- [ ] Testar kill switch em todos os ambientes.

#### Checklist com servidor (VPS)
- (sem itens)

### Como fazer
- Ver Anexo: POLITICA_SEGURANCA_PRIVACIDADE.md

## Fase 2 - Memoria robusta (VPS)
### Objetivo
- Memoria de longo prazo com baixo custo, em VPS CPU, com exportacao mensal.

### Estado atual (codigo)
- [x] Memoria local SQLite com cache minimo.
- [x] Comandos fixar/esquecer (FIXED).
- [ ] Supabase opcional (schema + RPC match_memories externo) ainda nao implementado no codigo.
- [ ] RAG completo no VPS (SQLite + FTS + vetores).

### Entregaveis da fase
- Memoria no VPS com FTS+vetores e exportacao mensal.
- Regras de escrita/leitura e consolidacao funcionando.

### Funcao: Base (Fase 0 interna) (Responsavel: Dev Data)
#### Checklist sem servidor (local)
- [ ] Definir JARVIS_EMBED_DIM=384 fixo.
- [ ] Padronizar modelo de embeddings (multilingual-e5-small ou similar).
- [ ] Criar estrutura SQLite para texto + vetores + FTS.

#### Checklist com servidor (VPS)
- (sem itens)

### Funcao: Hibrido simples (Fase 1 interna) (Responsavel: Dev Data)
#### Checklist sem servidor (local)
- [ ] Escrita por regras (episodica/procedural/semantica).
- [ ] Deduplicacao por hash.
- [ ] Busca FTS + recencia.

#### Checklist com servidor (VPS)
- (sem itens)

### Funcao: Vetores (Fase 2 interna) (Responsavel: Dev Data)
#### Checklist sem servidor (local)
- [ ] Integrar embeddings locais CPU.
- [ ] Busca vetorial e score hibrido (sim * 0.6 + recencia * 0.2 + sucesso * 0.2).
- [ ] Cache LRU para consultas recentes.

#### Checklist com servidor (VPS)
- (sem itens)

### Funcao: Robustez (Fase 3 interna) (Responsavel: Dev Data)
#### Checklist sem servidor (local)
- [ ] Feedback positivo/negativo com score.
- [ ] Regras de confirmacao por historico.
- [ ] Regras de importancia e consolidacao.
- [ ] Camadas HOT/WARM/COLD/FIXED/ARCHIVE aplicadas.

#### Checklist com servidor (VPS)
- [ ] Resumo periodico (COLD) com modelo base.
- [ ] Exportacao mensal para Drive (rclone + manifesto).

### Funcao: Privacidade e backup (Responsavel: Dev Sec)
#### Checklist sem servidor (local)
- [ ] Passar PrivacyMasker antes de salvar dados sensiveis.
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
- [x] Loop GUI do Agent S3 integrado ao Jarvis (Python) com policy/validacao.
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
- [ ] Captura Wayland via portal (ScreenCast + PipeWire) + fallback.
- [ ] OCR com leptess (fallback CLI).
- [ ] Cache por hash + diff para OCR parcial.
- [ ] APIs: take_screenshot_png, ocr_text, detect_error_modal, detect_captcha_2fa.

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
- [x] Loop S3 (Python) integrado ao Jarvis com acao unica, policy e validacao por passo.
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
- [ ] Testes de regressao (captura, OCR, click, hotkey).
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
- [x] Roteamento LLM local + MockLLM fallback + guidance manual via navegador (sem cloud automatica).
- [x] Budget diario de chamadas/caracteres integrado ao fluxo (orcamento.py utilizado via BudgetedLLMClient com telemetria local).
- [x] Gate de confianca heuristico (schema/warnings).
- [ ] Self-score do modelo e penalidades de risco/volume.
**(removido: nao usamos APIs externas)**
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
- [ ] Implementar self-score do modelo.
- [ ] Penalidades por risco e tamanho do plano.
- [ ] Recalibrar limiares com benchmarks.

#### Checklist com servidor (VPS)
- (sem itens)

### Funcao: Pool de APIs externas (Responsavel: Dev Core)
#### Checklist sem servidor (local)
- (removido: nao usamos APIs externas de IA)

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
- [x] Regras de classificacao e redacao antes de enviar a qualquer servico remoto (inclui cerebro no VPS).
- [ ] Politicas refinadas para dados sensiveis no VPS.

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
- [x] Cliente HTTP de memoria remota leve (fallback local) com servidor minimo para VPS/local.
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
- [ ] Chat local com atalho/botao (UI + inbox ok; atalho pendente).

#### Checklist com servidor (VPS)
- (sem itens)

### Funcao: Integracoes locais (Responsavel: Dev Infra)
#### Checklist sem servidor (local)
- [ ] Instalar dependencias locais faltantes e validar preflight sem falhas criticas.

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
