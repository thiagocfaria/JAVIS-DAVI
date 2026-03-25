# Testes realizados da interface

## 2026-01-18 (eos_to_first_audio + suite completa)
- Teste: suite completa `testes/`
- Comando: `PYTHONPATH=. ./.venv/bin/python -m pytest -q testes/`
- Resultado: PASS (255 passed, 4 warnings)
- Observacao: warning do `pynput/Xlib` em ambiente sem display e warnings de deps (`webrtcvad`, `resemblyzer`, `audioop`).

- Teste: sanidade (auto-config + TTS + preflight probe)
- Comando: `PYTHONPATH=. ./.venv/bin/python -m pytest -q testes/test_tts_interface.py testes/test_preflight_probe.py testes/test_voice_profile_autoconfig.py`
- Resultado: PASS (21 passed, 3 warnings)

- Preflight (voz)
- Comando: `PYTHONPATH=. ./.venv/bin/python -m jarvis.app --preflight --preflight-profile voice`
- Resultado: PASS (6 OK, 0 WARN, 0 FAIL)

### Roteiro rapido (rodar Jarvis real em --voice com perfil CPU-safe)
Objetivo: validar em uso real (microfone/saida de audio) com **voz humanizada** + folga de CPU.

1) Ajuste `.env` (base): ver perfil “PRODUCAO / CPU-SAFE” em `.env.example`.
2) Rode:
   - `PYTHONPATH=. JARVIS_DRY_RUN=0 ./.venv/bin/python -m jarvis.app --voice`
3) Medir CPU (manual):
   - Abra `top`/`htop` e observe o processo do Python durante 2–3 interacoes.
4) Validar telemetria (se estiver usando `JARVIS_DATA_DIR`):
   - Procure eventos `voice_stage_metrics` em `storage/.../events.jsonl`.

- Benchmark: numero unico (EoS -> primeiro audio)
- Comando: `PYTHONPATH=. JARVIS_STT_MODEL=tiny ./.venv/bin/python scripts/bench_interface.py eos_to_first_audio --audio Documentos/DOC_INTERFACE/bench_audio/voice_clean.wav --text "ok" --repeat 3 --resample`
- Resultado (resumo):
  - `eos_to_first_audio_ms_p50`: 2643 ms
  - `eos_to_first_audio_ms_p95`: 3209 ms

- Benchmark: numero unico (EoS -> primeiro audio, warm baseline)
- Comando: `PYTHONPATH=. JARVIS_STT_MODEL=tiny ./.venv/bin/python scripts/bench_interface.py eos_to_first_audio --audio Documentos/DOC_INTERFACE/bench_audio/voice_clean.wav --text "ok" --repeat 5 --resample`
- Resultado (resumo):
  - `eos_to_first_audio_ms_p50`: 1888 ms
  - `eos_to_first_audio_ms_p95`: 2543 ms

- Benchmark: numero unico (EoS -> primeiro audio, apos PRIORIDADE 1)
- Comando: `PYTHONPATH=. JARVIS_STT_MODEL=tiny ./.venv/bin/python scripts/bench_interface.py eos_to_first_audio --audio Documentos/DOC_INTERFACE/bench_audio/voice_clean.wav --text "ok" --repeat 20 --resample`
- Resultado (resumo):
  - `eos_to_first_audio_ms_p50`: 500 ms
  - `eos_to_first_audio_ms_p95`: 1492 ms

- Benchmark: numero unico (EoS -> primeiro audio, re-run apos novas mudancas)
- Comando: `PYTHONPATH=. JARVIS_STT_MODEL=tiny ./.venv/bin/python scripts/bench_interface.py eos_to_first_audio --audio Documentos/DOC_INTERFACE/bench_audio/voice_clean.wav --text "ok" --repeat 20 --resample`
- Resultado (resumo):
  - `eos_to_first_audio_ms_p50`: 661 ms
  - `eos_to_first_audio_ms_p95`: 1600 ms

- Benchmark: TTS TTFA (baseline, espeak-ng)
- Comando: `PYTHONPATH=. ./.venv/bin/python scripts/bench_interface.py tts --text "ok" --repeat 5`
- Resultado (resumo):
  - `tts_engine`: espeak-ng
  - `tts_first_audio_ms_p50`: 0.41 ms
  - `tts_first_audio_ms_p95`: 0.60 ms

- Benchmark: TTS TTFA (apos `JARVIS_TTS_ENGINE`, espeak-ng)
- Comando: `PYTHONPATH=. ./.venv/bin/python scripts/bench_interface.py tts --text "ok" --repeat 5`
- Resultado (resumo):
  - `tts_engine`: espeak-ng
  - `tts_first_audio_ms_p50`: 0.50 ms
  - `tts_first_audio_ms_p95`: 0.60 ms

- Benchmark: TTS TTFA (re-run, espeak-ng)
- Comando: `PYTHONPATH=. ./.venv/bin/python scripts/bench_interface.py tts --text "ok" --repeat 5`
- Resultado (resumo):
  - `tts_engine`: espeak-ng
  - `tts_first_audio_ms_p50`: 0.54 ms
  - `tts_first_audio_ms_p95`: 1.38 ms

- Check: deps de TTS (binarios)
- Comando: `PYTHONPATH=. ./.venv/bin/python -c "from jarvis.interface.saida.tts import check_tts_deps; print(check_tts_deps())"`
- Resultado: `{'piper': True, 'espeak-ng': True, 'aplay': True}`
- Observacao: Piper binario esta disponivel via `.venv/bin/piper`, mas o modelo `.onnx` ainda precisa estar presente em `JARVIS_PIPER_MODELS_DIR` para `tts_engine=piper` funcionar.

- Benchmark: TTS (piper strict, sem modelo local) — validacao do “nao cair para robotico”
- Comando: `PYTHONPATH=. JARVIS_TTS_ENGINE=piper JARVIS_TTS_ENGINE_STRICT=1 JARVIS_PIPER_MODELS_DIR=storage/models/piper ./.venv/bin/python scripts/bench_interface.py tts --text "ok" --repeat 3`
- Resultado (resumo):
  - `tts_engine`: none
- Observacao: com `strict=1`, o Jarvis **nao** faz fallback para `espeak-ng` (fica silencioso) se o modelo local do Piper nao estiver disponivel.

- Benchmark: TTS (Piper funcionando, modelo local no repo)
- Comando: `PYTHONPATH=. JARVIS_TTS_ENGINE=piper JARVIS_TTS_ENGINE_STRICT=1 JARVIS_PIPER_MODELS_DIR=storage/models/piper JARVIS_PIPER_VOICE=pt_BR-faber-medium JARVIS_TTS_STREAMING=1 JARVIS_TTS_VOLUME=0 ./.venv/bin/python scripts/bench_interface.py tts --text "ok" --repeat 3`
- Resultado (resumo):
  - `tts_engine`: piper
  - `tts_first_audio_ms_p50`: 1627 ms
  - `tts_first_audio_ms_p95`: 2052 ms
  - Observacao: este resultado era do caminho CLI antigo (processo `piper` por fala), antes do backend in-proc.

- Benchmark: TTS (Piper in-proc / backend Python + limite de threads)
- Comando: `PYTHONPATH=. JARVIS_TTS_ENGINE=piper JARVIS_TTS_ENGINE_STRICT=1 JARVIS_PIPER_BACKEND=python JARVIS_PIPER_INTRA_OP_THREADS=2 JARVIS_PIPER_INTER_OP_THREADS=1 JARVIS_PIPER_MODELS_DIR=storage/models/piper JARVIS_PIPER_VOICE=pt_BR-faber-medium JARVIS_TTS_STREAMING=1 JARVIS_TTS_ACK_EARCON=0 JARVIS_TTS_VOLUME=0 JARVIS_TTS_WARMUP=1 JARVIS_TTS_WARMUP_BLOCKING=1 ./.venv/bin/python scripts/bench_interface.py tts --text "ok" --repeat 10`
- Resultado (resumo):
  - `tts_engine`: piper
  - `tts_first_audio_ms_p50`: 48.87 ms
  - `tts_first_audio_ms_p95`: 62.06 ms
  - CPU (psutil): `psutil_cpu_percent` ~ 180%

- Benchmark: TTS (Piper in-proc, CPU-safe 1/1)
- Comando: `PYTHONPATH=. JARVIS_TTS_ENGINE=piper JARVIS_TTS_ENGINE_STRICT=1 JARVIS_PIPER_BACKEND=python JARVIS_PIPER_INTRA_OP_THREADS=1 JARVIS_PIPER_INTER_OP_THREADS=1 JARVIS_PIPER_MODELS_DIR=storage/models/piper JARVIS_PIPER_VOICE=pt_BR-faber-medium JARVIS_TTS_STREAMING=1 JARVIS_TTS_ACK_EARCON=0 JARVIS_TTS_VOLUME=0 JARVIS_TTS_WARMUP=1 JARVIS_TTS_WARMUP_BLOCKING=1 ./.venv/bin/python scripts/bench_interface.py tts --text "ok" --repeat 10`
- Resultado (resumo):
  - `tts_engine`: piper
  - `tts_first_audio_ms_p50`: 74.14 ms
  - `tts_first_audio_ms_p95`: 79.51 ms
  - CPU (psutil): `psutil_cpu_percent` ~ 101%

- Check: TTS (Piper warm dentro do mesmo processo, 8 falas seguidas)
- Comando: `PYTHONPATH=. JARVIS_TTS_ENGINE=piper JARVIS_TTS_ENGINE_STRICT=1 JARVIS_PIPER_BACKEND=python JARVIS_PIPER_INTRA_OP_THREADS=2 JARVIS_PIPER_INTER_OP_THREADS=1 JARVIS_PIPER_MODELS_DIR=storage/models/piper JARVIS_PIPER_VOICE=pt_BR-faber-medium JARVIS_TTS_STREAMING=1 JARVIS_TTS_ACK_EARCON=0 JARVIS_TTS_VOLUME=0 ./.venv/bin/python - <<'PY'\nfrom types import SimpleNamespace\nfrom jarvis.interface.saida.tts import TextToSpeech\n\ntts = TextToSpeech(SimpleNamespace(tts_mode='local'))\nvalues = []\nfor _ in range(8):\n    tts.speak('ok')\n    values.append(float(tts.get_last_metrics().get('tts_first_audio_ms') or 0.0))\nprint({'tts_first_audio_ms_per_call': values})\nPY`
- Resultado (resumo):
  - `tts_first_audio_ms_per_call`: `[1373.6, 52.9, 42.9, 45.9, 74.9, 53.3, 43.2, 40.0]` (ms)

- Benchmark: TTS (Piper + modo hibrido ack/earcon)
- Comando: `PYTHONPATH=. JARVIS_TTS_ENGINE=piper JARVIS_TTS_ENGINE_STRICT=1 JARVIS_PIPER_MODELS_DIR=storage/models/piper JARVIS_PIPER_VOICE=pt_BR-faber-medium JARVIS_TTS_STREAMING=1 JARVIS_TTS_ACK_EARCON=1 JARVIS_TTS_ACK_TIMEOUT_MS=250 JARVIS_TTS_VOLUME=0 ./.venv/bin/python scripts/bench_interface.py tts --text "ok" --repeat 5`
- Resultado (resumo):
  - `tts_engine`: piper
  - `tts_ack_ms_p50`: 251 ms
  - `tts_first_audio_ms_p50`: 1686 ms

