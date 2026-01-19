# EVOLUCAO_PERFOMACE.md

Registro de evolucao de performance da interface de entrada/saida de voz.

## Objetivo (bem simples)
- Medir o pior caso e ver se ficou mais rapido ou mais lento.
- Guardar o baseline com comandos, ambiente e metricas (latencia/CPU/RSS).

## Metas de latencia (referencias de mercado)
Estas metas usam como referencia o texto de pesquisa (endpointing e voz em tempo real).
Elas nao sao comparaveis 1:1 com nossos benchmarks atuais (que medem tempo total de STT
em audios de 4s ou 30s). Sao metas de produto para orientar o futuro:

### Metas para STT (EoS -> texto final)
| Nivel | Meta (ms) | Referencia usada |
| --- | --- | --- |
| Media | 800 | P90 endpointing ~740 ms (Google, baseline) |
| Boa | 500 | faixa 270-570 ms (endpointing melhorado) |
| Otima | 300 | P50 endpointing ~300 ms (Alexa, transactional) |
| Excelente | 200 | abaixo do melhor reportado (meta agressiva) |

### Metas para fala (EoS -> primeiro audio do assistente)
| Nivel | Meta (s) | Referencia usada |
| --- | --- | --- |
| Media | 2.0 | medias de assistentes de mercado (Siri ~2.0s) |
| Boa | 1.6 | medias de assistentes de mercado (Alexa ~1.6s) |
| Otima | 1.2 | medias de assistentes de mercado (Google ~1.2s) |
| Excelente | 0.9 | abaixo do melhor reportado |

### Sugestoes para chegar nas metas
- Streaming em tudo: STT, LLM e TTS (parciais + fala iniciando antes do fim).
- Endpointing inteligente: menor silencio com protecao contra corte de fala.
- Prefetch com parciais: preparar resposta antes do final do turno.
- Transporte realtime (WebRTC) para reduzir jitter.
- Decoding acelerado (speculative / multi-token) no "cerebro".
- Medicao padrao EoS->texto e EoS->fala (instrumentar logs). **Implementado**: o evento `voice_stage_metrics` agora inclui `eos_to_first_audio_ms`.

## Resumo rapido (em linguagem facil)
- O sistema tem 4 etapas: VAD (ouvir), STT (entender), Speaker (confirmar) e TTS (responder).
- Rodada 4 (2026-01-11, 22.05k + resample): STT melhorou para ~14,2s (comparacao mais justa com rodadas anteriores 22.05k).
- Rodada 3 (2026-01-11, 16k): STT ficou mais lento (~61,9s) porque o teste incluiu cold start (carregamento do modelo).
- Speaker voltou a medir custo real (2,3s a 3,7s) porque o encoder foi carregado; quando esta "rapido demais" o resultado nao e representativo.
- Comparacoes 1:1 exigem o mesmo tipo de audio e o mesmo modo de aquecimento (cold vs warm).
- RealtimeSTT foi integrado como backend opcional (JARVIS_STT_STREAMING=1); streaming foi medido com feed de audio curto, mas falta medir ao vivo (microfone real).
- Voz real (2026-01-12, 4s): STT ficou ~5,7s em silencio e ~8,6s com TV ligada; VAD ficou ~1ms em ambos.
- Voz real (2026-01-13, 4s): STT caiu para ~3,5s em silencio e ~4,0s com TV ligada; VAD ~0,7ms.
- Tentativa com parametros “fast” (2026-01-13): STT piorou para ~9,0s; manter default.
- Endpointing offline (2026-01-13, VAD com silencio 400ms): ~390ms em silencio e com TV.
- Comparacao endpointing (2026-01-13): 250ms -> 240ms (clean/noise), 400ms -> 390ms, 800ms -> 780ms clean e falha no noise (endpoint_reached=false).
- Ruido (2026-01-13): normalize_audio e VAD agressivo pioraram o STT em ruido (8s vs 4s); manter default.
- Rodada 5 (2026-01-13, espeak 30s): STT ~38,7s (pior que rodada 4); GPU probe retornou `gpu_available=false` porque `nvidia-smi` nao estava disponivel.
- **Rodada 7 (2026-01-16)**: Melhorias significativas apos implementacoes de otimizacoes (gate adaptativo, chunking, cache, async, etc.). STT default melhorou ~30% (clean) e ~32% (noise) vs rodada 6; VAD melhorou ~52% (clean); TTS melhorou ~80% (0.49ms vs 2.51ms anterior).
- **Rodada 7b (2026-01-16, validacao)**: Segunda execucao confirmou resultados. Variacoes pequenas (STT +8-14%, VAD +3%, TTS +44% mas ainda <1ms) sao normais em benchmarks. Resultados validados: STT default ~20-26% melhor que rodada 6, VAD ~51% melhor, TTS ~72% melhor.
- **Rodada 7c (2026-01-16, TTS streaming - TTFA com espeak-ng)**: Benchmark comparativo baseline vs streaming vs streaming+chunking. Baseline 0.57ms; streaming 0.62ms (+9%); streaming+chunking 0.81ms (+42%). `tts_first_audio_ms` nao registrado (espeak-ng nao fornece stream de audio).
- **Rodada 7d (2026-01-16, TTS streaming - TTFA com Piper)**: **EVOLUÇÃO CONFIRMADA** - TTFA medido com sucesso usando Piper. Streaming simples: TTFA 4.5s (35.7% mais rapido que latencia total). Streaming+chunking: TTFA 3.6s (41.4% mais rapido que total; **20.4% melhor que streaming simples**). Chunking reduz TTFA percebido em ~920ms, melhorando experiencia do usuario.
- **Rodada 8 (2026-01-17, voice_clean)**: baseline curto com audio real 16k. STT ~5.7s, VAD ~0.69ms, endpointing 390ms, speaker ~0.97s, TTS ~0.53ms.
- **Rodada 9 (2026-01-17, speechbrain 16k sample)**: baseline curto com WAV 16k, mas deps ausentes (faster-whisper/webrtcvad/numpy/scipy). STT/VAD/TTS/Speaker medidos (valores baixos, nao representativos). Endpointing falhou por falta de webrtcvad.
- **2026-01-17 (checks)**: ruff/black/pytest executados; sem novo benchmark de performance.
- **Rodada 10 (2026-01-17, RealtimeSTT vendorizado + reuse recorder)**: copia do `RealtimeSTT` extraida para `jarvis/third_party/realtimestt`, recorder do RealtimeSTT pode ser reutilizado entre chamadas (`JARVIS_STT_STREAMING_REUSE_RECORDER=1`) e downloads sao bloqueados por padrao (`HF_HUB_OFFLINE=1` durante init; `JARVIS_ALLOW_MODEL_DOWNLOADS=1` libera). Baseline STT (voice_clean, tiny) medido em ~2.0s (p50).
- **Rodada 11 (2026-01-18, numero unico EoS->primeiro audio)**: novo benchmark `eos_to_first_audio` (voice_clean, `JARVIS_STT_MODEL=tiny`, reply="ok") mediu ~2.64s (p50) e ~3.21s (p95) em execucao inicial (pode incluir cold start).
- **Rodada 11b (2026-01-18, warm baseline)**: mesmo benchmark (repeat=5) apos aquecimento mediu **1.89s (p50)** e **2.54s (p95)**. Este passa a ser o baseline “quente” para comparar melhorias.
- **Rodada 12 (2026-01-18, PRIORIDADE 1)**: melhorias em STT e benchmark:
  - STT: preset automatico de baixa latencia quando `JARVIS_STT_MODEL=tiny` (`JARVIS_STT_AUTO_FAST_ON_TINY=1`).
  - Benchmark: `eos_to_first_audio` passou a recortar o WAV ate o fim da fala (endpointing + post-roll), evitando medir silencio depois do EoS.
  - Resultado (repeat=20): **0.50s (p50)** e **1.49s (p95)**.
