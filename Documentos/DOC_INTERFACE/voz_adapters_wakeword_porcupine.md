# voz/adapters/wakeword_porcupine.py

- Caminho: `jarvis/voz/adapters/wakeword_porcupine.py`
- Papel: detector de wake word por audio (PCM int16 16 kHz).
- Onde entra no fluxo: usado pelo STT quando `JARVIS_WAKE_WORD_AUDIO=1`.
- Atualizado em: 2026-01-11 (revisado com o codigo)

## Responsabilidades
- Validar audio PCM int16 (tamanho par, 16 kHz).
- Rodar o Porcupine por frames e detectar a palavra-chave.
- Retornar `True/False` sem quebrar o fluxo se a lib nao existir.

## Entrada e saida
- Entrada: `audio_i16` (bytes) + `sample_rate=16000`.
- Saida: `bool` (detectou ou nao a wake word).

## Configuracao (env)
- `JARVIS_WAKE_WORD_AUDIO=1` habilita deteccao por audio.
- `JARVIS_WAKE_WORD_AUDIO_BACKEND=porcupine` (default).
- `JARVIS_PORCUPINE_ACCESS_KEY` (obrigatorio para criar o detector).
- `JARVIS_PORCUPINE_KEYWORD_PATH` (opcional, arquivo .ppn).
- `JARVIS_PORCUPINE_SENSITIVITY` (0.0-1.0).
- `JARVIS_WAKE_WORD` (fallback do texto/keyword).

## Dependencias diretas
- `pvporcupine` (opcional).

## Testes relacionados
- `testes/test_voice_adapters.py` (Porcupine fake, detecta e valida erros).

## Comandos uteis
- Teste: `PYTHONPATH=. pytest -q testes/test_voice_adapters.py`

## Qualidade e limites
- Funciona apenas em 16 kHz mono (PCM int16).
- Sem `pvporcupine` ou sem access key, o detector nao e criado.

## Observabilidade
- Logs apenas quando `JARVIS_DEBUG=1` (via STT).