- Benchmark: numero unico (EoS -> primeiro audio, com Piper)
- Comando: `PYTHONPATH=. JARVIS_STT_MODEL=tiny JARVIS_TTS_ENGINE=piper JARVIS_TTS_ENGINE_STRICT=1 JARVIS_PIPER_MODELS_DIR=storage/models/piper JARVIS_PIPER_VOICE=pt_BR-faber-medium JARVIS_TTS_STREAMING=1 JARVIS_TTS_VOLUME=0 ./.venv/bin/python scripts/bench_interface.py eos_to_first_audio --audio Documentos/DOC_INTERFACE/bench_audio/voice_clean.wav --text "ok" --repeat 20 --resample`
- Resultado (resumo):
  - `eos_to_first_audio_ms_p50`: 2638 ms
  - `eos_to_first_audio_ms_p95`: 3394 ms
  - `tts_first_audio_ms_p50`: 1968 ms

- Benchmark: numero unico (EoS -> ack, modo hibrido; e EoS -> 1o audio do Piper)
- Comando: `PYTHONPATH=. JARVIS_STT_MODEL=tiny JARVIS_TTS_ENGINE=piper JARVIS_TTS_ENGINE_STRICT=1 JARVIS_PIPER_MODELS_DIR=storage/models/piper JARVIS_PIPER_VOICE=pt_BR-faber-medium JARVIS_TTS_STREAMING=1 JARVIS_TTS_ACK_EARCON=1 JARVIS_TTS_ACK_TIMEOUT_MS=250 JARVIS_TTS_VOLUME=0 ./.venv/bin/python scripts/bench_interface.py eos_to_first_audio --audio Documentos/DOC_INTERFACE/bench_audio/voice_clean.wav --text "ok" --repeat 20 --resample`
- Resultado (resumo):
  - `eos_to_ack_ms_p50`: 848 ms
  - `eos_to_ack_ms_p95`: 2278 ms
  - `eos_to_first_audio_ms_p50`: 2473 ms
  - `eos_to_first_audio_ms_p95`: 3712 ms

- Benchmark: numero unico (EoS -> primeiro audio, com Piper in-proc + warmup blocking + fase 1)
- Comando: `PYTHONPATH=. JARVIS_STT_MODEL=tiny JARVIS_TTS_ENGINE=piper JARVIS_TTS_ENGINE_STRICT=1 JARVIS_PIPER_BACKEND=python JARVIS_PIPER_INTRA_OP_THREADS=1 JARVIS_PIPER_INTER_OP_THREADS=1 JARVIS_PIPER_MODELS_DIR=storage/models/piper JARVIS_PIPER_VOICE=pt_BR-faber-medium JARVIS_TTS_STREAMING=1 JARVIS_TTS_ACK_EARCON=0 JARVIS_TTS_VOLUME=0 JARVIS_TTS_WARMUP=1 JARVIS_TTS_WARMUP_BLOCKING=1 JARVIS_TTS_WARMUP_TEXT=ola JARVIS_BENCH_PHASE1=1 ./.venv/bin/python scripts/bench_interface.py eos_to_first_audio --audio Documentos/DOC_INTERFACE/bench_audio/voice_clean.wav --text "ok" --repeat 10 --resample`
- Resultado (resumo):
  - `eos_to_first_audio_ms_p50`: 588.08 ms
  - `eos_to_first_audio_ms_p95`: 2108.33 ms
  - `tts_first_audio_ms_p50`: 76.72 ms
  - `eos_to_phase1_ms_p50`: 0.032 ms
  - Observacao: o ack interno do TTS fica desnecessario quando o Piper começa rapido (warm). Para “sinal de vida”, use `JARVIS_VOICE_PHASE1=1` + `JARVIS_TTS_ACK_PHRASE` se quiser.

- Benchmark: ack falado (phrase) em vez de beep (validacao)
- Comando: `PYTHONPATH=. JARVIS_TTS_ENGINE=piper JARVIS_TTS_ENGINE_STRICT=1 JARVIS_PIPER_MODELS_DIR=storage/models/piper JARVIS_PIPER_VOICE=pt_BR-faber-medium JARVIS_TTS_STREAMING=1 JARVIS_TTS_ACK_TIMEOUT_MS=250 JARVIS_TTS_ACK_PHRASE="Entendi. Já vou responder." JARVIS_TTS_ACK_PHRASE_WARMUP_BLOCKING=1 JARVIS_TTS_VOLUME=0 ./.venv/bin/python scripts/bench_interface.py tts --text "ok" --repeat 3`
- Resultado (resumo):
  - `tts_ack_ms_p50`: 251 ms
  - `tts_first_audio_ms_p50`: 1482 ms

- Benchmark: numero unico (EoS -> ack falado)
- Comando: `PYTHONPATH=. JARVIS_STT_MODEL=tiny JARVIS_TTS_ENGINE=piper JARVIS_TTS_ENGINE_STRICT=1 JARVIS_PIPER_MODELS_DIR=storage/models/piper JARVIS_PIPER_VOICE=pt_BR-faber-medium JARVIS_TTS_STREAMING=1 JARVIS_TTS_ACK_TIMEOUT_MS=250 JARVIS_TTS_ACK_PHRASE="Entendi. Já vou responder." JARVIS_TTS_ACK_PHRASE_WARMUP_BLOCKING=1 JARVIS_TTS_VOLUME=0 ./.venv/bin/python scripts/bench_interface.py eos_to_first_audio --audio Documentos/DOC_INTERFACE/bench_audio/voice_clean.wav --text "ok" --repeat 10 --resample`
- Resultado (resumo):
  - `eos_to_ack_ms_p50`: 775 ms
  - `eos_to_ack_ms_p95`: 2658 ms

- Benchmark: offline (EoS -> 1o audio) com fase 1 humanizada (phase1 phrase) + perfil CPU-safe
- Comando: `PYTHONPATH=. JARVIS_STT_MODEL=tiny JARVIS_BENCH_PHASE1=1 JARVIS_TTS_ENGINE=piper JARVIS_TTS_ENGINE_STRICT=1 JARVIS_TTS_ACK_PHRASE="Entendi. Já vou responder." JARVIS_TTS_ACK_PHRASE_WARMUP_BLOCKING=1 JARVIS_PIPER_MODELS_DIR=storage/models/piper JARVIS_PIPER_VOICE=pt_BR-faber-medium JARVIS_PIPER_BACKEND=python JARVIS_PIPER_INTRA_OP_THREADS=1 JARVIS_PIPER_INTER_OP_THREADS=1 JARVIS_TTS_STREAMING=1 JARVIS_TTS_CACHE=1 JARVIS_TTS_WARMUP=1 JARVIS_TTS_WARMUP_BLOCKING=1 ./.venv/bin/python scripts/bench_interface.py eos_to_first_audio --audio Documentos/DOC_INTERFACE/bench_audio/voice_clean.wav --text "ok" --repeat 10 --resample`
- Resultado (resumo):
  - `eos_to_first_audio_ms_p50`: 2491 ms
  - `eos_to_first_audio_ms_p95`: 4443 ms
  - `eos_to_phase1_ms_p50`: 0.029 ms
  - `phase1_source`: phase1_phrase

- Benchmark: Piper streaming chunk (comparacao 1024 vs 4096)
- Comandos:
  - `PYTHONPATH=. JARVIS_TTS_ENGINE=piper JARVIS_TTS_ENGINE_STRICT=1 JARVIS_PIPER_MODELS_DIR=storage/models/piper JARVIS_PIPER_VOICE=pt_BR-faber-medium JARVIS_TTS_STREAMING=1 JARVIS_TTS_ACK_EARCON=0 JARVIS_TTS_VOLUME=0 JARVIS_TTS_STREAM_CHUNK_BYTES=1024 ./.venv/bin/python scripts/bench_interface.py tts --text "ok" --repeat 10`
  - `PYTHONPATH=. JARVIS_TTS_ENGINE=piper JARVIS_TTS_ENGINE_STRICT=1 JARVIS_PIPER_MODELS_DIR=storage/models/piper JARVIS_PIPER_VOICE=pt_BR-faber-medium JARVIS_TTS_STREAMING=1 JARVIS_TTS_ACK_EARCON=0 JARVIS_TTS_VOLUME=0 JARVIS_TTS_STREAM_CHUNK_BYTES=4096 ./.venv/bin/python scripts/bench_interface.py tts --text "ok" --repeat 10`
- Resultado (resumo):
  - chunk=1024: `tts_first_audio_ms_p50`: 1855 ms / `tts_first_audio_ms_p95`: 2043 ms
  - chunk=4096: `tts_first_audio_ms_p50`: 1789 ms / `tts_first_audio_ms_p95`: 1969 ms (**melhor aqui**)

- Benchmark: cache de frases curtas (Piper)
- Comando: `PYTHONPATH=. JARVIS_TTS_ENGINE=piper JARVIS_TTS_ENGINE_STRICT=1 JARVIS_PIPER_MODELS_DIR=storage/models/piper JARVIS_PIPER_VOICE=pt_BR-faber-medium JARVIS_TTS_STREAMING=1 JARVIS_TTS_STREAM_CHUNK_BYTES=4096 JARVIS_TTS_CACHE=1 JARVIS_TTS_ACK_EARCON=0 JARVIS_TTS_VOLUME=0 ./.venv/bin/python -c "from types import SimpleNamespace; from jarvis.interface.saida.tts import TextToSpeech; tts=TextToSpeech(SimpleNamespace(tts_mode='local')); t='Entendi. Ja vou responder.'; tts.speak(t); m1=tts.get_last_metrics(); tts.speak(t); m2=tts.get_last_metrics(); keys=['tts_engine','tts_first_audio_ms','tts_ack_source']; print('run1', {k:m1.get(k) for k in keys}); print('run2', {k:m2.get(k) for k in keys})"`
- Resultado:
  - run1: `tts_engine='piper'`, `tts_first_audio_ms` ~ 1441 ms (cache miss)
  - run2: `tts_engine='piper'`, `tts_first_audio_ms` = 0 ms, `tts_ack_source='cache'` (cache hit)

- Benchmark: fase 1 (ack imediato do orchestrator) — overhead da chamada
- Comando: `PYTHONPATH=. JARVIS_TTS_ENGINE=piper JARVIS_TTS_ENGINE_STRICT=1 JARVIS_PIPER_MODELS_DIR=storage/models/piper JARVIS_PIPER_VOICE=pt_BR-faber-medium JARVIS_TTS_STREAMING=1 JARVIS_TTS_VOLUME=0 JARVIS_TTS_ACK_PHRASE="Entendi. Já vou responder." JARVIS_TTS_ACK_PHRASE_WARMUP_BLOCKING=1 ./.venv/bin/python -c "import statistics, time; from types import SimpleNamespace; from jarvis.interface.saida.tts import TextToSpeech; tts=TextToSpeech(SimpleNamespace(tts_mode='local')); values=[]; \nfor _ in range(50):\n s=time.perf_counter(); tts.play_phase1_ack(); e=time.perf_counter(); values.append((e-s)*1000.0)\nprint({'repeat':len(values),'call_ms_p50':statistics.median(values),'call_ms_p95':statistics.quantiles(values,n=20)[-1]})\nprint('tts_metrics', {k: tts.get_last_metrics().get(k) for k in ('tts_engine','tts_first_audio_ms','tts_ack_source')})\"`
- Resultado (resumo):
  - `call_ms_p50`: 0.003 ms
  - `call_ms_p95`: 0.009 ms
  - `tts_ack_source`: `phase1_phrase`

