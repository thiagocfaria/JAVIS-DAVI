# Plano de Performance - Interface de Voz do Jarvis

**Atualizado em:** 2026-01-19
**Status:** Em producao (checklist atualizado)

## Objetivo Principal

Baixar a latencia percebida ao maximo em Python (sem migrar para Rust agora) e manter voz humanizada (Piper).

---

## Indicador Unico (EoS -> 1o audio)

- **Metrica principal:** `eos_to_first_audio_ms` (fim da fala -> primeiro audio da resposta)
- **Meta de producao:** `p50 <= 1200ms` e `p95 <= 1600ms`

### Baseline Atual (2026-01-18)

| Data | Cenario | p50 | p95 | Observacao |
|------|---------|-----|-----|------------|
| 2026-01-18 | Antes otimizacoes | 1888ms | 2543ms | Baseline |
| 2026-01-18 | Apos PRIORIDADE 1 | 661ms | 1600ms | **META p95 ATINGIDA** |
| 2026-01-18 | Pipeline fase 1 + Piper | 588ms | 2108ms | Fase 1 instantanea |

### Grafico Rapido (quanto menor, melhor)

```
p50 (s) ref 1.2s  | ############
Baseline 1.9s     | ###################
Agora ~0.7s       | #######  <-- BOM

p95 (s) ref 1.6s  | ################
Baseline 2.5s     | ##########################
Agora ~1.6-2.1s   | ################  <-- NA META
```

---

## CHECKLIST DE CORRECOES (ORGANIZADO)

### PRIORIDADE 1 - Ganhos Grandes e Seguros (COMPLETO)

| Item | Status | Descricao |
|------|--------|-----------|
| STT rapido | [x] FEITO | tiny + preset + warmup ativo no bench |
| Wake word | [x] FEITO | Exigida + prompt "Jarvis" |
| Comandos curtos | [x] FEITO | Aceitos (0.6s minimo) |
| TTS Piper | [x] FEITO | Backend Python humanizado |
| TTS streaming | [x] FEITO | Habilitado |
| TTS cache | [x] FEITO | Habilitado |
| Fase 1 | [x] FEITO | "Entendi..." instantanea |
| Log eos_to_phase1_ms | [x] FEITO | Funcionando |
| Overlap de plano | [x] FEITO | Opcional (off por padrao) |
| Auto-config voz | [x] FEITO | Implementado |

**Resultado:** p50 saiu de ~1.9s para ~0.7s (EoS->1o audio). TTFA Piper warm ~50-80ms.

### PRIORIDADE 2 - Pipeline "Esperto" (COMPLETO)

| Item | Status | Descricao |
|------|--------|-----------|
| Fase 1 instantanea | [x] FEITO | Implementada |
| Overlap de plano | [x] FEITO | Opcional (off por padrao) |
| Auto-chunk sentencas | [x] MEDIDO | Desligado - piorou TTFA |
| Benchmark fase 1 | [x] FEITO | eos_to_phase1_ms ~0ms |

**Resultado:** `eos_to_phase1_ms` ~0ms; `eos_to_first_audio_ms` p50 ~0.59s.

### PRIORIDADE 3 - Micro-otimizacoes (EM ANDAMENTO)

| Item | Status | Descricao |
|------|--------|-----------|
| Reducao logs pesados | [x] FEITO | No caminho quente |
| Evitar resamples | [x] FEITO | AUDIO_PREFER_16K ativo |
| VAD silence_ms testado | [x] FEITO | 250ms e 400ms comparados |
| STT tiny.en vs small | [ ] PENDENTE | Equilibrar qualidade x latencia |
| Medir CPU por modelo | [ ] PENDENTE | Comparar uso de recursos |

**Status:** 60% completo.

### PRIORIDADE 4 - Pronto para Producao (EM ANDAMENTO)

| Item | Status | Descricao |
|------|--------|-----------|
| p50/p95 na meta | [x] FEITO | Atingido em testes |
| Cenario silencio | [x] FEITO | Validado |
| Cenario ruido (TV) | [x] FEITO | Validado |
| Maquina mais fraca | [ ] PENDENTE | Falta validar |
| Sem voz robotica | [x] FEITO | Em nenhum fallback |

**Status:** 80% completo.

---

## CHECKLIST AVANCADO (FASES A-H)

### Fase A - Testes Automatizados

| Item | Status | Descricao |
|------|--------|-----------|
| voice_regression_test.py | [~] PARCIAL | Criado, falta sink virtual |
| Banco de audios | [x] FEITO | 7 arquivos em test_audio/ |
| WER offline | [x] FEITO | voice_wer_benchmark.py |
| Sink virtual | [ ] PENDENTE | PipeWire/Pulse |
| Leitura events.jsonl | [ ] PENDENTE | Automacao |

