# entrada/followup.py

- Caminho: `jarvis/entrada/followup.py`
- Papel: janela de follow-up para nao exigir wake word a cada comando.
- Onde entra no fluxo: usada pelo orquestrador ao aceitar comandos de voz.

## Responsabilidades
- Controlar tempo de follow-up (ativo/inativo).
- Decidir se wake word e exigida.
- Resetar quando falha.

## Entrada e saida
- Entrada: bool de comando aceito + timestamp opcional.
- Saida: bool indicando se precisa wake word.

## Configuracao (env)
- `JARVIS_FOLLOWUP_SECONDS` (padrao 20).
- `JARVIS_FOLLOWUP_MAX_COMMANDS` (padrao 2; inclui o comando que abriu a janela).

## Dependencias diretas
- Apenas stdlib (time, os).

## Testes relacionados
- `testes/test_followup_mode.py`

## Comandos uteis
- Teste: `PYTHONPATH=. pytest -q testes/test_followup_mode.py`

## Qualidade e limites
- Se followup_seconds = 0, nunca ativa.
- Se max_commands <= 0, follow-up fica desativado.
- A janela e limitada por tempo **e** quantidade de comandos.


## Performance (estimativa)
- Uso esperado: baixo.
- Medir: use `/usr/bin/time -v <comando>` e monitore `top`/`htop`.

## Observabilidade
- Nao possui log proprio; comportamento visto no fluxo de voz.

## Problemas conhecidos (hoje)
- Nao tem indicador visual do estado ativo.

## Melhorias sugeridas
- Expor estado ativo para UI (ex: indicador visual do microfone).