- Benchmark: auto-chunk de texto longo (Piper) — **nao recomendado neste CPU**
- Texto: "Isso e um teste bem longo..." (2+ frases)
- Comandos:
  - Sem auto-chunk: `PYTHONPATH=. JARVIS_TTS_ENGINE=piper JARVIS_TTS_ENGINE_STRICT=1 JARVIS_PIPER_MODELS_DIR=storage/models/piper JARVIS_PIPER_VOICE=pt_BR-faber-medium JARVIS_TTS_STREAMING=1 JARVIS_TTS_VOLUME=0 JARVIS_TTS_CHUNKING=0 JARVIS_TTS_AUTO_CHUNK_LONG_TEXT=0 ./.venv/bin/python scripts/bench_interface.py tts --text "<texto>" --repeat 5`
  - Com auto-chunk: `PYTHONPATH=. JARVIS_TTS_ENGINE=piper JARVIS_TTS_ENGINE_STRICT=1 JARVIS_PIPER_MODELS_DIR=storage/models/piper JARVIS_PIPER_VOICE=pt_BR-faber-medium JARVIS_TTS_STREAMING=1 JARVIS_TTS_VOLUME=0 JARVIS_TTS_CHUNKING=0 JARVIS_TTS_AUTO_CHUNK_LONG_TEXT=1 JARVIS_TTS_AUTO_CHUNK_MIN_CHARS=120 ./.venv/bin/python scripts/bench_interface.py tts --text "<texto>" --repeat 5`
- Resultado (resumo):
  - Sem auto-chunk: `tts_first_audio_ms_p50`: 1868 ms / `tts_first_audio_ms_p95`: 2068 ms
  - Com auto-chunk: `tts_first_audio_ms_p50`: 2052 ms / `tts_first_audio_ms_p95`: 2418 ms (piorou)

- Benchmark: numero unico com fase 1 (offline; mede `eos_to_phase1_ms`)
- Comando: `PYTHONPATH=. JARVIS_STT_MODEL=tiny JARVIS_BENCH_PHASE1=1 JARVIS_VOICE_PHASE1=1 JARVIS_TTS_ENGINE=piper JARVIS_TTS_ENGINE_STRICT=1 JARVIS_PIPER_MODELS_DIR=storage/models/piper JARVIS_PIPER_VOICE=pt_BR-faber-medium JARVIS_TTS_STREAMING=1 JARVIS_TTS_STREAM_CHUNK_BYTES=4096 JARVIS_TTS_CACHE=0 JARVIS_TTS_ACK_PHRASE="Entendi. Já vou responder." JARVIS_TTS_ACK_PHRASE_WARMUP_BLOCKING=1 JARVIS_TTS_VOLUME=0 ./.venv/bin/python scripts/bench_interface.py eos_to_first_audio --audio Documentos/DOC_INTERFACE/bench_audio/voice_clean.wav --text "ok" --repeat 10 --resample`
- Resultado (resumo):
  - `eos_to_phase1_ms_p50`: 0.025 ms
  - `eos_to_phase1_ms_p95`: 0.034 ms
  - `eos_to_ack_ms_p50`: 899 ms
  - `eos_to_ack_ms_p95`: 2646 ms
  - `eos_to_first_audio_ms_p50`: 2482 ms
  - `eos_to_first_audio_ms_p95`: 4070 ms

- Validacao: campo `eos_to_first_audio_ms` presente no log de voz real (`voice_stage_metrics`)
- Comando (sem prompts, headless): `PYTHONPATH=. JARVIS_DISABLE_DOTENV=1 JARVIS_DATA_DIR=storage/tmp_jarvis_data3 JARVIS_REQUIRE_APPROVAL=0 JARVIS_BROWSER_AI_ENABLED=0 JARVIS_MAX_GUIDANCE_ATTEMPTS=0 JARVIS_DRY_RUN=1 JARVIS_VOICE_MAX_SECONDS=6 JARVIS_STT_MODEL=tiny ./.venv/bin/python -m jarvis.app --voice`
- Resultado: evento `voice_stage_metrics` registrado em `storage/tmp_jarvis_data3/events.jsonl` com o campo `eos_to_first_audio_ms` (pode ser `null` sem endpoint de fala).

## 2026-01-17 (suite completa + checks)
- Teste: suite completa `testes/`
- Comando: `PYTHONPATH=. pytest -q`
- Resultado: PASS (240 passed, 13 skipped, 1 warning)
- Observacao: `ruff` e `black` nao encontrados no ambiente (checks falharam por falta de binario).

## 2026-01-17 (checks com .venv)
- Ruff: `./.venv/bin/ruff check .`
  - Resultado: PASS
- Black: `./.venv/bin/black --check .`
  - Resultado: FAIL (4 arquivos precisariam de formatacao: `jarvis/interface/entrada/emocao.py`, `jarvis/interface/entrada/stt.py`, `jarvis/interface/saida/tts.py`, `testes/test_tts_verification.py`)
- Pytest: `./.venv/bin/pytest -q`
  - Resultado: PASS (254 passed, 3 warnings)

## 2026-01-17 (baseline 16k - speechbrain sample, deps ausentes)
- Benchmark: STT/VAD/endpointing/Speaker/TTS (WAV 16k)
- Comandos:
  - `PYTHONPATH=. python scripts/bench_interface.py stt --audio jarvis/REPOSITORIOS_CLONAR/speechbrain/tests/samples/ASR/spk1_snt2.wav --repeat 5`
  - `PYTHONPATH=. python scripts/bench_interface.py vad --audio jarvis/REPOSITORIOS_CLONAR/speechbrain/tests/samples/ASR/spk1_snt2.wav --repeat 10`
  - `PYTHONPATH=. python scripts/bench_interface.py endpointing --audio jarvis/REPOSITORIOS_CLONAR/speechbrain/tests/samples/ASR/spk1_snt2.wav --repeat 10`
  - `PYTHONPATH=. python scripts/bench_interface.py tts --text "ola" --repeat 3`
  - `PYTHONPATH=. python scripts/bench_interface.py speaker --audio jarvis/REPOSITORIOS_CLONAR/speechbrain/tests/samples/ASR/spk1_snt2.wav --repeat 5`
- Resultado (resumo):
  - STT: avg 3.97 ms (p50 3.93 / p95 4.47), cpu_time_s_avg 0.00398, rss_kb 25780
  - VAD: avg 3.98 ms (p50 3.77 / p95 4.92), cpu_time_s_avg 0.00399, rss_kb 25668
  - Endpointing: FALHOU (webrtcvad ausente)
  - Speaker: avg 0.005 ms (p50 0.003 / p95 0.018), cpu_time_s_avg 0.000008, rss_kb 23628
  - TTS: avg 0.63 ms (p50 0.55 / p95 1.09), cpu_time_s_avg 0.00039, rss_kb 20928
- Observacao: deps ausentes no ambiente (`faster-whisper`, `webrtcvad`, `numpy`, `scipy`), resultados nao sao representativos.

## 2026-01-17 (baseline voz real curta - voice_clean)
- Benchmark: STT/VAD/endpointing/Speaker/TTS (audio real curto)
- Comandos:
  - `PYTHONPATH=. .venv/bin/python scripts/bench_interface.py stt --audio Documentos/DOC_INTERFACE/bench_audio/voice_clean.wav --repeat 3 --resample --json /tmp/bench_stt.json`
  - `PYTHONPATH=. .venv/bin/python scripts/bench_interface.py vad --audio Documentos/DOC_INTERFACE/bench_audio/voice_clean.wav --repeat 5 --resample --json /tmp/bench_vad.json`
  - `PYTHONPATH=. .venv/bin/python scripts/bench_interface.py endpointing --audio Documentos/DOC_INTERFACE/bench_audio/voice_clean.wav --repeat 5 --resample --json /tmp/bench_endpointing.json`
  - `PYTHONPATH=. JARVIS_SPK_VERIFY=1 .venv/bin/python scripts/bench_interface.py speaker --audio Documentos/DOC_INTERFACE/bench_audio/voice_clean.wav --repeat 3 --resample --json /tmp/bench_speaker.json`
  - `PYTHONPATH=. .venv/bin/python scripts/bench_interface.py tts --text "ola jarvis, teste de desempenho de voz" --repeat 3 --json /tmp/bench_tts.json`
- Resultado (resumo):
  - STT: avg 5692.64 ms (p50 5926.83 / p95 6899.97), cpu_time_s_avg 15.77, rss_kb 1264960
  - VAD: avg 0.69 ms (p50 0.66 / p95 0.84), cpu_time_s_avg 0.0007, rss_kb 608536
  - Endpointing: avg 0.08 ms (p50 0.08 / p95 0.11), endpoint_ms 390
  - Speaker: avg 969.22 ms (p50 138.81 / p95 4624.36), cpu_time_s_avg 1.45, rss_kb 727872
  - TTS: avg 0.53 ms (p50 0.46 / p95 0.94), cpu_time_s_avg 0.00031, rss_kb 101732
- Registro historico: `Documentos/DOC_INTERFACE/bench_history.json` (baseline_2026-01-17_voice_clean)

## 2026-01-16 (correcao bugs TTS - verificacao)
- Teste: verificacao pós-correcao de bugs críticos do TTS
- Data/hora: 2026-01-16 23:44 (apos correcao de race conditions e processos orfaos)
- Comando: `PYTHONPATH=. python testes/test_tts_verification.py`
- Resultado: PASS
  - ✓ Nenhum processo piper orfao encontrado
  - ✓ Nenhum processo aplay orfao encontrado
  - ✓ Chunking com lock funcionando corretamente (3 chamadas simultaneas processadas sem race conditions)
- Bugs corrigidos:
  1. **Race condition no cleanup de processos**: `finally` agora so fecha stdin quando nao ha interrupcao/excecao
  2. **Processos orfaos em excecoes**: processos sao terminados antes de relancar excecao
  3. **Race condition no chunking**: lock externo no loop de chunks + mudanca para `RLock()` para permitir reentrancia
- Arquivo de teste: `testes/test_tts_verification.py`
- Observacao: Teste criado para validar correcoes de bugs criticos identificados durante debug do sistema de interface entrada/saida.

## 2026-01-16 (migracao interface - validacao)
- Testes (entrada): `PYTHONPATH=. pytest -q testes/test_stt_flow.py testes/test_vad_streaming_interface.py testes/test_preflight_headless.py testes/test_chat_ui_interface.py testes/test_gui_panel_interface.py testes/test_shortcut_interface.py testes/test_speaker_verify_interface.py`
- Resultado: PASS (44 passed, 5 skipped, 1 warning)

- Teste (TTS): `PYTHONPATH=. pytest -q testes/test_tts_interface.py`
- Resultado: PASS (13 passed, 1 warning)

- Benchmark: TTS streaming+chunking com Piper (TTFA real)
- Comando: `PATH=/home/u/Documentos/Jarvis/.venv/bin:$PATH PYTHONPATH=. JARVIS_TTS_STREAMING=1 JARVIS_TTS_CHUNKING=1 .venv/bin/python scripts/bench_interface.py tts --text "ola jarvis, teste de desempenho de voz" --repeat 3 --json Documentos/DOC_INTERFACE/bench_audio/tts.2026-01-16_interface_refactor_piper.json`
- Resultado (resumo):
  - Latencia total: 4199.41 ms (p50 4051.69 / p95 5073.97)
  - TTFA: 1736.06 ms (p50 1671.87 / p95 2240.70)
  - cpu_time_s_avg 0.03722, rss_kb 103460
- Observacao: TTFA mantido/melhorado apos migracao para `jarvis/interface` (sem regressao percebida).

