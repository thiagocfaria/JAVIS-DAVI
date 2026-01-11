# Testes da interface (entrada/saida)

Este documento lista todos os testes que cobrem a interface de entrada/saida. Use estes comandos com `PYTHONPATH=.`.

## Comando geral
- `PYTHONPATH=. pytest -q testes/`

## Requisitos para nao pular testes
- Instale deps de voz/UI: `numpy`, `scipy`, `sounddevice`, `webrtcvad`, `faster-whisper`, `resemblyzer`, `pynput`, `python3-tk`.
- Sem essas deps, alguns testes usam `importorskip` e podem ser pulados.
- Para testes massivos/perf: `psutil`, `py-spy` e (opcional) `pvporcupine` para wake word por audio.

## Rodada massiva (release)
- Suite completa: `PYTHONPATH=. ./.venv/bin/pytest -q testes/`
- Objetivo: garantir que todos os testes automatizados passam antes da liberacao.
- Registro: anotar resultado em `Documentos/DOC_INTERFACE/TESTES_REALISADOS_INTERFACE.MD`.

## Testes por arquivo (o que faz + onde fica + como usar)
| Teste (arquivo) | O que valida | Como rodar |
| --- | --- | --- |
| `testes/test_app_voice_interface.py` | CLI/flags de voz, inicializacao do loop e integracao basica com UI/painel. | `PYTHONPATH=. pytest -q testes/test_app_voice_interface.py` |
| `testes/test_chat_inbox.py` | Leitura incremental do inbox de comandos (append, cursor, ack). | `PYTHONPATH=. pytest -q testes/test_chat_inbox.py` |
| `testes/test_chat_log.py` | Escrita do chat log, auto_open e cooldown. | `PYTHONPATH=. pytest -q testes/test_chat_log.py` |
| `testes/test_chat_ui_interface.py` | UI de chat: tail do log, timestamps e escrita no inbox. | `PYTHONPATH=. pytest -q testes/test_chat_ui_interface.py` |
| `testes/test_gui_panel_interface.py` | Painel flutuante: enviar comando, cancelar e comportamento basico da UI. | `PYTHONPATH=. pytest -q testes/test_gui_panel_interface.py` |
| `testes/test_shortcut_interface.py` | Atalho global: parsing de combo, debounce e start/stop. | `PYTHONPATH=. pytest -q testes/test_shortcut_interface.py` |
| `testes/test_preflight_headless.py` | Preflight em ambiente headless. | `PYTHONPATH=. pytest -q testes/test_preflight_headless.py` |
| `testes/test_preflight_shortcut_ui.py` | Preflight para UI e atalho (deps e mensagens). | `PYTHONPATH=. pytest -q testes/test_preflight_shortcut_ui.py` |
| `testes/test_preflight_probe.py` | Preflight com probe real de captura/TTS (via env). | `PYTHONPATH=. pytest -q testes/test_preflight_probe.py` |
| `testes/test_preflight_profiles.py` | Preflight por perfil (voz/UI/desktop) filtra checks. | `PYTHONPATH=. pytest -q testes/test_preflight_profiles.py` |
| `testes/test_stt_flow.py` | Fluxo STT: streaming VAD, fallback, coercao de bytes e escrita WAV. | `PYTHONPATH=. pytest -q testes/test_stt_flow.py` |
| `testes/test_stt_filters.py` | Wake word (exigir/normalizar) e limpeza de texto. | `PYTHONPATH=. pytest -q testes/test_stt_filters.py` |
| `testes/test_stt_rust_trim.py` | Trim Rust: cortar silencio e normalizar payload. | `PYTHONPATH=. pytest -q testes/test_stt_rust_trim.py` |
| `testes/test_stt_capture_config.py` | Config de device/sample rate e bypass de streaming fora de 16 kHz. | `PYTHONPATH=. pytest -q testes/test_stt_capture_config.py` |
| `testes/test_stt_speech_fallback.py` | Fallback de `check_speech_present` sem VAD/Rust (limiar de pico). | `PYTHONPATH=. pytest -q testes/test_stt_speech_fallback.py` |
| `testes/test_stt_metrics.py` | Logs de duracao (captura/transcricao) via env. | `PYTHONPATH=. pytest -q testes/test_stt_metrics.py` |
| `testes/teste_stt_gap_latency.py` | Debounce entre gravacoes, limite de latencia e normalizacao opcional. | `PYTHONPATH=. pytest -q testes/teste_stt_gap_latency.py` |
| `testes/test_stt_vad_env.py` | Parametros de VAD via env (silence/pre/post/max). | `PYTHONPATH=. pytest -q testes/test_stt_vad_env.py` |
| `testes/test_stt_whisper_kwargs.py` | Parametros do Whisper via env (beam/best/temperatura/prompt/suppress). | `PYTHONPATH=. pytest -q testes/test_stt_whisper_kwargs.py` |
| `testes/test_stt_streaming_controls.py` | Early transcribe, limite de buffer e transcricao por bytes. | `PYTHONPATH=. pytest -q testes/test_stt_streaming_controls.py` |
| `testes/test_stt_partials.py` | Parciais via callback e modelo realtime opcional. | `PYTHONPATH=. pytest -q testes/test_stt_partials.py` |
| `testes/test_stt_silero_deactivity.py` | Trim opcional de fim de fala com Silero. | `PYTHONPATH=. pytest -q testes/test_stt_silero_deactivity.py` |
| `testes/test_audio_resample.py` | Reamostragem 44.1k -> 16k. | `PYTHONPATH=. pytest -q testes/test_audio_resample.py` |
| `testes/test_audio_utils.py` | Coercao de listas de int16 e rejeicao de out-of-range. | `PYTHONPATH=. pytest -q testes/test_audio_utils.py` |
| `testes/test_vad_pre_roll.py` | Pre/post-roll do VAD e corte correto. | `PYTHONPATH=. pytest -q testes/test_vad_pre_roll.py` |
| `testes/test_vad_streaming_interface.py` | VAD streaming: frames, record_fixed_duration e record_until_silence. | `PYTHONPATH=. pytest -q testes/test_vad_streaming_interface.py` |
| `testes/test_vad_metrics.py` | Logs de frames/duracao via env. | `PYTHONPATH=. pytest -q testes/test_vad_metrics.py` |
| `testes/test_tts_interface.py` | TTS: selecao Piper/espeak, fallback, modo none e serializacao. | `PYTHONPATH=. pytest -q testes/test_tts_interface.py` |
| `testes/test_speaker_verify_interface.py` | Enrollment e verificacao de locutor (voiceprint). | `PYTHONPATH=. pytest -q testes/test_speaker_verify_interface.py` |
| `testes/test_voice_adapters.py` | Adapters de voz (wake word/speaker), validacao de audio e encaixe no orchestrator. | `PYTHONPATH=. pytest -q testes/test_voice_adapters.py` |
| `testes/test_followup_mode.py` | Janela de follow-up e reset por falha. | `PYTHONPATH=. pytest -q testes/test_followup_mode.py` |
| `testes/test_voice_max_seconds_env.py` | max_seconds via env (voz/enroll) e clamp. | `PYTHONPATH=. pytest -q testes/test_voice_max_seconds_env.py` |
| `testes/test_protocolo_validar.py` | Validacao de mensagens (campos obrigatorios/tipos). | `PYTHONPATH=. pytest -q testes/test_protocolo_validar.py` |
| `testes/test_bench_interface.py` | Benchmark: reamostragem opcional e validacao de WAV. | `PYTHONPATH=. pytest -q testes/test_bench_interface.py` |

