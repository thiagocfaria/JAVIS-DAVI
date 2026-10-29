# Correcoes e melhorias da interface (ordem de execucao)

Checklist organizado por ordem real de execucao.
Legenda: (Problema) = algo ruim hoje. (Melhoria) = evolucao desejada. (Analise) = avaliar depois.

## FASE 1 - Corrigir falhas e padronizar o fluxo (fazer agora)
1) [x] (Problema) Erro em runtime: `TypeError: cannot unpack non-iterable NoneType object` no STT.
   - Como: garantir que `_trim_with_rust` e `_record_until_silence` sempre retornem tupla.
   - Quando: antes de qualquer benchmark ou novo teste.
   - Por que: bloqueia o uso do STT e invalida testes.
   - Feito: guardas adicionadas para tratar retorno invalido/None do `_trim_with_rust`, com fallback para audio original.
   - Teste: `PYTHONPATH=. pytest -q testes/test_stt_trim_guard.py` (PASS).
   - Resultado: erro nao ocorre mais quando o trim em Rust retorna None; STT segue funcionando.

2) [x] (Problema) Consolidar VAD (evitar duplicidade entre webrtcvad, Silero e VAD do Whisper/RealtimeSTT).
   - Como: definir estrategia unica via env (ex.: `JARVIS_VAD_STRATEGY=webrtc|silero|realtimestt`) e desligar os outros.
   - Quando: logo apos corrigir o erro runtime.
   - Por que: VAD duplo gera latencia e falso negativo.
   - Feito: adicionado `JARVIS_VAD_STRATEGY` (webrtc|silero|whisper|realtimestt) para escolher um unico VAD e desativar os demais.
   - Teste: `PYTHONPATH=. pytest -q testes/test_vad_strategy.py` (PASS).
   - Resultado: estrategia unica aplicada; duplicidade de VAD removida por configuracao.

2.1) [x] (Problema) Flags/env do STT nao refletiam o comportamento real (wake word strict + trim Rust).
   - Como: aplicar `JARVIS_WAKE_WORD_AUDIO_STRICT` no gate por audio e ler `JARVIS_AUDIO_TRIM_BACKEND` no Config.
   - Quando: junto com a padronizacao do fluxo de voz.
   - Por que: evita configuracoes "fantasma" e melhora previsibilidade do STT.
   - Feito: gate por audio agora respeita `JARVIS_WAKE_WORD_AUDIO_STRICT`; `JARVIS_AUDIO_TRIM_BACKEND` passa a configurar `stt_audio_trim_backend`.
   - Teste: manual (wake word por audio e trim Rust com env).
   - Resultado: flags/env passam a mudar o comportamento de verdade.

3) [x] (Problema) Observabilidade obrigatoria (logs por etapa + p95).
   - Como: registrar `capture_ms`, `vad_ms`, `endpoint_ms`, `stt_ms`, `llm_ms`, `tts_ms`, `play_ms` e p95.
   - Quando: antes do baseline.
   - Por que: sem isso nao sabemos se o gargalo e record_ms, stt_ms ou tts_ms.
   - Feito: STT/VAD/TTS agora guardam metricas por etapa; orquestrador agrega `llm_ms` e grava `voice_stage_metrics` em `~/.jarvis/events.jsonl` com p95 rolling.
   - Teste: manual (rodar comando de voz e inspecionar `events.jsonl`).
   - Resultado: cada comando de voz passa a registrar tempos por etapa e p95 no log local.

4) [x] (Melhoria) Baseline padronizado (clean/noise) e registro em `EVOLUCAO_PERFOMACE.MD`.
   - Como: rodar `auto_voice_bench` e gravar resultados com data, device e metricas por etapa.
   - Quando: depois do item 3.
   - Por que: sem baseline nao ha comparacao real.
   - Feito: baseline padrao definido usando as gravacoes `bench_audio/voice_clean.wav` e `bench_audio/voice_noise.wav`; benchmarks rodados (STT/VAD/endpointing) e resultados registrados em `EVOLUCAO_PERFOMACE.MD` + `bench_history.json`.
   - Teste: `PYTHONPATH=. ./.venv/bin/pytest -q testes/` (PASS 245).
   - Benchmark (clean/noise): `PYTHONPATH=. JARVIS_STT_MODEL=tiny ./.venv/bin/python scripts/bench_interface.py ...` (resultados em `Documentos/DOC_INTERFACE/bench_audio/*.2026-01-15.json`).
   - Resultado: baseline agora e repetivel e comparavel por data (clean/noise) com historico em `bench_history.json`.

