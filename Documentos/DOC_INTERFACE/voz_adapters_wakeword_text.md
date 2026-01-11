# voz/adapters/wakeword_text.py

- Caminho: `jarvis/voz/adapters/wakeword_text.py`
- Papel: adapter de wake word para fluxos baseados em texto.
- Onde entra no fluxo: usado pelo STT/orquestrador para filtrar comandos.
- Atualizado em: 2026-01-10 (revisado com o codigo)

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
- `testes/test_voice_adapters.py` (cobre o adapter e o wake word por audio)

## Comandos uteis
- Teste: `PYTHONPATH=. pytest -q testes/test_stt_filters.py`

## Qualidade e limites
- `detect()` sempre retorna False (nao detecta audio; este adapter e so para texto).
- Wake word por audio existe como opcional via Porcupine (ver abaixo).

## Wake word por audio (opcional)
- Modulo: `jarvis/voz/adapters/wakeword_porcupine.py`.
- Ativar: `JARVIS_WAKE_WORD_AUDIO=1` e `JARVIS_PORCUPINE_ACCESS_KEY`.
- Quando ativo e `require_wake_word=True`, o STT usa o detector de audio antes do texto.


## Performance (estimativa)
- Uso esperado: baixo.
- Medir: use `/usr/bin/time -v <comando>` e monitore `top`/`htop`.

## Observabilidade
- Sem logs.

## Problemas conhecidos (hoje)
- Sem Porcupine configurado, continua dependente do texto transcrito.

## Melhorias sugeridas
- ~~Implementar detector real por audio quando houver lib.~~ (resolvido com Porcupine opcional)