## 2026-01-16 (tts streaming - TTFA com Piper)
- Teste: suite completa `testes/`
- Data/hora: 2026-01-16 10:03 (apos instalacao do Piper e modelos PT-BR)
- Comando: `PYTHONPATH=. .venv/bin/pytest -q testes/`
- Resultado: PASS (245 passed, 3 warnings)

- Instalacao: Piper instalado via `pip install piper-tts`; modelo PT-BR baixado (`pt_BR-faber-medium.onnx`)

- Benchmark: TTS comparativo com Piper (baseline vs streaming vs streaming+chunking)
- Data/hora: 2026-01-16 10:03
- Comandos:
  - `PYTHONPATH=. python scripts/bench_interface.py tts --text "ola jarvis, teste de desempenho de voz" --repeat 5 --json Documentos/DOC_INTERFACE/bench_audio/tts.2026-01-16_piper_baseline.json`
  - `PYTHONPATH=. JARVIS_TTS_STREAMING=1 python scripts/bench_interface.py tts --text "ola jarvis, teste de desempenho de voz" --repeat 5 --json Documentos/DOC_INTERFACE/bench_audio/tts.2026-01-16_piper_streaming.json`
  - `PYTHONPATH=. JARVIS_TTS_STREAMING=1 JARVIS_TTS_CHUNKING=1 python scripts/bench_interface.py tts --text "ola jarvis, teste de desempenho de voz" --repeat 5 --json Documentos/DOC_INTERFACE/bench_audio/tts.2026-01-16_piper_streaming_chunking.json`
- Resultado (resumo):
  - TTS baseline (Piper): avg 4810.88 ms (p50 4244.51 / p95 8375.75), cpu_time_s_avg 0.02074, rss_kb 104580
  - TTS streaming (Piper): avg 6993.16 ms (p50 7241.77 / p95 8937.82), cpu_time_s_avg 0.02924, rss_kb 104096
    - **TTFA: 4497.93 ms** (p50 4912.62 / p95 6096.85) - **35.7% mais rapido que latencia total**
  - TTS streaming+chunking (Piper): avg 6111.03 ms (p50 5679.56 / p95 9726.42), cpu_time_s_avg 0.03120, rss_kb 104420
    - **TTFA: 3578.53 ms** (p50 3190.42 / p95 6828.10) - **41.4% mais rapido que total; 20.4% melhor TTFA vs streaming simples**
- **EVOLUCAO CONFIRMADA**: Chunking reduz TTFA em ~920ms (de 4.5s para 3.6s), melhorando experiencia do usuario. TTFA medido com sucesso usando Piper.

## 2026-01-16 (tts streaming - TTFA com espeak-ng)
- Teste: suite completa `testes/`
- Data/hora: 2026-01-16 09:21 (apos ajustes de TTS streaming)
- Comando: `PYTHONPATH=. .venv/bin/pytest -q testes/`
- Resultado: PASS (245 passed, 3 warnings)

- Benchmark: TTS comparativo (baseline vs streaming vs streaming+chunking)
- Data/hora: 2026-01-16 09:21
- Comandos:
  - `PYTHONPATH=. python scripts/bench_interface.py tts --text "ola jarvis, teste de desempenho de voz" --repeat 5 --json Documentos/DOC_INTERFACE/bench_audio/tts.2026-01-16_baseline.json`
  - `PYTHONPATH=. JARVIS_TTS_STREAMING=1 python scripts/bench_interface.py tts --text "ola jarvis, teste de desempenho de voz" --repeat 5 --json Documentos/DOC_INTERFACE/bench_audio/tts.2026-01-16_streaming.json`
  - `PYTHONPATH=. JARVIS_TTS_STREAMING=1 JARVIS_TTS_CHUNKING=1 python scripts/bench_interface.py tts --text "ola jarvis, teste de desempenho de voz" --repeat 5 --json Documentos/DOC_INTERFACE/bench_audio/tts.2026-01-16_streaming_chunking.json`
- Resultado (resumo):
  - TTS baseline: avg 0.57 ms (p50 0.55 / p95 0.92), cpu_time_s_avg 0.00027, rss_kb 100704
  - TTS streaming: avg 0.62 ms (p50 0.58 / p95 0.93), cpu_time_s_avg 0.00030, rss_kb 100692 (+9% vs baseline)
  - TTS streaming+chunking: avg 0.81 ms (p50 0.83 / p95 1.23), cpu_time_s_avg 0.00034, rss_kb 100656 (+42% vs baseline)
  - Observacao: `tts_first_audio_ms` nao registrado (espeak-ng nao fornece stream de audio). Streaming e chunking funcionam corretamente, mas sem Piper nao e possivel medir o tempo ate o primeiro audio (TTFA).

## 2026-01-16 (validacao - segunda execucao)
- Teste: suite completa `testes/`
- Data/hora: 2026-01-16 06:36
- Comando: `PYTHONPATH=. source .venv/bin/activate && pytest -q testes/`
- Resultado: PASS (245 passed, 3 warnings)

- Benchmark: STT/VAD/endpointing/TTS (validacao completa com --resample)
- Data/hora: 2026-01-16 06:34-06:36
- Comandos:
  - `PYTHONPATH=. python scripts/bench_interface.py stt --audio Documentos/DOC_INTERFACE/bench_audio/voice_clean.wav --repeat 5 --resample --json Documentos/DOC_INTERFACE/bench_audio/voice_clean.stt.2026-01-16_063424.json`
  - `PYTHONPATH=. python scripts/bench_interface.py stt --audio Documentos/DOC_INTERFACE/bench_audio/voice_noise.wav --repeat 5 --resample --json Documentos/DOC_INTERFACE/bench_audio/voice_noise.stt.2026-01-16_063504.json`
  - `PYTHONPATH=. JARVIS_STT_MODEL=tiny python scripts/bench_interface.py stt --audio Documentos/DOC_INTERFACE/bench_audio/voice_clean.wav --repeat 5 --resample --json Documentos/DOC_INTERFACE/bench_audio/voice_clean.stt.tiny.2026-01-16_063546.json`
  - `PYTHONPATH=. python scripts/bench_interface.py vad --audio Documentos/DOC_INTERFACE/bench_audio/voice_clean.wav --repeat 10 --resample --json Documentos/DOC_INTERFACE/bench_audio/voice_clean.vad.2026-01-16_063616.json`
  - `PYTHONPATH=. python scripts/bench_interface.py vad --audio Documentos/DOC_INTERFACE/bench_audio/voice_noise.wav --repeat 10 --resample --json Documentos/DOC_INTERFACE/bench_audio/voice_noise.vad.2026-01-16_063616.json`
  - `PYTHONPATH=. python scripts/bench_interface.py endpointing --audio Documentos/DOC_INTERFACE/bench_audio/voice_clean.wav --repeat 10 --resample --json Documentos/DOC_INTERFACE/bench_audio/voice_clean.endpointing.2026-01-16_063625.json`
  - `PYTHONPATH=. python scripts/bench_interface.py endpointing --audio Documentos/DOC_INTERFACE/bench_audio/voice_noise.wav --repeat 10 --resample --json Documentos/DOC_INTERFACE/bench_audio/voice_noise.endpointing.2026-01-16_063625.json`
  - `PYTHONPATH=. python scripts/bench_interface.py tts --text "ola jarvis, teste de desempenho de voz" --repeat 3 --json Documentos/DOC_INTERFACE/bench_audio/tts.2026-01-16_063628.json`
- Resultado (resumo):
  - STT (default): clean avg 6793 ms (p50 6844 / p95 7937), noise avg 7109 ms (p50 6523 / p95 10214)
  - STT (tiny): clean avg 3354 ms (p50 3181 / p95 4907)
  - VAD: clean avg 0.67 ms (p50 0.65 / p95 0.88), noise avg 0.70 ms (p50 0.66 / p95 0.94)
  - Endpointing: clean 390 ms, noise 390 ms (endpoint_reached=true)
  - TTS: avg 0.71 ms (p50 0.67 / p95 0.89), cpu_time_s_avg 0.000374, rss_kb 99100
- Observacao: segunda execucao para validacao. Variacoes pequenas em relacao a primeira execucao (STT +8-14%, VAD +3%, TTS +44% mas ainda muito rapido <1ms). Resultados confirmam melhorias significativas vs rodada 6 (2026-01-15): STT default ~20% mais rapido, VAD ~51% mais rapido, TTS ~72% mais rapido.

## 2026-01-16 (rodada completa)
- Teste: suite completa `testes/`
- Data/hora: 2026-01-16 06:28
- Comando: `PYTHONPATH=. source .venv/bin/activate && pytest -q testes/`
- Resultado: PASS (245 passed, 3 warnings)

- Benchmark: STT/VAD/endpointing/TTS (completo com --resample)
- Data/hora: 2026-01-16 06:28-06:29
- Comandos:
  - `PYTHONPATH=. python scripts/bench_interface.py stt --audio Documentos/DOC_INTERFACE/bench_audio/voice_clean.wav --repeat 5 --resample --json Documentos/DOC_INTERFACE/bench_audio/voice_clean.stt.2026-01-16.json`
  - `PYTHONPATH=. python scripts/bench_interface.py stt --audio Documentos/DOC_INTERFACE/bench_audio/voice_noise.wav --repeat 5 --resample --json Documentos/DOC_INTERFACE/bench_audio/voice_noise.stt.2026-01-16.json`
  - `PYTHONPATH=. JARVIS_STT_MODEL=tiny python scripts/bench_interface.py stt --audio Documentos/DOC_INTERFACE/bench_audio/voice_clean.wav --repeat 5 --resample --json Documentos/DOC_INTERFACE/bench_audio/voice_clean.stt.tiny.2026-01-16.json`
  - `PYTHONPATH=. python scripts/bench_interface.py vad --audio Documentos/DOC_INTERFACE/bench_audio/voice_clean.wav --repeat 10 --resample --json Documentos/DOC_INTERFACE/bench_audio/voice_clean.vad.2026-01-16.json`
  - `PYTHONPATH=. python scripts/bench_interface.py vad --audio Documentos/DOC_INTERFACE/bench_audio/voice_noise.wav --repeat 10 --resample --json Documentos/DOC_INTERFACE/bench_audio/voice_noise.vad.2026-01-16.json`
  - `PYTHONPATH=. python scripts/bench_interface.py endpointing --audio Documentos/DOC_INTERFACE/bench_audio/voice_clean.wav --repeat 10 --resample --json Documentos/DOC_INTERFACE/bench_audio/voice_clean.endpointing.2026-01-16.json`
  - `PYTHONPATH=. python scripts/bench_interface.py endpointing --audio Documentos/DOC_INTERFACE/bench_audio/voice_noise.wav --repeat 10 --resample --json Documentos/DOC_INTERFACE/bench_audio/voice_noise.endpointing.2026-01-16.json`
  - `PYTHONPATH=. python scripts/bench_interface.py tts --text "ola jarvis, teste de desempenho de voz" --repeat 3 --json Documentos/DOC_INTERFACE/bench_audio/tts.2026-01-16.json`
- Resultado (resumo):
  - STT (default): clean avg 5934 ms (p50 6118 / p95 6434), noise avg 6534 ms (p50 6550 / p95 6583)
  - STT (tiny): clean avg 3223 ms (p50 3205 / p95 4466)
  - VAD: clean avg 0.65 ms (p50 0.64 / p95 0.78), noise avg 0.68 ms (p50 0.68 / p95 0.86)
  - Endpointing: clean 390 ms, noise 390 ms (endpoint_reached=true)
  - TTS: avg 0.49 ms (p50 0.44 / p95 0.85), cpu_time_s_avg 0.000261, rss_kb 99740
