# Testes realizados da interface

## 2026-01-15
- Teste: suite completa `testes/`
- Data/hora: 2026-01-15 06:05
- Comando: `PYTHONPATH=. ./.venv/bin/pytest -q testes/`
- Resultado: PASS (245 passed, 3 warnings)

- Benchmark: STT/VAD/endpointing com gravacoes (WAV)
- Data/hora: 2026-01-15 06:05
- Comandos:
  - `PYTHONPATH=. ./.venv/bin/python scripts/bench_interface.py stt --audio Documentos/DOC_INTERFACE/bench_audio/voice_clean.wav --repeat 5 --resample --json Documentos/DOC_INTERFACE/bench_audio/voice_clean.stt.2026-01-15.json`
  - `PYTHONPATH=. ./.venv/bin/python scripts/bench_interface.py stt --audio Documentos/DOC_INTERFACE/bench_audio/voice_noise.wav --repeat 5 --resample --json Documentos/DOC_INTERFACE/bench_audio/voice_noise.stt.2026-01-15.json`
  - `PYTHONPATH=. JARVIS_STT_MODEL=tiny ./.venv/bin/python scripts/bench_interface.py stt --audio Documentos/DOC_INTERFACE/bench_audio/voice_clean.wav --repeat 5 --resample --json Documentos/DOC_INTERFACE/bench_audio/voice_clean.stt.tiny.2026-01-15.json`
  - `PYTHONPATH=. JARVIS_STT_MODEL=tiny ./.venv/bin/python scripts/bench_interface.py stt --audio Documentos/DOC_INTERFACE/bench_audio/voice_noise.wav --repeat 5 --resample --json Documentos/DOC_INTERFACE/bench_audio/voice_noise.stt.tiny.2026-01-15.json`
  - `PYTHONPATH=. ./.venv/bin/python scripts/bench_interface.py vad --audio Documentos/DOC_INTERFACE/bench_audio/voice_clean.wav --repeat 10 --resample --json Documentos/DOC_INTERFACE/bench_audio/voice_clean.vad.2026-01-15.json`
  - `PYTHONPATH=. ./.venv/bin/python scripts/bench_interface.py vad --audio Documentos/DOC_INTERFACE/bench_audio/voice_noise.wav --repeat 10 --resample --json Documentos/DOC_INTERFACE/bench_audio/voice_noise.vad.2026-01-15.json`
  - `PYTHONPATH=. ./.venv/bin/python scripts/bench_interface.py endpointing --audio Documentos/DOC_INTERFACE/bench_audio/voice_clean.wav --repeat 10 --resample --json Documentos/DOC_INTERFACE/bench_audio/voice_clean.endpointing.2026-01-15.json`
  - `PYTHONPATH=. ./.venv/bin/python scripts/bench_interface.py endpointing --audio Documentos/DOC_INTERFACE/bench_audio/voice_noise.wav --repeat 10 --resample --json Documentos/DOC_INTERFACE/bench_audio/voice_noise.endpointing.2026-01-15.json`
- Resultado (resumo):
  - STT (default / sem `JARVIS_STT_MODEL`): clean avg 8463 ms (p50 8588 / p95 9345); noise avg 9550 ms (p50 9735 / p95 10132)
  - STT (`JARVIS_STT_MODEL=tiny`): clean avg 1529 ms (p50 1364 / p95 2254); noise avg 1636 ms (p50 1604 / p95 2222)
  - VAD: clean avg 1.37 ms (p50 0.75 / p95 9.56); noise avg 0.69 ms (p50 0.66 / p95 1.03)
  - Endpointing (`JARVIS_VAD_SILENCE_MS=400`): clean 390 ms; noise 390 ms (`endpoint_reached=true`)
- Observacao: sem `JARVIS_STT_MODEL`, o STT usa default `small` (mais lento). Para comparar 1:1 com rodadas antigas, fixar `JARVIS_STT_MODEL=tiny`.

## 2026-01-13
- Teste: `testes/test_vad_strategy.py`
- Data/hora: 2026-01-13 23:53
- Comando: `PYTHONPATH=. pytest -q testes/test_vad_strategy.py`
- Resultado: PASS (3 passed)

- Teste: `testes/test_stt_trim_guard.py`
- Data/hora: 2026-01-13 23:35
- Comando: `PYTHONPATH=. pytest -q testes/test_stt_trim_guard.py`
- Resultado: PASS (1 passed)

- Benchmark: STT/VAD (audio espeak 30s + probe de GPU)
- Comandos:
  - `PYTHONPATH=. .venv/bin/python scripts/bench_interface.py stt --audio /tmp/jarvis_bench_30s.wav --repeat 1 --resample --json /tmp/jarvis_bench_30s.stt.json --gpu`
  - `PYTHONPATH=. .venv/bin/python scripts/bench_interface.py vad --audio /tmp/jarvis_bench_30s.wav --repeat 5 --resample --json /tmp/jarvis_bench_30s.vad.json --gpu`
- Resultado (resumo):
  - STT: 38723.81 ms (p50/p95 iguais), CPU avg 78.1962 s, RSS 1413100 KB
  - VAD: 5.21 ms (p50 5.26 / p95 6.00), CPU avg 0.0052 s, RSS 615276 KB
  - GPU: `gpu_available=false` (nvidia-smi indisponivel no ambiente)
- Observacao: audio sintetico (espeak) 22.05 kHz com `--resample`; nao e comparavel 1:1 com voz real.

- Benchmark automatico: voz real curta (silencio + TV ligada)
- Data/hora: 2026-01-13 01:27
- Comando:
  - `PYTHONPATH=. python scripts/auto_voice_bench.py --device 6 --with-noise --output-dir Documentos/DOC_INTERFACE/bench_audio --phrase "oi jarvis teste automatico" --seconds 4`