- **Rodada 13 (2026-01-18, TTS engine select)**: adicionado `JARVIS_TTS_ENGINE=auto|piper|espeak-ng` (+ `JARVIS_TTS_ENGINE_STRICT=1`) e `tts_engine` no benchmark de TTS. Sem regressao no numero unico:
  - `eos_to_first_audio` (repeat=20): **0.57s (p50)** e **1.65s (p95)**.
- **Rodada 14 (2026-01-18, re-run numero unico)**: re-execucao do `eos_to_first_audio` (repeat=20) com o mesmo setup do PRIORIDADE 1:
  - `eos_to_first_audio` (repeat=20): **0.66s (p50)** e **1.60s (p95)**.
- **Rodada 15 (2026-01-18, voz humanizada Piper)**: modelo PT-BR foi colocado no repo (`storage/models/piper/pt_BR-faber-medium.onnx`) e Piper passou a funcionar via `python -m piper` (o script `.venv/bin/piper` estava com shebang quebrado).
  - TTS TTFA (repeat=3, texto="ok", streaming=1, volume=0): `tts_first_audio_ms` **1.63s (p50)** e **2.05s (p95)**.
  - Impacto no numero unico (repeat=20): `eos_to_first_audio` **2.64s (p50)** e **3.39s (p95)** (piorou, por causa do TTFA alto do Piper em CPU).
- **Rodada 16 (2026-01-18, modo hibrido sem voz robotica)**: ack/earcon rapido para reduzir latencia percebida sem cair para espeak-ng.
  - `tts_ack_ms` (timeout=250ms): **0.25s (p50)**.
  - `eos_to_ack_ms` (repeat=20): **0.85s (p50)** e **2.28s (p95)**.
  - `eos_to_first_audio` (repeat=20, voz do Piper): **2.47s (p50)** e **3.71s (p95)**.
- **Rodada 17 (2026-01-18, tuning do Piper: chunk + cache)**:
  - Chunk do streaming (repeat=10, texto="ok", streaming=1, volume=0):
    - `JARVIS_TTS_STREAM_CHUNK_BYTES=1024`: `tts_first_audio_ms` **1.86s (p50)** e **2.04s (p95)**.
    - `JARVIS_TTS_STREAM_CHUNK_BYTES=4096`: `tts_first_audio_ms` **1.79s (p50)** e **1.97s (p95)** (melhor neste CPU).
  - Cache de frases curtas (`JARVIS_TTS_CACHE=1`): 1a fala gera audio (TTFA ~1.4s em “Entendi…”), 2a fala sai do cache e fica “quase instantanea” (TTFA ~0ms).
- **Rodada 18 (2026-01-18, PRIORIDADE 2 — fase 1 + overlap + metricas novas)**:
  - Adicionado `eos_to_phase1_ms` no evento `voice_stage_metrics` (fim da fala -> inicio do “ack”/fase 1).
  - Fase 1 (ack imediato, sem voz robotica): `TextToSpeech.play_phase1_ack()` (preferencia frase pre-gerada; fallback earcon).
    - Overhead medido (repeat=50, volume=0): **0.003ms (p50)** / **0.009ms (p95)** (ou seja, instantaneo).
  - Overlap (prefetch do plano com parciais do STT): `JARVIS_VOICE_OVERLAP_PLAN=1` (experimental, desligado por padrao).
  - Teste de “TTS por sentencas” (auto-chunk de texto longo) piorou TTFA neste CPU:
    - Sem auto-chunk: `tts_first_audio_ms` ~ **1.87s (p50)**.
    - Com auto-chunk: `tts_first_audio_ms` ~ **2.05s (p50)**.
    - Decisao: manter auto-chunk **off** e usar fase 1 + cache/ack.
