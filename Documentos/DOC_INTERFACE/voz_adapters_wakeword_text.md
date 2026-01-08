# voz/adapters/wakeword_text.py

- Caminho: `jarvis/voz/adapters/wakeword_text.py`
- Papel: adapter de wake word para fluxos baseados em texto.
- Onde entra no fluxo: usado pelo STT/orquestrador para filtrar comandos.

## Responsabilidades
- Manter a mesma interface de detectores de audio.
- Aplicar `apply_wake_word_filter` em texto.

## Entrada e saida
- Entrada: texto transcrito.
- Saida: texto filtrado (sem wake word) ou vazio.

## Configuracao
- Repassa `wake_word` e `require` para o filtro.

## Dependencias diretas
- `jarvis.entrada.stt.apply_wake_word_filter`

## Testes relacionados
- `testes/test_stt_filters.py` (cobre o filtro)

## Comandos uteis
- Teste: `PYTHONPATH=. pytest -q testes/test_stt_filters.py`

## Qualidade e limites
- `detect()` sempre retorna False (nao detecta audio).


## Performance (estimativa)
- Uso esperado: baixo.
- Medir: use `/usr/bin/time -v <comando>` e monitore `top`/`htop`.

## Observabilidade
- Sem logs.

## Problemas conhecidos (hoje)
- `detect()` sempre retorna False; nao detecta wake word em audio.
- Depende do texto ja transcrito para filtrar.

## Melhorias sugeridas
- Implementar detector real por audio quando houver lib.
