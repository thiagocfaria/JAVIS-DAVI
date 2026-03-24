# interface/entrada/adapters/wakeword_openwakeword.py

- Caminho oficial: `jarvis/interface/entrada/adapters/wakeword_openwakeword.py`
- Papel: detector de wake word por audio (PCM int16 16 kHz) usando OpenWakeWord.
- Onde entra no fluxo: usado pelo STT quando `JARVIS_WAKE_WORD_AUDIO=1` e backend `openwakeword`.
- Atualizado em: 2026-01-14 (revisado com o codigo)

## Responsabilidades
- Validar audio PCM int16 (tamanho par, 16 kHz).
- Rodar OpenWakeWord e detectar wake word pelos scores do modelo.
- Retornar `True/False` sem quebrar o fluxo se a lib nao existir.

## Entrada e saida
- Entrada: `audio_i16` (bytes) + `sample_rate=16000`.
- Saida: `bool` (detectou ou nao a wake word).

## Configuracao (env)
- `JARVIS_WAKE_WORD_AUDIO=1` habilita deteccao por audio.
- `JARVIS_WAKE_WORD_AUDIO_BACKEND=openwakeword`.
- `JARVIS_OPENWAKEWORD_MODEL_PATHS` (lista de modelos `.onnx`/`.tflite` separados por virgula).
- `JARVIS_OPENWAKEWORD_INFERENCE_FRAMEWORK` (`onnx` ou `tflite`).
- `JARVIS_OPENWAKEWORD_SENSITIVITY` (0.0-1.0).
- `JARVIS_OPENWAKEWORD_AUTO_DOWNLOAD=1` (baixa modelos padrao).
- `JARVIS_WAKE_WORD_AUDIO_STRICT=1` bloqueia o comando se o audio nao detectar wake word.
- `JARVIS_WAKE_WORD` (referencia textual; o modelo define a palavra real).

## Dependencias diretas
- `openwakeword` (opcional).
- `numpy` (buffer de audio).

## Testes relacionados
- `testes/test_voice_adapters.py` (OpenWakeWord fake, detecta e valida erros).

## Comandos uteis
- Teste: `PYTHONPATH=. pytest -q testes/test_voice_adapters.py`

## Qualidade e limites
- Funciona apenas em 16 kHz mono (PCM int16).
- Sem modelos carregados, o detector nao e criado.
- Modelos podem exigir download (usar `JARVIS_OPENWAKEWORD_AUTO_DOWNLOAD=1`).

## Observabilidade
- Logs apenas quando `JARVIS_DEBUG=1` (via STT).