5) [ ] (Problema) Wake word real falhando no teste manual (comando "jarvis ...").
   - Como: validar microfone, limiar de VAD e fluxo de wake word (texto vs audio).
   - Quando: depois do baseline com logs.
   - Por que: e a porta de entrada do sistema.

6) [ ] (Problema) Ruido alto (TV) gera transcricao lixo e ativa fallback.
   - Como: perfil dedicado de ruido (noise floor + VAD agressivo + silence_ms ajustado).
   - Quando: depois do wake word ok.
   - Por que: evita ativacao falsa e melhora robustez.

7) [ ] (Melhoria) Noise gate adaptativo antes do VAD (RMS vs ruido base).
   - Como: medir ruido inicial (1-2s) e reduzir gatilhos abaixo do limiar.
   - Quando: junto com o perfil de ruido.
   - Por que: evita abrir STT por ruido constante.
   - Cuidado: nunca bloquear fala baixa; se VAD detectar fala, ignorar o gate.

8) [ ] (Melhoria) Endpointing "humano" (fim de fala com 3 sinais).
   - Como: VAD + RMS + estabilidade do parcial (se streaming).
   - Quando: apos perfil de ruido.
   - Por que: reduzir record_ms e encerrar mais rapido sem cortar fala.

9) [ ] (Problema) Erros no shutdown do RealtimeSTT (handle closed / bad file descriptor).
   - Como: garantir encerramento limpo sem tracebacks apos Ctrl+C.
   - Quando: se streaming estiver ativo no fluxo atual.
   - Por que: melhora estabilidade e evita perda de recursos.

## FASE 2 - Otimizacao guiada por benchmark (depois de estavel)
10) [ ] (Problema) Latencia perceptivel no comando de voz manual.
   - Como: ajustar parametros STT/VAD/TTS com base no benchmark.
   - Quando: apos baseline confiavel.
   - Por que: melhora resposta sem adivinhar.

11) [ ] (Melhoria) STT streaming com parciais (sensacao de instantaneo).
   - Como: expor parciais durante a fala e finalizar no fim do turno.
   - Quando: apos latencia estar medida.
   - Por que: reduz latencia percebida mesmo em CPU.

12) [ ] (Melhoria) Dois modos de STT (comando rapido vs precisao).
   - Como: modelo pequeno para comandos curtos e modelo maior apenas sob demanda.
   - Quando: apos streaming com parciais.
   - Por que: CPU-only precisa de modo rapido.

13) [ ] (Melhoria) Modo comando com "bias/gramatica" de frases esperadas.
   - Como: usar prompt/bias no STT (se suportar) ou pos-processo (regex + fuzzy).
   - Quando: junto com o modo comando.
   - Por que: aumenta precisao com modelo pequeno e reduz transcricao lixo.

14) [ ] (Melhoria) Filtro de repeticao / confirmacao rapida em baixa confianca.
   - Como: se confianca baixa, perguntar "Voce quis dizer X?" antes de executar.
   - Quando: apos modo comando com bias.
   - Por que: evita execucoes erradas em ruido.

15) [ ] (Melhoria) TTS em chunks + barge-in.
   - Como: iniciar fala por frases curtas e cortar TTS ao detectar nova fala.
   - Quando: apos STT estabilizado.
   - Por que: melhora percepcao de velocidade.

16) [ ] (Melhoria) Cache de respostas curtas no TTS.
   - Como: pre-sintetizar frases repetidas (ex.: "Oi! Como posso ajudar?").
   - Quando: apos TTS em chunks.
   - Por que: reduz TTFA sem mudar modelo.

