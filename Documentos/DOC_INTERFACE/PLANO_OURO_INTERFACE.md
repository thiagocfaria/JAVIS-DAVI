# Plano OURO — Interface Entrada/Saída (Pop!_OS, CPU fraca, offline)

Documento guia (curto) para manter latência baixa e comportamento estável. Use como roteiro de trabalho.

## Objetivos
- **PRATA:** p95 do `eos_to_first_audio` ≤ 1200–1500ms; barge-in p95 ≤ 120ms; decisão→TTS p95 ≤ 200ms.
- **OURO:** p95 do `eos_to_first_audio` ≤ 900–1200ms (**ATINGIDO:** p95=**1190ms** com faster_whisper, margem 10ms); barge-in p95 ≤ 80ms (atual: ~60ms); estabilidade 24–72h sem regressão (pendente).

## Estado atual (jan/2026)

**✅ Atualização 29/01/2026 (Validação Etapa 5 CONCLUÍDA):**
- **Backend PRODUÇÃO:** `faster_whisper` (tiny) — **META OURO ATINGIDA E VALIDADA** ✅
  - **BLOCO 2 (Long-run 2000 iter):** p50: 636.2ms, p95: **798.5ms** (< 1200ms ✅), p99: 1136.6ms
  - **CPU% VÁLIDO:** 219.1% (psutil_cpu_percent agora funciona)
  - RSS: 301.8MB (estável, sem vazamento)
  - cpu_time_avg: 1.44s
- **Backend EXPERIMENTAL:** `whisper_cpp` (tiny) — **REGRESSÃO SEVERA CONFIRMADA**
  - p50: ~2613ms (3.3x pior), p95: ~10042ms (8.4x pior)
  - Status: BLOQUEADO para produção
- **BLOCO 3 (WER + Latência):**
  - tiny: 61.3% WER, p95 1917ms (warming frio, 10 reps)
  - small: 38.7% WER, p95 9232ms (9x mais lento, inaceitável)
  - base: 58.1% WER, p95 21228ms (26x mais lento, inaceitável)
- **Recomendação final:** `faster_whisper` + modelo `tiny` para produção
- Piper in-proc com streaming/cache; TTFA warm ~0.05–0.08s (threads 1/1 CPU-safe).
- Perfis FAST/BALANCED/NOISY usam `tiny` via `faster_whisper` (default seguro).

## Pendências prioritárias

### ✅ Concluído (29/01/2026)
- [x] CPU% validado e funcional (219.1% no long-run)
- [x] Long-run 2000 iterações com p95 controlado (798.5ms)
- [x] WER + Latência para tiny/small/base documentado
- [x] Regressão whisper_cpp investigada e documentada (bloqueado)
- [x] Documentação final (README_FINAL.md como fonte única de verdade)

### 🔄 Próximas etapas (Pós META OURO)
- Validar robustez 24–72h em hardware mais fraco
- Investigar causa raiz regressão whisper_cpp (pywhispercpp==1.4.1)
- Medir decisão→TTS (p95) e barge-in stop_ms em produção
- Validar GPU (ctranslate2) se suportado
- Considerar fine-tuning ou otimizações para melhorar WER (opcional)

## Fontes de verdade
- Evolução e métricas: `Documentos/DOC_INTERFACE/EVOLUCAO_PERFOMACE.MD`.
- Benchmarks e uso: `Documentos/DOC_INTERFACE/testes/benchmark_interface.md`.
- Decisões/infra: `Documentos/DOC_INTERFACE/infra/*.md` (profiles, voice_profile, decisão tiny).
- Checklists/ideias externas: `Documentos/DOC_INTERFACE/repositorios_interface.md`.

## Regras do jogo
- 1 mudança por vez; sempre medir (bench) e registrar p50/p95/p99 + config.
- Se p95 piorar >5% sem justificativa, reverter.
- Sem doc curta (ADR/bench) → não mergeia.

## Checklist rápido (Etapa 5 — Validação META OURO)
- [x] **META OURO ATINGIDA** (faster_whisper, p95=798.5ms < 1200ms, repeat=2000) ✅
- [x] Warm vs cold padronizado nos benches.
- [x] Barge-in medido (p95 ~60ms).
- [x] Perfis FAST/BALANCED/NOISY fechados (tiny).
- [x] Backend STT plugável (whisper.cpp/faster-whisper) ativo.
- [x] **BLOCO 2:** Robustez long-run (2000 iterações, 30–60min) validada ✅
- [x] **BLOCO 3:** Qualidade modelo tiny/small/base documentada ✅
- [x] **BLOCO 4:** Documentação final (README_FINAL.md) ✅
- [x] CPU% válido nos JSONs (219.1%, funcional) ✅
- [ ] **Próximo:** Auto-seleção bloquear whisper_cpp por padrão (usar env explícito).
- [ ] **Próximo:** Robustez 24–72h em hardware mais fraco validada.

## Papéis (resumo)
- **ARQUITETO_IO:** propõe 1 mudança com métrica-alvo e plano de teste.
- **IMPLEMENTADOR_IO:** aplica somente o escopo do ticket + teste mínimo.
- **ANALISTA_BENCH:** compara antes/depois, lista Top 10 slow runs e causa por etapa.
- **REVISOR_SENIOR:** caça race/threads/subprocess/buffers; aprova/recusa com riscos.
- **DOCUMENTADOR:** atualiza ADR/bench/README curto (o que mudou/por quê/como medir).

## Etapas recomendadas
1) **Diagrama da interface** (`DIAGRAMA_INTERFACE.svg`) — garantir que pontos de medição estão claros.
2) **Bench warm**: `PYTHONPATH=. python scripts/bench_interface.py eos_to_first_audio --audio Documentos/DOC_INTERFACE/bench_audio/voice_clean.wav --text "ok" --repeat 5 --resample` (registrar JSON se relevante).
3) **Barge-in**: `PYTHONPATH=. python scripts/bench_interface.py barge_in --audio ... --repeat 5 --resample` (stop_ms).
4) **Decisão→TTS**: medir dentro do bench ou via `voice_stage_metrics` (precisa instrumentar se faltando).
5) **Long-run**: voz real (`--voice-loop`) por 30–60min e spot-check p95; opcional 24–72h.

## Notas rápidas
- Overlap de plano só funciona com parciais (RealtimeSTT); default faster_whisper não gera parciais.
- Para GPU: validar `JARVIS_STT_BACKEND=ctranslate2` (ainda não testado).
- Quando ajustar algo, atualizar o doc curto correspondente (infra/..., testes/benchmark_interface.md).***
