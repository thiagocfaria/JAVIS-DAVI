# voz/vad.py

- Caminho: `jarvis/voz/vad.py`
- Papel: VAD (detectar fala) e gravacao streaming.
- Onde entra no fluxo: usado pelo STT para cortar silencio.

## Responsabilidades
- Detectar fala em frames PCM int16.
- Gravar ate silencio (StreamingVAD).
- Gerar pre/post-roll para nao cortar o inicio/fim.
- Opcionalmente retornar `speech_detected` junto com os bytes.

## Entrada e saida
- Entrada: bytes PCM int16 ou stream do microfone (float32 -> int16).
- Saida: bytes de audio; quando `return_speech_flag=True`, retorna `(bytes, bool)`.

## Configuracao
- Parametros no init: aggressiveness, sample_rate, silence_duration, pre/post-roll.
- Defaults do StreamingVAD: sample_rate=16000, frame=30ms, silence=800ms, max=30s, pre=200ms, post=200ms.

## Dependencias diretas
- `webrtcvad`
- `sounddevice`
- `numpy`

## Testes relacionados
- `testes/test_vad_pre_roll.py`
- `testes/test_vad_streaming_interface.py`
- `testes/test_stt_flow.py` (usa VAD em fluxo)

## Comandos uteis
- Testes: `PYTHONPATH=. pytest -q testes/test_vad_pre_roll.py testes/test_vad_streaming_interface.py`

## Qualidade e limites
- webrtcvad aceita SR: 8/16/32/48 kHz.
- Frames precisam ter tamanho exato (10/20/30 ms).
- `VADError` e levantado quando o frame tem tamanho invalido.


## Performance (estimativa)
- Uso esperado: medio (processa audio).
- Medir: use `/usr/bin/time -v <comando>` e monitore `top`/`htop`.

## Observabilidade
- Sem log proprio; erros viram excecao.

## Problemas conhecidos (hoje)
- webrtcvad pode errar com voz baixa/ruido.
- Nao ha AEC/NS/AGC antes do VAD.
- StreamingVAD nao expone escolha de device.

## Melhorias sugeridas
- Expor metricas de frames processados e duracao.