17) [ ] (Melhoria) Pre-warm de STT/TTS no startup.
   - Como: rodar 1 transcricao curta e 1 TTS curto ao iniciar.
   - Quando: apos cache de TTS.
   - Por que: remove pico de latencia inicial.

18) [ ] (Melhoria) Captura otimizada 16kHz mono direto.
   - Como: usar device que suporta 16kHz e evitar resample quando possivel.
   - Quando: apos pre-warm.
   - Por que: reduz custo de CPU e risco de erro de capture.

19) [ ] (Melhoria) Pipeline concorrente (nao bloquear voz).
   - Como: separar captura, STT, orquestrador e TTS em tasks/threads.
   - Quando: apos TTS em chunks.
   - Por que: evita fila e travamento.

## FASE 3 - Itens para analisar depois (so implementar se valer a pena)
20) [ ] (Analise) Backend de STT plugavel (faster-whisper vs whisper.cpp vs sherpa-onnx).
   - Quando analisar: apos escolher modo comando/precisao.
   - Como decidir: qualidade PT-BR, tempo de transcricao e uso de CPU.
   - Implementar se: ganho >= 20% em latencia ou consumo.

21) [ ] (Analise) Prosodia/emocao simples (CPU-only) como metadata.
   - Quando analisar: apos latencia estar boa.
   - Como decidir: melhora perceptivel sem piorar tempo.
   - Implementar se: UX melhora sem custo significativo.

## INTEGRACOES DE REPOSITORIOS (por prioridade, sem re-clonar)
R1) [ ] (Repo) RealtimeTTS: TTS em streaming para reduzir TTFA.
   - Buscar em: `jarvis/REPOSITORIOS_CLONAR/realtimetts/RealtimeTTS/text_to_stream.py`, `stream_player.py`, `threadsafe_generators.py`.
   - O que trazer: fragmentacao por sentenca + callbacks de chunk + stop imediato.
   - Por que: reduz latencia percebida sem exigir GPU.

R2) [ ] (Repo) RealtimeSTT: fonte de audio externa para testes e consistencia.
   - Buscar em: `jarvis/REPOSITORIOS_CLONAR/realtimestt/RealtimeSTT/audio_input.py` e `audio_recorder.py`.
   - O que trazer: `use_microphone=False`/input externo para rodar bench automatico.
   - Por que: evita testar manualmente e padroniza resultados.

R3) [ ] (Repo) RealtimeSTT: encerramento limpo (shutdown) e correcoes de fila.
   - Buscar em: `jarvis/REPOSITORIOS_CLONAR/realtimestt/RealtimeSTT/audio_recorder.py`.
   - O que trazer: tratamento de `handle is closed`/`bad file descriptor`.
   - Por que: evita crash e recursos presos apos Ctrl+C.

R4) [ ] (Repo) LiveKit turn detector (apenas se entrar em modo remoto/WebRTC).
   - Buscar em: `jarvis/REPOSITORIOS_CLONAR/livekit-agents/livekit-agents/livekit/agents` e
     `jarvis/REPOSITORIOS_CLONAR/livekit-agents/livekit-plugins/livekit-plugins-turn-detector/livekit/plugins`.
   - O que trazer: endpointing e barge-in em chamadas remotas.
   - Por que: melhora experiencia remota, mas nao deve misturar com o fluxo local.

R5) [ ] (Repo) UI (Vercel AI Chatbot) como front-end opcional.
   - Buscar em: `jarvis/REPOSITORIOS_CLONAR/vercel-ai-chatbot/`.
   - O que trazer: streaming UI + estados de voz (ouvindo/transcrevendo).
   - Por que: melhora UX sem mexer na latencia do backend.

R6) [ ] (Repo) Emoção/tonalidade (SpeechBrain + openSMILE) apenas como metadata.
   - Buscar em: `jarvis/REPOSITORIOS_CLONAR/speechbrain/` e `jarvis/REPOSITORIOS_CLONAR/opensmile/`.
   - O que trazer: classificador leve e features rapidas (sem travar o pipeline).
   - Por que: opcional; so se nao aumentar latencia e sem alterar o fluxo principal.
