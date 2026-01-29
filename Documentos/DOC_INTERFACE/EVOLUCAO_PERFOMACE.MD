# Evolução de Performance – Interface de Voz

Histórico curto dos principais marcos de latência/STT/TTS. Valores são p50/p95 quando disponíveis.

## Metas (produto)
- STT (EoS → texto): p95 0.8–1.2s.
- Voz percebida (EoS → 1º áudio): p95 0.9–1.6s.

## Linha do tempo resumida
- **12–13/01/2026 (baseline inicial)**  
  - STT `small` (default): p95 ~9–13s (silêncio/ruído).  
  - Endpointing offline: 390 ms (silêncio/TV).  
  - Conclusão: latência inaceitável; `small` descartado.

- **15/01/2026 (troca para `tiny`)**  
  - STT `tiny`: p95 ~2.2s (silêncio) / ~2.2s (ruído).  
  - VAD estável (~1 ms).  
  - Ganho ~4–5x vs `small`.

- **16/01/2026 (otimizações VAD/STT/TTS)**  
  - STT default melhorou ~30% vs rodada anterior; VAD -50%; TTS ~0.5 ms.  
  - Endpointing mantido em 390 ms.

- **18/01/2026 (eos_to_first_audio benchmark + preset tiny)**  
  - Warm baseline: p50 1.89s / p95 2.54s (EoS → 1º áudio, tiny).  
  - PRIORIDADE 1 (trim + preset tiny): p50 0.50s / p95 1.49s.  
  - Piper CLI (processo externo) piorou: p50 2.64s / p95 3.39s.  
  - Piper in-proc (modelo em memória) + threads 1/1: TTFA warm ~0.07s; EoS→1º áudio p50 0.59s / p95 2.11s.  
  - Fase 1 (ack) adicionada: overhead ~0 ms; melhora percepção sem usar espeak.

- **23–24/01/2026 (Etapa 5 – backend plugável whisper.cpp)**  
  - Primeiras medições indicaram speedup com whisper.cpp, mas **regressões apareceram depois** com pywhispercpp.  
  - GPU não validada (resultados CPU).
- **28/01/2026 (baseline v2 e regressão whisper_cpp)**  
  - **faster_whisper (tiny):** p95 **~1.19s** (repeat=30) → OURO no limite.  
  - **whisper_cpp (tiny):** p95 **~10.0s** (repeat=30) → **REGRESSÃO**; backend bloqueado.  
  - CPU% ainda precisa de validação estável (psutil/ cálculo).

### Evolução (EoS → 1º áudio, p95) – visão rápida
```
13/01  small           ~13s  ██████████████████████████
15/01  tiny             ~2.2s ████
18/01  warm baseline    ~2.5s █████
18/01  PRIORIDADE 1     ~1.5s ███
18/01  Piper in-proc    ~2.1s ████
Plan/Gold (fw v2)       ~1.19s ██
```
Referência atual (PLANO_OURO_INTERFACE.md): `eos_to_first_audio_ms p95 = 1190ms` (margem de 10ms dentro da meta ouro).

## Estado atual (resumo)
- Backend padrão: `faster_whisper` (tiny). **whisper_cpp bloqueado** por regressão.  
- TTS: Piper in-proc, streaming, cache de frases curtas, TTFA warm ~0.05–0.08s (CPU-safe 1/1 threads).  
- Barge-in, fase 1 e métricas (`voice_stage_metrics`) disponíveis para medir percepção.

## Como medir hoje
- Bench principal: `PYTHONPATH=. python scripts/bench_interface.py eos_to_first_audio --audio Documentos/DOC_INTERFACE/bench_audio/voice_clean.wav --text "ok" --repeat 5 --resample`
- STT isolado: `... bench_interface.py stt --audio ... --repeat 5 --resample`
- TTS isolado: `... bench_interface.py tts --text "ok" --repeat 5`
- Registrar resultados em `bench_history.json` se precisar de trilha longa.***
