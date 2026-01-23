# interface/infra/chat_inbox.py

- Caminho: `jarvis/interface/infra/chat_inbox.py`
- Papel: ler novos comandos escritos em arquivo texto.
- Onde entra no fluxo: consumido pelo app antes do loop de voz.
- Atualizado em: 2026-01-10 (revisado com o codigo)

## Responsabilidades
- Fazer tail do arquivo e retornar apenas linhas novas.
- Manter offset interno.
- Persistir cursor em arquivo `.cursor` para evitar reprocessar comandos apos reinicio.
- Oferecer append com lock (best-effort) para evitar intercalacao.

## Entrada e saida
- Entrada: arquivo texto (path configurado no config).
- Saida: lista de strings (comandos).

## Configuracao
- Caminho via config: `chat_inbox_path`.
- Env: `JARVIS_CHAT_INBOX_PATH`.
- Env opcional: `JARVIS_CHAT_INBOX_MAX_LINES` (limita quantas linhas retorna por drain).
- Padrao (config): `~/.jarvis/chat_inbox.txt`.
  - Default de `JARVIS_CHAT_INBOX_MAX_LINES`: 0 (sem limite).

## Dependencias diretas
- Apenas stdlib (`pathlib`, `os`).
- `fcntl` (opcional; apenas em Linux/macOS para lock advisory).

## Testes relacionados
- `testes/test_chat_inbox.py`

## Comandos uteis
- Teste: `PYTHONPATH=. pytest -q testes/test_chat_inbox.py`

## Qualidade e limites
- Se o arquivo for truncado, o offset e resetado.
- Linhas vazias sao descartadas.
- Se nao conseguir gravar o cursor (permissao/IO), volta ao comportamento antigo.
- Lock e apenas consultivo (advisory); writers externos precisam usar `append_line`.
- Em Windows (sem `fcntl`), o lock nao e aplicado.


## Performance (estimativa)
- Uso esperado: baixo.
- Medir: use `/usr/bin/time -v <comando>` e monitore `top`/`htop`.

## Observabilidade
- Sem log proprio.

## Problemas conhecidos (hoje)
~~Nao ha confirmacao/ack do consumo do comando.~~ (resolvido com cursor)
~~Sem lock de arquivo; multiplos escritores podem intercalar linhas.~~ (resolvido com `append_line` + lock)

## Melhorias sugeridas
Nenhuma pendente.
