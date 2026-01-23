# RealtimeSTT (vendorizado)

Objetivo: manter o backend RealtimeSTT disponivel (para STT streaming/latencia percebida) sem depender do clone em `jarvis/REPOSITORIOS_CLONAR/`.

## Onde fica
- Copia vendorizada: `jarvis/third_party/realtimestt/RealtimeSTT`
- License upstream: `jarvis/third_party/realtimestt/LICENSE`
- README upstream (referencia): `jarvis/third_party/realtimestt/README_UPSTREAM.md`

## Como o Jarvis usa
- Adapter: `jarvis/voz/adapters/stt_realtimestt.py`
  - Ordem: tenta `pip` (`import RealtimeSTT`), depois `jarvis/third_party/realtimestt`, depois o clone (fallback de transicao).
- STT: `jarvis/interface/entrada/stt.py`
  - Habilitar: `JARVIS_STT_STREAMING=1`
  - Backend: `JARVIS_STT_STREAMING_BACKEND=realtimestt`
  - Reuso do recorder (para reduzir overhead entre chamadas): `JARVIS_STT_STREAMING_REUSE_RECORDER=1` (padrao)
  - Silero interno do RealtimeSTT: `JARVIS_STT_STREAMING_SILERO=1` (padrao desligado para evitar downloads inesperados)
  - Downloads: por padrao o Jarvis seta `HF_HUB_OFFLINE=1` durante o init do RealtimeSTT; para permitir downloads: `JARVIS_ALLOW_MODEL_DOWNLOADS=1`.

## Como validar
1) Teste unitario do backend:
   - `PYTHONPATH=. ./.venv/bin/pytest -q testes/test_stt_realtimestt_backend.py`
2) Benchmark do RealtimeSTT por arquivo (sem microfone):
   - `PYTHONPATH=. ./.venv/bin/python scripts/bench_interface.py stt_realtimestt --audio Documentos/DOC_INTERFACE/bench_audio/voice_clean.wav --repeat 1 --resample`

## Remover o clone (quando estiver pronto)
Depois de validar, o clone em `jarvis/REPOSITORIOS_CLONAR/realtimestt` pode ser removido, porque o Jarvis passa a depender da copia em `jarvis/third_party/realtimestt`.