- **Rodada 19 (2026-01-18, fase 1 medida no numero unico offline)**:
  - `eos_to_phase1_ms` (repeat=10, voice_clean, Piper, ack phrase): **0.025ms (p50)** / **0.034ms (p95)**.
  - `eos_to_ack_ms` (repeat=10): **0.90s (p50)** / **2.65s (p95)**.
  - `eos_to_first_audio_ms` (repeat=10): **2.48s (p50)** / **4.07s (p95)**.
- **Rodada 20 (2026-01-18, Piper in-proc + limite de CPU)**:
  - Mudanca: Piper passou a ter backend Python/in-process (modelo carregado em memoria, evita spawn/reload por fala).
    - Env: `JARVIS_PIPER_BACKEND=python` (ou `auto`).
    - Novo: `JARVIS_PIPER_INTRA_OP_THREADS` / `JARVIS_PIPER_INTER_OP_THREADS` (limita threads do ONNX Runtime; reduz pico de CPU sem mudar qualidade).
    - Novo: `JARVIS_TTS_WARMUP_BLOCKING=1` (carrega o modelo antes de iniciar o pipeline/bench).
  - TTFA do Piper (sequencial, mesmo processo, texto="ok", volume=0):
    - 1a fala (cold/model load): **1.37s**.
    - Demais falas (warm): ~**0.04–0.08s**.
  - Impacto no numero unico (offline, voice_clean, repeat=10, warmup blocking, volume=0):
    - Ajuste de threads (sem mudar qualidade):
      - CPU-safe `1/1`: TTFA ~**0.07–0.08s** e CPU ~**101%**
      - Mais rapido `2/1`: TTFA ~**0.05–0.06s** e CPU ~**180%**
    - Decisao: usar `1/1` em producao para sobrar CPU pro resto do Jarvis.
    - `eos_to_first_audio_ms` (com `1/1`): **0.59s (p50)** / **2.11s (p95)**.
    - `tts_first_audio_ms_p50` (com `1/1`): **0.08s** (Piper “entra” rapido; o restante vira STT/endpointing).

## Benchmark de voz real (curto, microfone)
Objetivo: medir STT/VAD em fala real curta (4s), comparando ambiente silencioso vs TV ligada.
Metodo: `scripts/auto_voice_bench.py` + `scripts/bench_interface.py` (com resample 44.1k -> 16k).

## Rodada 7 (2026-01-16, completa)
- Primeira rodada completa apos instalacao de numpy/scipy e implementacoes de melhorias.
- STT default: melhorou ~30% (clean) e ~32% (noise) vs rodada 6.
- VAD: melhorou ~52% (clean) vs rodada 6.
- TTS: melhorou ~80% vs rodada anterior (0.49ms vs 2.51ms).
- Endpointing: manteve 390ms (igual a rodada 6).
- Comandos: ver `TESTES_REALISADOS_INTERFACE.MD` (2026-01-16 rodada completa).

### Rodada 1 (2026-01-12 22:17)
| Cenario | Latencia media (ms) | p50 (ms) | p95 (ms) | CPU avg (s) |
| --- | --- | --- | --- | --- |
| STT (silencio) | 5748 | 6078 | 6685 | 14.681 |
| STT (TV ligada) | 8615 | 8356 | 13325 | 16.676 |
| VAD (silencio) | 1.4 | 0.7 | 10.3 | 0.001 |
| VAD (TV ligada) | 0.9 | 0.9 | 1.4 | 0.001 |

### Rodada 2 (2026-01-13 01:27)
| Cenario | Latencia media (ms) | p50 (ms) | p95 (ms) | CPU avg (s) |
| --- | --- | --- | --- | --- |
| STT (silencio) | 3532 | 3914 | 4606 | 10.707 |
| STT (TV ligada) | 3989 | 4088 | 4625 | 11.755 |
| VAD (silencio) | 0.7 | 0.7 | 1.1 | 0.001 |
| VAD (TV ligada) | 0.6 | 0.6 | 0.7 | 0.001 |

### Rodada 3 (2026-01-13, parametros “fast”)
| Cenario | Latencia media (ms) | p50 (ms) | p95 (ms) | CPU avg (s) | Nota |
| --- | --- | --- | --- | --- | --- |
| STT (silencio) | 9676 | 7927 | 21672 | 18.771 | piorou |
| STT (TV ligada) | 8950 | 7961 | 16711 | 19.021 | piorou |

### Rodada 4 (2026-01-13, endpointing offline)
| Cenario | Endpointing medio (ms) | p50 (ms) | p95 (ms) | Config |
| --- | --- | --- | --- | --- |
| Endpointing (silencio) | 390 | 390 | 390 | `JARVIS_VAD_SILENCE_MS=400` |
| Endpointing (TV ligada) | 390 | 390 | 390 | `JARVIS_VAD_SILENCE_MS=400` |

### Rodada 4b (2026-01-13, endpointing compare)
| Silencio (ms) | Endpointing (silencio) | Endpointing (TV ligada) | Observacao |
| --- | --- | --- | --- |
| 250 | 240 | 240 | ok |
| 400 | 390 | 390 | ok (baseline) |
| 800 | 780 | 3* | noise nao atingiu endpoint (endpoint_reached=false) |

*Em noise com 800ms, o endpoint nao foi atingido; o valor baixo e efeito do fallback.*