- Saidas JSON:
  - `Documentos/DOC_INTERFACE/bench_audio/voice_clean.stt.json`
  - `Documentos/DOC_INTERFACE/bench_audio/voice_clean.vad.json`
  - `Documentos/DOC_INTERFACE/bench_audio/voice_noise.stt.json`
  - `Documentos/DOC_INTERFACE/bench_audio/voice_noise.vad.json`
- Resultado (resumo):
  - STT silencio: 3532 ms (p50 3914 / p95 4606)
  - STT TV ligada: 3989 ms (p50 4088 / p95 4625)
  - VAD: ~0,7 ms (silencio) / ~0,6 ms (TV)
  - Observacao: captura 44.1 kHz com `--resample` para 16 kHz.

- Benchmark: STT com parametros “fast” (beam/best/temp + warmup)
- Data/hora: 2026-01-13 01:40
- Comandos:
  - `PYTHONPATH=. JARVIS_STT_BEAM_SIZE=1 JARVIS_STT_BEST_OF=1 JARVIS_STT_TEMPERATURE=0 JARVIS_STT_WARMUP=1 JARVIS_STT_WARMUP_SECONDS=0.5 python scripts/bench_interface.py stt --audio Documentos/DOC_INTERFACE/bench_audio/voice_clean.wav --repeat 5 --resample --json Documentos/DOC_INTERFACE/bench_audio/voice_clean.stt.fast.json`
  - `PYTHONPATH=. JARVIS_STT_BEAM_SIZE=1 JARVIS_STT_BEST_OF=1 JARVIS_STT_TEMPERATURE=0 JARVIS_STT_WARMUP=1 JARVIS_STT_WARMUP_SECONDS=0.5 python scripts/bench_interface.py stt --audio Documentos/DOC_INTERFACE/bench_audio/voice_noise.wav --repeat 5 --resample --json Documentos/DOC_INTERFACE/bench_audio/voice_noise.stt.fast.json`
- Resultado (resumo):
  - STT silencio: 9676 ms (p50 7927 / p95 21672)
  - STT TV ligada: 8950 ms (p50 7961 / p95 16711)
  - Observacao: piorou vs default; nao aplicar como padrao.

- Benchmark: endpointing compare (silence_ms 250/400/800)
- Data/hora: 2026-01-13 02:17
- Comandos:
  - `JARVIS_VAD_SILENCE_MS=250 PYTHONPATH=. .venv/bin/python scripts/bench_interface.py endpointing --audio Documentos/DOC_INTERFACE/bench_audio/voice_clean.wav --repeat 10 --json Documentos/DOC_INTERFACE/bench_audio/voice_clean.endpointing.ms250.json --resample`
  - `JARVIS_VAD_SILENCE_MS=250 PYTHONPATH=. .venv/bin/python scripts/bench_interface.py endpointing --audio Documentos/DOC_INTERFACE/bench_audio/voice_noise.wav --repeat 10 --json Documentos/DOC_INTERFACE/bench_audio/voice_noise.endpointing.ms250.json --resample`
  - `JARVIS_VAD_SILENCE_MS=400 PYTHONPATH=. .venv/bin/python scripts/bench_interface.py endpointing --audio Documentos/DOC_INTERFACE/bench_audio/voice_clean.wav --repeat 10 --json Documentos/DOC_INTERFACE/bench_audio/voice_clean.endpointing.ms400.json --resample`
  - `JARVIS_VAD_SILENCE_MS=400 PYTHONPATH=. .venv/bin/python scripts/bench_interface.py endpointing --audio Documentos/DOC_INTERFACE/bench_audio/voice_noise.wav --repeat 10 --json Documentos/DOC_INTERFACE/bench_audio/voice_noise.endpointing.ms400.json --resample`
  - `JARVIS_VAD_SILENCE_MS=800 PYTHONPATH=. .venv/bin/python scripts/bench_interface.py endpointing --audio Documentos/DOC_INTERFACE/bench_audio/voice_clean.wav --repeat 10 --json Documentos/DOC_INTERFACE/bench_audio/voice_clean.endpointing.ms800.json --resample`
  - `JARVIS_VAD_SILENCE_MS=800 PYTHONPATH=. .venv/bin/python scripts/bench_interface.py endpointing --audio Documentos/DOC_INTERFACE/bench_audio/voice_noise.wav --repeat 10 --json Documentos/DOC_INTERFACE/bench_audio/voice_noise.endpointing.ms800.json --resample`
- Saidas JSON:
  - `Documentos/DOC_INTERFACE/bench_audio/voice_clean.endpointing.ms250.json`
  - `Documentos/DOC_INTERFACE/bench_audio/voice_noise.endpointing.ms250.json`
  - `Documentos/DOC_INTERFACE/bench_audio/voice_clean.endpointing.ms400.json`
  - `Documentos/DOC_INTERFACE/bench_audio/voice_noise.endpointing.ms400.json`
  - `Documentos/DOC_INTERFACE/bench_audio/voice_clean.endpointing.ms800.json`
  - `Documentos/DOC_INTERFACE/bench_audio/voice_noise.endpointing.ms800.json`
- Resultado (resumo):
  - 250ms: 240ms (clean/noise) com endpoint ok.
  - 400ms: 390ms (clean/noise) com endpoint ok.
  - 800ms: 780ms (clean), mas no noise endpoint_reached=false (nao recomendado).

