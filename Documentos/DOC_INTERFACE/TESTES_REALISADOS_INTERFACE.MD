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