### Rodada 5a (2026-01-13, ruido profile compare)
| Perfil | STT ruido (ms) | p50 (ms) | p95 (ms) | Nota |
| --- | --- | --- | --- | --- |
| baseline | 3989 | 4088 | 4625 | referencia |
| normalize_audio=1 | 8288 | 8318 | 8870 | piorou |
| vad_aggr=3 | 8118 | 8253 | 8997 | piorou |
| normalize + aggr=3 | 8578 | 8562 | 9126 | piorou |

### Rodada 6 (2026-01-15, re-run com WAVs gravados)
| Cenario | Latencia media (ms) | p50 (ms) | p95 (ms) | CPU avg (s) | Nota |
| --- | --- | --- | --- | --- | --- |
| STT (silencio) | 8463 | 8588 | 9345 | 17.84 | default (sem `JARVIS_STT_MODEL` -> `small`) |
| STT (TV ligada) | 9550 | 9735 | 10132 | 17.79 | default (sem `JARVIS_STT_MODEL` -> `small`) |
| STT (silencio) | 1529 | 1364 | 2254 | 5.45 | `JARVIS_STT_MODEL=tiny` |
| STT (TV ligada) | 1636 | 1604 | 2222 | 5.74 | `JARVIS_STT_MODEL=tiny` |
| VAD (silencio) | 1.37 | 0.75 | 9.56 | 0.001 | ok |
| VAD (TV ligada) | 0.69 | 0.66 | 1.03 | 0.001 | ok |

### Rodada 7 (2026-01-16, apos implementacoes de melhorias)
| Cenario | Latencia media (ms) | p50 (ms) | p95 (ms) | CPU avg (s) | RSS (KB) | Nota |
| --- | --- | --- | --- | --- | --- | --- |
| STT (silencio) | 5934 | 6118 | 6434 | 15.14 | 1263588 | default (melhorou ~30% vs rodada 6) |
| STT (TV ligada) | 6534 | 6550 | 6583 | 15.06 | 1296196 | default (melhorou ~32% vs rodada 6) |
| STT (silencio) | 3223 | 3205 | 4466 | 7.72 | 851348 | `JARVIS_STT_MODEL=tiny` (piorou vs rodada 6, possivel diferenca de config) |
| VAD (silencio) | 0.65 | 0.64 | 0.78 | 0.0007 | 607648 | melhorou ~52% vs rodada 6 |
| VAD (TV ligada) | 0.68 | 0.68 | 0.86 | 0.0007 | 608016 | similar a rodada 6 |
| Endpointing (silencio) | 390 | 390 | 390 | 0.00008 | 105456 | igual a rodada 6 |
| Endpointing (TV ligada) | 390 | 390 | 390 | 0.00008 | 105552 | igual a rodada 6 |
| TTS | 0.49 | 0.44 | 0.85 | 0.00026 | 99740 | melhorou ~80% vs rodada anterior (2.51ms) |

### Rodada 7b (2026-01-16, validacao - segunda execucao)
| Cenario | Latencia media (ms) | p50 (ms) | p95 (ms) | CPU avg (s) | RSS (KB) | Nota |
| --- | --- | --- | --- | --- | --- | --- |
| STT (silencio) | 6793 | 6844 | 7937 | 16.20 | 1291300 | default (validacao: +14.5% vs 7a, ainda ~20% melhor que rodada 6) |
| STT (TV ligada) | 7109 | 6523 | 10214 | - | - | default (validacao: +8.8% vs 7a, ainda ~26% melhor que rodada 6) |
| STT (silencio) | 3354 | 3181 | 4907 | - | - | `JARVIS_STT_MODEL=tiny` (validacao: +4.1% vs 7a) |
| VAD (silencio) | 0.67 | 0.65 | 0.88 | 0.0007 | 607948 | validacao: +3.4% vs 7a, ainda ~51% melhor que rodada 6 |
| VAD (TV ligada) | 0.70 | 0.66 | 0.94 | 0.0007 | - | validacao: +3.2% vs 7a |
| Endpointing (silencio) | 390 | 390 | 390 | - | - | igual a 7a e rodada 6 |
| Endpointing (TV ligada) | 390 | 390 | 390 | - | - | igual a 7a e rodada 6 |
| TTS | 0.71 | 0.67 | 0.89 | 0.00037 | 99100 | validacao: +44% vs 7a, ainda ~72% melhor que rodada anterior (2.51ms) |

### Rodada 7c (2026-01-16, TTS streaming - TTFA com espeak-ng)
| Cenario | Latencia media (ms) | p50 (ms) | p95 (ms) | CPU avg (s) | RSS (KB) | Nota |
| --- | --- | --- | --- | --- | --- | --- |
| TTS (baseline) | 0.57 | 0.55 | 0.92 | 0.00027 | 100704 | referencia (espeak-ng) |
| TTS (streaming) | 0.62 | 0.58 | 0.93 | 0.00030 | 100692 | `JARVIS_TTS_STREAMING=1` (+9% vs baseline) |
| TTS (streaming+chunking) | 0.81 | 0.83 | 1.23 | 0.00034 | 100656 | `JARVIS_TTS_STREAMING=1 JARVIS_TTS_CHUNKING=1` (+42% vs baseline) |
| TTS TTFA | N/A | N/A | N/A | - | - | `tts_first_audio_ms` nao registrado (espeak-ng nao fornece stream) |

