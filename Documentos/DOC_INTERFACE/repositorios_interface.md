# Repositorios de interface (entrada/saida)

Este documento lista repositorios externos para acelerar a interface do Jarvis. Escolha atual: foco em maxima performance e customizacao (Caminho B).

## Agrupamento por funcionalidade (fonte de verdade)
Objetivo: juntar funcionalidades parecidas para integrar uma unica vez e nao perder qualidade.

1) UI/Chat (apresentacao)
- Fonte principal: `vercel-ai-chatbot`.
- Complementos: `chat_log`/`chat_inbox` do Jarvis (historico local).
- Regra de uniao: UI = front; Jarvis = backend. Streaming via SSE/WS.

2) Transporte de audio (entrada/saida)
- Fonte principal: LiveKit/WebRTC quando remoto; `sounddevice` quando local.
- Complementos: RealtimeTTS (saida em streaming) + AEC reference.
- Regra de uniao: somente um canal de entrada ativo por vez.

3) VAD/turn detection (fim de fala)
- Fonte principal: LiveKit (quando remoto) ou `jarvis/voz/vad.py` (local).
- Complementos: thresholds do RealtimeSTT (endpointing curto).
- Regra de uniao: um VAD por fluxo; usar pre/post-roll unico.

4) Wake word (ativacao)
- Fonte principal: Porcupine/OpenWakeWord (audio).
- Complemento: filtro por texto (fallback).
- Regra de uniao: audio primeiro; texto so se audio nao existir.

5) STT streaming (parciais + final)
- Fonte principal: RealtimeSTT para parciais e estabilizado.
- Complementos: faster-whisper final no Jarvis.
- Regra de uniao: parciais so atualizam UI; final dispara comando.

6) TTS streaming
- Fonte principal: RealtimeTTS com Piper local.
- Complementos: volume + AEC + fallback espeak.
- Regra de uniao: TTS sempre local; APIs pagas opcionais.

7) Emoção/tonalidade (metadata)
- Fonte principal: SpeechBrain (classificacao por utterance).
- Complemento: openSMILE como fallback leve.
- Regra de uniao: metadata apenas; nunca bloquear STT/TTS.

8) Observabilidade/bench
- Fonte principal: Telemetry do Jarvis.
- Complementos: scripts de benchmark + logs de tempo por etapa.
- Regra de uniao: medir sem interferir na resposta.

9) Empacotamento desktop
- Fonte principal: Tauri.
- Regra de uniao: UI bundlada + backend sidecar opcional.

## Checklist integrado por funcionalidade (sem repeticao)

### 1) UI/Chat (Vercel AI Chatbot)
Checklist (recursos do template que nao podemos perder):
1) [ ] Streaming com resume (resumable stream + `resumeStream`)
2) [ ] Canal de dados paralelo (DataStream)
3) [ ] Fluxo de aprovacao de ferramentas (tool approval)
4) [ ] Upload de anexos (MultimodalInput + `/api/files/upload`)
5) [ ] Historico e paginacao de chats
6) [ ] Visibilidade do chat (publico/privado)
7) [ ] Auto-resume de input e rascunho (localStorage)
8) [ ] Artifacts (document/code) e tool UI
9) [ ] Auth/roles/entitlements
10) [ ] Titulo automatico do chat
11) [ ] Tratamento de erros com toast + mensagens claras
12) [ ] Persistencia de mensagens (DB local ou log)

Plano de implementacao (UI -> Jarvis):
1) [ ] Mapear pontos da UI (`components/chat.tsx`, `app/(chat)/api/chat/route.ts`, `lib/ai/providers.ts`)
2) [ ] Definir contrato do Jarvis (endpoint local + SSE opcional)
3) [ ] Criar backend local no Jarvis (API simples)
4) [ ] Capturar resposta do Jarvis (`_say` ou `chat_log`)
5) [ ] Ajustar UI para chamar o Jarvis
6) [ ] Desligar Auth/DB/gateway desnecessarios no modo local
7) [ ] Integrar com Tauri (sidecar + healthcheck)
8) [ ] Validacao final (comandos simples + streaming)

