# interface/audio/audio_utils.py

- Caminho: `jarvis/interface/audio/audio_utils.py`
- Papel: contrato de audio (SAMPLE_RATE, BYTES_PER_SAMPLE) e coercoes para PCM bytes.
- Onde entra no fluxo: usado por STT, VAD, trim Rust e testes.
- Atualizado em: 2026-01-24 (revisado com o código)

## Responsabilidades
- Normalizar payloads de áudio para `bytes` PCM int16 LE (mono).
- Rejeitar tipos/formatos inesperados (None, listas com valores fora de int16, buffers desalinhados).

## Entrada e saída
- Aceita: `bytes`/`bytearray`/`memoryview`, objetos com `tobytes()`, listas de ints, listas de frames (`bytes`).
- Retorna: `bytes` PCM int16 LE (mono, 16 kHz por contrato).

## Configuração
- Constantes: `SAMPLE_RATE=16000`, `BYTES_PER_SAMPLE=2`.
  - Não reamostra nem valida canais; só garante formato int16 LE.

## Dependencias diretas
- Apenas stdlib (`array`).

## Testes relacionados
- `testes/test_stt_flow.py` (coerce + write_wav)
- `testes/test_stt_rust_trim.py` (coerce de retornos Rust)
- `testes/test_audio_utils.py` (listas de int16 e limites)

## Comandos uteis
- Testes: `PYTHONPATH=. pytest -q testes/test_stt_flow.py::test_write_wav_coerces_payloads`

## Qualidade e limites
- Levanta `TypeError` para: payload `None`, tipo não suportado, buffer ímpar (não alinhado a int16), ints fora de -32768..32767.
- Não reamostra nem checa número de canais; assume contrato mono/16 kHz definido pelo restante da interface.


## Performance (estimativa)
- Uso esperado: baixo.
- Medir: use `/usr/bin/time -v <comando>` e monitore `top`/`htop`.

## Observabilidade
- Sem logs diretos; logs aparecem no STT.

## Problemas conhecidos (hoje)
~~Nao valida sample rate ou canais; apenas tipo do payload.~~ (resolvido para alinhamento int16)
~~Lista de ints 0-255 e tratada como bytes, o que pode mascarar erro.~~ (resolvido)

## Melhorias sugeridas
Nenhuma pendente.