- Benchmark: ruido profile (normalize_audio / vad_aggr=3)
- Data/hora: 2026-01-13 02:25
- Comandos:
  - `PYTHONPATH=. .venv/bin/python scripts/bench_interface.py stt --audio Documentos/DOC_INTERFACE/bench_audio/voice_noise.wav --repeat 5 --resample --json Documentos/DOC_INTERFACE/bench_audio/voice_noise.stt.json`
  - `PYTHONPATH=. JARVIS_STT_NORMALIZE_AUDIO=1 .venv/bin/python scripts/bench_interface.py stt --audio Documentos/DOC_INTERFACE/bench_audio/voice_noise.wav --repeat 5 --resample --json Documentos/DOC_INTERFACE/bench_audio/voice_noise.stt.norm.json`
  - `PYTHONPATH=. JARVIS_VAD_AGGRESSIVENESS=3 .venv/bin/python scripts/bench_interface.py stt --audio Documentos/DOC_INTERFACE/bench_audio/voice_noise.wav --repeat 5 --resample --json Documentos/DOC_INTERFACE/bench_audio/voice_noise.stt.aggr3.json`
  - `PYTHONPATH=. JARVIS_STT_NORMALIZE_AUDIO=1 JARVIS_VAD_AGGRESSIVENESS=3 .venv/bin/python scripts/bench_interface.py stt --audio Documentos/DOC_INTERFACE/bench_audio/voice_noise.wav --repeat 5 --resample --json Documentos/DOC_INTERFACE/bench_audio/voice_noise.stt.norm.aggr3.json`
- Resultado (resumo):
  - baseline ruido: 3989 ms (p50 4088 / p95 4625)
  - normalize_audio=1: 8288 ms (p50 8318 / p95 8870) — piorou
  - vad_aggr=3: 8118 ms (p50 8253 / p95 8997) — piorou
  - normalize+aggr=3: 8578 ms (p50 8562 / p95 9126) — piorou

## 2026-01-07
- Teste: `testes/test_audio_resample.py`
- Comando: `. .venv/bin/activate && PYTHONPATH=. pytest -q testes/test_audio_resample.py`
- Resultado: PASS (1 passed, 1 warning de `pkg_resources` do `webrtcvad`)
- Observacao: fora da `.venv` o teste foi pulado por falta de deps.

- Teste: `testes/test_chat_inbox.py`
- Comando: `. .venv/bin/activate && PYTHONPATH=. pytest -q testes/test_chat_inbox.py`
- Resultado: PASS (3 passed)

- Teste: `testes/test_preflight_shortcut_ui.py`
- Comando: `. .venv/bin/activate && PYTHONPATH=. pytest -q testes/test_preflight_shortcut_ui.py`
- Resultado: PASS (7 passed, 1 warning de `pkg_resources` do `webrtcvad`)

- Teste: `testes/test_stt_capture_config.py`
- Comando: `. .venv/bin/activate && PYTHONPATH=. pytest -q testes/test_stt_capture_config.py`
- Resultado: PASS (4 passed, 1 warning de `pkg_resources` do `webrtcvad`)

- Teste: `testes/test_chat_log.py`
- Comando: `. .venv/bin/activate && PYTHONPATH=. pytest -q testes/test_chat_log.py`
- Resultado: PASS (4 passed)

- Teste: `testes/test_audio_utils.py`
- Comando: `. .venv/bin/activate && PYTHONPATH=. pytest -q testes/test_audio_utils.py`
- Resultado: PASS (3 passed)

- Teste: `testes/test_app_voice_interface.py`
- Comando: `. .venv/bin/activate && PYTHONPATH=. pytest -q testes/test_app_voice_interface.py`
- Resultado: PASS (8 passed, 2 warnings de deps opcionais)

- Teste: `testes/test_chat_ui_interface.py`
- Comando: `. .venv/bin/activate && PYTHONPATH=. pytest -q testes/test_chat_ui_interface.py`
- Resultado: PASS (3 passed)

- Teste: `testes/test_preflight_probe.py`
- Comando: `PYTHONPATH=. pytest -q testes/test_preflight_probe.py`
- Resultado: PASS (4 passed)

## 2026-01-12
- Teste manual: STT streaming (RealtimeSTT, inicio rapido)
- Data/hora: 2026-01-12 09:03
- Comando:
  - `JARVIS_STT_STREAMING=1 JARVIS_STT_STREAMING_BACKEND=realtimestt JARVIS_STT_STREAMING_FORCE_START=1 JARVIS_REQUIRE_WAKE_WORD=0 JARVIS_CHAT_AUTO_OPEN=0 PYTHONPATH=. ./.venv/bin/python -m jarvis.app --voice`
- Resultado: PASS (respondeu "Oi! Como posso ajudar?")
- Observacao: ao encerrar com Ctrl+C apareceu aviso "Bad file descriptor" no worker do RealtimeSTT (encerramento abrupto).
- Serie A (TV desligada) - latencia de encerramento (record_ms)
  - Data/hora: 2026-01-12 09:17
  - Medidas: 8830, 9554, 8135, 10288, 9133 ms
  - Media: 9188 ms (~9.2s) para encerrar a fala
  - Observacao: `transcribe_ms=0` indica que o gargalo esta no fim de fala (endpointing), nao no STT em si.
- Serie B (TV ligada) - latencia/ruido (record_ms)
  - Data/hora: 2026-01-12 09:27
  - Medidas: 9493, 14491, 8776, 9618, 14251 ms
  - Observacao: 2 de 5 comandos cairam em fallback (“Nao consegui completar...”) por texto ruidoso (TV); 3 de 5 responderam “Oi! Como posso ajudar?”. Gargalo segue no fim de fala (endpointing) e o ruido da TV impacta a transcricao.