- Observacao: primeira rodada completa apos instalacao de numpy/scipy; comparacao com baseline 2026-01-15 mostra melhorias significativas em STT default (~30% mais rapido) e VAD (~52% mais rapido).

## 2026-01-16 (inicial)
- Teste: suite completa `testes/`
- Data/hora: 2026-01-16 05:46
- Comando: `pytest -q`
- Resultado: PASS (232 passed, 12 skipped, 1 warning)

- Benchmark: TTS (text)
- Data/hora: 2026-01-16 05:46
- Comando: `PYTHONPATH=. python scripts/bench_interface.py tts --text "ola" --repeat 3`
- Resultado (resumo): avg 2.51 ms (p50 0.60 / p95 11.15), cpu_time_s_avg 0.000435, rss_kb 19256
- Observacao: STT/VAD/endpointing nao executados (falta numpy/scipy para resample)

## 2026-01-15
- Teste: suite completa `testes/`
- Data/hora: 2026-01-15 06:05
- Comando: `PYTHONPATH=. ./.venv/bin/pytest -q testes/`
- Resultado: PASS (245 passed, 3 warnings)

- Benchmark: STT/VAD/endpointing com gravacoes (WAV)
- Data/hora: 2026-01-15 06:05
- Comandos:
  - `PYTHONPATH=. ./.venv/bin/python scripts/bench_interface.py stt --audio Documentos/DOC_INTERFACE/bench_audio/voice_clean.wav --repeat 5 --resample --json Documentos/DOC_INTERFACE/bench_audio/voice_clean.stt.2026-01-15.json`
  - `PYTHONPATH=. ./.venv/bin/python scripts/bench_interface.py stt --audio Documentos/DOC_INTERFACE/bench_audio/voice_noise.wav --repeat 5 --resample --json Documentos/DOC_INTERFACE/bench_audio/voice_noise.stt.2026-01-15.json`
  - `PYTHONPATH=. JARVIS_STT_MODEL=tiny ./.venv/bin/python scripts/bench_interface.py stt --audio Documentos/DOC_INTERFACE/bench_audio/voice_clean.wav --repeat 5 --resample --json Documentos/DOC_INTERFACE/bench_audio/voice_clean.stt.tiny.2026-01-15.json`
  - `PYTHONPATH=. JARVIS_STT_MODEL=tiny ./.venv/bin/python scripts/bench_interface.py stt --audio Documentos/DOC_INTERFACE/bench_audio/voice_noise.wav --repeat 5 --resample --json Documentos/DOC_INTERFACE/bench_audio/voice_noise.stt.tiny.2026-01-15.json`
  - `PYTHONPATH=. ./.venv/bin/python scripts/bench_interface.py vad --audio Documentos/DOC_INTERFACE/bench_audio/voice_clean.wav --repeat 10 --resample --json Documentos/DOC_INTERFACE/bench_audio/voice_clean.vad.2026-01-15.json`
  - `PYTHONPATH=. ./.venv/bin/python scripts/bench_interface.py vad --audio Documentos/DOC_INTERFACE/bench_audio/voice_noise.wav --repeat 10 --resample --json Documentos/DOC_INTERFACE/bench_audio/voice_noise.vad.2026-01-15.json`
  - `PYTHONPATH=. ./.venv/bin/python scripts/bench_interface.py endpointing --audio Documentos/DOC_INTERFACE/bench_audio/voice_clean.wav --repeat 10 --resample --json Documentos/DOC_INTERFACE/bench_audio/voice_clean.endpointing.2026-01-15.json`
  - `PYTHONPATH=. ./.venv/bin/python scripts/bench_interface.py endpointing --audio Documentos/DOC_INTERFACE/bench_audio/voice_noise.wav --repeat 10 --resample --json Documentos/DOC_INTERFACE/bench_audio/voice_noise.endpointing.2026-01-15.json`
- Resultado (resumo):
  - STT (default / sem `JARVIS_STT_MODEL`): clean avg 8463 ms (p50 8588 / p95 9345); noise avg 9550 ms (p50 9735 / p95 10132)
  - STT (`JARVIS_STT_MODEL=tiny`): clean avg 1529 ms (p50 1364 / p95 2254); noise avg 1636 ms (p50 1604 / p95 2222)
  - VAD: clean avg 1.37 ms (p50 0.75 / p95 9.56); noise avg 0.69 ms (p50 0.66 / p95 1.03)
  - Endpointing (`JARVIS_VAD_SILENCE_MS=400`): clean 390 ms; noise 390 ms (`endpoint_reached=true`)
- Observacao: sem `JARVIS_STT_MODEL`, o STT usa default `small` (mais lento). Para comparar 1:1 com rodadas antigas, fixar `JARVIS_STT_MODEL=tiny`.

## 2026-01-13
- Teste: `testes/test_vad_strategy.py`
- Data/hora: 2026-01-13 23:53
- Comando: `PYTHONPATH=. pytest -q testes/test_vad_strategy.py`
- Resultado: PASS (3 passed)

- Teste: `testes/test_stt_trim_guard.py`
- Data/hora: 2026-01-13 23:35
- Comando: `PYTHONPATH=. pytest -q testes/test_stt_trim_guard.py`
- Resultado: PASS (1 passed)

- Benchmark: STT/VAD (audio espeak 30s + probe de GPU)
- Comandos:
  - `PYTHONPATH=. .venv/bin/python scripts/bench_interface.py stt --audio /tmp/jarvis_bench_30s.wav --repeat 1 --resample --json /tmp/jarvis_bench_30s.stt.json --gpu`
  - `PYTHONPATH=. .venv/bin/python scripts/bench_interface.py vad --audio /tmp/jarvis_bench_30s.wav --repeat 5 --resample --json /tmp/jarvis_bench_30s.vad.json --gpu`
- Resultado (resumo):
  - STT: 38723.81 ms (p50/p95 iguais), CPU avg 78.1962 s, RSS 1413100 KB
  - VAD: 5.21 ms (p50 5.26 / p95 6.00), CPU avg 0.0052 s, RSS 615276 KB
  - GPU: `gpu_available=false` (nvidia-smi indisponivel no ambiente)
- Observacao: audio sintetico (espeak) 22.05 kHz com `--resample`; nao e comparavel 1:1 com voz real.

- Benchmark automatico: voz real curta (silencio + TV ligada)
- Data/hora: 2026-01-13 01:27
- Comando:
  - `PYTHONPATH=. python scripts/auto_voice_bench.py --device 6 --with-noise --output-dir Documentos/DOC_INTERFACE/bench_audio --phrase "oi jarvis teste automatico" --seconds 4`
- Saidas JSON:
  - `Documentos/DOC_INTERFACE/bench_audio/voice_clean.stt.json`
  - `Documentos/DOC_INTERFACE/bench_audio/voice_clean.vad.json`
  - `Documentos/DOC_INTERFACE/bench_audio/voice_noise.stt.json`
  - `Documentos/DOC_INTERFACE/bench_audio/voice_noise.vad.json`
- Resultado (resumo):
  - STT silencio: 3532 ms (p50 3914 / p95 4606)
  - STT TV ligada: 3989 ms (p50 4088 / p95 4625)
  - VAD: ~0,7 ms (silencio) / ~0,6 ms (TV)
  - Observacao: captura 44.1 kHz com `--resample` para 16 kHz.

- Benchmark: STT com parametros “fast” (beam/best/temp + warmup)
- Data/hora: 2026-01-13 01:40
- Comandos:
  - `PYTHONPATH=. JARVIS_STT_BEAM_SIZE=1 JARVIS_STT_BEST_OF=1 JARVIS_STT_TEMPERATURE=0 JARVIS_STT_WARMUP=1 JARVIS_STT_WARMUP_SECONDS=0.5 python scripts/bench_interface.py stt --audio Documentos/DOC_INTERFACE/bench_audio/voice_clean.wav --repeat 5 --resample --json Documentos/DOC_INTERFACE/bench_audio/voice_clean.stt.fast.json`
  - `PYTHONPATH=. JARVIS_STT_BEAM_SIZE=1 JARVIS_STT_BEST_OF=1 JARVIS_STT_TEMPERATURE=0 JARVIS_STT_WARMUP=1 JARVIS_STT_WARMUP_SECONDS=0.5 python scripts/bench_interface.py stt --audio Documentos/DOC_INTERFACE/bench_audio/voice_noise.wav --repeat 5 --resample --json Documentos/DOC_INTERFACE/bench_audio/voice_noise.stt.fast.json`
- Resultado (resumo):
  - STT silencio: 9676 ms (p50 7927 / p95 21672)
  - STT TV ligada: 8950 ms (p50 7961 / p95 16711)
  - Observacao: piorou vs default; nao aplicar como padrao.

- Benchmark: endpointing compare (silence_ms 250/400/800)
- Data/hora: 2026-01-13 02:17
- Comandos:
  - `JARVIS_VAD_SILENCE_MS=250 PYTHONPATH=. .venv/bin/python scripts/bench_interface.py endpointing --audio Documentos/DOC_INTERFACE/bench_audio/voice_clean.wav --repeat 10 --json Documentos/DOC_INTERFACE/bench_audio/voice_clean.endpointing.ms250.json --resample`
  - `JARVIS_VAD_SILENCE_MS=250 PYTHONPATH=. .venv/bin/python scripts/bench_interface.py endpointing --audio Documentos/DOC_INTERFACE/bench_audio/voice_noise.wav --repeat 10 --json Documentos/DOC_INTERFACE/bench_audio/voice_noise.endpointing.ms250.json --resample`
  - `JARVIS_VAD_SILENCE_MS=400 PYTHONPATH=. .venv/bin/python scripts/bench_interface.py endpointing --audio Documentos/DOC_INTERFACE/bench_audio/voice_clean.wav --repeat 10 --json Documentos/DOC_INTERFACE/bench_audio/voice_clean.endpointing.ms400.json --resample`
  - `JARVIS_VAD_SILENCE_MS=400 PYTHONPATH=. .venv/bin/python scripts/bench_interface.py endpointing --audio Documentos/DOC_INTERFACE/bench_audio/voice_noise.wav --repeat 10 --json Documentos/DOC_INTERFACE/bench_audio/voice_noise.endpointing.ms400.json --resample`
  - `JARVIS_VAD_SILENCE_MS=800 PYTHONPATH=. .venv/bin/python scripts/bench_interface.py endpointing --audio Documentos/DOC_INTERFACE/bench_audio/voice_clean.wav --repeat 10 --json Documentos/DOC_INTERFACE/bench_audio/voice_clean.endpointing.ms800.json --resample`
  - `JARVIS_VAD_SILENCE_MS=800 PYTHONPATH=. .venv/bin/python scripts/bench_interface.py endpointing --audio Documentos/DOC_INTERFACE/bench_audio/voice_noise.wav --repeat 10 --json Documentos/DOC_INTERFACE/bench_audio/voice_noise.endpointing.ms800.json --resample`
- Saidas JSON:
  - `Documentos/DOC_INTERFACE/bench_audio/voice_clean.endpointing.ms250.json`
  - `Documentos/DOC_INTERFACE/bench_audio/voice_noise.endpointing.ms250.json`
  - `Documentos/DOC_INTERFACE/bench_audio/voice_clean.endpointing.ms400.json`
  - `Documentos/DOC_INTERFACE/bench_audio/voice_noise.endpointing.ms400.json`
  - `Documentos/DOC_INTERFACE/bench_audio/voice_clean.endpointing.ms800.json`
  - `Documentos/DOC_INTERFACE/bench_audio/voice_noise.endpointing.ms800.json`
