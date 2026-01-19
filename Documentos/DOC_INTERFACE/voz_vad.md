# interface/entrada/vad.py

- Caminho: `jarvis/interface/entrada/vad.py`
- Papel: VAD (detectar fala) e gravacao streaming.
- Onde entra no fluxo: usado pelo STT para cortar silencio.
- Atualizado em: 2026-01-10 (revisado com o codigo)

## Responsabilidades
- Detectar fala em frames PCM int16.
- Gravar ate silencio (StreamingVAD).
- Gerar pre/post-roll para nao cortar o inicio/fim.
- Opcionalmente retornar `speech_detected` junto com os bytes.
- Aplicar AEC simples (quando habilitado) antes de checar fala.

## Entrada e saida
- Entrada: bytes PCM int16 ou stream do microfone (float32 -> int16).
- Saida: bytes de audio; quando `return_speech_flag=True`, retorna `(bytes, bool)`.

## Configuracao
- Parametros no init: aggressiveness, sample_rate, silence_duration, pre/post-roll, device.
- Defaults do StreamingVAD: sample_rate=16000, frame=30ms, silence=800ms, max=30s, pre=200ms, post=200ms.
- Env opcional: `JARVIS_VAD_STRATEGY=webrtc|silero|whisper|realtimestt` (se nao for `webrtc`, o STT nao usa StreamingVAD).
- Env opcional: `JARVIS_VAD_METRICS=1` para logar frames/duracao.
- Env opcional: `JARVIS_VAD_AGGRESSIVENESS=0..3` (default 2) para ajustar sensibilidade.
- Env opcional: `JARVIS_VAD_SILENCE_MS`, `JARVIS_VAD_PRE_ROLL_MS`, `JARVIS_VAD_POST_ROLL_MS`, `JARVIS_VAD_MAX_SECONDS` (ajusta o StreamingVAD).
- Env opcional: `JARVIS_VAD_PREPROCESS=1` habilita pre-processamento (NS/AGC leve) antes do VAD.
- Env opcional: `JARVIS_AEC_BACKEND=simple` habilita AEC simples (precisa referencia de playback).
- Ajustes do AEC:
  - `JARVIS_AEC_REF_SECONDS` (tamanho do buffer de playback; default 5s)
  - `JARVIS_AEC_MAX_GAIN` (limite de ganho; default 1.0)
- Ajustes de pre-processamento:
  - `JARVIS_AUDIO_AGC_TARGET_RMS` (default 0.06)
  - `JARVIS_AUDIO_AGC_MAX_GAIN` (default 6.0)
  - `JARVIS_AUDIO_NS_GATE_RMS` (default 0.01)
  - `JARVIS_AUDIO_NS_ADAPTIVE=1` (mede ruido inicial e ajusta gate dinamicamente)
  - `JARVIS_AUDIO_NS_ADAPTIVE_MS` (janela inicial em ms; default 1000)
  - `JARVIS_AUDIO_NS_ADAPTIVE_MULT` (multiplicador do ruido base; default 2.0)
  - `JARVIS_VAD_RMS_SILENCE` (se >0, trata frame com RMS baixo como silencio)

## Dependencias diretas
- `webrtcvad`
- `sounddevice` (apenas para gravacao streaming)
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
- Quando `empty_if_no_speech=True` (padrao), retorna `b""` se nao houve fala.
- Streaming VAD precisa de `sounddevice`; se faltar backend de audio, gravação falha com `VADError`.
- AEC simples so roda em 16 kHz e depende de referencia de playback (piper).
- Gate de ruido adaptativo so atua antes da primeira fala; depois que o VAD detecta fala, o gate e desativado.
- `JARVIS_VAD_RMS_SILENCE` pode reduzir falsos positivos em ruido alto, mas pode cortar fala muito baixa.


## Performance (estimativa)
- Uso esperado: medio (processa audio).
- Medir: use `/usr/bin/time -v <comando>` e monitore `top`/`htop`.

## Observabilidade
- Metrics via `JARVIS_VAD_METRICS=1` (frames e duracao).
- `StreamingVAD.get_last_metrics()` retorna `vad_ms` e `endpoint_ms` da ultima captura.
- Sem log proprio; erros viram excecao.

## Problemas conhecidos (hoje)
- Voz baixa/ruido pode exigir ajuste de `JARVIS_VAD_AGGRESSIVENESS`.
- AEC simples depende de ter referencia valida; se nao houver, vira passthrough.

## Melhorias sugeridas
- (nenhuma pendente relevante no momento)
