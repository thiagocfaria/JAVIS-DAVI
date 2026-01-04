# Especificacao do Projeto (para analise automatica)

## Visao geral
- Jarvis e um agente de automacao de desktop self-hosted.
- Core em Python (3.11+), sem uso de APIs externas de IA.
- O LLM e servido por endpoints OpenAI-compat self-hosted (local ou GPU alugada).
- Policy/kill-switch/validacao rodam no PC local.

## Linguagens e runtime
- Linguagem principal: Python.
- Runtime alvo: Linux (Pop!_OS/Ubuntu), Wayland preferido.
- Modulo opcional em Rust: rust/jarvis_vision (OCR/vision).

## Entrypoints principais
- Preflight (checa dependencias):
  - `python -m jarvis.app --preflight --preflight-strict`
- Loop de texto:
  - `python -m jarvis.app --loop`
- Comando unico:
  - `python -m jarvis.app --text "sua tarefa"`
- Agente GUI (S3):
  - `python -m jarvis.app --s3 "sua tarefa"`
- Painel grafico:
  - `python -m jarvis.app --gui-panel`

## Setup local (Python)
1) Criar venv:
   - `python3 -m venv .venv`
   - `. .venv/bin/activate`
2) Instalar deps Python:
   - `pip install -r requirements.txt`
3) Playwright:
   - `python -m playwright install chromium`

## Dependencias de sistema (Linux)
Instalar manualmente (requer sudo):
- OCR: `tesseract-ocr`, `tesseract-ocr-por`
- Audio: `portaudio19-dev`, `espeak-ng`
- GUI: `python3-tk`
- Automacao:
  - Wayland: `wtype` e `ydotool`
  - X11: `xdotool`

## Variaveis de ambiente
- O arquivo `.env` e carregado automaticamente (pode desativar com `JARVIS_DISABLE_DOTENV=1`).
- Principais variaveis:
  - `JARVIS_LOCAL_LLM_BASE_URL` (endpoint LLM self-hosted)
  - `JARVIS_LOCAL_LLM_MODEL`
  - `JARVIS_S3_WORKER_BASE_URL`, `JARVIS_S3_GROUNDING_BASE_URL`
  - `JARVIS_S3_WORKER_MODEL`, `JARVIS_S3_GROUNDING_MODEL`

## Testes
- Rodar testes unitarios:
  - `python -m pytest -q`
- Preflight completo:
  - `python -m jarvis.app --preflight --preflight-strict`

## Estrutura do repositorio
- `jarvis/` Core do sistema (orquestrador, policy, validacao, memoria, automacao, agent_s3)
- `scripts/` Scripts utilitarios (benchmarks, telemetry, install)
- `Documentos/` Plano, diagrama e historico
- `rust/` Modulo opcional de vision
- `testes/` Testes unitarios

## Dados locais
- Dados e logs ficam em `~/.jarvis/`:
  - `events.jsonl` (telemetria)
  - `memory.sqlite3` (memoria local)
  - `procedures.db` (procedimentos)

## Observacoes para revisao
- Nao ha dependencia de API externa; tudo e self-hosted.
- Policy/kill-switch devem bloquear acoes criticas sem aprovacao.
- O agent S3 (GUI) deve respeitar policy + validacao local.
- Verificar se preflight e testes passam no ambiente atual.
