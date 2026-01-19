# interface/infra/chat_log.py

- Caminho: `jarvis/interface/infra/chat_log.py`
- Papel: log append-only com mensagens do Jarvis.
- Onde entra no fluxo: usado para feedback e historico visivel.
- Atualizado em: 2026-01-10 (revisado com o codigo)

## Responsabilidades
- Registrar mensagens com timestamp.
- (Opcional) abrir o log automaticamente respeitando cooldown.

## Entrada e saida
- Entrada: role, message, meta.
- Saida: escreve linha JSONL no arquivo.

## Configuracao (config/env)
- `chat_log_path` (config)
- `chat_auto_open` (config / env via load_config; default False)
- `chat_open_command` (config)
- `chat_open_cooldown_s` (config / env via load_config; default 60s)
  - Envs: `JARVIS_CHAT_AUTO_OPEN`, `JARVIS_CHAT_OPEN_COMMAND`, `JARVIS_CHAT_OPEN_COOLDOWN_S`
- Rotacao por tamanho:
  - `JARVIS_CHAT_LOG_MAX_BYTES` (default 5 MB)
  - `JARVIS_CHAT_LOG_BACKUPS` (default 3)
- Padrao (config): `~/.jarvis/chat.log`

## Dependencias diretas
- Apenas stdlib (subprocess, time, json).

## Testes relacionados
- `testes/test_chat_log.py`

## Comandos uteis
- Abrir log: `PYTHONPATH=. python -m jarvis.interface.entrada.app --open-chat`
- Teste: `PYTHONPATH=. pytest -q testes/test_chat_log.py`

## Qualidade e limites
- Rotacao automatica por tamanho com backups.
- Auto-open respeita cooldown e so funciona quando `chat_auto_open=True`.
- Formato JSONL (campos: `ts`, `role`, `message`, `meta`).
- Se `JARVIS_CHAT_LOG_BACKUPS=0`, o log atual e descartado quando atingir o limite.


## Performance (estimativa)
- Uso esperado: baixo.
- Medir: use `/usr/bin/time -v <comando>` e monitore `top`/`htop`.

## Observabilidade
- Todas as linhas ficam em `chat.log`.
- Debug em `JARVIS_DEBUG=1` quando o auto-open falha.

## Problemas conhecidos (hoje)

## Melhorias sugeridas
~~Rotacao basica (por tamanho) para nao crescer sem controle.~~ (resolvido)
