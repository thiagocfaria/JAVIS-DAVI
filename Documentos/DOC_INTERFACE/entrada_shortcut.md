# entrada/shortcut.py

- Caminho: `jarvis/entrada/shortcut.py`
- Papel: atalho global (Ctrl+Shift+J) para abrir Chat UI.
- Onde entra no fluxo: opcional, iniciado pelo CLI.

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
- Opcional: `chat_ui_command` e `chat_shortcut_combo` se existirem no config (fallback para padrao).
- Opcional: `JARVIS_CHAT_SHORTCUT_COMBO` para definir o combo via env.

## Dependencias diretas
- `pynput`

## Testes relacionados
- `testes/test_shortcut_interface.py`
- `testes/test_preflight_shortcut_ui.py` (preflight depende do check)

## Comandos uteis
- Start via app: `PYTHONPATH=. python -m jarvis.entrada.app --enable-shortcut --chat-ui`
- Teste: `PYTHONPATH=. pytest -q testes/test_shortcut_interface.py`

## Qualidade e limites
- Em Wayland puro, atalho pode nao funcionar.
- `cooldown_s` evita repeticao quando a tecla fica pressionada.


## Performance (estimativa)
- Uso esperado: baixo.
- Medir: use `/usr/bin/time -v <comando>` e monitore `top`/`htop`.

## Observabilidade
- Sem log proprio; imprime aviso no CLI se indisponivel.

## Problemas conhecidos (hoje)
- Em Wayland sem X11, atalho global nao funciona.
- Depende de pynput; se ausente, nao ativa.

## Melhorias sugeridas
- Padronizar `chat_shortcut_combo` via env/config (hoje e opcional).