- Teste: `testes/test_stt_speech_fallback.py`
- Comando: `PYTHONPATH=. pytest -q testes/test_stt_speech_fallback.py`
- Resultado: PASS (2 passed)

- Teste: `testes/test_speaker_verify_interface.py`
- Comando: `PYTHONPATH=. pytest -q testes/test_speaker_verify_interface.py`
- Resultado: PASS (4 passed, 1 skipped)

- Teste: `testes/test_tts_interface.py`
- Comando: `PYTHONPATH=. pytest -q testes/test_tts_interface.py`
- Resultado: PASS (9 passed)

- Teste: `testes/test_protocolo_validar.py`
- Comando: `PYTHONPATH=. pytest -q testes/test_protocolo_validar.py`
- Resultado: PASS (7 passed)

- Teste: `testes/test_app_voice_interface.py`
- Comando: `PYTHONPATH=. pytest -q testes/test_app_voice_interface.py`
- Resultado: PASS (9 passed)

- Teste: `testes/test_audio_utils.py`
- Comando: `PYTHONPATH=. pytest -q testes/test_audio_utils.py`
- Resultado: PASS (5 passed)

- Teste: `testes/test_speaker_verify_interface.py`
- Comando: `PYTHONPATH=. pytest -q testes/test_speaker_verify_interface.py`
- Resultado: PASS (5 passed, 1 skipped)

- Teste: `testes/test_app_voice_interface.py`
- Comando: `PYTHONPATH=. pytest -q testes/test_app_voice_interface.py`
- Resultado: PASS (10 passed)

- Teste: `testes/test_app_voice_interface.py`
- Comando: `PYTHONPATH=. pytest -q testes/test_app_voice_interface.py`
- Resultado: PASS (11 passed)

- Teste: `testes/test_tts_interface.py`
- Comando: `PYTHONPATH=. pytest -q testes/test_tts_interface.py`
- Resultado: PASS (10 passed)

- Teste: `testes/test_chat_log.py`
- Comando: `PYTHONPATH=. pytest -q testes/test_chat_log.py`
- Resultado: PASS (5 passed)

- Teste: `testes/test_app_voice_interface.py`
- Comando: `PYTHONPATH=. pytest -q testes/test_app_voice_interface.py`
- Resultado: PASS (12 passed)

- Teste: `testes/test_protocolo_validar.py`
- Comando: `PYTHONPATH=. pytest -q testes/test_protocolo_validar.py`
- Resultado: PASS (12 passed)

- Teste: `testes/test_chat_inbox.py`
- Comando: `PYTHONPATH=. pytest -q testes/test_chat_inbox.py`
- Resultado: PASS (4 passed)

- Teste: `testes/test_chat_log.py`
- Comando: `PYTHONPATH=. pytest -q testes/test_chat_log.py testes/test_chat_ui_interface.py`
- Resultado: PASS (8 passed)

