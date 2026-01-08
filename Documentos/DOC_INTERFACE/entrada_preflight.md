# entrada/preflight.py

- Caminho: `jarvis/entrada/preflight.py`
- Papel: validar deps e ambiente antes de usar a interface (voz/UI).
- Onde entra no fluxo: chamado pelo CLI (`--preflight`).

## Responsabilidades
- Checar Python, data dir e kill switch.
- Validar deps de STT, TTS, UI, atalho e OCR.
- Reportar WARN/FAIL com sugestoes.

## Entrada e saida
- Entrada: `Config` e variaveis de ambiente.
- Saida: `PreflightReport` com lista de checks.

## Configuracao (env)
- `JARVIS_HEADLESS`, `DISPLAY`, `WAYLAND_DISPLAY`
- `JARVIS_STT_MODE`, `JARVIS_TTS_MODE`
- `JARVIS_LOCAL_LLM_BASE_URL`
- `JARVIS_FORCE_RUST_VISION`
- `JARVIS_PREFLIGHT_PROBE` (0/1) ativa teste real de captura/TTS
- `JARVIS_PREFLIGHT_PROBE_SECONDS` (float) duracao da captura no probe

## Dependencias diretas
- `jarvis.entrada.stt.check_stt_deps`
- `jarvis.voz.tts.check_tts_deps`
- `jarvis.entrada.shortcut.check_shortcut_deps`
- `jarvis.validacao.validator.check_validator_deps`
- `jarvis.acoes.desktop.DesktopAutomation`
- `jarvis.acoes.web.check_playwright_deps`
- `jarvis.aprendizado.recorder.check_recorder_deps`

## Testes relacionados
- `testes/test_preflight_headless.py`
- `testes/test_preflight_shortcut_ui.py`
- `testes/test_preflight_probe.py`

## Comandos uteis
- Rodar preflight: `PYTHONPATH=. python -m jarvis.entrada.app --preflight`
- Testes: `PYTHONPATH=. pytest -q testes/test_preflight_headless.py testes/test_preflight_shortcut_ui.py`

## Qualidade e limites
- Sem deps de audio: STT fica FAIL.
- Em headless: acoes desktop viram WARN (nao FAIL).
- Sem `scipy`: STT fica WARN porque reamostragem pode falhar em devices != 16 kHz.
- Se piper estiver instalado sem modelo local, TTS fica WARN.


## Performance (estimativa)
- Uso esperado: baixo (execucao pontual).
- Medir: use `/usr/bin/time -v <comando>` e monitore `top`/`htop`.

## Observabilidade
- Saida textual via `format_report`.

## Problemas conhecidos (hoje)
- Deteccao de headless e heuristica; pode errar em ambientes atipicos.

## Melhorias sugeridas
- Separar checks por perfil (voz/UI/desktop) para reduzir ruido.
