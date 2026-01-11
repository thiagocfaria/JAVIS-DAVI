# Testes realizados da interface

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
