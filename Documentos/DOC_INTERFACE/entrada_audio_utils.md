# entrada/audio_utils.py

- Caminho: `jarvis/entrada/audio_utils.py`
- Papel: contrato de audio (SAMPLE_RATE, BYTES_PER_SAMPLE) e coercoes para PCM bytes.
- Onde entra no fluxo: usado por STT, VAD, trim Rust e testes.
- Atualizado em: 2026-01-10 (revisado com o codigo)

## Responsabilidades
- Normalizar diferentes tipos (bytes, list[int], list[frames]) para `bytes`.
- Garantir int16 little-endian.

## Entrada e saida
- Entrada: payload variado (bytes, list, memoryview, array).
- Saida: `bytes` PCM int16 LE mono 16 kHz.

## Configuracao
- Constantes: `SAMPLE_RATE=16000`, `BYTES_PER_SAMPLE=2`.

## Dependencias diretas
- Apenas stdlib (`array`).

## Testes relacionados
- `testes/test_stt_flow.py` (coerce + write_wav)
- `testes/test_stt_rust_trim.py` (coerce de retornos Rust)
- `testes/test_audio_utils.py` (listas de int16 e limites)

## Comandos uteis
- Testes: `PYTHONPATH=. pytest -q testes/test_stt_flow.py::test_write_wav_coerces_payloads`

## Qualidade e limites
- Se o payload nao e suportado, levanta `TypeError`.
- Se o payload em bytes nao estiver alinhado a 2 bytes (int16), levanta `TypeError`.


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
