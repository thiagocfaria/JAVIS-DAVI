# interface/entrada/adapters/wakeword_text.py

- Caminho oficial: `jarvis/interface/entrada/adapters/wakeword_text.py`
- Papel: adapter de wake word para fluxos baseados em texto.
- Onde entra no fluxo: usado pelo STT/orquestrador para filtrar comandos.
- Atualizado em: 2026-01-14 (revisado com o codigo)

## Responsabilidades
- Manter a mesma interface de detectores de audio.
- Aplicar `apply_wake_word_filter` em texto.

## Entrada e saida
- Entrada: texto transcrito.
- Saida: texto filtrado (sem wake word) ou vazio.

## Configuracao
- Repassa `wake_word` e `require` para o filtro.

## Dependencias diretas
- `jarvis.interface.entrada.stt.apply_wake_word_filter`

## Testes relacionados
- `testes/test_stt_filters.py` (cobre o filtro)
- `testes/test_voice_adapters.py` (cobre o adapter e o wake word por audio)

## Comandos uteis
- Teste: `PYTHONPATH=. pytest -q testes/test_stt_filters.py`

## Qualidade e limites
- `detect()` sempre retorna False (nao detecta audio; este adapter e so para texto).
- Wake word por audio existe como opcional (Porcupine ou OpenWakeWord).

## Wake word por audio (opcional)
- Modulos oficiais relacionados: `jarvis/interface/entrada/adapters/wakeword_porcupine.py` e `jarvis/interface/entrada/adapters/wakeword_openwakeword.py`.
- Ativar: `JARVIS_WAKE_WORD_AUDIO=1`.
- Backend: `JARVIS_WAKE_WORD_AUDIO_BACKEND=pvporcupine` (default) ou `openwakeword`.
- Porcupine: exige `JARVIS_PORCUPINE_ACCESS_KEY` (ou `JARVIS_PORCUPINE_KEYWORD_PATH`).
- OpenWakeWord: exige `JARVIS_OPENWAKEWORD_MODEL_PATHS` ou `JARVIS_OPENWAKEWORD_AUTO_DOWNLOAD=1`.
- `JARVIS_WAKE_WORD_AUDIO_STRICT=1` bloqueia o comando se o audio nao detectar wake word.
- Quando ativo e `require_wake_word=True`, o STT aplica o gate de audio antes de transcrever; se detectar, remove a wake word do texto.


## Performance (estimativa)
- Uso esperado: baixo.
- Medir: use `/usr/bin/time -v <comando>` e monitore `top`/`htop`.

## Observabilidade
- Sem logs.

## Problemas conhecidos (hoje)
- Sem wake word por audio configurado, continua dependente do texto transcrito.

## Melhorias sugeridas
- (nenhuma pendente no momento)