- Resultado (resumo):
  - 250ms: 240ms (clean/noise) com endpoint ok.
  - 400ms: 390ms (clean/noise) com endpoint ok.
  - 800ms: 780ms (clean), mas no noise endpoint_reached=false (nao recomendado).

- Benchmark: ruido profile (normalize_audio / vad_aggr=3)
- Data/hora: 2026-01-13 02:25
- Comandos:
  - `PYTHONPATH=. .venv/bin/python scripts/bench_interface.py stt --audio Documentos/DOC_INTERFACE/bench_audio/voice_noise.wav --repeat 5 --resample --json Documentos/DOC_INTERFACE/bench_audio/voice_noise.stt.json`
  - `PYTHONPATH=. JARVIS_STT_NORMALIZE_AUDIO=1 .venv/bin/python scripts/bench_interface.py stt --audio Documentos/DOC_INTERFACE/bench_audio/voice_noise.wav --repeat 5 --resample --json Documentos/DOC_INTERFACE/bench_audio/voice_noise.stt.norm.json`
  - `PYTHONPATH=. JARVIS_VAD_AGGRESSIVENESS=3 .venv/bin/python scripts/bench_interface.py stt --audio Documentos/DOC_INTERFACE/bench_audio/voice_noise.wav --repeat 5 --resample --json Documentos/DOC_INTERFACE/bench_audio/voice_noise.stt.aggr3.json`
  - `PYTHONPATH=. JARVIS_STT_NORMALIZE_AUDIO=1 JARVIS_VAD_AGGRESSIVENESS=3 .venv/bin/python scripts/bench_interface.py stt --audio Documentos/DOC_INTERFACE/bench_audio/voice_noise.wav --repeat 5 --resample --json Documentos/DOC_INTERFACE/bench_audio/voice_noise.stt.norm.aggr3.json`
- Resultado (resumo):
  - baseline ruido: 3989 ms (p50 4088 / p95 4625)
  - normalize_audio=1: 8288 ms (p50 8318 / p95 8870) — piorou
  - vad_aggr=3: 8118 ms (p50 8253 / p95 8997) — piorou
  - normalize+aggr=3: 8578 ms (p50 8562 / p95 9126) — piorou

## 2026-01-07
- Teste: `testes/test_audio_resample.py`
- Comando: `. .venv/bin/activate && PYTHONPATH=. pytest -q testes/test_audio_resample.py`
- Resultado: PASS (1 passed, 1 warning de `pkg_resources` do `webrtcvad`)
- Observacao: fora da `.venv` o teste foi pulado por falta de deps.

- Teste: `testes/test_chat_inbox.py`
- Comando: `. .venv/bin/activate && PYTHONPATH=. pytest -q testes/test_chat_inbox.py`
- Resultado: PASS (3 passed)

- Teste: `testes/test_preflight_shortcut_ui.py`
- Comando: `. .venv/bin/activate && PYTHONPATH=. pytest -q testes/test_preflight_shortcut_ui.py`
- Resultado: PASS (7 passed, 1 warning de `pkg_resources` do `webrtcvad`)

- Teste: `testes/test_stt_capture_config.py`
- Comando: `. .venv/bin/activate && PYTHONPATH=. pytest -q testes/test_stt_capture_config.py`
- Resultado: PASS (4 passed, 1 warning de `pkg_resources` do `webrtcvad`)

- Teste: `testes/test_chat_log.py`
- Comando: `. .venv/bin/activate && PYTHONPATH=. pytest -q testes/test_chat_log.py`
- Resultado: PASS (4 passed)

- Teste: `testes/test_audio_utils.py`
- Comando: `. .venv/bin/activate && PYTHONPATH=. pytest -q testes/test_audio_utils.py`
- Resultado: PASS (3 passed)

- Teste: `testes/test_app_voice_interface.py`
- Comando: `. .venv/bin/activate && PYTHONPATH=. pytest -q testes/test_app_voice_interface.py`
- Resultado: PASS (8 passed, 2 warnings de deps opcionais)

- Teste: `testes/test_chat_ui_interface.py`
- Comando: `. .venv/bin/activate && PYTHONPATH=. pytest -q testes/test_chat_ui_interface.py`
- Resultado: PASS (3 passed)

- Teste: `testes/test_preflight_probe.py`
- Comando: `PYTHONPATH=. pytest -q testes/test_preflight_probe.py`
- Resultado: PASS (4 passed)

## 2026-01-12
- Teste manual: STT streaming (RealtimeSTT, inicio rapido)
- Data/hora: 2026-01-12 09:03
- Comando:
  - `JARVIS_STT_STREAMING=1 JARVIS_STT_STREAMING_BACKEND=realtimestt JARVIS_STT_STREAMING_FORCE_START=1 JARVIS_REQUIRE_WAKE_WORD=0 JARVIS_CHAT_AUTO_OPEN=0 PYTHONPATH=. ./.venv/bin/python -m jarvis.app --voice`
- Resultado: PASS (respondeu "Oi! Como posso ajudar?")
- Observacao: ao encerrar com Ctrl+C apareceu aviso "Bad file descriptor" no worker do RealtimeSTT (encerramento abrupto).
- Serie A (TV desligada) - latencia de encerramento (record_ms)
  - Data/hora: 2026-01-12 09:17
  - Medidas: 8830, 9554, 8135, 10288, 9133 ms
  - Media: 9188 ms (~9.2s) para encerrar a fala
  - Observacao: `transcribe_ms=0` indica que o gargalo esta no fim de fala (endpointing), nao no STT em si.
- Serie B (TV ligada) - latencia/ruido (record_ms)
  - Data/hora: 2026-01-12 09:27
  - Medidas: 9493, 14491, 8776, 9618, 14251 ms
  - Observacao: 2 de 5 comandos cairam em fallback (“Nao consegui completar...”) por texto ruidoso (TV); 3 de 5 responderam “Oi! Como posso ajudar?”. Gargalo segue no fim de fala (endpointing) e o ruido da TV impacta a transcricao.

- Teste: `testes/test_stt_speech_fallback.py`
- Comando: `PYTHONPATH=. pytest -q testes/test_stt_speech_fallback.py`
- Resultado: PASS (2 passed)

- Teste: `testes/test_speaker_verify_interface.py`
- Comando: `PYTHONPATH=. pytest -q testes/test_speaker_verify_interface.py`
- Resultado: PASS (4 passed, 1 skipped)

- Teste: `testes/test_tts_interface.py`
- Comando: `PYTHONPATH=. pytest -q testes/test_tts_interface.py`
- Resultado: PASS (9 passed)

- Teste: `testes/test_protocolo_validar.py`
- Comando: `PYTHONPATH=. pytest -q testes/test_protocolo_validar.py`
- Resultado: PASS (7 passed)

- Teste: `testes/test_app_voice_interface.py`
- Comando: `PYTHONPATH=. pytest -q testes/test_app_voice_interface.py`
- Resultado: PASS (9 passed)

- Teste: `testes/test_audio_utils.py`
- Comando: `PYTHONPATH=. pytest -q testes/test_audio_utils.py`
- Resultado: PASS (5 passed)

- Teste: `testes/test_speaker_verify_interface.py`
- Comando: `PYTHONPATH=. pytest -q testes/test_speaker_verify_interface.py`
- Resultado: PASS (5 passed, 1 skipped)

- Teste: `testes/test_app_voice_interface.py`
- Comando: `PYTHONPATH=. pytest -q testes/test_app_voice_interface.py`
- Resultado: PASS (10 passed)

- Teste: `testes/test_app_voice_interface.py`
- Comando: `PYTHONPATH=. pytest -q testes/test_app_voice_interface.py`
- Resultado: PASS (11 passed)

- Teste: `testes/test_tts_interface.py`
- Comando: `PYTHONPATH=. pytest -q testes/test_tts_interface.py`
- Resultado: PASS (10 passed)

- Teste: `testes/test_chat_log.py`
- Comando: `PYTHONPATH=. pytest -q testes/test_chat_log.py`
- Resultado: PASS (5 passed)

- Teste: `testes/test_app_voice_interface.py`
- Comando: `PYTHONPATH=. pytest -q testes/test_app_voice_interface.py`
- Resultado: PASS (12 passed)

- Teste: `testes/test_protocolo_validar.py`
- Comando: `PYTHONPATH=. pytest -q testes/test_protocolo_validar.py`
- Resultado: PASS (12 passed)

- Teste: `testes/test_chat_inbox.py`
- Comando: `PYTHONPATH=. pytest -q testes/test_chat_inbox.py`
- Resultado: PASS (4 passed)

- Teste: `testes/test_chat_log.py`
- Comando: `PYTHONPATH=. pytest -q testes/test_chat_log.py testes/test_chat_ui_interface.py`
- Resultado: PASS (8 passed)

## 2026-01-08
- Teste: `testes/test_protocolo_validar.py`
- Comando: `PYTHONPATH=. pytest -q testes/test_protocolo_validar.py`
- Resultado: PASS (15 passed)
- Teste: `testes/test_chat_ui_interface.py`
- Comando: `PYTHONPATH=. pytest -q testes/test_chat_ui_interface.py`
- Resultado: PASS (4 passed)
- Teste: `testes/test_speaker_verify_interface.py`
- Comando: `PYTHONPATH=. pytest -q testes/test_speaker_verify_interface.py`
- Resultado: PASS (6 passed, 1 skipped)
- Teste: `testes/test_gui_panel_interface.py`
- Comando: `PYTHONPATH=. pytest -q testes/test_gui_panel_interface.py`
- Resultado: PASS (4 passed)
- Teste: `testes/test_followup_mode.py`
- Comando: `PYTHONPATH=. pytest -q testes/test_followup_mode.py`
- Resultado: PASS (5 passed)
- Teste: `testes/test_tts_interface.py`
- Comando: `PYTHONPATH=. pytest -q testes/test_tts_interface.py`
- Resultado: PASS (11 passed)
- Teste: `testes/test_vad_streaming_interface.py`
- Comando: `PYTHONPATH=. pytest -q testes/test_vad_streaming_interface.py`
- Resultado: PASS (1 passed, 3 skipped)
- Teste: `testes/test_voice_adapters.py`
- Comando: `PYTHONPATH=. pytest -q testes/test_voice_adapters.py`
- Resultado: PASS (4 passed)
- Teste: `testes/test_preflight_profiles.py` + preflight suite
- Comando: `PYTHONPATH=. pytest -q testes/test_preflight_profiles.py testes/test_preflight_headless.py testes/test_preflight_shortcut_ui.py testes/test_preflight_probe.py`
- Resultado: PASS (15 passed)
- Teste: `testes/test_preflight_headless.py`
- Comando: `PYTHONPATH=. pytest -q testes/test_preflight_headless.py`
- Resultado: PASS (3 passed)
- Teste: `testes/test_stt_metrics.py`
- Comando: `PYTHONPATH=. pytest -q testes/test_stt_metrics.py`
- Resultado: PASS (2 passed)
- Teste: `testes/test_voice_adapters.py`
- Comando: `PYTHONPATH=. pytest -q testes/test_voice_adapters.py`
- Resultado: PASS (5 passed)
- Teste: `testes/test_vad_metrics.py`
- Comando: `PYTHONPATH=. pytest -q testes/test_vad_metrics.py`
- Resultado: PASS (1 passed)
- Teste: `testes/test_shortcut_interface.py`
- Comando: `PYTHONPATH=. pytest -q testes/test_shortcut_interface.py`
- Resultado: PASS (7 passed)
- Teste: `testes/test_chat_ui_interface.py`
- Comando: `PYTHONPATH=. pytest -q testes/test_chat_ui_interface.py`
- Resultado: PASS (5 passed)
- Teste: `testes/test_speaker_verify_interface.py`
- Comando: `PYTHONPATH=. pytest -q testes/test_speaker_verify_interface.py`
- Resultado: PASS (7 passed, 1 skipped)
- Teste: `testes/test_stt_flow.py`
- Comando: `PYTHONPATH=. pytest -q testes/test_stt_flow.py`
- Resultado: PASS (9 passed)
- Teste: `testes/test_vad_streaming_interface.py`
- Comando: `PYTHONPATH=. pytest -q testes/test_vad_streaming_interface.py`
- Resultado: PASS (3 passed, 4 skipped)
- Nota: sem teste automatizado para travamento do import do `sounddevice` (depende de PortAudio/ALSA); cobertura indireta via STT/VAD.
- Teste: `testes/test_voice_max_seconds_env.py`
- Comando: `PYTHONPATH=. pytest -q testes/test_voice_max_seconds_env.py`
- Resultado: PASS (9 passed, 1 warning de `audioop`)
- Teste: `testes/test_shortcut_interface.py`
- Comando: `PYTHONPATH=. pytest -q testes/test_shortcut_interface.py`
- Resultado: PASS (9 passed)
- Teste: `testes/test_gui_panel_interface.py`
- Comando: `PYTHONPATH=. pytest -q testes/test_gui_panel_interface.py`
- Resultado: PASS (6 passed)
- Teste: `testes/test_app_voice_interface.py`
- Comando: `PYTHONPATH=. pytest -q testes/test_app_voice_interface.py`
- Resultado: PASS (13 passed, 1 warning de `audioop`)
- Teste: `testes/test_gui_panel_interface.py`
- Comando: `PYTHONPATH=. pytest -q testes/test_gui_panel_interface.py`
- Resultado: PASS (5 passed)

