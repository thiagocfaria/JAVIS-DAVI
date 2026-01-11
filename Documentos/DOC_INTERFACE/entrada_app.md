# entrada/app.py

- Caminho: `jarvis/entrada/app.py`
- Papel: entrypoint da interface (CLI) para voz, texto, painel e preflight.
- Onde entra no fluxo: recebe comandos e aciona o orquestrador (fora do escopo da interface).
- Atualizado em: 2026-01-10 (revisado com o codigo e flags conferidas)

## Responsabilidades
- Parsear flags de fluxo (`--voice`, `--voice-loop`, `--loop`, `--gui-panel`, `--chat-ui`).
- Suportar rotas auxiliares (`--open-chat`, `--s3`) e modos (`--dry-run`).
- Permitir preflight por perfil via `--preflight-profile` (voz/UI/desktop).
- Controlar pausa do voice-loop com `--voice-loop-sleep`.
- Permitir override de device/SR via CLI (`--audio-device`, `--audio-capture-sr`).
- Permitir ajustar o polling do follow-up no painel (`--gui-followup-poll-ms`).
- Garantir que STT esta disponivel antes de usar voz.
- Criar `Orchestrator` e `ChatInbox` para drenar comandos de UI/arquivo.
- Iniciar loop de voz ou loop interativo.
- Acionar `ChatShortcut` quando pedido (`--enable-shortcut`).

## Entrada e saida
- Entrada: args CLI + linhas do inbox (texto) + opcional microfone.
- Saida: execucao de comandos, prints no console, abertura de UI.

## Configuracao (env/config)
- Config: `stt_mode`, `chat_log_path`, `chat_inbox_path`, `chat_open_command`,
  `chat_open_cooldown_s`, `stop_file_path`.
- Opcional (se existir no config): `chat_ui_command`, `chat_shortcut_combo`.
- Opcional (env): `JARVIS_CHAT_SHORTCUT_COMBO`.
- Flags CLI controlam o comportamento do fluxo.

## Dependencias diretas
- `jarvis.cerebro.orchestrator.Orchestrator`
- `jarvis.comunicacao.chat_inbox.ChatInbox`
- `jarvis.entrada.preflight.run_preflight`
- `jarvis.entrada.shortcut.ChatShortcut`

## Testes relacionados
- `testes/test_app_voice_interface.py`

## Comandos uteis
- Preflight: `PYTHONPATH=. python -m jarvis.entrada.app --preflight`
- Preflight por perfil (voz): `PYTHONPATH=. python -m jarvis.entrada.app --preflight --preflight-profile voice`
- Voz unica: `PYTHONPATH=. python -m jarvis.entrada.app --voice`
- Voice loop: `PYTHONPATH=. python -m jarvis.entrada.app --voice-loop --voice-loop-sleep 0.5`
- Voice loop com device/SR: `PYTHONPATH=. python -m jarvis.entrada.app --voice-loop --audio-device 3 --audio-capture-sr 44100`
- Chat UI: `PYTHONPATH=. python -m jarvis.entrada.app --chat-ui`
- Painel: `PYTHONPATH=. python -m jarvis.entrada.app --gui-panel`
- Painel (polling follow-up): `PYTHONPATH=. python -m jarvis.entrada.app --gui-panel --gui-followup-poll-ms 750`
- Teste: `PYTHONPATH=. pytest -q testes/test_app_voice_interface.py`

## Qualidade e limites
- Se `stt_mode=none`, voz nao inicia.
- Se faltarem deps (sounddevice/numpy/faster-whisper), a voz e bloqueada.
- No voice-loop, deps de STT sao rechecadas durante o loop.
- O console agora lista as deps ausentes e um comando `pip install` sugerido.


## Performance (estimativa)
- Uso esperado: baixo.
- Medir: use `/usr/bin/time -v <comando>` e monitore `top`/`htop`.

## Observabilidade
- Console logs durante os loops.
- O chat log e atualizado pelo orquestrador.

## Problemas conhecidos (hoje)
Nenhum relevante.

## Melhorias sugeridas
Nenhuma pendente.
