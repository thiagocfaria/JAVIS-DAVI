# Diagrama de Arquitetura - Interface de Entrada/Saida do Jarvis

**Atualizado em:** 2026-01-19
**Status:** Producao (pronto para uso)

## Visao Geral

A Interface de Entrada/Saida do Jarvis e responsavel por toda comunicacao entre o usuario e o sistema atraves de voz e texto.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           USUARIO                                            │
│                    (Fala / Texto / Atalhos)                                  │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                        CAMADA DE ENTRADA                                     │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐ │
│  │  Microfone  │  │  Chat UI    │  │  Shortcut   │  │  GUI Panel          │ │
│  │ (sounddev.) │  │  (texto)    │  │ (pynput)    │  │  (tkinter)          │ │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘  └──────────┬──────────┘ │
│         │                │                │                     │           │
│         ▼                │                │                     │           │
│  ┌─────────────┐         │                │                     │           │
│  │ VAD (webrtc)│         │                │                     │           │
│  │ Detecta fala│         │                │                     │           │
│  └──────┬──────┘         │                │                     │           │
│         │                │                │                     │           │
│         ▼                │                │                     │           │
│  ┌─────────────┐         │                │                     │           │
│  │ STT (Whisper│         │                │                     │           │
│  │ faster-whis)│         │                │                     │           │
│  └──────┬──────┘         │                │                     │           │
│         │                │                │                     │           │
│         └────────────────┴────────────────┴─────────────────────┘           │
│                                    │                                         │
│                                    ▼                                         │
│                          ┌─────────────────┐                                │
│                          │  Texto do       │                                │
│                          │  Usuario        │                                │
│                          └────────┬────────┘                                │
└───────────────────────────────────┼─────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                        CAMADA DE PROCESSAMENTO                               │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                        Orchestrator                                  │    │
│  │  - Recebe texto do usuario                                          │    │
│  │  - Envia para LLM (cerebro)                                         │    │
│  │  - Recebe resposta                                                  │    │
│  │  - Dispara fase 1 (ack imediato) quando habilitado                  │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                    │                                         │
└────────────────────────────────────┼────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                        CAMADA DE SAIDA                                       │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                           TTS                                        │    │
│  │  ┌─────────────────┐     ┌─────────────────┐                        │    │
│  │  │   Piper (voz    │     │  espeak-ng      │                        │    │
│  │  │   humanizada)   │     │  (fallback)     │                        │    │
│  │  │   RECOMENDADO   │     │  voz robotica   │                        │    │
│  │  └────────┬────────┘     └────────┬────────┘                        │    │
│  │           │                       │                                  │    │
│  │           └───────────┬───────────┘                                  │    │
│  │                       ▼                                              │    │
│  │              ┌─────────────────┐                                     │    │
│  │              │  aplay (ALSA)   │                                     │    │
│  │              │  Saida de audio │                                     │    │
│  │              └─────────────────┘                                     │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           USUARIO                                            │
│                    (Ouve a resposta)                                         │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Componentes Detalhados

### 1. ENTRADA DE VOZ

```
┌─────────────────────────────────────────────────────────────────┐
│                      PIPELINE DE VOZ                             │
│                                                                  │
│  Microfone ──► Captura ──► VAD ──► STT ──► Texto               │
│  (hardware)    (sounddev)  (webrtc) (whisper)                   │
│                                                                  │
│  Configuracoes principais:                                       │
│  - JARVIS_AUDIO_DEVICE: dispositivo de captura                  │
│  - JARVIS_VAD_SILENCE_MS: tempo de silencio (default 400ms)     │
│  - JARVIS_STT_MODEL: modelo whisper (tiny/small/medium)         │
│  - JARVIS_STT_DEVICE: cpu/cuda/auto                             │
└─────────────────────────────────────────────────────────────────┘
```

#### Fluxo de Captura de Audio

1. **Captura** (`sounddevice`): Captura audio do microfone
   - Taxa: 16kHz (preferido) ou nativo com resample
   - Formato: float32 -> int16 PCM mono

