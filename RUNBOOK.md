# RUNBOOK

Guia rápido para subir, testar e executar o Jarvis de forma reproduzível.

## Pré-requisitos
- Linux (Wayland ou X11) com acesso a terminal.
- Python 3.11+.
- Dependências opcionais para automação web/voz/visão: `scripts/install_deps.sh` (Playwright/browsers, piper/espeak, pytesseract etc.).

## Setup do zero
1. (Opcional) criar ambiente virtual:
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```
2. Instalar dependências:
   ```bash
   pip install -r requirements.txt
   ```

## Configuração
1. Copie o template de ambiente:
   ```bash
   cp .env.example .env
   ```
2. Ajuste variáveis principais (ver `PROJECT_MAP.md` para detalhes):
   - `JARVIS_DATA_DIR` (pasta de dados/cache/logs)
   - `JARVIS_LOCAL_LLM_BASE_URL` (URL do LLM local; deixe vazio para MockLLM)
   - `JARVIS_TTS_MODE` / `JARVIS_STT_MODE` (`none` para desativar voz)
   - `JARVIS_BUDGET_PATH`, `JARVIS_BUDGET_MAX_CALLS`, `JARVIS_BUDGET_MAX_CHARS`
   - Endpoints opcionais do Agent S3 (`JARVIS_S3_*`).

## Como rodar
- Loop interativo (Ctrl+C para sair):
  ```bash
  python -m jarvis.app --loop
  ```
- Comando único em texto:
  ```bash
  python -m jarvis.app --text "abrir firefox"
  ```
- Painel GUI flutuante (desliga aprovação):
  ```bash
  python -m jarvis.app --gui-panel
  ```
- Agent S3 (modo GUI com tarefa):
  ```bash
  python -m jarvis.app --s3 "tarefa"
  ```
- Modo somente plano (sem executar ações):
  ```bash
  python -m jarvis.app --text "ping" --dry-run
  ```

## Telemetria e relatórios
- Gerar relatório de telemetria/local:
  ```bash
  python scripts/telemetry_report.py
  ```

## Preflight e benchmarks
- Preflight padrão:
  ```bash
  python -m jarvis.app --preflight
  ```
- Preflight estrito (retorna erro se falhar):
  ```bash
  python -m jarvis.app --preflight --preflight-strict
  ```
- Benchmarks (quando disponíveis em `scripts/benchmarks/`):
  ```bash
  python scripts/benchmarks/<script>.py
  ```