## 2026-01-17
- Teste: `testes/` (suite completa)
- Comando: `PYTHONPATH=. ./.venv/bin/python -m pytest -q testes/`
- Resultado: PASS (255 passed)
- Observacao: warnings esperados (`webrtcvad/pkg_resources`, `resemblyzer/binary_dilation`, `audioop` deprecation) e warning de thread do `pynput` tentando conectar em display em ambiente headless.

- Benchmark: STT baseline (voice_clean, tiny)
- Comando: `PYTHONPATH=. JARVIS_STT_MODEL=tiny ./.venv/bin/python scripts/bench_interface.py stt --audio Documentos/DOC_INTERFACE/bench_audio/voice_clean.wav --repeat 5 --resample`
- Resultado: `latency_ms_p50` ~= 1977ms, `latency_ms_avg` ~= 1990ms, `latency_ms_p95` ~= 2968ms
- Teste: `scripts/bench_interface.py endpointing` (voz real gravada)
- Data/hora: 2026-01-13 02:10
- Comando: `PYTHONPATH=. ./.venv/bin/python scripts/bench_interface.py endpointing --audio Documentos/DOC_INTERFACE/bench_audio/voice_clean.wav --repeat 10 --json Documentos/DOC_INTERFACE/bench_audio/voice_clean.endpointing.json --resample`
- Resultado: PASS (endpoint_ms_avg=390ms, speech_detected=true)
- Teste: `scripts/bench_interface.py endpointing` (ruido/TV)
- Data/hora: 2026-01-13 02:10
- Comando: `PYTHONPATH=. ./.venv/bin/python scripts/bench_interface.py endpointing --audio Documentos/DOC_INTERFACE/bench_audio/voice_noise.wav --repeat 10 --json Documentos/DOC_INTERFACE/bench_audio/voice_noise.endpointing.json --resample`
- Resultado: PASS (endpoint_ms_avg=390ms, speech_detected=true)

- Benchmark automatico (voz real curta, silencio + TV ligada)
- Nome: auto_voice_bench (voz real)
- Objetivo: medir STT/VAD com fala real curta em dois cenarios (silencio vs ruido).
- Data/hora: 2026-01-12 22:17
- Comando: `python scripts/auto_voice_bench.py --device 6 --with-noise`
- Saidas JSON:
  - `/tmp/jarvis_voice_bench/voice_clean.stt.json`
  - `/tmp/jarvis_voice_bench/voice_clean.vad.json`
  - `/tmp/jarvis_voice_bench/voice_noise.stt.json`
  - `/tmp/jarvis_voice_bench/voice_noise.vad.json`
- Resultado (resumo):
  - STT silencio: ~5,7s (p50 6,1s)
  - STT TV ligada: ~8,6s (p95 13,3s)
  - VAD: ~1ms em ambos
  - Observacao: ruído aumenta latencia do STT; registrado em `EVOLUCAO_PERFOMACE.MD`.

## 2026-01-11
- Benchmark (interface voz: STT/VAD/Speaker/TTS) - rodada 4 (22.05k + resample)
- Data/hora: 2026-01-11 04:59
- Comandos:
  - STT: `PYTHONPATH=. .venv/bin/python scripts/bench_interface.py stt --audio /tmp/jarvis_bench_30s_22050.wav --repeat 1 --json /tmp/bench_stt_22050.json --resample`
  - VAD: `PYTHONPATH=. .venv/bin/python scripts/bench_interface.py vad --audio /tmp/jarvis_bench_30s_22050.wav --repeat 5 --json /tmp/bench_vad_22050.json --resample`
  - Speaker: `PYTHONPATH=. JARVIS_SPK_VERIFY=1 .venv/bin/python scripts/bench_interface.py speaker --audio /tmp/jarvis_bench_30s_22050.wav --repeat 3 --json /tmp/bench_speaker_22050.json --resample`
  - TTS: `PYTHONPATH=. .venv/bin/python scripts/bench_interface.py tts --text "ola jarvis, teste de desempenho de voz" --repeat 3 --json /tmp/bench_tts_22050.json`
- Resultado: registrado em `Documentos/DOC_INTERFACE/bench_history.json` (baseline_2026-01-11_pior_caso_30s_r4)

- Medicao fria vs quente (STT curto)
- Data/hora: 2026-01-11 04:58
- Comando:
```
JARVIS_STT_MODEL=tiny JARVIS_STT_LANGUAGE=pt PYTHONPATH=. .venv/bin/python - <<'PY'
import time
import wave
from pathlib import Path
from jarvis.cerebro.config import load_config
from jarvis.interface.entrada.stt import SpeechToText

wav_path = Path('jarvis/REPOSITORIOS_CLONAR/realtimestt/RealtimeSTT/warmup_audio.wav')
with wave.open(str(wav_path), 'rb') as f:
    frames = f.readframes(f.getnframes())

stt = SpeechToText(load_config())

start = time.perf_counter()
_ = stt._transcribe_audio_bytes(frames, require_wake_word=False, skip_speech_check=False)
mid = time.perf_counter()
_ = stt._transcribe_audio_bytes(frames, require_wake_word=False, skip_speech_check=False)
end = time.perf_counter()

print({'audio': str(wav_path), 'cold_s': round(mid - start, 3), 'warm_s': round(end - mid, 3)})
PY
```
- Resultado: cold ~2.924s, warm ~2.003s (ganho ~0.92s)

- Streaming simulado (RealtimeSTT, feed de audio)
- Data/hora: 2026-01-11 04:58
- Comando:
```
PYTHONPATH=. .venv/bin/python - <<'PY'
import json
import sys
import time
import wave
from pathlib import Path

sys.path.insert(0, 'jarvis/REPOSITORIOS_CLONAR/realtimestt')
from RealtimeSTT import AudioToTextRecorder

wav_path = Path('jarvis/REPOSITORIOS_CLONAR/realtimestt/RealtimeSTT/warmup_audio.wav')
with wave.open(str(wav_path), 'rb') as f:
    frames = f.readframes(f.getnframes())
    sr = f.getframerate()
    channels = f.getnchannels()
    sampwidth = f.getsampwidth()

if channels != 1 or sampwidth != 2 or sr != 16000:
    raise SystemExit('audio deve ser mono 16k int16')

duration_s = len(frames) / (sr * sampwidth)

recorder = AudioToTextRecorder(
    use_microphone=False,
    spinner=False,
    device='cpu',
    model='tiny',
    language='pt',
    enable_realtime_transcription=True,
    use_main_model_for_realtime=False,
    realtime_model_type='tiny',
    silero_deactivity_detection=False,
    faster_whisper_vad_filter=True,
    normalize_audio=False,
    min_length_of_recording=0.1,
    post_speech_silence_duration=0.2,
    min_gap_between_recordings=0.0,
)

chunk_ms = 100
chunk_size = int(sr * (chunk_ms / 1000.0) * sampwidth)

recorder.start()
start_ts = time.perf_counter()

for i in range(0, len(frames), chunk_size):
    recorder.feed_audio(frames[i:i+chunk_size])
    time.sleep(chunk_ms / 1000.0)

recorder.stop()
text = recorder.text()
end_ts = time.perf_counter()

recorder.shutdown()

elapsed = end_ts - start_ts
approx_latency = max(0.0, elapsed - duration_s)

result = {
    'audio': str(wav_path),
    'duration_s': round(duration_s, 3),
    'elapsed_s': round(elapsed, 3),
    'approx_latency_s': round(approx_latency, 3),
    'text_preview': (text or '')[:120],
}
print(json.dumps(result, ensure_ascii=True, indent=2))
PY
```
- Resultado: duracao 1.62s, tempo total 4.577s, latencia aprox 2.96s

- Benchmark (interface voz: STT/VAD/Speaker/TTS) - rodada 3
- Data/hora: 2026-01-11 04:33
- Comandos:
  - STT: `JARVIS_STT_MODEL=tiny JARVIS_STT_LANGUAGE=pt PYTHONPATH=. .venv/bin/python scripts/bench_interface.py stt --audio /tmp/jarvis_bench_30s.wav --repeat 1 --json /tmp/bench_stt.json`
  - VAD: `PYTHONPATH=. .venv/bin/python scripts/bench_interface.py vad --audio /tmp/jarvis_bench_30s.wav --repeat 5 --json /tmp/bench_vad.json`
  - Speaker: `PYTHONPATH=. JARVIS_SPK_VERIFY=1 .venv/bin/python scripts/bench_interface.py speaker --audio /tmp/jarvis_bench_30s.wav --repeat 3 --json /tmp/bench_speaker.json`
  - TTS: `PYTHONPATH=. .venv/bin/python scripts/bench_interface.py tts --text "ola jarvis, teste de desempenho de voz" --repeat 3 --json /tmp/bench_tts.json`
- Resultado: registrado em `Documentos/DOC_INTERFACE/bench_history.json` (baseline_2026-01-11_pior_caso_30s_r3)
- Nota: audio 16k do warmup do RealtimeSTT; STT inclui cold start do modelo tiny (comparacao nao e 1:1 com r2).

- Teste: `testes/test_stt_realtimestt_backend.py`
- Comando: `PYTHONPATH=. ./.venv/bin/python -m pytest -q testes/test_stt_realtimestt_backend.py`
- Resultado: PASS (2 passed, 1 warning de `webrtcvad/pkg_resources`)
- Hora: 04:26