2. **VAD** (`webrtcvad`): Detecta inicio/fim da fala
   - Aggressiveness: 0-3 (default 2)
   - Pre-roll: 200ms (nao corta inicio)
   - Post-roll: 200ms (nao corta fim)
   - Silencio para endpoint: 400ms

3. **STT** (`faster-whisper`): Transcreve audio para texto
   - Modelo: tiny (rapido) / small (default) / medium (preciso)
   - Device: auto (detecta GPU se disponivel)
   - Warmup: opcional para reduzir latencia cold start

### 2. SAIDA DE VOZ (TTS)

```
┌─────────────────────────────────────────────────────────────────┐
│                      PIPELINE TTS                                │
│                                                                  │
│  Texto ──► Engine ──► Audio ──► aplay ──► Alto-falante          │
│            (piper)    (stream)  (ALSA)                          │
│                                                                  │
│  Configuracoes principais:                                       │
│  - JARVIS_TTS_ENGINE: piper/espeak-ng/auto                      │
│  - JARVIS_TTS_STREAMING: 1 (reduz latencia percebida)           │
│  - JARVIS_TTS_CACHE: 1 (frases repetidas saem do cache)         │
│  - JARVIS_TTS_WARMUP: 1 (pre-aquece modelo no startup)          │
└─────────────────────────────────────────────────────────────────┘
```

#### Engines Disponiveis

| Engine | Qualidade | Latencia | CPU | Quando usar |
|--------|-----------|----------|-----|-------------|
| Piper | Alta (neural) | ~50-80ms warm | Baixa | Producao |
| espeak-ng | Baixa (robotica) | ~0.5ms | Minima | Fallback/dev |

### 3. LATENCIA PERCEBIDA

```
┌─────────────────────────────────────────────────────────────────┐
│                   TIMELINE DE LATENCIA                           │
│                                                                  │
│  Usuario    ──────────────────────────────────────────────────► │
│  fala                                                            │
│             │                                                    │
│             ▼                                                    │
│  VAD detecta ─────► Silencio detectado                          │
│  fala               (endpoint)                                   │
│                     │                                            │
│                     ▼                                            │
│  STT        ────────────────────► Texto pronto                  │
│  transcreve                       │                              │
│                                   ▼                              │
│  Fase 1     ─► "Entendi."         │ (latencia percebida ~0ms)   │
│  (ack)          │                 │                              │
│                 │                 ▼                              │
│  LLM        ────┼─────────────────────────► Resposta pronta     │
│  processa       │                           │                    │
│                 │                           ▼                    │
│  TTS        ────┼───────────────────────────────────► Audio     │
│  fala           │                                                │
│                 │                                                │
│  Usuario    ◄───┘  (ouve "Entendi." quase imediatamente)        │
│  percebe                                                         │
└─────────────────────────────────────────────────────────────────┘
```

### 4. ESTRUTURA DE ARQUIVOS

```
jarvis/interface/
├── entrada/                    # Entrada (voz/texto)
│   ├── app.py                 # Ponto de entrada principal
│   ├── stt.py                 # Speech-to-Text
│   ├── vad.py                 # Voice Activity Detection
│   ├── chat_ui.py             # Interface de texto
│   ├── gui_panel.py           # Painel grafico
│   ├── shortcut.py            # Atalhos de teclado
│   ├── followup.py            # Modo followup
│   ├── speaker_verify.py      # Verificacao de locutor
│   ├── preflight.py           # Checagens pre-execucao
│   └── emocao.py              # Deteccao de emocao
│
├── saida/                      # Saida (voz)
│   └── tts.py                 # Text-to-Speech
│
├── audio/                      # Utilidades de audio
│   └── audio_utils.py         # Funcoes auxiliares
│
├── infra/                      # Infraestrutura
│   ├── chat_log.py            # Log de conversas
│   ├── chat_inbox.py          # Caixa de mensagens
│   └── voice_profile.py       # Auto-config de voz
│
└── telemetria/                 # Metricas
    └── __init__.py            # Telemetria
```

