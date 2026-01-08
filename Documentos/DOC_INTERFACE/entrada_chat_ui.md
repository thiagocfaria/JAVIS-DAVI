# entrada/chat_ui.py

- Caminho: `jarvis/entrada/chat_ui.py`
- Papel: UI simples (tkinter) para enviar texto e ver log local.
- Onde entra no fluxo: escreve no inbox e mostra chat.log.

## Responsabilidades
- Ler log (JSONL) e mostrar ultimas linhas.
- Escrever comandos no inbox (arquivo texto) via `append_line` com lock.
- Atualizar UI em polling.
- Adicionar timestamp quando a linha nao possui.

## Entrada e saida
- Entrada: texto digitado pelo usuario.
- Saida: linha no inbox + atualizacao do painel.

## Configuracao (env/CLI)
- `JARVIS_CHAT_LOG_PATH` (padrao: `~/.jarvis/chat.log`)
- `JARVIS_CHAT_INBOX_PATH` (padrao: `~/.jarvis/chat_inbox.txt`)
- CLI: `--log-path`, `--inbox-path`, `--tail` (linhas), `--poll-ms` (intervalo)

## Dependencias diretas
- `tkinter`

## Testes relacionados
- `testes/test_chat_ui_interface.py`

## Comandos uteis
- Rodar UI: `PYTHONPATH=. python -m jarvis.entrada.chat_ui`
- Teste: `PYTHONPATH=. pytest -q testes/test_chat_ui_interface.py`

## Qualidade e limites
- Polling simples (default 800 ms), sem websocket.
- Se log nao existe, mostra vazio.
- Se houver erro ao escrever no inbox, mostra status de falha.
- Lock e consultivo; writers externos precisam usar `append_line`.
- Tail do log usa leitura por blocos para evitar carregar o arquivo inteiro.


## Performance (estimativa)
- Uso esperado: baixo/medio (polling UI).
- Medir: use `/usr/bin/time -v <comando>` e monitore `top`/`htop`.

## Observabilidade
- UI exibe mensagens e timestamps (com suporte a JSONL).

## Problemas conhecidos (hoje)
- Polling (sem websocket) pode atrasar atualizacoes.
~~UI baseada em arquivos; sem lock/concorrencia.~~ (resolvido com `append_line`)

## Melhorias sugeridas
- (nenhuma no momento)
