# benchmark_interface.md

- Caminho: `scripts/bench_interface.py`
- Papel: medir latência/CPU/memória dos cenários da interface de voz (diagnóstico, não produção).
- Atualizado em: 2026-01-24 (cenários atuais + perfis via `jarvis.interface.infra.profiles`).

## Responsabilidades
- Rodar cenários controlados: `stt`, `stt_realtimestt`, `vad`, `endpointing`, `tts`, `speaker`, `eos_to_first_audio`, `llm_plan`, `barge_in`.
- Medir p50/p95, CPU time e RSS (opcional GPU via `nvidia-smi`).
- Gerar JSON opcional para histórico.

## Entradas/saídas
- Entrada: WAV mono 16 kHz (use `--resample` para 44.1/48 kHz); texto para TTS.
- Saída: JSON com métricas; inclui `stt_backend` (whisper.cpp ou faster-whisper) quando disponível.

## CLI (principais flags)
- `scenario`: `stt|stt_realtimestt|vad|endpointing|tts|speaker|eos_to_first_audio|llm_plan|barge_in`
- `--audio <wav>` (obrigatório p/ cenários de áudio)
- `--text "frase"` (TTS/eos_to_first_audio/llm_plan)
- `--repeat N`
- `--tts-mode local|none`
- `--profile fast_cpu|balanced_cpu|noisy_room` (aplica perfis de `infra/profiles.py`, todos hoje usam STT `tiny`)
- `--json saida.json`
- `--resample` (converte para 16 kHz; requer scipy/numpy)
- `--gpu` (usa `nvidia-smi` se existir)
- `--print-text`, `--require-wake-word`, `--no-warmup` (STT)

## Dependências
- Stdlib + módulos da interface.
- Opcionais: `psutil` (CPU/RSS), `scipy`/`numpy` (reamostragem), `sounddevice` (apenas para `auto_voice_bench.py`), `nvidia-smi` (GPU).
- Teste: `testes/test_bench_interface.py`.

## Comandos úteis (usar os WAV padronizados)
- STT: `PYTHONPATH=. python scripts/bench_interface.py stt --audio Documentos/DOC_INTERFACE/bench_audio/voice_clean.wav --repeat 5 --resample`
- STT streaming (RealtimeSTT): `PYTHONPATH=. python scripts/bench_interface.py stt_realtimestt --audio Documentos/DOC_INTERFACE/bench_audio/voice_clean.wav --repeat 3 --resample`
- VAD: `PYTHONPATH=. python scripts/bench_interface.py vad --audio Documentos/DOC_INTERFACE/bench_audio/voice_clean.wav --repeat 10 --resample`
- Endpointing: `PYTHONPATH=. python scripts/bench_interface.py endpointing --audio Documentos/DOC_INTERFACE/bench_audio/voice_clean.wav --repeat 10 --resample`
- TTS: `PYTHONPATH=. python scripts/bench_interface.py tts --text "ola" --repeat 3`
- EoS -> 1º áudio: `PYTHONPATH=. python scripts/bench_interface.py eos_to_first_audio --audio Documentos/DOC_INTERFACE/bench_audio/voice_clean.wav --text "ok" --repeat 5 --resample`
- Barge-in: `PYTHONPATH=. python scripts/bench_interface.py barge_in --audio Documentos/DOC_INTERFACE/bench_audio/voice_clean.wav --repeat 5 --resample`
- JSON: adicionar `--json out.json` para arquivar.
- Profiling: `py-spy record -o profile.svg -- python scripts/bench_interface.py stt --audio ...`

## Auto-benchmark (voz real via mic)
- `scripts/auto_voice_bench.py` grava amostras (clean/noise) e roda STT/VAD/endpointing.
- Ex.: `PYTHONPATH=. python scripts/auto_voice_bench.py --device <idx> --with-noise --output-dir Documentos/DOC_INTERFACE/bench_audio --phrase "oi jarvis teste automatico" --seconds 4`

## Baseline padronizado (clean/noise)
- STT (fixar modelo para comparar): `PYTHONPATH=. JARVIS_STT_MODEL=tiny python scripts/bench_interface.py stt --audio Documentos/DOC_INTERFACE/bench_audio/voice_clean.wav --repeat 5 --resample --json Documentos/DOC_INTERFACE/bench_audio/voice_clean.stt.<data>.json`
- VAD: `PYTHONPATH=. python scripts/bench_interface.py vad --audio Documentos/DOC_INTERFACE/bench_audio/voice_clean.wav --repeat 10 --resample --json .../voice_clean.vad.<data>.json`
- Endpointing: `PYTHONPATH=. python scripts/bench_interface.py endpointing --audio Documentos/DOC_INTERFACE/bench_audio/voice_clean.wav --repeat 10 --resample --json .../voice_clean.endpointing.<data>.json`
- EoS -> 1º áudio: `PYTHONPATH=. python scripts/bench_interface.py eos_to_first_audio --audio Documentos/DOC_INTERFACE/bench_audio/voice_clean.wav --text "ok" --repeat 5 --resample --json .../voice_clean.eos_to_first_audio.<data>.json`
- Atualize `bench_history.json` se quiser histórico.

## Limites e dicas
- Use os WAV de `Documentos/DOC_INTERFACE/bench_audio` para comparabilidade.
- Resultados variam por máquina; rode várias repetições e registre p50/p95.
- `barge_in` mede tempo de parada ao detectar voz durante TTS; exige `sounddevice`/`webrtcvad`.
- `stt_realtimestt` depende do backend vendorizado ou instalado; se ausente, marca indisponível.