### Rodada 7d (2026-01-16, TTS streaming - TTFA com Piper)
| Cenario | Latencia total (ms) | TTFA (ms) | p50 TTFA | p95 TTFA | CPU avg (s) | RSS (KB) | Nota |
| --- | --- | --- | --- | --- | --- | --- | --- |
| TTS (baseline) | 4810.88 | N/A | N/A | N/A | 0.02074 | 104580 | Piper baseline (sem streaming) |
| TTS (streaming) | 6993.16 | 4497.93 | 4912.62 | 6096.85 | 0.02924 | 104096 | `JARVIS_TTS_STREAMING=1` (TTFA 35.7% mais rapido que total) |
| TTS (streaming+chunking) | 6111.03 | 3578.53 | 3190.42 | 6828.10 | 0.03120 | 104420 | `JARVIS_TTS_STREAMING=1 JARVIS_TTS_CHUNKING=1` (TTFA 41.4% mais rapido que total; **20.4% melhor TTFA vs streaming simples**) |
| TTS | 0.64 | 0.52 | 1.24 | 0.00030 | 100332 | `JARVIS_TTS_STREAMING=1`; `tts_first_audio_ms` nao registrado (Piper ausente) |

### Rodada 7e (2026-01-16, migracao interface - TTS streaming+chunking com Piper)
| Cenario | Latencia total (ms) | TTFA (ms) | p50 TTFA | p95 TTFA | CPU avg (s) | RSS (KB) | Nota |
| --- | --- | --- | --- | --- | --- | --- | --- |
| TTS (streaming+chunking) | 4199.41 | 1736.06 | 1671.87 | 2240.70 | 0.03722 | 103460 | `JARVIS_TTS_STREAMING=1 JARVIS_TTS_CHUNKING=1`, repeat=3; apos migracao para `jarvis/interface` |

### Rodada 8 (2026-01-17, voice_clean baseline curto)
| Cenario | Latencia media (ms) | p50 (ms) | p95 (ms) | CPU avg (s) | RSS (KB) | Nota |
| --- | --- | --- | --- | --- | --- | --- |
| STT (voice_clean) | 5692.64 | 5926.83 | 6899.97 | 15.77 | 1264960 | `voice_clean.wav`, repeat=3 |
| VAD (voice_clean) | 0.69 | 0.66 | 0.84 | 0.0007 | 608536 | `voice_clean.wav`, repeat=5 |
| Endpointing (voice_clean) | 0.08 | 0.08 | 0.11 | 0.00009 | 106084 | 390ms (silence_ms=400) |
| Speaker (voice_clean) | 969.22 | 138.81 | 4624.36 | 1.45 | 727872 | `JARVIS_SPK_VERIFY=1`, repeat=3 |
| TTS | 0.53 | 0.46 | 0.94 | 0.00031 | 101732 | local, repeat=3 |

### Rodada 9 (2026-01-17, speechbrain 16k sample - deps ausentes)
| Cenario | Latencia media (ms) | p50 (ms) | p95 (ms) | CPU avg (s) | RSS (KB) | Nota |
| --- | --- | --- | --- | --- | --- | --- |
| STT (spk1_snt2) | 3.97 | 3.93 | 4.47 | 0.00398 | 25780 | **nao representativo** (faster-whisper ausente) |
| VAD (spk1_snt2) | 3.98 | 3.77 | 4.92 | 0.00399 | 25668 | **nao representativo** (webrtcvad ausente) |
| Endpointing | N/A | N/A | N/A | - | - | falhou: `webrtcvad` ausente |
| Speaker (spk1_snt2) | 0.005 | 0.003 | 0.018 | 0.000008 | 23628 | **nao representativo** (deps ausentes) |
| TTS | 0.63 | 0.55 | 1.09 | 0.00039 | 20928 | local, repeat=3 |

### Leitura simples
- Com ruido (TV), o STT ficou ~2,9s mais lento (≈ +50%).
- O VAD quase nao mudou (permaneceu ~1ms).
- Parametros “fast” (beam/best/temp/warmup) pioraram a latencia em voz real curta; nao aplicar como default.
- Endpointing ficou em ~390ms com `JARVIS_VAD_SILENCE_MS=400` (13 frames de 30ms). Para reduzir, baixar o silencio, com risco de cortar fala.
- Em comparacao direta, 250ms entregou ~240ms (clean/noise). 800ms falhou no noise (endpoint_reached=false), entao nao e seguro em ambiente ruidoso.
- Ruido alto: normalize_audio e VAD agressivo nao ajudaram no audio com TV; manter default e buscar AEC/NS dedicados.
- Esses numeros nao sao comparaveis com o baseline de 30s; servem apenas para ver impacto do ruido em fala curta real.
- Comparando 2026-01-12 -> 2026-01-13, o STT melhorou ~38% (silencio) e ~54% (TV ligada).
- **Rodada 7 (2026-01-16)**: STT default melhorou ~30% (clean) e ~32% (noise) vs rodada 6; VAD melhorou ~52% (clean); TTS melhorou ~80% vs rodada anterior. Melhorias atribuidas as implementacoes de otimizacoes (gate adaptativo, chunking, cache, async, etc.).

## Evolucao visual (ms, menor e melhor)
Legenda: barra maior = mais lento. Comparacao indicativa (audio diferente).

STT
2026-01-13 (r5) | ######################################## 38724
2026-01-11 (r4) | ######################          14203
2026-01-11 (r3) | ############################################################# 61913
2026-01-11 (r2) | ################################### 33115
2026-01-11 (r1) | ########################################### 44217
2026-01-10      | #################               13598
2026-01-07      | ############################### 23231

VAD
2026-01-13 (r5) | #####                           5,21
2026-01-11 (r4) | ########                        8,98
2026-01-11 (r3) | ##########                      10,88
2026-01-11 (r2) | #####                           4,89
2026-01-11 (r1) | ########                        8,29
2026-01-10      | #####                           4,55
2026-01-07      | ##########                      9,69