## 2026-01-08
- Teste: `testes/test_protocolo_validar.py`
- Comando: `PYTHONPATH=. pytest -q testes/test_protocolo_validar.py`
- Resultado: PASS (15 passed)
- Teste: `testes/test_chat_ui_interface.py`
- Comando: `PYTHONPATH=. pytest -q testes/test_chat_ui_interface.py`
- Resultado: PASS (4 passed)
- Teste: `testes/test_speaker_verify_interface.py`
- Comando: `PYTHONPATH=. pytest -q testes/test_speaker_verify_interface.py`
- Resultado: PASS (6 passed, 1 skipped)
- Teste: `testes/test_gui_panel_interface.py`
- Comando: `PYTHONPATH=. pytest -q testes/test_gui_panel_interface.py`
- Resultado: PASS (4 passed)
- Teste: `testes/test_followup_mode.py`
- Comando: `PYTHONPATH=. pytest -q testes/test_followup_mode.py`
- Resultado: PASS (5 passed)
- Teste: `testes/test_tts_interface.py`
- Comando: `PYTHONPATH=. pytest -q testes/test_tts_interface.py`
- Resultado: PASS (11 passed)
- Teste: `testes/test_vad_streaming_interface.py`
- Comando: `PYTHONPATH=. pytest -q testes/test_vad_streaming_interface.py`
- Resultado: PASS (1 passed, 3 skipped)
- Teste: `testes/test_voice_adapters.py`
- Comando: `PYTHONPATH=. pytest -q testes/test_voice_adapters.py`
- Resultado: PASS (4 passed)
- Teste: `testes/test_preflight_profiles.py` + preflight suite
- Comando: `PYTHONPATH=. pytest -q testes/test_preflight_profiles.py testes/test_preflight_headless.py testes/test_preflight_shortcut_ui.py testes/test_preflight_probe.py`
- Resultado: PASS (15 passed)
- Teste: `testes/test_preflight_headless.py`
- Comando: `PYTHONPATH=. pytest -q testes/test_preflight_headless.py`
- Resultado: PASS (3 passed)
- Teste: `testes/test_stt_metrics.py`
- Comando: `PYTHONPATH=. pytest -q testes/test_stt_metrics.py`
- Resultado: PASS (2 passed)
- Teste: `testes/test_voice_adapters.py`
- Comando: `PYTHONPATH=. pytest -q testes/test_voice_adapters.py`
- Resultado: PASS (5 passed)
- Teste: `testes/test_vad_metrics.py`
- Comando: `PYTHONPATH=. pytest -q testes/test_vad_metrics.py`
- Resultado: PASS (1 passed)
- Teste: `testes/test_shortcut_interface.py`
- Comando: `PYTHONPATH=. pytest -q testes/test_shortcut_interface.py`
- Resultado: PASS (7 passed)
- Teste: `testes/test_chat_ui_interface.py`
- Comando: `PYTHONPATH=. pytest -q testes/test_chat_ui_interface.py`
- Resultado: PASS (5 passed)
- Teste: `testes/test_speaker_verify_interface.py`
- Comando: `PYTHONPATH=. pytest -q testes/test_speaker_verify_interface.py`
- Resultado: PASS (7 passed, 1 skipped)
- Teste: `testes/test_stt_flow.py`
- Comando: `PYTHONPATH=. pytest -q testes/test_stt_flow.py`
- Resultado: PASS (9 passed)
- Teste: `testes/test_vad_streaming_interface.py`
- Comando: `PYTHONPATH=. pytest -q testes/test_vad_streaming_interface.py`
- Resultado: PASS (3 passed, 4 skipped)
- Nota: sem teste automatizado para travamento do import do `sounddevice` (depende de PortAudio/ALSA); cobertura indireta via STT/VAD.
- Teste: `testes/test_voice_max_seconds_env.py`
- Comando: `PYTHONPATH=. pytest -q testes/test_voice_max_seconds_env.py`
- Resultado: PASS (9 passed, 1 warning de `audioop`)
- Teste: `testes/test_shortcut_interface.py`
- Comando: `PYTHONPATH=. pytest -q testes/test_shortcut_interface.py`
- Resultado: PASS (9 passed)
- Teste: `testes/test_gui_panel_interface.py`
- Comando: `PYTHONPATH=. pytest -q testes/test_gui_panel_interface.py`
- Resultado: PASS (6 passed)
- Teste: `testes/test_app_voice_interface.py`
- Comando: `PYTHONPATH=. pytest -q testes/test_app_voice_interface.py`
- Resultado: PASS (13 passed, 1 warning de `audioop`)
- Teste: `testes/test_gui_panel_interface.py`
- Comando: `PYTHONPATH=. pytest -q testes/test_gui_panel_interface.py`
- Resultado: PASS (5 passed)
- Teste: `scripts/bench_interface.py endpointing` (voz real gravada)
- Data/hora: 2026-01-13 02:10
- Comando: `PYTHONPATH=. ./.venv/bin/python scripts/bench_interface.py endpointing --audio Documentos/DOC_INTERFACE/bench_audio/voice_clean.wav --repeat 10 --json Documentos/DOC_INTERFACE/bench_audio/voice_clean.endpointing.json --resample`
- Resultado: PASS (endpoint_ms_avg=390ms, speech_detected=true)
- Teste: `scripts/bench_interface.py endpointing` (ruido/TV)
- Data/hora: 2026-01-13 02:10
- Comando: `PYTHONPATH=. ./.venv/bin/python scripts/bench_interface.py endpointing --audio Documentos/DOC_INTERFACE/bench_audio/voice_noise.wav --repeat 10 --json Documentos/DOC_INTERFACE/bench_audio/voice_noise.endpointing.json --resample`
- Resultado: PASS (endpoint_ms_avg=390ms, speech_detected=true)

- Benchmark automatico (voz real curta, silencio + TV ligada)
- Nome: auto_voice_bench (voz real)
- Objetivo: medir STT/VAD com fala real curta em dois cenarios (silencio vs ruido).
- Data/hora: 2026-01-12 22:17
- Comando: `python scripts/auto_voice_bench.py --device 6 --with-noise`
- Saidas JSON:
  - `/tmp/jarvis_voice_bench/voice_clean.stt.json`
  - `/tmp/jarvis_voice_bench/voice_clean.vad.json`
  - `/tmp/jarvis_voice_bench/voice_noise.stt.json`
  - `/tmp/jarvis_voice_bench/voice_noise.vad.json`
- Resultado (resumo):
  - STT silencio: ~5,7s (p50 6,1s)
  - STT TV ligada: ~8,6s (p95 13,3s)
  - VAD: ~1ms em ambos
  - Observacao: ruído aumenta latencia do STT; registrado em `EVOLUCAO_PERFOMACE.MD`.

## 2026-01-11
- Benchmark (interface voz: STT/VAD/Speaker/TTS) - rodada 4 (22.05k + resample)
- Data/hora: 2026-01-11 04:59
- Comandos:
  - STT: `PYTHONPATH=. .venv/bin/python scripts/bench_interface.py stt --audio /tmp/jarvis_bench_30s_22050.wav --repeat 1 --json /tmp/bench_stt_22050.json --resample`
  - VAD: `PYTHONPATH=. .venv/bin/python scripts/bench_interface.py vad --audio /tmp/jarvis_bench_30s_22050.wav --repeat 5 --json /tmp/bench_vad_22050.json --resample`
  - Speaker: `PYTHONPATH=. JARVIS_SPK_VERIFY=1 .venv/bin/python scripts/bench_interface.py speaker --audio /tmp/jarvis_bench_30s_22050.wav --repeat 3 --json /tmp/bench_speaker_22050.json --resample`
  - TTS: `PYTHONPATH=. .venv/bin/python scripts/bench_interface.py tts --text "ola jarvis, teste de desempenho de voz" --repeat 3 --json /tmp/bench_tts_22050.json`
- Resultado: registrado em `Documentos/DOC_INTERFACE/bench_history.json` (baseline_2026-01-11_pior_caso_30s_r4)

