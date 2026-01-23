# voz/adapters/vad_silero.py

- Caminho: `jarvis/voz/adapters/vad_silero.py`
- Papel: deactivity detection com Silero (fim de fala mais robusto).
- Onde entra no fluxo: usado pelo STT (`SpeechToText._record_until_silence`).
- Atualizado em: 2026-01-11

## Responsabilidades
- Carregar modelo Silero VAD via `torch.hub`.
- Detectar ultimo trecho de fala e cortar silencio do fim.
- Nao quebrar se o modelo nao estiver disponivel.

## Entrada e saida
- Entrada: `audio_i16` (PCM int16 mono 16 kHz).
- Saida: `trimmed_bytes` + flag de fala (`bool | None`).

## Configuracao (env)
- `JARVIS_SILERO_DEACTIVITY=1` ativa o uso.
- `JARVIS_SILERO_SENSITIVITY` (0-1) controla o threshold.
- `JARVIS_SILERO_USE_ONNX=1` tenta usar ONNX.
- `JARVIS_SILERO_AUTO_DOWNLOAD=1` permite baixar o modelo no primeiro uso.

## Dependencias
- `torch` (obrigatorio para Silero).
- `onnxruntime` (opcional, quando `JARVIS_SILERO_USE_ONNX=1`).

## Limites
- Requer audio em 16 kHz; se nao for, nao aplica o trim e retorna `None` como flag.
- Se o modelo nao estiver no cache e `AUTO_DOWNLOAD=0`, nao roda.
- Em falhas/indisponibilidade, retorna audio original e flag `None`.

## Testes relacionados
- `testes/test_stt_silero_deactivity.py`