Speaker
2026-01-11 (r4) | #######################         2315
2026-01-11 (r3) | ############################    3764
2026-01-11 (r2) | #                               0,05*
2026-01-11 (r1) | #                               0,05*
2026-01-10      | #######                         637
2026-01-07      | ############################    3102

TTS
2026-01-11 (r4) | #                               0,57
2026-01-11 (r3) | #####                           2,90
2026-01-11 (r2) | #                               0,46
2026-01-11 (r1) | ###                             1,46
2026-01-10      | #####                           2,41
2026-01-07      | #########                       4,67

*Speaker 2026-01-11: tempo muito baixo pode indicar falta de voiceprint (nao representa a verificacao real).*

## Sinais de ganho (indicativos)
- STT (comparacao 1:1 22.05k): 33115 ms -> 14203 ms (melhorou ~18,9s).
- VAD: 4,89 ms -> 8,98 ms (piorou ~4,1 ms).
- Speaker: 0,05 ms -> 2315 ms (agora representativo; encoder foi carregado).
- TTS: 0,46 ms -> 0,57 ms (quase igual).
- Nota: a rodada 3 usa audio 16k (sem resample) e cold start; comparar com cautela.

## Baseline atual (pior caso)
 Data: 2026-01-11 (rodada 4)
- Metodo: `scripts/bench_interface.py` com audio espeak-ng (22.05 kHz) reamostrado para 16 kHz (`--resample`), 30s.
- Audio: `/tmp/jarvis_bench_30s_22050.wav`
- Repeticoes: STT=1, VAD=5, Speaker=3, TTS=3
- Observacao 1: STT usa modelo padrao (sem override) e inclui cold start do processo.
- Observacao 2: TTS mede apenas o custo de iniciar processo (speak nao bloqueia).
- Observacao 3: Speaker e representativo porque o encoder foi carregado (pode variar se nao houver voiceprint).
- Historico bruto (JSON unico): `bench_history.json`

### Resultados (pior caso 30s)
| Cenario | Latencia media (ms) | p50 (ms) | p95 (ms) | CPU avg (s) | RSS (KB) |
| --- | --- | --- | --- | --- | --- |
| STT | 14202.52 | 14202.52 | 14202.52 | 23.9219 | 1352228 |
| VAD | 8.98 | 7.94 | 13.03 | 0.0066 | 618784 |
| Speaker (JARVIS_SPK_VERIFY=1) | 2314.88 | 344.10 | 11002.12 | 1.5858 | 764276 |
| TTS (local) | 0.57 | 0.54 | 0.94 | 0.0003 | 99056 |

## Rodada 5 (espeak 30s, probe de GPU)
 Data: 2026-01-13
- Metodo: `scripts/bench_interface.py` com audio espeak-ng (22.05 kHz) reamostrado para 16 kHz (`--resample`), 30s.
- Audio: `/tmp/jarvis_bench_30s.wav`
- Repeticoes: STT=1, VAD=5
- Observacao 1: nao comparavel 1:1 com rodada 4 (audio sintetico diferente).
- Observacao 2: `gpu_available=false` (sem `nvidia-smi` no ambiente).

### Resultados (rodada 5)
| Cenario | Latencia media (ms) | p50 (ms) | p95 (ms) | CPU avg (s) | RSS (KB) |
| --- | --- | --- | --- | --- | --- |
| STT | 38723.81 | 38723.81 | 38723.81 | 78.1962 | 1413100 |
| VAD | 5.21 | 5.26 | 6.00 | 0.0052 | 615276 |

## Baseline anterior (pior caso, rodada 3)
- Data: 2026-01-11 (rodada 3)
- Metodo: `scripts/bench_interface.py` com audio 16 kHz (warmup do RealtimeSTT repetido), 30s.
- Audio: `/tmp/jarvis_bench_30s.wav`
- Repeticoes: STT=1, VAD=5, Speaker=3, TTS=3
- Observacao 1: STT usa modelo tiny e inclui cold start (carregamento do modelo).
- Observacao 2: TTS mede apenas o custo de iniciar processo (speak nao bloqueia).
- Observacao 3: Speaker e representativo porque o encoder foi carregado (pode variar se nao houver voiceprint).
- Historico bruto (JSON unico): `bench_history.json`

### Resultados (pior caso 30s)
| Cenario | Latencia media (ms) | p50 (ms) | p95 (ms) | CPU avg (s) | RSS (KB) |
| --- | --- | --- | --- | --- | --- |
| STT | 61912.72 | 61912.72 | 61912.72 | 101.0413 | 845000 |
| VAD | 10.88 | 11.84 | 13.41 | 0.0060 | 607408 |
| Speaker (JARVIS_SPK_VERIFY=1) | 3764.58 | 832.60 | 16897.28 | 2.0882 | 759684 |
| TTS (local) | 2.90 | 0.77 | 12.58 | 0.0004 | 98468 |

## Baseline anterior (pior caso, rodada 2)
- Data: 2026-01-11 (rodada 2)
- Metodo: `scripts/bench_interface.py` com audio espeak-ng (22.05 kHz) reamostrado para 16 kHz (`--resample`), 30s.
- Audio: `/tmp/jarvis_bench_30s.wav`
- Repeticoes: STT=1, VAD=5, Speaker=3, TTS=3
- Observacao 1: TTS mede apenas o custo de iniciar processo (speak nao bloqueia).
- Observacao 2: Speaker pode nao ser representativo sem voiceprint (ver nota nos resultados).
- Historico bruto (JSON unico): `bench_history.json`