### 5. ADAPTADORES DE VOZ

```
jarvis/interface/entrada/adapters/
├── base.py                    # Interface base
├── stt_realtimestt.py         # STT streaming (RealtimeSTT)
├── vad_silero.py              # VAD alternativo (Silero)
├── speaker_resemblyzer.py     # Verificacao de locutor
├── wakeword_openwakeword.py   # Wake word (OpenWakeWord)
├── wakeword_porcupine.py      # Wake word (Porcupine)
└── wakeword_text.py           # Wake word (texto)
```

## Metricas de Performance (Baseline)

### Ambiente de Teste
- CPU: Desktop Linux
- RAM: 8GB+
- GPU: Nao utilizada (modo CPU)

### Resultados (2026-01-18)

| Componente | P50 | P95 | Observacao |
|------------|-----|-----|------------|
| VAD | 0.65ms | 0.88ms | webrtcvad |
| STT (tiny) | 3.2s | 4.9s | faster-whisper |
| STT (small) | 6.1s | 6.4s | faster-whisper |
| TTS (Piper warm) | 48ms | 62ms | backend Python |
| Endpointing | 390ms | 390ms | silence_ms=400 |

### Numero Unico (End-to-End)

| Metrica | P50 | P95 | Configuracao |
|---------|-----|-----|--------------|
| EoS -> 1o audio | 588ms | 2108ms | Piper warm + fase 1 |
| EoS -> fase 1 | 0.03ms | 0.03ms | Frase pre-gerada |

## Configuracao Recomendada (Producao)

```bash
# TTS - Voz humanizada (Piper)
JARVIS_TTS_ENGINE=piper
JARVIS_TTS_ENGINE_STRICT=1
JARVIS_PIPER_MODELS_DIR=storage/models/piper
JARVIS_PIPER_VOICE=pt_BR-faber-medium
JARVIS_PIPER_BACKEND=python
JARVIS_PIPER_INTRA_OP_THREADS=1
JARVIS_PIPER_INTER_OP_THREADS=1
JARVIS_TTS_STREAMING=1
JARVIS_TTS_CACHE=1
JARVIS_TTS_WARMUP=1

# Fase 1 - Latencia percebida
JARVIS_VOICE_PHASE1=1
JARVIS_TTS_ACK_PHRASE="Entendi. Ja vou responder."
JARVIS_TTS_ACK_PHRASE_WARMUP_BLOCKING=1

# STT - Transcricao
JARVIS_STT_MODEL=tiny  # ou small para mais precisao
JARVIS_STT_DEVICE=auto
JARVIS_STT_CPU_THREADS=2
JARVIS_STT_WORKERS=1

# VAD - Deteccao de fala
JARVIS_VAD_SILENCE_MS=400
JARVIS_VAD_PRE_ROLL_MS=200
JARVIS_VAD_POST_ROLL_MS=200
```

## Glossario

- **VAD**: Voice Activity Detection - detecta quando ha fala no audio
- **STT**: Speech-to-Text - converte audio em texto
- **TTS**: Text-to-Speech - converte texto em audio
- **TTFA**: Time To First Audio - tempo ate o primeiro som sair
- **EoS**: End of Speech - fim da fala do usuario (endpoint)
- **Fase 1**: Ack imediato ("Entendi.") para reduzir latencia percebida
- **Warmup**: Pre-aquecimento do modelo para reduzir cold start
- **Piper**: Engine TTS neural de alta qualidade
- **espeak-ng**: Engine TTS simples (voz robotica)
- **webrtcvad**: Biblioteca C para VAD (leve e rapida)
- **faster-whisper**: Implementacao otimizada do Whisper

## Referencias

- Documentacao dos modulos: `Documentos/DOC_INTERFACE/*.md`
- Testes: `testes/test_*_interface.py`
- Benchmarks: `scripts/bench_interface.py`
- Resultados: `Documentos/DOC_INTERFACE/bench_audio/*.json`