- Teste: `testes/test_stt_flow.py` + `testes/test_stt_streaming_controls.py` + `testes/test_stt_partials.py`
- Comando: `PYTHONPATH=. ./.venv/bin/python -m pytest -q testes/test_stt_flow.py testes/test_stt_streaming_controls.py testes/test_stt_partials.py`
- Resultado: PASS (16 passed, 1 warning de `webrtcvad/pkg_resources`)
- Hora: 04:26
- Teste: `testes/test_stt_*.py` (suite STT completa)
- Data/hora: 2026-01-11 02:56
- Comando: `PYTHONPATH=. .venv/bin/pytest -q testes/test_stt_*.py`
- Resultado: PASS (41 passed, 1 warning: `webrtcvad/pkg_resources`)
- Benchmark (interface voz: STT/VAD/Speaker/TTS)
- Data/hora: 2026-01-11 02:56
- Comandos:
  - STT: `PYTHONPATH=. .venv/bin/python scripts/bench_interface.py stt --audio /tmp/jarvis_bench_30s.wav --repeat 1 --json /tmp/bench_stt.json --resample`
  - VAD: `PYTHONPATH=. .venv/bin/python scripts/bench_interface.py vad --audio /tmp/jarvis_bench_30s.wav --repeat 5 --json /tmp/bench_vad.json --resample`
  - Speaker: `PYTHONPATH=. JARVIS_CONFIG_DIR=/tmp/jarvis_bench_config JARVIS_SPK_VERIFY=1 .venv/bin/python scripts/bench_interface.py speaker --audio /tmp/jarvis_bench_30s.wav --repeat 3 --json /tmp/bench_speaker.json --resample`
  - TTS: `PYTHONPATH=. .venv/bin/python scripts/bench_interface.py tts --text "ola jarvis, teste de desempenho de voz" --repeat 3 --json /tmp/bench_tts.json`
- Resultado: registrado em `Documentos/DOC_INTERFACE/bench_history.json` (baseline_2026-01-11_pior_caso_30s_r2)
- Teste: `testes/test_stt_silero_deactivity.py`
- Data/hora: 2026-01-11 01:52
- Comando: `PYTHONPATH=. pytest -q testes/test_stt_silero_deactivity.py`
- Resultado: PASS (3 passed)
- Teste: `testes/test_preflight_profiles.py`
- Data/hora: 2026-01-11 01:52
- Comando: `PYTHONPATH=. pytest -q testes/test_preflight_profiles.py`
- Resultado: PASS (3 passed, 1 warning `audioop`)
- Teste: `testes/test_aec_interface.py` + `testes/test_vad_streaming_interface.py` + `testes/test_tts_interface.py`
- Comando: `PYTHONPATH=. pytest -q testes/test_aec_interface.py testes/test_vad_streaming_interface.py testes/test_tts_interface.py`
- Resultado: PASS (17 passed, 5 skipped, 1 warning de `audioop`)
- Teste: `testes/test_chat_ui_interface.py`
- Comando: `PYTHONPATH=. pytest -q testes/test_chat_ui_interface.py`
- Resultado: PASS (6 passed)
- Teste: `testes/test_gui_panel_interface.py`
- Comando: `PYTHONPATH=. pytest -q testes/test_gui_panel_interface.py`
- Resultado: PASS (7 passed)
- Teste: `testes/test_speaker_verify_interface.py`
- Comando: `PYTHONPATH=. pytest -q testes/test_speaker_verify_interface.py`
- Resultado: PASS (7 passed, 1 skipped)
- Teste: `testes/test_stt_capture_config.py`
- Comando: `PYTHONPATH=. pytest -q testes/test_stt_capture_config.py`
- Resultado: PASS (5 passed)
- Teste: `testes/test_preflight_probe.py`
- Comando: `PYTHONPATH=. pytest -q testes/test_preflight_probe.py`
- Resultado: PASS (4 passed, 1 warning de `audioop`)

## 2026-01-10
- Teste: `testes/test_preflight_shortcut_ui.py`
- Comando: `PYTHONPATH=. pytest -q testes/test_preflight_shortcut_ui.py`
- Resultado: PASS (9 passed, 1 warning de `audioop`)
- Teste: `testes/test_voice_adapters.py`
- Comando: `PYTHONPATH=. pytest -q testes/test_voice_adapters.py`
- Resultado: PASS (8 passed, 1 warning de `audioop`)
- Teste: `testes/test_voice_adapters.py` + `testes/test_stt_flow.py::test_transcribe_with_vad_blocks_without_audio_wake`
- Comando: `PYTHONPATH=. pytest -q testes/test_voice_adapters.py testes/test_stt_flow.py::test_transcribe_with_vad_blocks_without_audio_wake`
- Resultado: PASS (9 passed, 1 warning de `audioop`)

## 2026-01-11
- Teste: `testes/test_stt_partials.py`
- Comando: `PYTHONPATH=. pytest -q testes/test_stt_partials.py`
- Resultado: PASS (3 passed)
- Hora: 01:23:16

- Teste: suite completa `testes/`
- Comando: `PYTHONPATH=. pytest -q testes/`
- Resultado: PASS (222 passed, 9 skipped, 1 warning de `audioop`)
- Hora: 01:23:16

- Teste: `testes/test_voice_adapters.py`
- Comando: `PYTHONPATH=. pytest -q testes/test_voice_adapters.py`
- Resultado: PASS (8 passed, 2 skipped, 1 warning de `audioop`)
- Hora: 01:35:37

- Teste: `testes/test_preflight_shortcut_ui.py`
- Comando: `PYTHONPATH=. pytest -q testes/test_preflight_shortcut_ui.py`
- Resultado: PASS (12 passed, 1 warning de `audioop`)
- Hora: 01:35:37

- Teste: suite completa `testes/`
- Comando: `PYTHONPATH=. pytest -q testes/`
- Resultado: PASS (225 passed, 11 skipped, 1 warning de `audioop`)
- Hora: 01:35:37

## 2026-01-11
- Teste: `testes/test_stt_streaming_controls.py`
- Comando: `PYTHONPATH=. pytest -q testes/test_stt_streaming_controls.py`
- Resultado: PASS (4 passed)

- Teste: `testes/test_stt_flow.py`
- Comando: `PYTHONPATH=. pytest -q testes/test_stt_flow.py`
- Resultado: PASS (9 passed)

- Teste: `pytest -q testes/` (suite completa)
- Comando: `PYTHONPATH=. pytest -q testes/`
- Resultado: FAIL (1 failed, 218 passed, 9 skipped)
- Detalhe: `test_stt_vad_env.py` falhou por env `JARVIS_AUDIO_DEVICE` herdado do sistema.
- Correcao: teste passou a limpar `JARVIS_AUDIO_DEVICE`/`JARVIS_AUDIO_CAPTURE_SR`.

- Teste: `pytest -q testes/` (suite completa, apos correção)
- Comando: `PYTHONPATH=. pytest -q testes/`
- Resultado: PASS (219 passed, 9 skipped, 1 warning de `audioop`)

## 2026-01-11
- Teste: `testes/teste_stt_gap_latency.py`
- Comando: `PYTHONPATH=. pytest -q testes/teste_stt_gap_latency.py`
- Resultado: PASS (2 passed, 1 skipped: `numpy` nao disponivel no ambiente do teste)

- Teste: `testes/test_stt_flow.py`
- Comando: `PYTHONPATH=. pytest -q testes/test_stt_flow.py`
- Resultado: PASS (9 passed)

- Teste: `testes/test_stt_filters.py` + `testes/test_stt_metrics.py`
- Comando: `PYTHONPATH=. pytest -q testes/test_stt_filters.py testes/test_stt_metrics.py`
- Resultado: PASS (8 passed)

- Teste: `testes/test_stt_vad_env.py`
- Comando: `PYTHONPATH=. pytest -q testes/test_stt_vad_env.py`
- Resultado: PASS (1 passed)

- Teste: `testes/test_stt_whisper_kwargs.py`
- Comando: `PYTHONPATH=. pytest -q testes/test_stt_whisper_kwargs.py`
- Resultado: PASS (2 passed)
- Teste manual #1 (Preflight voz)
- Data/hora: 2026-01-10 20:59
- Comando: `PYTHONPATH=. ./.venv/bin/python -m jarvis.app --preflight --preflight-profile voice`
- Resultado: PASS (6 OK, 0 avisos, 0 falhas; warning `pkg_resources` do `webrtcvad`)
- Teste manual #2 (Voz unica: captura + STT + TTS)
- Data/hora: 2026-01-10 20:59
- Comando: `PYTHONPATH=. JARVIS_VOICE_MAX_SECONDS=6 python -m jarvis.app --voice`
- Resultado: PASS parcial (respondeu "Oi! Como posso ajudar?", mas com latencia perceptivel)
- Teste manual #3 (Wake word obrigatoria sem "jarvis")
- Data/hora: 2026-01-10 21:05
- Comando: `JARVIS_REQUIRE_WAKE_WORD=1 PYTHONPATH=. ./.venv/bin/python -m jarvis.app --voice`
- Resultado: PASS (nao respondeu, comportamento esperado)
- Teste manual #4 (Wake word obrigatoria com "jarvis")
- Data/hora: 2026-01-10 21:08
- Comando: `JARVIS_REQUIRE_WAKE_WORD=1 PYTHONPATH=. ./.venv/bin/python -m jarvis.app --voice`
- Resultado: FAIL (sem resposta; TV ligada pode ter atrapalhado VAD/ruido)
- Reteste manual #4 (Wake word obrigatoria com "jarvis", TV desligada)
- Data/hora: 2026-01-10 21:10
- Comando: `JARVIS_REQUIRE_WAKE_WORD=1 PYTHONPATH=. ./.venv/bin/python -m jarvis.app --voice`
- Resultado: FAIL (sem resposta mesmo em silencio)
- Teste: `testes/` (suite completa)
- Comando: `PYTHONPATH=. ./.venv/bin/pytest -q testes/`
- Resultado: PASS (218 passed, 3 warnings: `webrtcvad/pkg_resources`, `resemblyzer/binary_dilation`, `audioop` deprecation)
- Teste: `testes/test_vad_streaming_interface.py`
- Comando: `PYTHONPATH=. pytest -q testes/test_vad_streaming_interface.py`
- Resultado: PASS (3 passed, 3 skipped)
- Teste: `testes/test_vad_streaming_interface.py`
- Comando: `PYTHONPATH=. pytest -q testes/test_vad_streaming_interface.py`
- Resultado: PASS (3 passed, 4 skipped)
- Teste: `testes/test_tts_interface.py`
- Comando: `PYTHONPATH=. pytest -q testes/test_tts_interface.py`
- Resultado: PASS (13 passed, 1 warning)
- Teste: `testes/test_voice_max_seconds_env.py`
- Comando: `PYTHONPATH=. pytest -q testes/test_voice_max_seconds_env.py`
- Resultado: PASS (9 passed, 1 warning)
- Teste: `testes/test_bench_interface.py`
- Comando: `PYTHONPATH=. pytest -q testes/test_bench_interface.py`
- Resultado: PASS (1 passed, 1 skipped)
- Teste: `testes/test_bench_interface.py`
- Comando: `PYTHONPATH=. pytest -q testes/test_bench_interface.py`
- Resultado: PASS (3 passed, 1 skipped)
- Teste: `testes/test_bench_interface.py`
- Comando: `PYTHONPATH=. pytest -q testes/test_bench_interface.py`
- Resultado: PASS (5 passed, 1 skipped)
- Teste: `testes/test_shortcut_interface.py` + `testes/test_preflight_shortcut_ui.py`
- Comando: `PYTHONPATH=. pytest -q testes/test_shortcut_interface.py testes/test_preflight_shortcut_ui.py`
- Resultado: PASS (16 passed, 1 warning)
- Teste: `testes/test_gui_panel_interface.py`
- Comando: `PYTHONPATH=. pytest -q testes/test_gui_panel_interface.py`
- Resultado: PASS (5 passed)
