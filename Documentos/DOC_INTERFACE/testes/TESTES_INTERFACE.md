# Testes da interface (entrada/saida)

Este documento lista todos os testes que cobrem a interface de entrada/saida. Use estes comandos com `PYTHONPATH=.`.

## Comandos gerais
- Testes: `PYTHONPATH=. pytest -q testes/`
- Lint/format: `./.venv/bin/ruff check .` e `./.venv/bin/black --check .`

## Requisitos para nao pular testes
- Instale deps de voz/UI: `numpy`, `scipy`, `sounddevice`, `webrtcvad`, `faster-whisper`, `resemblyzer`, `pynput`, `python3-tk`.
- Sem essas deps, alguns testes usam `importorskip` e podem ser pulados.
- Para streaming RealtimeSTT (opcional): `RealtimeSTT` + `pyaudio`.
- Para wake word por audio (opcional): `pvporcupine` ou `openwakeword`.
- Para testes massivos/perf: `psutil`, `py-spy`.

## Rodada massiva (release)
- Suite completa: `PYTHONPATH=. ./.venv/bin/pytest -q testes/`
- Objetivo: garantir que todos os testes automatizados passam antes da liberacao.

## Principais suítes da interface (amostra)
Lista não exaustiva; veja `testes/` para o conjunto completo.
- Voz/CLI/UI: `test_app_voice_interface.py`, `test_chat_ui_interface.py`, `test_gui_panel_interface.py`, `test_shortcut_interface.py`.
- Preflight: `test_preflight_headless.py`, `test_preflight_shortcut_ui.py`, `test_preflight_probe.py`, `test_preflight_profiles.py`.
- STT/VAD: `test_stt_flow.py`, `test_stt_filters.py`, `test_stt_metrics.py`, `test_stt_streaming_controls.py`, `test_stt_realtimestt_backend.py`, `test_vad_streaming_interface.py`, `test_vad_pre_roll.py`, `test_vad_metrics.py`.
- TTS: `test_tts_interface.py`, `test_tts_verification.py`.
- Segurança/voz: `test_speaker_verify_interface.py`, `test_speaker_lock_interface.py`, `test_voice_adapters.py`, `test_voice_max_seconds_env.py`.
- Outros utilitários: `test_chat_inbox.py`, `test_chat_log.py`, `test_audio_utils.py`, `test_audio_resample.py`, `test_bench_interface.py`.

## Benchmark/diagnostico
- `scripts/bench_interface.py` - mede latencia, CPU e RSS em cenarios de voz.
  - STT: `PYTHONPATH=. python scripts/bench_interface.py stt --audio Documentos/DOC_INTERFACE/bench_audio/voice_clean.wav --repeat 5 --resample`
  - STT (RealtimeSTT, streaming por arquivo): `PYTHONPATH=. python scripts/bench_interface.py stt_realtimestt --audio Documentos/DOC_INTERFACE/bench_audio/voice_clean.wav --repeat 3 --resample`
    - Para simular tempo real (pacing por chunk): `JARVIS_BENCH_REALTIME_PACE=1` (padrao).
    - Para medir apenas compute (feed acelerado): `JARVIS_BENCH_REALTIME_PACE=0`.
    - Para evitar downloads: o benchmark seta `HF_HUB_OFFLINE=1` por padrao; para permitir downloads: `JARVIS_BENCH_ALLOW_DOWNLOADS=1`.
  - VAD: `PYTHONPATH=. python scripts/bench_interface.py vad --audio Documentos/DOC_INTERFACE/bench_audio/voice_clean.wav --repeat 10 --resample`
  - Endpointing: `PYTHONPATH=. python scripts/bench_interface.py endpointing --audio Documentos/DOC_INTERFACE/bench_audio/voice_clean.wav --repeat 10 --resample`
  - TTS: `PYTHONPATH=. python scripts/bench_interface.py tts --text "ola" --repeat 3`
  - Numero unico (EoS -> primeiro audio): `PYTHONPATH=. python scripts/bench_interface.py eos_to_first_audio --audio Documentos/DOC_INTERFACE/bench_audio/voice_clean.wav --text "ok" --repeat 5 --resample`
  - LLM planner (tempo de “pensar”): `PYTHONPATH=. python scripts/bench_interface.py llm_plan --text "digite oi" --repeat 30`
  - Speaker: `PYTHONPATH=. python scripts/bench_interface.py speaker --audio samples/voz_16k.wav --repeat 5`
  - Profiling profundo: `py-spy record -o profile.svg -- python scripts/bench_interface.py stt --audio samples/voz_16k.wav`
- `scripts/auto_voice_bench.py` - grava voz real (silencio + ruido) e roda os benchmarks de STT/VAD.
  - Inclui endpointing quando disponivel.
  - Exemplo: `PYTHONPATH=. python scripts/auto_voice_bench.py --device 6 --with-noise --output-dir Documentos/DOC_INTERFACE/bench_audio --phrase "oi jarvis teste automatico" --seconds 4`

## Testes reais (manual)
- Voice-loop real (microfone + alto-falante): `PYTHONPATH=. python -m jarvis.interface.entrada.app --voice-loop` e validar STT/TTS reais.
  - Observacao: por padrao o loop e infinito. Para limitar: `--voice-loop-max-iter 2` ou `JARVIS_VOICE_LOOP_MAX_ITER=2`.
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
