# interface/entrada/preflight.py

- Caminho: `jarvis/interface/entrada/preflight.py`
- Papel: validar deps e ambiente antes de usar a interface (voz/UI).
- Onde entra no fluxo: chamado pelo CLI (`--preflight`).
- Atualizado em: 2026-01-14 (revisado com o codigo)

## Responsabilidades
- Checar Python, data dir e kill switch.
- Validar deps por perfil (voz/UI/desktop) para reduzir ruido.
- Reportar WARN/FAIL com sugestoes.

## Entrada e saida
- Entrada: `Config` e variaveis de ambiente.
- Saida: `PreflightReport` com lista de checks.

## Configuracao (env)
- `JARVIS_HEADLESS`, `DISPLAY`, `WAYLAND_DISPLAY`, `XDG_SESSION_TYPE`, `CI`
- `JARVIS_STT_MODE`, `JARVIS_TTS_MODE`
- `JARVIS_TTS_ENGINE` (`auto`/`piper`/`espeak-ng`) para forcar engine de voz (ou deixar em auto)
- `JARVIS_TTS_ENGINE_STRICT=1` (quando `JARVIS_TTS_ENGINE=piper`) nao cai para espeak-ng
- `JARVIS_LOCAL_LLM_BASE_URL`
- `JARVIS_FORCE_RUST_VISION`
- `JARVIS_PREFLIGHT_PROFILE` (`full`, `voice`, `ui`, `desktop` ou combinacoes)
- `JARVIS_PREFLIGHT_PROBE` (0/1) ativa teste real de captura/TTS
- `JARVIS_PREFLIGHT_PROBE_SECONDS` (float) duracao da captura no probe
- `JARVIS_WAKE_WORD_AUDIO` (0/1) ativa wake word por audio (backend configuravel)
- `JARVIS_WAKE_WORD_AUDIO_BACKEND` (`pvporcupine` ou `openwakeword`)
- `JARVIS_PORCUPINE_ACCESS_KEY`, `JARVIS_PORCUPINE_KEYWORD_PATH`, `JARVIS_PORCUPINE_SENSITIVITY`
- `JARVIS_OPENWAKEWORD_MODEL_PATHS`, `JARVIS_OPENWAKEWORD_AUTO_DOWNLOAD`

## Dependencias diretas
- `jarvis.interface.entrada.stt.check_stt_deps`
- `jarvis.interface.saida.tts.check_tts_deps`
- `jarvis.interface.entrada.shortcut.check_shortcut_deps`
- `jarvis.validacao.validator.check_validator_deps`
- `jarvis.acoes.desktop.DesktopAutomation`
- `jarvis.acoes.web.check_playwright_deps`
- `jarvis.aprendizado.recorder.check_recorder_deps`

## Testes relacionados
- `testes/test_preflight_headless.py`
- `testes/test_preflight_shortcut_ui.py`
- `testes/test_preflight_probe.py`
- `testes/test_preflight_profiles.py`

## Comandos uteis
- Rodar preflight: `PYTHONPATH=. python -m jarvis.interface.entrada.app --preflight`
- Preflight por perfil (voz): `PYTHONPATH=. python -m jarvis.interface.entrada.app --preflight --preflight-profile voice`
- Testes: `PYTHONPATH=. pytest -q testes/test_preflight_headless.py testes/test_preflight_shortcut_ui.py`

## Qualidade e limites
- Sem deps de audio: STT fica FAIL.
- Em headless: acoes desktop viram WARN (nao FAIL).
- Sem `scipy`: STT fica WARN porque reamostragem pode falhar em devices != 16 kHz.
- Se piper estiver instalado sem modelo local, TTS fica WARN.
- Se `JARVIS_WAKE_WORD_AUDIO=1` e `pvporcupine` nao estiver instalado, preflight emite WARN.
- Se `JARVIS_WAKE_WORD_AUDIO=1` e backend `openwakeword` sem modelo, preflight emite WARN.
- Quando o probe de audio esta ativo, o relatorio inclui device e sample_rate usados.


## Performance (estimativa)
- Uso esperado: baixo (execucao pontual).
- Medir: use `/usr/bin/time -v <comando>` e monitore `top`/`htop`.

## Observabilidade
- Saida textual via `format_report`.

## Problemas conhecidos (hoje)
- Deteccao de headless e heuristica; apesar de usar `XDG_SESSION_TYPE`/`DISPLAY`, pode errar em ambientes atipicos.
- Em alguns ambientes, o import do `sounddevice` pode travar (PortAudio/ALSA). Isso afeta o probe de audio.

## Melhorias sugeridas
- ~~Mostrar no relatorio o device e `sample_rate` usados no probe, para diagnostico rapido.~~ (resolvido)