## Benchmark/diagnostico
- `scripts/bench_interface.py` - mede latencia, CPU e RSS em cenarios de voz.
  - STT: `PYTHONPATH=. python scripts/bench_interface.py stt --audio samples/voz_16k.wav --repeat 5`
  - VAD: `PYTHONPATH=. python scripts/bench_interface.py vad --audio samples/voz_16k.wav --repeat 10`
  - TTS: `PYTHONPATH=. python scripts/bench_interface.py tts --text "ola" --repeat 3`
  - Speaker: `PYTHONPATH=. python scripts/bench_interface.py speaker --audio samples/voz_16k.wav --repeat 5`
  - Profiling profundo: `py-spy record -o profile.svg -- python scripts/bench_interface.py stt --audio samples/voz_16k.wav`

## Testes reais (manual)
- Voice-loop real (microfone + alto-falante): `PYTHONPATH=. python -m jarvis.app --voice-loop` e validar STT/TTS reais.
- Wake word por audio (Porcupine): `JARVIS_WAKE_WORD_AUDIO=1` e validar deteccao sem transcrever ruido.
- Speaker verify real: `JARVIS_SPK_VERIFY=1`, registrar voz e testar fala autorizada vs. nao autorizada.
- AEC simples: tocar audio de retorno e confirmar reducao de eco/ruido com microfone real.
- UI/atalho: validar `chat_ui` e `gui_panel` em Wayland/X11 conforme ambiente.

## Checklist de testes a criar (futuros)
1) [ ] Teste de loopback/AEC com audio de referencia (virtual cable/loopback).
2) [ ] Teste de wake word por audio com dataset real (Porcupine).
3) [ ] Teste de speaker verify com amostras positivas/negativas reais.
4) [ ] Teste de VAD com ruido ambiente e voz baixa (dataset controlado).
5) [ ] Teste de STT com audio longo (>60s) para medir memoria/latencia.
6) [ ] Teste de TTS bloqueante (medir duracao real de fala).
7) [ ] Teste de UI/atalho em Wayland sem X11 (manual guiado).
8) [ ] Teste de reamostragem 44.1k/48k com device real (sem stub).
9) [ ] Teste end-to-end: mic -> STT -> orq -> TTS (com logs).
10) [ ] Teste de resiliencia: deps ausentes + preflight/avisos corretos.
