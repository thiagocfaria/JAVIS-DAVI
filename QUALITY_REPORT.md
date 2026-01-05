# Quality Report

## Status
- Tests: PASS (`make test`) - 35 tests in 2.24s.
- Preflight: PASS (`make preflight`) - strict mode exited 0 with warnings for optional deps (Playwright/Pillow/pynput) because system python is not using the venv.
- Smoke: PASS (`make smoke`) - artifacts written to `artifacts/smoke_result.json` and `artifacts/smoke.log`.

## Ajustes aplicados
- Preflight headless: quando o ambiente e headless e nao ha drivers de desktop, agora retorna `WARN` em vez de `FAIL`.
- Smoke runner: usa `sys.executable` para evitar falha quando `python` nao existe no PATH.
- Teste de fallback de memoria remota: garante que busca local funciona se o remoto falhar.
- Teste de preflight headless: valida o novo comportamento de `WARN`.

## Avisos do preflight (atual)
- STT desativado em modo preflight (`JARVIS_STT_MODE=none`).
- Playwright, Pillow e pynput ausentes no Python do sistema. Use `. .venv/bin/activate` para preflight completo.

## Riscos restantes
- Dependencias de automacao e voz podem faltar fora do venv.
- Telemetria local cresce sem rotacao automatica (existe script `scripts/rotate_logs.sh`).
