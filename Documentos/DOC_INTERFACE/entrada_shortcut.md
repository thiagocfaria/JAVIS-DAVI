# interface/entrada/shortcut.py

- Caminho: `jarvis/interface/entrada/shortcut.py`
- Papel: atalho global (Ctrl+Shift+J) para abrir Chat UI.
- Onde entra no fluxo: opcional, iniciado pelo CLI.
- Atualizado em: 2026-01-10 (revisado com o codigo)

## Responsabilidades
- Capturar combinacao global via pynput.
- Debounce para evitar repeticao.
- Detectar Wayland sem X11 e desabilitar.
- Default: combo `ctrl+shift+j` e cooldown 0.6s.

## Entrada e saida
- Entrada: eventos de teclado.
- Saida: executa comando para abrir UI.

## Configuracao (env/config)
- Usa `DISPLAY` e `WAYLAND_DISPLAY` para detectar Wayland.
- Opcional: `chat_ui_command` e `chat_shortcut_combo` se existirem no config (fallback para env).
- Env: `JARVIS_CHAT_SHORTCUT_COMBO` define o combo direto (ex: `alt+k`).
- Opcional: `JARVIS_CHAT_SHORTCUT_FILE` ativa gatilho por arquivo (fallback sem pynput).
- Opcional: `JARVIS_CHAT_SHORTCUT_FILE_POLL_MS` (default 500) ajusta o polling do arquivo.

## Dependencias diretas
- `pynput`

## Testes relacionados
- `testes/test_shortcut_interface.py`
- `testes/test_preflight_shortcut_ui.py` (preflight depende do check)

## Comandos uteis
- Start via app: `PYTHONPATH=. python -m jarvis.interface.entrada.app --enable-shortcut --chat-ui`
- Teste: `PYTHONPATH=. pytest -q testes/test_shortcut_interface.py`

## Qualidade e limites
- Em Wayland puro, atalho pode nao funcionar.
- `cooldown_s` evita repeticao quando a tecla fica pressionada.
- Gatilho por arquivo funciona mesmo sem pynput (use um atalho do sistema para `touch`).


## Performance (estimativa)
- Uso esperado: baixo.
- Medir: use `/usr/bin/time -v <comando>` e monitore `top`/`htop`.

## Observabilidade
- Sem log proprio; imprime aviso no CLI se indisponivel e expõe `last_error`.

## Problemas conhecidos (hoje)
- Em Wayland sem X11, atalho global nao funciona (agora detectado com `last_error`).
- Depende de pynput para o atalho global; fallback por arquivo evita bloqueio.

## Melhorias sugeridas
- (nenhuma pendente relevante no momento)