- Medicao fria vs quente (STT curto)
- Data/hora: 2026-01-11 04:58
- Comando:
```
JARVIS_STT_MODEL=tiny JARVIS_STT_LANGUAGE=pt PYTHONPATH=. .venv/bin/python - <<'PY'
import time
import wave
from pathlib import Path
from jarvis.cerebro.config import load_config
from jarvis.entrada.stt import SpeechToText

wav_path = Path('jarvis/REPOSITORIOS_CLONAR/realtimestt/RealtimeSTT/warmup_audio.wav')
with wave.open(str(wav_path), 'rb') as f:
    frames = f.readframes(f.getnframes())

stt = SpeechToText(load_config())

start = time.perf_counter()
_ = stt._transcribe_audio_bytes(frames, require_wake_word=False, skip_speech_check=False)
mid = time.perf_counter()
_ = stt._transcribe_audio_bytes(frames, require_wake_word=False, skip_speech_check=False)
end = time.perf_counter()

print({'audio': str(wav_path), 'cold_s': round(mid - start, 3), 'warm_s': round(end - mid, 3)})
PY
```
- Resultado: cold ~2.924s, warm ~2.003s (ganho ~0.92s)

- Streaming simulado (RealtimeSTT, feed de audio)
- Data/hora: 2026-01-11 04:58
- Comando:
```
PYTHONPATH=. .venv/bin/python - <<'PY'
import json
import sys
import time
import wave
from pathlib import Path

sys.path.insert(0, 'jarvis/REPOSITORIOS_CLONAR/realtimestt')
from RealtimeSTT import AudioToTextRecorder

wav_path = Path('jarvis/REPOSITORIOS_CLONAR/realtimestt/RealtimeSTT/warmup_audio.wav')
with wave.open(str(wav_path), 'rb') as f:
    frames = f.readframes(f.getnframes())
    sr = f.getframerate()
    channels = f.getnchannels()
    sampwidth = f.getsampwidth()

if channels != 1 or sampwidth != 2 or sr != 16000:
    raise SystemExit('audio deve ser mono 16k int16')

duration_s = len(frames) / (sr * sampwidth)

recorder = AudioToTextRecorder(
    use_microphone=False,
    spinner=False,
    device='cpu',
    model='tiny',
    language='pt',
    enable_realtime_transcription=True,
    use_main_model_for_realtime=False,
    realtime_model_type='tiny',
    silero_deactivity_detection=False,
    faster_whisper_vad_filter=True,
    normalize_audio=False,
    min_length_of_recording=0.1,
    post_speech_silence_duration=0.2,
    min_gap_between_recordings=0.0,
)

chunk_ms = 100
chunk_size = int(sr * (chunk_ms / 1000.0) * sampwidth)

recorder.start()
start_ts = time.perf_counter()

for i in range(0, len(frames), chunk_size):
    recorder.feed_audio(frames[i:i+chunk_size])
    time.sleep(chunk_ms / 1000.0)

recorder.stop()
text = recorder.text()
end_ts = time.perf_counter()

recorder.shutdown()

elapsed = end_ts - start_ts
approx_latency = max(0.0, elapsed - duration_s)

result = {
    'audio': str(wav_path),
    'duration_s': round(duration_s, 3),
    'elapsed_s': round(elapsed, 3),
    'approx_latency_s': round(approx_latency, 3),
    'text_preview': (text or '')[:120],
}
print(json.dumps(result, ensure_ascii=True, indent=2))
PY
```
- Resultado: duracao 1.62s, tempo total 4.577s, latencia aprox 2.96s

- Benchmark (interface voz: STT/VAD/Speaker/TTS) - rodada 3
- Data/hora: 2026-01-11 04:33
- Comandos:
  - STT: `JARVIS_STT_MODEL=tiny JARVIS_STT_LANGUAGE=pt PYTHONPATH=. .venv/bin/python scripts/bench_interface.py stt --audio /tmp/jarvis_bench_30s.wav --repeat 1 --json /tmp/bench_stt.json`
  - VAD: `PYTHONPATH=. .venv/bin/python scripts/bench_interface.py vad --audio /tmp/jarvis_bench_30s.wav --repeat 5 --json /tmp/bench_vad.json`
  - Speaker: `PYTHONPATH=. JARVIS_SPK_VERIFY=1 .venv/bin/python scripts/bench_interface.py speaker --audio /tmp/jarvis_bench_30s.wav --repeat 3 --json /tmp/bench_speaker.json`
  - TTS: `PYTHONPATH=. .venv/bin/python scripts/bench_interface.py tts --text "ola jarvis, teste de desempenho de voz" --repeat 3 --json /tmp/bench_tts.json`
- Resultado: registrado em `Documentos/DOC_INTERFACE/bench_history.json` (baseline_2026-01-11_pior_caso_30s_r3)
- Nota: audio 16k do warmup do RealtimeSTT; STT inclui cold start do modelo tiny (comparacao nao e 1:1 com r2).

- Teste: `testes/test_stt_realtimestt_backend.py`
- Comando: `PYTHONPATH=. ./.venv/bin/python -m pytest -q testes/test_stt_realtimestt_backend.py`
- Resultado: PASS (2 passed, 1 warning de `webrtcvad/pkg_resources`)
- Hora: 04:26

