# DOC_INTERFACE - Documentação da Interface de Entrada/Saída

# Documentação da interface de entrada/saída

Documentação técnica do sistema de voz local do Jarvis, espelhando o código em `jarvis/interface/` e a camada de compatibilidade em `jarvis/voz/`.

## Estrutura de pastas (docs)

```
DOC_INTERFACE/
├── entrada/                  # Entrada (STT, VAD, wake word, preflight, UI)
├── saida/                    # Saída (TTS)
├── voz/                      # Adapters/compat do pacote jarvis/voz (wake word, VAD, RealtimeSTT)
├── audio/                    # Utilidades de áudio
├── telemetria/               # Telemetria da interface (stub atual)
├── infra/                    # Perfis, decisão de modelo, comunicação
├── benchmarks/               # WER e perf medidos
├── bench_audio/              # Áudios de referência para bench (com README)
├── test_audio/               # Áudios de teste (com README)
├── testes/                   # Roteiros de teste/benchmark
└── raiz                      # Docs de visão geral e dependências
```

## Índice rápido (docs)
- Visão: `PLANO_OURO_INTERFACE.md`, `EVOLUCAO_PERFOMACE.MD`, `orchestrator_voice.md`
- Dependências: `DEPENDENCIAS_INTERFACE.md`
- Entrada: `entrada/entrada_stt.md`, `entrada/entrada_app.md`, `entrada/voz_vad.md`, `entrada/voz_speaker_verify.md`
- Saída: `saida/voz_tts.md`
- Adapters/voz: `voz/README.md`, `voz/adapters/voz_adapters_*.md`, `voz/terceiros_realtimestt.md`
- Infra/perfis: `infra/decisao_stt_model_tiny.md`, `infra/ETAPA5_BACKEND_PLUGAVEL.md`, `infra/profiles.md`, `infra/voice_profile.md`
- Testes/bench: `testes/TESTES_INTERFACE.md`, `testes/benchmark_interface.md`, `testes/TESTE_MANUAL.md`, `testes/TESTES_VOZ_SEM_MICROFONE.MD`
- Áudios: `bench_audio/README.md`, `test_audio/README.md`
- Telemetria: `telemetria/telemetria.md` (stub)

## Mapa código → doc
- `jarvis/interface/entrada/stt.py` → `entrada/entrada_stt.md`
- `jarvis/interface/entrada/vad.py` → `entrada/voz_vad.md`
- `jarvis/interface/entrada/speaker_verify.py` → `entrada/voz_speaker_verify.md`
- `jarvis/interface/entrada/app.py` → `entrada/entrada_app.md`
- `jarvis/interface/entrada/preflight.py` → `entrada/entrada_preflight.md`
- `jarvis/interface/entrada/chat_ui.py` → `entrada/entrada_chat_ui.md`
- `jarvis/interface/entrada/gui_panel.py` → `entrada/entrada_gui_panel.md`
- `jarvis/interface/entrada/shortcut.py` → `entrada/entrada_shortcut.md`
- `jarvis/interface/entrada/followup.py` → `entrada/entrada_followup.md`
- `jarvis/interface/entrada/turn_taking.py` → `entrada/entrada_turn_taking.md`
- `jarvis/interface/entrada/emocao.py` → `entrada/entrada_emocao.md`
- `jarvis/interface/audio/audio_utils.py` → `audio/entrada_audio_utils.md`
- `jarvis/interface/infra/chat_inbox.py` → `infra/comunicacao_chat_inbox.md`
- `jarvis/interface/infra/chat_log.py` → `infra/comunicacao_chat_log.md`
- `jarvis/interface/infra/profiles.py` → `infra/profiles.md`
- `jarvis/interface/infra/voice_profile.py` → `infra/voice_profile.md`
- `jarvis/interface/infra/` (decisão tiny/backends) → `infra/decisao_stt_model_tiny.md`, `infra/ETAPA5_BACKEND_PLUGAVEL.md`
- `jarvis/interface/saida/tts.py` → `saida/voz_tts.md`
- `jarvis/interface/telemetria/__init__.py` → `telemetria/telemetria.md` (stub)
- `jarvis/voz/adapters/*.py` → `voz/adapters/voz_adapters_*.md`
- `jarvis/third_party/realtimestt` → `voz/terceiros_realtimestt.md`

## Dependências (resumo + onde ler)
- STT: `faster-whisper` (padrão tiny, produção), `pywhispercpp` (bloqueado por regressão) — ver `DEPENDENCIAS_INTERFACE.md`
- Streaming STT: `RealtimeSTT` + `pyaudio` (opcional) — `DEPENDENCIAS_INTERFACE.md` e `voz/terceiros_realtimestt.md`
- TTS: `piper-tts` (backend Python/CLI) + `espeak-ng` (fallback) — `saida/voz_tts.md`
- Áudio básico: `sounddevice`, `webrtcvad`, `numpy`, `scipy`, `aplay` — `DEPENDENCIAS_INTERFACE.md`
- Wake word (opcional): `pvporcupine`, `openwakeword` — `voz/adapters/voz_adapters_wakeword_*.md`
- Speaker verify (opcional): `resemblyzer` — `entrada/voz_speaker_verify.md`
- Deactivity Silero (opcional): `torch` — `voz/adapters/voz_adapters_vad_silero.md`
## Por onde começar
- `PLANO_OURO_INTERFACE.md` — objetivos, estado atual (faster_whisper tiny padrão, p95 ~1190ms; whisper_cpp bloqueado).
- `EVOLUCAO_PERFOMACE.MD` — histórico resumido de performance.
- `DEPENDENCIAS_INTERFACE.md` — dependências e flags principais.
- `orchestrator_voice.md` — visão do fluxo de voz no orquestrador.

## Componentes
- Entrada: `entrada/entrada_stt.md`, `entrada/voz_vad.md`, `entrada/voz_speaker_verify.md`, `entrada/entrada_app.md`.
- Saída: `saida/voz_tts.md` (Piper/espeak, warmup implementado).
- Adapters/voz: `voz/` (wake word Porcupine/OpenWakeWord, VAD Silero, RealtimeSTT vendorizado).
- Infra: `infra/decisao_stt_model_tiny.md`, `infra/ETAPA5_BACKEND_PLUGAVEL.md`, `infra/profiles.md`, `infra/voice_profile.md`.
- Telemetria: `telemetria/telemetria.md` (stub; sem APIs ativas ainda).

## Status de performance (28/01/2026)
- Meta OURO atingida no limite para `eos_to_first_audio_ms p95`: ~1190ms com warmup STT+TTS (faster_whisper).
- Barge-in: `barge_in_stop_ms p95 ~60ms` (OK).

## Comandos úteis
- Testes: `PYTHONPATH=. pytest -q testes/`
- Benchmark principal (voz limpa, warmup):  
  `PYTHONPATH=. JARVIS_STT_MODEL=tiny python scripts/bench_interface.py eos_to_first_audio --audio Documentos/DOC_INTERFACE/bench_audio/voice_clean.wav --text "ok" --repeat 20 --resample`

## Notas de organização
- `entrada/` cobre tudo que vive em `jarvis/interface/entrada/`.
- `saida/` cobre `jarvis/interface/saida/tts.py`.
- `voz/` documenta a camada `jarvis/voz/` (compat/adapters usados pelo STT e wake word). Mantemos separado para refletir o código e evitar confundir entrada/saída.