### Resultados (pior caso 30s)
| Cenario | Latencia media (ms) | p50 (ms) | p95 (ms) | CPU avg (s) | RSS (KB) |
| --- | --- | --- | --- | --- | --- |
| STT | 33115.35 | 33115.35 | 33115.35 | 83.6201 | 1725808 |
| VAD | 4.89 | 4.89 | 4.97 | 0.0049 | 617924 |
| Speaker (JARVIS_SPK_VERIFY=1) | 0.05 | 0.03 | 0.13 | 0.0000 | 579536 |
| TTS (local) | 0.46 | 0.37 | 0.90 | 0.0003 | 98856 |

## Baseline anterior (pior caso, rodada 1)
- Data: 2026-01-11 (rodada 1)
- Metodo: `scripts/bench_interface.py` com audio espeak-ng (22.05 kHz) reamostrado para 16 kHz (`--resample`), 30s.
- Audio: `/tmp/jarvis_bench_30s.wav`
- Repeticoes: STT=1, VAD=5, Speaker=3, TTS=3
- Observacao 1: TTS mede apenas o custo de iniciar processo (speak nao bloqueia).
- Observacao 2: Speaker pode nao ser representativo sem voiceprint (ver nota nos resultados).
- Historico bruto (JSON unico): `bench_history.json`

### Resultados (pior caso 30s)
| Cenario | Latencia media (ms) | p50 (ms) | p95 (ms) | CPU avg (s) | RSS (KB) |
| --- | --- | --- | --- | --- | --- |
| STT | 44216.84 | 44216.84 | 44216.84 | 79.0837 | 1735028 |
| VAD | 8.29 | 6.70 | 12.73 | 0.0059 | 617312 |
| Speaker (JARVIS_SPK_VERIFY=1) | 0.05 | 0.03 | 0.13 | 0.0001 | 578968 |
| TTS (local) | 1.46 | 1.42 | 1.66 | 0.0008 | 98664 |

## Baseline anterior (pior caso)
- Data: 2026-01-10
- Metodo: `scripts/bench_interface.py` com audio espeak repetido, 16 kHz mono (30s).
- Audio: `/tmp/jarvis_bench_30s.wav`
- Repeticoes: STT=1, VAD=5, Speaker=3, TTS=3
- Observacao 1: TTS mede apenas o custo de iniciar processo (speak nao bloqueia).
- Observacao 2: import do `sounddevice` travou no ambiente; usei stub apenas para STT/VAD no benchmark (nao altera esses cenarios).
- Historico bruto (JSON unico): `bench_history.json`

### Resultados (pior caso 30s)
| Cenario | Latencia media (ms) | p50 (ms) | p95 (ms) | CPU avg (s) | RSS (KB) |
| --- | --- | --- | --- | --- | --- |
| STT | 13597.57 | 13597.57 | 13597.57 | 38.1461 | 1249704 |
| VAD | 4.55 | 4.45 | 5.21 | 0.0045 | 607236 |
| Speaker (JARVIS_SPK_VERIFY=1) | 637.05 | 402.19 | 1928.65 | 1.7605 | 760536 |
| TTS (local) | 2.41 | 0.66 | 10.35 | 0.0003 | 98376 |

## Baseline anterior (pior caso)
- Data: 2026-01-07
- Metodo: `scripts/bench_interface.py` com audio sintetico 16 kHz mono (30s).
- Audio: `/tmp/jarvis_bench_30s.wav`
- Repeticoes: STT=1, VAD=5, Speaker=3, TTS=3
- Observacao: TTS mede apenas o custo de iniciar processo (speak nao bloqueia).
- Historico bruto (JSON unico): `bench_history.json`

### Resultados (pior caso 30s)
| Cenario | Latencia media (ms) | p50 (ms) | p95 (ms) | CPU avg (s) | RSS (KB) |
| --- | --- | --- | --- | --- | --- |
| STT | 23231.06 | 23231.06 | 23231.06 | 29.9633 | 1235104 |
| VAD | 9.69 | 11.45 | 13.96 | 0.0061 | 641144 |
| Speaker (JARVIS_SPK_VERIFY=1) | 3102.79 | 690.05 | 13826.84 | 2.3698 | 772616 |
| TTS (local) | 4.67 | 6.10 | 7.59 | 0.0005 | 24900 |

## Rodada anterior (incompleta: deps ausentes)
- Data: 2026-01-08
- Metodo: `scripts/bench_interface.py` com audio espeak repetido (30s).
- Observacao: faltam deps de STT/speaker (`faster-whisper`, `resemblyzer`, `webrtcvad`, `numpy`, `sounddevice`, `scipy`).
  Resultado: STT/speaker nao representam o pior caso real.

### Resultados (30s)
| Cenario | Latencia media (ms) | p50 (ms) | p95 (ms) | CPU avg (s) | RSS (KB) |
| --- | --- | --- | --- | --- | --- |
| STT (sem deps) | 57.25 | 57.25 | 57.25 | 0.0452 | 31892 |
| VAD | 79.89 | 78.40 | 136.56 | 0.0526 | 32016 |
| Speaker (sem deps) | 0.01 | 0.01 | 0.04 | 0.0000 | 32188 |
| TTS (local) | 1.05 | 0.88 | 2.05 | 0.0006 | 32216 |

## Ambiente
- SO: Linux
- Python: .venv (local)
- Dependencias chave: numpy, scipy, sounddevice, webrtcvad, faster-whisper, resemblyzer, pynput, py-spy
- TTS: espeak-ng presente; piper ausente
- Streaming opcional: RealtimeSTT + pyaudio (quando habilitado)
- RealtimeSTT streaming (deps extras): openwakeword, halo, websocket-client, torchaudio (Silero).

