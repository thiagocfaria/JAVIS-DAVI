# entrada/gui_panel.py

- Caminho: `jarvis/entrada/gui_panel.py`
- Papel: painel flutuante para enviar comandos rapidamente.
- Onde entra no fluxo: chama `orchestrator.handle_text`.

## Responsabilidades
- UI pequena sempre no topo.
- Enviar texto ao orquestrador.
- Exibir status e log local no painel.
- Executa comandos em thread para nao travar a UI.
- Permitir cancelar comandos via STOP (kill switch).

## Entrada e saida
- Entrada: texto digitado no painel.
- Saida: chamada ao orquestrador + feedback visual.

## Configuracao
- Nao possui env proprio; depende do orquestrador.

## Dependencias diretas
- `tkinter`

## Testes relacionados
- `testes/test_gui_panel_interface.py`

## Comandos uteis
- Rodar via app: `PYTHONPATH=. python -m jarvis.entrada.app --gui-panel`
- Teste: `PYTHONPATH=. pytest -q testes/test_gui_panel_interface.py`

## Qualidade e limites
- Nao muda configuracao real do microfone (apenas indicador).
- Cancelamento cria/remove arquivo STOP (efeito no proximo checkpoint do orquestrador).


## Performance (estimativa)
- Uso esperado: baixo.
- Medir: use `/usr/bin/time -v <comando>` e monitore `top`/`htop`.

## Observabilidade
- Log interno na UI (texto).

## Problemas conhecidos (hoje)
- Botao de microfone e apenas indicador; nao altera STT real.
- (nenhum no momento)

## Melhorias sugeridas
- Indicador real de microfone (ligado/desligado) baseado no config.
