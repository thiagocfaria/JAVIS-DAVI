# PROJECT_MAP

## Visao geral
- Linguagem principal: Python 3.11+ com modulo opcional em Rust para visao/acoes.
- Dominio: orquestrador de automacao desktop self-hosted com LLM servindo via endpoint OpenAI-compat (Qwen2.5-7B quantizado).
- Principais diretorios: `jarvis/` (orquestrador + modulos), `scripts/` (utilitarios), `Documentos/` (plano/diagramas), `testes/` (suite pytest), `rust/` (modulos Rust opcionais).

## Entrypoints atuais
- CLI principal: `python -m jarvis.app` com modos `--loop`, `--text`, `--voice`, `--gui-panel`, `--s3`, `--preflight`.
- Painel rapido: `scripts/start_gui_panel.sh` (lancha painel flutuante e telemetria).
- Servico de memoria remota: `python -m jarvis.memoria.remote_service` ou wrapper `scripts/start_remote_memory_server.sh`.
- Benchmarks/telemetria: `scripts/run_benchmarks.sh`, `scripts/telemetry_report.py`.

## Como rodar hoje
1) Criar venv e instalar deps: `python3 -m venv .venv && . .venv/bin/activate && pip install -r requirements.txt`.
2) (Opcional) Instalar deps de sistema e Playwright via `scripts/install_deps.sh`.
3) Configurar `.env` a partir de `.env.example` (LLM local, memoria remota, budget diario).
4) Executar: `python -m jarvis.app --loop` (ou outro modo). Preflight: `python -m jarvis.app --preflight --preflight-strict`.

## Configuracao
- `.env` carregado automaticamente; variaveis principais: `JARVIS_LOCAL_LLM_BASE_URL`, `JARVIS_LOCAL_LLM_MODEL`, `JARVIS_REMOTE_MEMORY_URL`, `JARVIS_REMOTE_MEMORY_TOKEN`, `JARVIS_BUDGET_MAX_CALLS`, `JARVIS_BUDGET_MAX_CHARS`.
- Arquivos de config complementares: `pytest.ini` (teste), `requirements.txt` (deps Python).

## Testes
- Suite: `testes/` com 33 testes pytest.
- Comando: `python -m pytest -q` (passou em 2026-01-?? no ambiente atual).

## Estrutura (2 niveis)
- Raiz: `README.md`, `PROJECT_SPEC.md`, `.env.example`, `pytest.ini`, `requirements.txt`, `Documentos/`, `jarvis/`, `scripts/`, `testes/`, `rust/`, `ops/`.
- `jarvis/`: `app.py`, `__main__.py`, submodulos `cerebro/`, `memoria/`, `validacao/`, `acoes/`, `agent_s3/`, `entrada/`, `voz/`, `telemetria/`, `seguranca/`, `aprendizado/`, `comunicacao/`.
- `Documentos/`: `PLANO_UNICO.md`, `README.md`, `REGISTRO_IMPLEMENTACAO.md`, `DIAGRAMA_ARQUITETURA.svg`, `archive/`.
- `scripts/`: wrappers para benchmarks, instalacao, painel, launcher, memoria remota, healthcheck.
- `testes/`: cobrindo validacao de planos, orcamento, memoria local/remota, chat, policy, kill switch, telemetria.
- `rust/`: `jarvis_vision/` (OCR/visao) com scripts de build.
- `ops/`: `systemd/` (unidades de servicos).

## Saidas/dados locais
- `~/.jarvis/` para telemetria (`events.jsonl`), memórias (`memory.sqlite3`), procedimentos (`procedures.db`), screenshots e registros.

## Observacoes
- Projeto assume ambiente Linux (Pop!_OS/Ubuntu) preferindo Wayland com fallback X11.
- LLM e demais servicos devem ser self-hosted; nenhuma API externa eh usada por padrao.