### 2) Voz realtime: transporte + turn detection (LiveKit)
Checklist (importar do LiveKit no nosso interface):
1) [ ] Transporte WebRTC (RoomIO/audio input/output)
2) [ ] Canal de texto nativo (TextInput/TextOutput)
3) [ ] Turn detection avancado (realtime_llm / vad / stt)
4) [ ] VAD com eventos e probabilidade
5) [ ] Pre-connect audio buffer
6) [ ] Preemptive generation
7) [ ] Barge-in / interrupcoes (com falso-positivo)
8) [ ] AudioOutput com eventos de playout + pause
9) [ ] Transcript synchronizer (texto alinhado com TTS)
10) [ ] Noise cancellation / frame processor (AEC/NS)
11) [ ] Telemetria e metrics de voz
12) [ ] Eventos de STT por etapa (interim/preflight/final)
13) [ ] Parametros de interrupcao (min_interruption_duration/words)
14) [ ] False interruption timeout + resume
15) [ ] Aligned transcript por palavra (TimedString)
16) [ ] Resample 48k -> 16k no ingresso de audio WebRTC
17) [ ] Min/max endpointing delay configuravel
18) [ ] Stream pacer do TTS (controle de ritmo e interrupcoes)
19) [ ] User away timeout / silencio longo

O que manter do Jarvis:
- STT local (faster-whisper) e TTS local (Piper/espeak), sem custo por chamada.
- Orquestrador e politica local (controle de seguranca).

### 3) STT streaming (RealtimeSTT)
Checklist (o que importar e onde substituir no Jarvis):
1) [x] Transcricao parcial + estabilizada (callback de parciais)
2) [x] Wake word por audio (Porcupine/OpenWakeWord)
   - Backend selecionavel por `JARVIS_WAKE_WORD_AUDIO_BACKEND`.
3) [x] Pre-recording buffer (evita cortar o inicio)
4) [x] Fim de fala mais rapido (endpointing)
5) [x] Realtime model separado (opcional)
6) [x] Debounce entre gravacoes (min_gap_between_recordings)
7) [x] Normalizacao de audio (peak normalization)
8) [x] Limite de latencia (allowed_latency_limit)
9) [x] Early transcription on silence
10) [x] Handle buffer overflow + buffer_size
11) [x] Warmup do modelo
12) [x] Fonte de audio externa (use_microphone=False)
13) [x] Beam size e batch size (quality x latency)
14) [x] VAD filter do faster-whisper
15) [x] Prompt inicial e suppress_tokens
16) [x] Silero deactivity detection (opcional)

Checklist (o que NAO importar):
1) [ ] PyAudio e audio_input.py
2) [ ] client/server WebSocket do RealtimeSTT
3) [ ] Silero VAD obrigatorio
4) [ ] Multiprocessing + KMP_DUPLICATE_LIB_OK
5) [ ] GPU obrigatorio para realtime

Ordem recomendada (producao, sem MVP):
1) Integracao de callbacks realtime + parciais (itens 1)
2) Ajuste de VAD/endpointing + pre-roll (itens 3, 4, 9)
3) Wake word por audio + debounce (itens 2, 6)
4) Modelo realtime separado + backpressure (itens 5, 8, 10)
5) Confiabilidade e qualidade (itens 7, 11, 13, 14, 15)
6) Robustez final (item 16)

### 4) TTS streaming (RealtimeTTS)
Checklist (importar do RealtimeTTS no nosso interface):
1) [ ] Pipeline de TTS com streaming de texto
2) [ ] Fragmentacao por sentenca + buffer_threshold
3) [ ] Callbacks de audio chunk
4) [ ] Pause/Resume/Stop imediato
5) [ ] Word timing (quando suportado)
6) [ ] Controle de tamanho de chunk (frames_per_buffer/playout_chunk_size)
7) [ ] Fade-in/out e trim de silencio
8) [ ] Medir latencia ate o primeiro chunk
9) [ ] Modo silencioso (muted)
10) [ ] Audio output device selection (opcional)
11) [ ] Integracao Piper local (mantendo self-hosted)
12) [ ] AEC reference (preservar)

Checklist (o que NAO importar):
1) [ ] PyAudio como dependencia obrigatoria
2) [ ] Engines de API paga como padrao (Azure/ElevenLabs/OpenAI)
3) [ ] mpv obrigatorio para MPEG

O que manter do Jarvis:
- Piper local + espeak fallback (sem custo e offline).
- Controle de volume + AEC playback reference.

