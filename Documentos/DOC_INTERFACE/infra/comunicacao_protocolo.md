# comunicacao/protocolo.py

- Caminho: `jarvis/comunicacao/protocolo.py`
- Papel: contrato de mensagens (tipos, ids, timestamps).
- Onde entra no fluxo: base para mensagens entre modulos/servicos.
- Atualizado em: 2026-01-10 (revisado com o codigo)

## Responsabilidades
- Definir tipos de mensagem validos.
- Criar e validar payloads padronizados.
- Versionar mensagens via campo `version`.

## Entrada e saida
- Entrada: dados em dict com `version`, `type`, `id`, `ts`, `session_id`, `payload`.
- Saida: dataclass `Mensagem` ou erro de validacao (string).

## Configuracao
- Nao usa env.

## Dependencias diretas
- Apenas stdlib.

## Testes relacionados
- `testes/test_protocolo_validar.py`

## Comandos uteis
- Teste basico: `PYTHONPATH=. python -c "from jarvis.comunicacao.protocolo import criar_mensagem; print(criar_mensagem('hello','s',{}).to_dict())"`

## Qualidade e limites
- Validacao checa `version`, campos obrigatorios, tipos basicos e payload dict.


## Performance (estimativa)
- Uso esperado: baixo.
- Medir: use `/usr/bin/time -v <comando>` e monitore `top`/`htop`.

## Observabilidade
- Nao loga; e um contrato de dados.

## Problemas conhecidos (hoje)
- Nenhum especifico de versionamento no momento.

## Melhorias sugeridas
- Definir politica de compatibilidade quando `version` mudar.