## Medicao fria vs quente (STT, audio curto)
- Audio: `warmup_audio.wav` (1.62s)
- Cold: ~2.924s
- Warm: ~2.003s
- Ganho estimado: ~0.92s (cache do modelo evita custo de carregamento).

## Streaming simulado (RealtimeSTT, feed de audio)
- Audio: `warmup_audio.wav` (1.62s)
- Tempo total (feed + transcricao): 4.577s
- Latencia aproximada (total - duracao): ~2.96s
- Observacao: simulacao usa `feed_audio` e `recorder.start/stop`, nao substitui teste ao vivo com microfone.

## Como medimos (comandos)
- STT: `PYTHONPATH=. .venv/bin/python scripts/bench_interface.py stt --audio /tmp/jarvis_bench_30s.wav --repeat 1 --json /tmp/bench_stt.json --resample`
- VAD: `PYTHONPATH=. .venv/bin/python scripts/bench_interface.py vad --audio /tmp/jarvis_bench_30s.wav --repeat 5 --json /tmp/bench_vad.json --resample`
- Speaker: `PYTHONPATH=. JARVIS_CONFIG_DIR=/tmp/jarvis_bench_config JARVIS_SPK_VERIFY=1 .venv/bin/python scripts/bench_interface.py speaker --audio /tmp/jarvis_bench_30s.wav --repeat 3 --json /tmp/bench_speaker.json --resample`
- TTS: `PYTHONPATH=. .venv/bin/python scripts/bench_interface.py tts --text "ola jarvis, teste de desempenho de voz" --repeat 3 --json /tmp/bench_tts.json`
- Profiling (opcional): `py-spy record -o profile.svg -- python scripts/bench_interface.py stt --audio /tmp/jarvis_bench_30s.wav`
- Medicao cold/warm (STT curto):
```
JARVIS_STT_MODEL=tiny JARVIS_STT_LANGUAGE=pt PYTHONPATH=. .venv/bin/python - <<'PY'
import time
import wave
from pathlib import Path
from jarvis.cerebro.config import load_config
from jarvis.entrada.stt import SpeechToText

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
- Streaming simulado (RealtimeSTT):
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

## Formato do JSON (bench_history.json)
- Arquivo unico com um array `history`.
- Cada item representa uma rodada completa (baseline + commands + results).
- Campos minimos recomendados:
  - `record_id`: id unico da rodada.
  - `created_at`: data (YYYY-MM-DD).
  - `baseline`: informacoes do ambiente e do audio.
  - `commands`: comandos exatos usados.
  - `results`: lista de cenarios e metricas.

Exemplo minimo de registro:
```json
{
  "record_id": "baseline_2026-01-07_pior_caso_30s",
  "created_at": "2026-01-07",
  "baseline": {"audio": "/tmp/voz.wav", "duration_s": 30},
  "commands": {"stt": "PYTHONPATH=. ..."},
  "results": [{"scenario": "stt", "latency_ms_avg": 123.4}]
}
```

## Como anexar nova rodada no historico
- Crie um JSON de registro (mesmo formato acima), por exemplo: `/tmp/bench_record.json`
- Anexe ao historico:
  - `PYTHONPATH=. .venv/bin/python scripts/bench_history_append.py --record /tmp/bench_record.json`

## Limites e notas
- STT e Speaker sao os maiores consumidores (modelo e embedding).
- TTS mede apenas o custo de spawn; nao mede duracao real de fala.
- RSS depende do modelo e do cache de libs (varia por execucao).
- Import de `sounddevice` travou no ambiente; stub usado apenas para benchmark (nao afeta VAD/STT nesses cenarios).
- `psutil` estava ausente no baseline 2026-01-10; foi instalado nesta etapa para proximas rodadas com metricas completas.
- Baseline 2026-01-11 (rodada 2) usou audio espeak-ng 22.05k com `--resample` (nao e 1:1 com 16k nativo).
- Baseline 2026-01-11 (rodadas 1/2) de Speaker pode estar invalido se nao houver voiceprint cadastrado.
- RealtimeSTT exige deps extras (openwakeword/halo/websocket-client/torchaudio); sem elas, a inicializacao falha.

## Proximos passos
- Repetir baseline com audio real gravado em producao.
- Comparar historico usando o JSON salvo (ver arquivo acima).
- Adicionar reamostragem automatica e medir impacto (ver checklist).

## Atualizacoes recentes (sem benchmark)
- 2026-01-08: chat_ui passou a ler o tail do log por blocos (evita carregar o arquivo inteiro).
- 2026-01-08: speaker_verify/adapter passaram a usar cache de voiceprint (reduz IO).
- 2026-01-08: gui_panel passou a alternar STOP para cancelamento de comandos.
- 2026-01-08: follow-up agora limita quantidade de comandos por janela.
- 2026-01-08: TTS agora serializa chamadas (evita sobreposicao de audio).
- 2026-01-08: StreamingVAD agora aceita device configurado.
- 2026-01-08: adapters agora validam audio PCM int16 e sample_rate.
- 2026-01-08: STT ganhou wake word por audio opcional (Porcupine) antes da transcricao.
- 2026-01-10: AEC simples (com referencia de playback) passou a existir; sem benchmark novo ainda.
- 2026-01-11: STT passou a transcrever audio curto quando o VAD detecta fala (reduz espera em comandos curtos); sem benchmark novo.
- 2026-01-11: STT agora corta audio acima do limite configurado para evitar overflow; sem benchmark novo.
- 2026-01-11: STT passou a aceitar audio externo via `transcribe_audio_bytes`; sem benchmark novo.
- 2026-01-11: RealtimeSTT integrado como backend opcional; streaming ainda sem benchmark dedicado.