Ordem recomendada (producao, sem MVP):
1) Streaming + fragmentacao (itens 1, 2, 3)
2) Controle de interrupcao + AEC (itens 4, 12)
3) Qualidade de audio (itens 6, 7, 11)
4) Confiabilidade (itens 8, 9, 10)
5) UX de legenda (item 5)

### 5) Emoção/tonalidade (SpeechBrain + openSMILE)
Checklist (SpeechBrain - emocao por utterance):
1) [ ] Definir o modelo base e baixar os pesos
2) [ ] Definir dependencia minima
3) [ ] Criar adaptador local
4) [ ] Entrada padronizada
5) [ ] Gate por duracao e VAD
6) [ ] Cache do modelo (lazy-load)
7) [ ] Device controlado
8) [ ] Threshold de confianca
9) [ ] Nao bloquear o fluxo principal
10) [ ] Telemetria de emocao
11) [ ] Expor metadata para UI
12) [ ] Falha segura
13) [ ] Testes unitarios simples
14) [ ] Medir latencia

Ordem recomendada (producao, sem MVP):
1) Dependencias + modelo (itens 1-3)
2) Entrada padrao + gate VAD/duracao (itens 4-5)
3) Cache + device (itens 6-7)
4) Threshold + nao bloquear + telemetria (itens 8-10)
5) Expor UI + falha segura + testes (itens 11-13)
6) Benchmark (item 14)

Checklist (opcional - emocao com diarizacao):
1) [ ] Usar `Speech_Emotion_Diarization` em audio longo
2) [ ] Rodar so em modo analitico/pos-processo
3) [ ] Limitar tamanho maximo do audio

Checklist (openSMILE como suporte leve):
1) [ ] Extrair eGeMAPS via CLI
2) [ ] Classificador leve
3) [ ] Normalizacao e cache de features
4) [ ] Usar como fallback rapido

Checklist (estrutura de modulo no Jarvis):
1) [ ] Criar modulo `jarvis/voz/emocao.py`
2) [ ] Configurar entrada padrao
3) [ ] Configurar saida padrao
4) [ ] Integrar no fluxo de voz
5) [ ] Adicionar flags/env
6) [ ] Registrar telemetria
7) [ ] Expor para UI

Checklist (testes manuais - sem GPU):
1) [ ] Teste com audio curto
2) [ ] Teste com fala normal
3) [ ] Teste sem VAD (silencio)
4) [ ] Teste de falha segura

Checklist (o que NAO importar):
1) [ ] Treinamento completo (recipes) no fluxo principal
2) [ ] Diarizacao em tempo real por padrao
3) [ ] Modelos gigantes sem GPU

Checklist (o que manter do Jarvis):
1) [ ] Pipeline de audio 16k mono + VAD
2) [ ] STT/TTS locais como fluxo principal

#### openSMILE (features rapidas, completo)
Checklist (openSMILE no Jarvis - completo):
1) [ ] Validar licenca para uso comercial
2) [ ] Definir modo de execucao
3) [ ] Garantir binario disponivel
4) [ ] Padronizar config de features
5) [ ] Integrar no pipeline do Jarvis
6) [ ] Classificador leve
7) [ ] Gate por VAD e duracao
8) [ ] Execucao assincrona
9) [ ] Cache de features
10) [ ] Telemetria de custo
11) [ ] Flags/ambiente
12) [ ] Falha segura

Ordem recomendada (producao, sem MVP):
1) Licenca + binario (itens 1-3)
2) Config padrao + qualidade (itens 4 + boas praticas)
3) Integracao no pipeline + flags (itens 5, 11)
4) Classificador leve + normalizacao (item 6)
5) Gate VAD + execucao assincrona + cache (itens 7-9)
6) Telemetria + falha segura (itens 10, 12)

Checklist (o que NAO importar do openSMILE):
1) [ ] Pipeline de treino completo (scripts/modeltrain)
2) [ ] Configs gigantes sem necessidade
3) [ ] Modos live/streaming no inicio

Checklist (boas praticas para qualidade):
1) [ ] Normalizar audio antes de extrair
2) [ ] Fixar sample rate (16k) no WAV
3) [ ] Documentar features usadas

### 6) Observabilidade/bench
Checklist (medicao sem atrapalhar):
1) [ ] Telemetria por etapa (captura, VAD, STT, TTS)
2) [ ] Metricas de latencia (tempo total e time-to-first-token/chunk)
3) [ ] CPU/RAM (psutil) e GPU (nvidia-smi quando disponivel)
4) [ ] Logs em JSONL (eventos e resultados)
5) [ ] Bench por comando padrao (mesma frase para comparacao)
6) [ ] Modo silencioso para medir STT isolado