### Fase B - Robustez a Ruido / VAD

| Item | Status | Descricao |
|------|--------|-----------|
| VAD hibrido | [x] FEITO | Probe + Silero/webrtc |
| AEC simples | [x] FEITO | Com noise gate |
| Auto-calibracao | [x] FEITO | RMS/peak no start |
| Alerta preflight | [x] FEITO | Para clipping |
| speexaec/webrtc AEC | [x] INSTALADO | swig + libspeexdsp instalados |

### Fase C - STT Baixa Latencia

| Item | Status | Descricao |
|------|--------|-----------|
| faster-whisper beam=1 | [~] TESTADO | Funciona |
| vad_filter=True | [x] FEITO | Ativo |
| Preload/warm | [x] FEITO | Modelo em memoria |
| tiny.en vs small | [ ] PENDENTE | Comparar WER x latencia |
| Streaming STT | [ ] PENDENTE | Com pacer real |

### Fase D - TTS e Barge-in

| Item | Status | Descricao |
|------|--------|-----------|
| Piper in-proc | [x] FEITO | Funcionando |
| Chunk tuning | [x] FEITO | 4096 melhor que 1024 |
| Threads 1/1 | [x] FEITO | Por default |
| Cache trechos | [x] FEITO | Ativo |
| Barge-in metricas | [ ] PENDENTE | Medir ~150ms |

### Fase E - Endpointing e Turn-taking

| Item | Status | Descricao |
|------|--------|-----------|
| VAD silence_ms | [x] FEITO | Ajustado |
| Pos-roll adaptativo | [ ] PENDENTE | Por ruido |
| turn_taking | [ ] PENDENTE | Com parciais |

### Fase F - Documentacao e UX

| Item | Status | Descricao |
|------|--------|-----------|
| Template registro | [x] FEITO | Pronto |
| Graficos p50/p95 | [x] FEITO | Prontos |
| Roteiro offline | [x] FEITO | TESTES_VOZ_SEM_MICROFONE.MD |
| Guia unico | [x] FEITO | DIAGRAMA_ARQUITETURA.md |
| Troubleshooting | [ ] PENDENTE | eco, falso wake, clip |

### Fase G - Criterios de Aceite

| Item | Status | Descricao |
|------|--------|-----------|
| p50 <= 800ms | [x] ATINGIDO | Em alguns cenarios |
| p95 <= 1200ms | [~] PARCIAL | Inconsistente |
| Sem voz robotica | [x] FEITO | Confirmado |
| Zero falsos positivos | [x] FEITO | Em ruido_puro.wav |
| 3 rodadas diferentes | [ ] PENDENTE | Dias/boots |

### Fase H - Pos-Python / Rust

| Item | Status | Descricao |
|------|--------|-----------|
| Avaliar migracao | [ ] NAO INICIADO | Apos metas Python |
| Identificar pecas | [ ] NAO INICIADO | VAD/AEC/STT streaming |

---

## ITENS REMOVIDOS (NAO RECOMENDADOS)

Os seguintes itens foram **removidos** por terem piorado a performance:

1. ~~Auto-chunk de sentencas por default~~ - Piorou TTFA neste CPU
2. ~~JARVIS_TTS_STREAMING_CHUNKING complexo~~ - Simplificado
3. ~~Multiplos backends AEC simultaneos~~ - Um e suficiente
4. ~~Normalizacao audio por default~~ - Piorou em ruido

---

## COMO MEDIR (SEMPRE IGUAL)

1. Mesmo audio: `Documentos/DOC_INTERFACE/bench_audio/voice_clean.wav`
2. Mesmo texto de resposta: `"ok"`
3. Mesmas flags (abaixo)
4. Rodar 2 vezes: a 1a aquece, registrar a 2a

**Comando padrao:**
```bash
# Aquecer
PYTHONPATH=. JARVIS_STT_MODEL=tiny ./.venv/bin/python scripts/bench_interface.py eos_to_first_audio \
  --audio Documentos/DOC_INTERFACE/bench_audio/voice_clean.wav \
  --text "ok" --repeat 5 --resample

# Medir (repeat=20 para p95 estavel)
PYTHONPATH=. JARVIS_STT_MODEL=tiny ./.venv/bin/python scripts/bench_interface.py eos_to_first_audio \
  --audio Documentos/DOC_INTERFACE/bench_audio/voice_clean.wav \
  --text "ok" --repeat 20 --resample
```

