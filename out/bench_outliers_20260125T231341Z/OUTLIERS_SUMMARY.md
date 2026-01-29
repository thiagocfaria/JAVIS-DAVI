# OUTLIERS_SUMMARY

- Cenário: eos_to_first_audio
- Repetições medidas: 200 (1 warmup separado)
- Áudio: Documentos/DOC_INTERFACE/bench_audio/voice_clean.wav
- Texto: ok

## Latência total (EoS -> 1º áudio)
- p50: 730.98 ms
- p95: 921.31 ms
- p99: 1050.12 ms
- média: 740.93 ms

## Quebra por estágio (p95)
- stt: avg 666.21 ms, p50 652.78 ms, p95 831.27 ms
- tts: avg 74.33 ms, p50 74.94 ms, p95 97.37 ms
- endpointing: avg 0.21 ms, p50 0.14 ms, p95 0.22 ms
- trim: avg 0.01 ms, p50 0.01 ms, p95 0.01 ms
- ack: avg 0.00 ms, p50 0.00 ms, p95 0.00 ms
- overhead: avg 0.17 ms, p50 0.12 ms, p95 0.28 ms

## Bottleneck
- Contagem de rodadas onde bottleneck=stt: 200 / 200

## Top 10 rodadas mais lentas
1) iter 0 — total 1111.71 ms | stt 1049.61 ms | tts_first_audio 61.54 ms | tts_total 677.26 ms
2) iter 149 — total 1050.18 ms | stt 943.00 ms | tts_first_audio 100.74 ms | tts_total 835.08 ms
3) iter 165 — total 1044.73 ms | stt 930.89 ms | tts_first_audio 113.62 ms | tts_total 862.58 ms
4) iter 192 — total 1000.55 ms | stt 898.60 ms | tts_first_audio 101.66 ms | tts_total 841.04 ms
5) iter 126 — total 968.37 ms | stt 880.42 ms | tts_first_audio 87.71 ms | tts_total 680.97 ms
6) iter 191 — total 965.20 ms | stt 850.15 ms | tts_first_audio 114.79 ms | tts_total 816.87 ms
7) iter 164 — total 945.20 ms | stt 864.16 ms | tts_first_audio 80.71 ms | tts_total 668.87 ms
8) iter 163 — total 930.29 ms | stt 831.46 ms | tts_first_audio 98.63 ms | tts_total 833.01 ms
9) iter 148 — total 929.87 ms | stt 832.36 ms | tts_first_audio 97.20 ms | tts_total 831.48 ms
10) iter 128 — total 921.41 ms | stt 834.12 ms | tts_first_audio 87.03 ms | tts_total 722.71 ms

## Notas
- Backend: whisper.cpp tiny (JARVIS_STT_MODEL=tiny); TTS Piper in-proc; warmup rodado antes do lote medido.
- Comando: PYTHONPATH=. JARVIS_STT_MODEL=tiny ./.venv/bin/python scripts/bench_interface.py eos_to_first_audio --audio Documentos/DOC_INTERFACE/bench_audio/voice_clean.wav --text "ok" --repeat 200 --resample --json bench.json
- Sem perf stat (binário perf não disponível).

## Hyperfine (50 runs, comando com repeat=1)
- Comando: `PYTHONPATH=. JARVIS_STT_MODEL=tiny ./.venv/bin/python scripts/bench_interface.py eos_to_first_audio --audio Documentos/DOC_INTERFACE/bench_audio/voice_clean.wav --text "ok" --repeat 1 --resample`
- p50: 11.10 s | p95: 11.85 s | p99: 13.09 s | média: 11.15 s (cada run recarrega modelo/config)
- Min/max: 10.10 s / 14.07 s
- Dump completo em `hyperfine.json` e log em `hyperfine.log`.
