# interface/entrada/gui_panel.py

- Caminho: `jarvis/interface/entrada/gui_panel.py`
- Papel: painel flutuante para enviar comandos rapidamente.
- Onde entra no fluxo: chama `orchestrator.handle_text`.
- Atualizado em: 2026-01-10 (revisado com o codigo)

## Responsabilidades
- UI pequena sempre no topo.
- Enviar texto ao orquestrador.
- Exibir status e log local no painel.
- Mostrar estado de follow-up (ativo/inativo) para comandos de voz.
- Indicador de microfone reflete o `stt_mode` real do orquestrador.
- Alternar STT (stt_mode) pelo botao de microfone.
- Executa comandos em thread para nao travar a UI.
- Permitir cancelar comandos via STOP (kill switch).

## Entrada e saida
- Entrada: texto digitado no painel.
- Saida: chamada ao orquestrador + feedback visual.

## Configuracao
- Env: `JARVIS_GUI_FOLLOWUP_POLL_MS` (intervalo do polling em ms; default 500).
- CLI: `--gui-followup-poll-ms` (define o mesmo intervalo via `jarvis.interface.entrada.app`).

## Dependencias diretas
- `tkinter`

## Testes relacionados
- `testes/test_gui_panel_interface.py`

## Comandos uteis
- Rodar via app: `PYTHONPATH=. python -m jarvis.interface.entrada.app --gui-panel`
- Teste: `PYTHONPATH=. pytest -q testes/test_gui_panel_interface.py`

## Qualidade e limites
- Botao de microfone alterna `stt_mode` entre `local/auto` e `none`.
- Cancelamento cria/remove arquivo STOP (efeito no proximo checkpoint do orquestrador).
- Indicador de follow-up e informativo (nao altera o fluxo).
- O status de follow-up e atualizado por polling (default 500 ms; configuravel por env/CLI).
- Se o `Config` nao puder ser clonado, tenta atualizar `stt_mode` no objeto atual; se falhar, mostra erro claro no log.


## Performance (estimativa)
- Uso esperado: baixo.
- Medir: use `/usr/bin/time -v <comando>` e monitore `top`/`htop`.

## Observabilidade
- Log interno na UI (texto).

## Problemas conhecidos (hoje)
- (nenhum no momento)

## Melhorias sugeridas
- (nenhuma pendente relevante no momento)