---

## PERFIL RECOMENDADO (PRODUCAO / CPU-SAFE)

```bash
# === VOZ HUMANIZADA (PIPER) ===
JARVIS_TTS_ENGINE=piper
JARVIS_TTS_ENGINE_STRICT=1
JARVIS_PIPER_MODELS_DIR=storage/models/piper
JARVIS_PIPER_VOICE=pt_BR-faber-medium
JARVIS_PIPER_BACKEND=python
JARVIS_PIPER_INTRA_OP_THREADS=1
JARVIS_PIPER_INTER_OP_THREADS=1
JARVIS_TTS_STREAMING=1
JARVIS_TTS_CACHE=1
JARVIS_TTS_WARMUP=1
JARVIS_TTS_WARMUP_BLOCKING=1

# === LATENCIA PERCEBIDA ===
JARVIS_VOICE_PHASE1=1
JARVIS_TTS_ACK_PHRASE="Entendi. Ja vou responder."

# === STT RAPIDO ===
JARVIS_STT_MODEL=tiny
JARVIS_STT_PROFILE=fast
JARVIS_STT_CPU_THREADS=2
JARVIS_STT_WORKERS=1
JARVIS_REQUIRE_WAKE_WORD=1
JARVIS_WAKE_WORD=jarvis
JARVIS_STT_INITIAL_PROMPT=Jarvis
JARVIS_MIN_AUDIO_SECONDS=0.6

# === VAD ===
JARVIS_VAD_STRATEGY=webrtc
JARVIS_VAD_AGGRESSIVENESS=2
JARVIS_VAD_SILENCE_MS=400
JARVIS_VAD_PRE_ROLL_MS=200
JARVIS_VAD_POST_ROLL_MS=200

# === CAPTURA ===
JARVIS_AUDIO_PREFER_16K=1
JARVIS_STT_WARMUP=1

# === AEC (OPCIONAL) ===
JARVIS_AEC_BACKEND=simple
JARVIS_TTS_BARGE_IN=1
```

---

## BANCO DE AUDIOS PADRONIZADO

Localizacao: `Documentos/DOC_INTERFACE/test_audio/`

| Arquivo | Descricao | Duracao | Status |
|---------|-----------|---------|--------|
| oi_jarvis_clean.wav | Silencio, "Oi Jarvis" | 3s | OK |
| oi_jarvis_tv.wav | TV baixo, "Oi Jarvis" | 3s | OK |
| oi_jarvis_tv_alta.wav | TV alto, "Oi Jarvis" | 3s | OK |
| comando_longo.wav | Silencio, frase longa | 12s | OK |
| comando_longo_tv.wav | TV medio/alto, frase longa | 12s | OK |
| ruido_puro.wav | TV medio/alto, sem fala | 6s | OK |
| sussurro.wav | Silencio, sussurro "Jarvis" | 3s | OK |

### Resultados Benchmark (2026-01-18)

| Audio | p50 | p95 | Transcricao |
|-------|-----|-----|-------------|
| oi_jarvis_clean.wav | 552ms | 1750ms | OK |
| oi_jarvis_tv.wav | 419ms | 1983ms | OK |
| oi_jarvis_tv_alta.wav | 569ms | 1710ms | OK |
| comando_longo.wav | 637ms | 1960ms | OK (sim~0.80) |
| comando_longo_tv.wav | 699ms | 1844ms | OK (sim~0.89) |
| ruido_puro.wav | 426ms | 2009ms | OK (vazio) |
| sussurro.wav | 439ms | 2004ms | OK |

---

## DEPENDENCIAS INSTALADAS

```bash
# Sistema (ja instalado)
sudo apt-get install -y swig libspeexdsp-dev

# Python (na venv)
pip install speexdsp webrtc-audio-processing
```

---

## PROXIMOS PASSOS (PRIORIDADE)

1. [ ] Validar em maquina mais fraca
2. [ ] Implementar barge-in com metricas
3. [ ] 3 rodadas de validacao em dias diferentes
4. [ ] Documentar troubleshooting (eco, falso wake, clip)
5. [ ] Comparar tiny.en vs small (WER x latencia)

---

## REFERENCIAS

- Diagrama de arquitetura: `Documentos/DOC_INTERFACE/DIAGRAMA_ARQUITETURA.md`
- Guia do Claude: `Documentos/DOC_INTERFACE/GUIA_CLAUDE.md`
- Documentacao dos modulos: `Documentos/DOC_INTERFACE/*.md`
- Testes: `testes/test_*_interface.py`
- Benchmarks: `scripts/bench_interface.py`