- Teste: `testes/test_stt_flow.py` + `testes/test_stt_streaming_controls.py` + `testes/test_stt_partials.py`
- Comando: `PYTHONPATH=. ./.venv/bin/python -m pytest -q testes/test_stt_flow.py testes/test_stt_streaming_controls.py testes/test_stt_partials.py`
- Resultado: PASS (16 passed, 1 warning de `webrtcvad/pkg_resources`)
- Hora: 04:26
- Teste: `testes/test_stt_*.py` (suite STT completa)
- Data/hora: 2026-01-11 02:56
- Comando: `PYTHONPATH=. .venv/bin/pytest -q testes/test_stt_*.py`
- Resultado: PASS (41 passed, 1 warning: `webrtcvad/pkg_resources`)
- Benchmark (interface voz: STT/VAD/Speaker/TTS)
- Data/hora: 2026-01-11 02:56
- Comandos:
  - STT: `PYTHONPATH=. .venv/bin/python scripts/bench_interface.py stt --audio /tmp/jarvis_bench_30s.wav --repeat 1 --json /tmp/bench_stt.json --resample`
  - VAD: `PYTHONPATH=. .venv/bin/python scripts/bench_interface.py vad --audio /tmp/jarvis_bench_30s.wav --repeat 5 --json /tmp/bench_vad.json --resample`
  - Speaker: `PYTHONPATH=. JARVIS_CONFIG_DIR=/tmp/jarvis_bench_config JARVIS_SPK_VERIFY=1 .venv/bin/python scripts/bench_interface.py speaker --audio /tmp/jarvis_bench_30s.wav --repeat 3 --json /tmp/bench_speaker.json --resample`
  - TTS: `PYTHONPATH=. .venv/bin/python scripts/bench_interface.py tts --text "ola jarvis, teste de desempenho de voz" --repeat 3 --json /tmp/bench_tts.json`
- Resultado: registrado em `Documentos/DOC_INTERFACE/bench_history.json` (baseline_2026-01-11_pior_caso_30s_r2)
- Teste: `testes/test_stt_silero_deactivity.py`
- Data/hora: 2026-01-11 01:52
- Comando: `PYTHONPATH=. pytest -q testes/test_stt_silero_deactivity.py`
- Resultado: PASS (3 passed)
- Teste: `testes/test_preflight_profiles.py`
- Data/hora: 2026-01-11 01:52
- Comando: `PYTHONPATH=. pytest -q testes/test_preflight_profiles.py`
- Resultado: PASS (3 passed, 1 warning `audioop`)
- Teste: `testes/test_aec_interface.py` + `testes/test_vad_streaming_interface.py` + `testes/test_tts_interface.py`
- Comando: `PYTHONPATH=. pytest -q testes/test_aec_interface.py testes/test_vad_streaming_interface.py testes/test_tts_interface.py`
- Resultado: PASS (17 passed, 5 skipped, 1 warning de `audioop`)
- Teste: `testes/test_chat_ui_interface.py`
- Comando: `PYTHONPATH=. pytest -q testes/test_chat_ui_interface.py`
- Resultado: PASS (6 passed)
- Teste: `testes/test_gui_panel_interface.py`
- Comando: `PYTHONPATH=. pytest -q testes/test_gui_panel_interface.py`
- Resultado: PASS (7 passed)
- Teste: `testes/test_speaker_verify_interface.py`
- Comando: `PYTHONPATH=. pytest -q testes/test_speaker_verify_interface.py`
- Resultado: PASS (7 passed, 1 skipped)
- Teste: `testes/test_stt_capture_config.py`
- Comando: `PYTHONPATH=. pytest -q testes/test_stt_capture_config.py`
- Resultado: PASS (5 passed)
- Teste: `testes/test_preflight_probe.py`
- Comando: `PYTHONPATH=. pytest -q testes/test_preflight_probe.py`
- Resultado: PASS (4 passed, 1 warning de `audioop`)

## 2026-01-10
- Teste: `testes/test_preflight_shortcut_ui.py`
- Comando: `PYTHONPATH=. pytest -q testes/test_preflight_shortcut_ui.py`
- Resultado: PASS (9 passed, 1 warning de `audioop`)
- Teste: `testes/test_voice_adapters.py`
- Comando: `PYTHONPATH=. pytest -q testes/test_voice_adapters.py`
- Resultado: PASS (8 passed, 1 warning de `audioop`)
- Teste: `testes/test_voice_adapters.py` + `testes/test_stt_flow.py::test_transcribe_with_vad_blocks_without_audio_wake`
- Comando: `PYTHONPATH=. pytest -q testes/test_voice_adapters.py testes/test_stt_flow.py::test_transcribe_with_vad_blocks_without_audio_wake`
- Resultado: PASS (9 passed, 1 warning de `audioop`)

## 2026-01-11
- Teste: `testes/test_stt_partials.py`
- Comando: `PYTHONPATH=. pytest -q testes/test_stt_partials.py`
- Resultado: PASS (3 passed)
- Hora: 01:23:16

- Teste: suite completa `testes/`
- Comando: `PYTHONPATH=. pytest -q testes/`
- Resultado: PASS (222 passed, 9 skipped, 1 warning de `audioop`)
- Hora: 01:23:16

- Teste: `testes/test_voice_adapters.py`
- Comando: `PYTHONPATH=. pytest -q testes/test_voice_adapters.py`
- Resultado: PASS (8 passed, 2 skipped, 1 warning de `audioop`)
- Hora: 01:35:37

- Teste: `testes/test_preflight_shortcut_ui.py`
- Comando: `PYTHONPATH=. pytest -q testes/test_preflight_shortcut_ui.py`
- Resultado: PASS (12 passed, 1 warning de `audioop`)
- Hora: 01:35:37

- Teste: suite completa `testes/`
- Comando: `PYTHONPATH=. pytest -q testes/`
- Resultado: PASS (225 passed, 11 skipped, 1 warning de `audioop`)
- Hora: 01:35:37

## 2026-01-11
- Teste: `testes/test_stt_streaming_controls.py`
- Comando: `PYTHONPATH=. pytest -q testes/test_stt_streaming_controls.py`
- Resultado: PASS (4 passed)

- Teste: `testes/test_stt_flow.py`
- Comando: `PYTHONPATH=. pytest -q testes/test_stt_flow.py`
- Resultado: PASS (9 passed)