### 7) Empacotamento desktop (Tauri)
Checklist (como empacotar corretamente):
1) [ ] Definir onde a UI roda no desktop
2) [ ] Configurar `tauri.conf.json`
3) [ ] Ligar a UI ao backend do Jarvis
4) [ ] Sidecar do Jarvis (opcional)
5) [ ] Permissoes do app
6) [ ] CSP/localhost/WS
7) [ ] Build e distribuicao
8) [ ] Atualizador (opcional)
9) [ ] Logs e diagnostico

## Matriz de substituicao (Jarvis vs repo)
| Funcionalidade | Jarvis atual | Repositorio(s) | Acao | Observacao |
| --- | --- | --- | --- | --- |
| UI/Chat | chat_log + UI simples | vercel-ai-chatbot | Hibrido | Manter log local + streaming na UI | 
| Transporte audio | sounddevice local | livekit-agents | Hibrido | LiveKit remoto, sounddevice local | 
| VAD/turn detection | webrtcvad (local) | livekit-agents + RealtimeSTT | Hibrido | Um VAD por fluxo; endpointing curto | 
| Wake word | filtro por texto + Porcupine/OpenWakeWord (audio) | RealtimeSTT | Hibrido | Audio primeiro, texto como fallback | 
| STT parcial | parciais via callback | RealtimeSTT | Adicionar | Parciais so atualizam UI | 
| STT final | faster-whisper local | RealtimeSTT (backend) | Manter | Final sempre no Jarvis | 
| TTS | Piper/espeak local | RealtimeTTS | Hibrido | Streaming + AEC + fallback local | 
| Emoção | nao tem | SpeechBrain + openSMILE | Adicionar | Metadata apenas | 
| Observabilidade | Telemetry | scripts/bench | Manter | Medir sem interferir | 
| Desktop app | nao tem | Tauri | Adicionar | UI bundlada + sidecar | 

## Repositorios (referencias e caminhos locais)
- Vercel AI Chatbot: https://github.com/vercel/ai-chatbot
  - Local: `jarvis/REPOSITORIOS_CLONAR/vercel-ai-chatbot`
- LiveKit Agents: https://github.com/livekit/agents
  - Local: `jarvis/REPOSITORIOS_CLONAR/livekit-agents`
- RealtimeSTT: https://github.com/KoljaB/RealtimeSTT
  - Local: `jarvis/REPOSITORIOS_CLONAR/realtimestt`
- RealtimeTTS: https://github.com/KoljaB/RealtimeTTS
  - Local: `jarvis/REPOSITORIOS_CLONAR/realtimetts`
- RealtimeVoiceChat (extra): https://github.com/KoljaB/RealtimeVoiceChat
  - Local: `jarvis/REPOSITORIOS_CLONAR/realtimevoicechat`
- SpeechBrain: https://github.com/speechbrain/speechbrain
  - Local: `jarvis/REPOSITORIOS_CLONAR/speechbrain`
- SpeechBrain emotion model: https://huggingface.co/speechbrain/emotion-recognition-wav2vec2-IEMOCAP
  - Local: `jarvis/REPOSITORIOS_CLONAR/speechbrain-emotion-model`
- openSMILE: https://github.com/audeering/opensmile
  - Local: `jarvis/REPOSITORIOS_CLONAR/opensmile`
- Tauri: https://github.com/tauri-apps/tauri
  - Local: `jarvis/REPOSITORIOS_CLONAR/tauri`

## Recomendacao (performance maxima sem baguncar o Jarvis)
- UI: vercel/ai-chatbot (bonita + streaming + customizavel)
- Voz realtime: livekit/agents (WebRTC + turn detection)
- STT streaming: RealtimeSTT (transcricao parcial)
- TTS streaming: RealtimeTTS (fala enquanto responde)
- Emocao: speechbrain + modelo pronto (metadata)
- Desktop app: tauri (empacotar a UI como software)

## Como encaixar no Jarvis
- Entrada/Saida: migrar por etapas (UI e voz podem vir primeiro).
- Cerebro: manter orchestrator/politica/validacao como backend.
- Execucao: manter automacao atual e plugar por API.
