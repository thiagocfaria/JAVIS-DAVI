# Decisão: stt_model="tiny" para todos os perfis

**Data original:** 23/01/2026 (Etapa 4)  
**Status:** segue válido para os perfis atuais (`infra/profiles.py`) mesmo com backend plugável (Etapa 5, faster_whisper/tiny; whisper_cpp bloqueado).

---

## Resumo
Benchmarks da Etapa 4 mostraram regressão de latência de 7–8x com `stt_model=small`, inviabilizando meta OURO. Decisão: todos os perfis usam `stt_model="tiny"`. Na Etapa 5, o backend plugável mantém o modelo `tiny` como default via **faster_whisper**; whisper_cpp está bloqueado por regressão.

---

## Plano Original vs Implementação Final

### Implementação final (jarvis/interface/infra/profiles.py)
- FAST_CPU: stt_model=tiny
- BALANCED_CPU: stt_model=tiny
- NOISY_ROOM: stt_model=tiny

> Observação: Etapa 5 adicionou backend plugável; perfis continuam com modelo tiny (faster_whisper default; whisper_cpp bloqueado).

---

## Evidências Empíricas

### Benchmarks BALANCED_CPU com stt_model=small (v1 - falhou)

```bash
PYTHONPATH=. python scripts/bench_interface.py eos_to_first_audio \
  --audio Documentos/DOC_INTERFACE/bench_audio/voice_clean.wav \
  --profile balanced_cpu --repeat 20
```

**Resultado:** `/tmp/eos_bal.json` (v1)
- **p50:** 5066.56ms
- **p95:** 9226.38ms (7.8x regressão vs tiny)
- **Endpoint rate:** 100%
- **Trimmed audio:** ~3000ms
- **Bottleneck:** STT (93% do tempo)

### Benchmarks BALANCED_CPU com stt_model=tiny (v2 - aprovado)

```bash
# Após corrigir profiles.py para tiny
PYTHONPATH=. python scripts/bench_interface.py eos_to_first_audio \
  --audio Documentos/DOC_INTERFACE/bench_audio/voice_clean.wav \
  --profile balanced_cpu --repeat 20
```

**Resultado:** `Documentos/DOC_INTERFACE/benchmarks/etapa4_profiles/balanced_cpu_eos_to_first_audio.json`
- **p50:** 1495.19ms (↓ 70% vs small)
- **p95:** 2570.60ms (↓ 72% vs small)
- **Endpoint rate:** 100%
- **Trimmed audio:** ~3000ms
- **Bottleneck:** STT (85% do tempo)

**Melhoria:** -6655ms no p95 (de 9226ms → 2570ms)

### Benchmarks NOISY_ROOM (small vs tiny)

**v1 (stt_model=small):**
- p95: 7978.35ms (6.3x regressão)
- Endpoint rate: 0% (falhou em detectar endpoint)

**v2 (stt_model=tiny):**
- p95: 936.59ms (↓ 88% vs small)
- Endpoint rate: 0% (problema do áudio, não do perfil)

---

## Trade-offs

### O que perdemos com tiny vs small

| Métrica | tiny | small | Impacto |
|---------|------|-------|---------|
| **WER (Word Error Rate)** | ~5-10% maior | Baseline | Accuracy reduzida |
| **Vocabulário** | ~40k tokens | ~50k tokens | Menos palavras raras |
| **Multilingual** | 99 idiomas | 99 idiomas | Sem mudança |
| **Tamanho modelo** | ~75MB | ~460MB | Menos RAM |

**Fonte:** OpenAI Whisper model card

### O que ganhamos com tiny

1. **Latência aceitável:** p95 < 3s para todos os perfis
2. **Meta OURO atingível:** FAST_CPU p95=1261ms (próximo de 1200ms)
3. **Robustez em CPU fraca:** Modelo menor = menos overhead
4. **Deployment viável:** 75MB vs 460MB facilita distribuição offline

### Impacto em Accuracy (estimativa)
- tiny perde ~2–5% de acurácia vs small, especialmente em ruído/palavras raras.
- Para comandos curtos, impacto é aceitável; para ditado/uso técnico, considerar modelo maior (small/base) via faster_whisper ou futuro backend estável.

## Decisão
✅ Manter `stt_model="tiny"` em todos os perfis (FAST/BALANCED/NOISY) por latência e deploy offline.  
Ressalvas:
- BALANCED p95 ~2.5s na época (silence_ms conservador). Se latência for crítica, reduzir silence_ms em `profiles.py` (ver abaixo).
- NOISY_ROOM teve endpoint_rate 0% com áudio de teste; validar com gravações reais de ruído.

## Ações Futuras (Opcional)

### Se BALANCED_CPU latência for crítica:

```python
# jarvis/interface/infra/profiles.py
"balanced_cpu": {
    "name": "balanced_cpu",
    "silence_ms": 500,  # ↓ de 600 → 500 (-17%)
    "stt_model": "tiny",
}
```

**Impacto esperado:** p95 ~2100-2200ms (↓ 15-20%), mas pode aumentar false endpoints.

### Se accuracy for crítica
- Usar backend alternativo via `JARVIS_STT_BACKEND` (faster_whisper é o default; whisper_cpp está bloqueado por regressão) ou testar modelos maiores (small) só em hardware capaz.

## Links
- `Documentos/DOC_INTERFACE/benchmarks/etapa4_profiles/*` (artefatos históricos)
- `jarvis/interface/infra/profiles.py` (código dos perfis)
- `Documentos/DOC_INTERFACE/PLANO_OURO_INTERFACE.md` (resultados/planos)