- Teste: `pytest -q testes/` (suite completa)
- Comando: `PYTHONPATH=. pytest -q testes/`
- Resultado: FAIL (1 failed, 218 passed, 9 skipped)
- Detalhe: `test_stt_vad_env.py` falhou por env `JARVIS_AUDIO_DEVICE` herdado do sistema.
- Correcao: teste passou a limpar `JARVIS_AUDIO_DEVICE`/`JARVIS_AUDIO_CAPTURE_SR`.

- Teste: `pytest -q testes/` (suite completa, apos correção)
- Comando: `PYTHONPATH=. pytest -q testes/`
- Resultado: PASS (219 passed, 9 skipped, 1 warning de `audioop`)

## 2026-01-11
- Teste: `testes/teste_stt_gap_latency.py`
- Comando: `PYTHONPATH=. pytest -q testes/teste_stt_gap_latency.py`
- Resultado: PASS (2 passed, 1 skipped: `numpy` nao disponivel no ambiente do teste)

- Teste: `testes/test_stt_flow.py`
- Comando: `PYTHONPATH=. pytest -q testes/test_stt_flow.py`
- Resultado: PASS (9 passed)

- Teste: `testes/test_stt_filters.py` + `testes/test_stt_metrics.py`
- Comando: `PYTHONPATH=. pytest -q testes/test_stt_filters.py testes/test_stt_metrics.py`
- Resultado: PASS (8 passed)

- Teste: `testes/test_stt_vad_env.py`
- Comando: `PYTHONPATH=. pytest -q testes/test_stt_vad_env.py`
- Resultado: PASS (1 passed)

- Teste: `testes/test_stt_whisper_kwargs.py`
- Comando: `PYTHONPATH=. pytest -q testes/test_stt_whisper_kwargs.py`
- Resultado: PASS (2 passed)
- Teste manual #1 (Preflight voz)
- Data/hora: 2026-01-10 20:59
- Comando: `PYTHONPATH=. ./.venv/bin/python -m jarvis.app --preflight --preflight-profile voice`
- Resultado: PASS (6 OK, 0 avisos, 0 falhas; warning `pkg_resources` do `webrtcvad`)
- Teste manual #2 (Voz unica: captura + STT + TTS)
- Data/hora: 2026-01-10 20:59
- Comando: `PYTHONPATH=. JARVIS_VOICE_MAX_SECONDS=6 python -m jarvis.app --voice`
- Resultado: PASS parcial (respondeu "Oi! Como posso ajudar?", mas com latencia perceptivel)
- Teste manual #3 (Wake word obrigatoria sem "jarvis")
- Data/hora: 2026-01-10 21:05
- Comando: `JARVIS_REQUIRE_WAKE_WORD=1 PYTHONPATH=. ./.venv/bin/python -m jarvis.app --voice`
- Resultado: PASS (nao respondeu, comportamento esperado)
- Teste manual #4 (Wake word obrigatoria com "jarvis")
- Data/hora: 2026-01-10 21:08
- Comando: `JARVIS_REQUIRE_WAKE_WORD=1 PYTHONPATH=. ./.venv/bin/python -m jarvis.app --voice`
- Resultado: FAIL (sem resposta; TV ligada pode ter atrapalhado VAD/ruido)
- Reteste manual #4 (Wake word obrigatoria com "jarvis", TV desligada)
- Data/hora: 2026-01-10 21:10
- Comando: `JARVIS_REQUIRE_WAKE_WORD=1 PYTHONPATH=. ./.venv/bin/python -m jarvis.app --voice`
- Resultado: FAIL (sem resposta mesmo em silencio)
- Teste: `testes/` (suite completa)
- Comando: `PYTHONPATH=. ./.venv/bin/pytest -q testes/`
- Resultado: PASS (218 passed, 3 warnings: `webrtcvad/pkg_resources`, `resemblyzer/binary_dilation`, `audioop` deprecation)
- Teste: `testes/test_vad_streaming_interface.py`
- Comando: `PYTHONPATH=. pytest -q testes/test_vad_streaming_interface.py`
- Resultado: PASS (3 passed, 3 skipped)
- Teste: `testes/test_vad_streaming_interface.py`
- Comando: `PYTHONPATH=. pytest -q testes/test_vad_streaming_interface.py`
- Resultado: PASS (3 passed, 4 skipped)
- Teste: `testes/test_tts_interface.py`
- Comando: `PYTHONPATH=. pytest -q testes/test_tts_interface.py`
- Resultado: PASS (13 passed, 1 warning)
- Teste: `testes/test_voice_max_seconds_env.py`
- Comando: `PYTHONPATH=. pytest -q testes/test_voice_max_seconds_env.py`
- Resultado: PASS (9 passed, 1 warning)
- Teste: `testes/test_bench_interface.py`
- Comando: `PYTHONPATH=. pytest -q testes/test_bench_interface.py`
- Resultado: PASS (1 passed, 1 skipped)
- Teste: `testes/test_bench_interface.py`
- Comando: `PYTHONPATH=. pytest -q testes/test_bench_interface.py`
- Resultado: PASS (3 passed, 1 skipped)
- Teste: `testes/test_bench_interface.py`
- Comando: `PYTHONPATH=. pytest -q testes/test_bench_interface.py`
- Resultado: PASS (5 passed, 1 skipped)
- Teste: `testes/test_shortcut_interface.py` + `testes/test_preflight_shortcut_ui.py`
- Comando: `PYTHONPATH=. pytest -q testes/test_shortcut_interface.py testes/test_preflight_shortcut_ui.py`
- Resultado: PASS (16 passed, 1 warning)
- Teste: `testes/test_gui_panel_interface.py`
- Comando: `PYTHONPATH=. pytest -q testes/test_gui_panel_interface.py`
- Resultado: PASS (5 passed)
