# Áudios de teste (voz)

Arquivos usados em testes/benchmarks manuais:
- `voice_clean.wav` / `voice_clean_16k.wav` (noisy-free)
- `voice_noise.wav` / `voice_noise_16k.wav` (com ruído)
- `comando_longo.wav` / `comando_longo_tv.wav` (frases longas)
- `oi_jarvis_clean.wav`, `oi_jarvis_tv.wav`, `oi_jarvis_tv_alta.wav` (saudações em ambientes diferentes)
- `ruido_puro.wav` (ruído puro), `sussurro.wav` (voz baixa)

Uso típico:
- Bench offline com `scripts/bench_interface.py` (usar versões 16 kHz ou `--resample`).
- Testes manuais sem microfone (`TESTES_VOZ_SEM_MICROFONE.MD`).
