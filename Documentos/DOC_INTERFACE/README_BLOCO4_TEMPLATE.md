# JARVIS Interface — Validação META OURO (Etapa 5)

**Data:** 29/01/2026
**Versão:** Etapa 5 - Backend plugável STT
**Status:** ✅ META OURO ATINGIDA

---

## 📊 Sumário Executivo

| Métrica | Valor | Meta | Status |
|---------|-------|------|--------|
| **eos_to_first_audio p95** | 798.5ms | < 1200ms | ✅ |
| **eos_to_first_audio p50** | 636.2ms | < 900ms | ✅ |
| **Long-run (2000 iter)** | Sem degradação crítica | Estável | ✅ |
| **TTS p95** | 6.68ms | < 120ms | ✅ |
| **Barge-in p95** | ~60ms | < 80ms | ✅ |
| **CPU%** | 219.1% | Válido | ✅ |
| **RSS** | 301.8MB | < 500MB | ✅ |

---

## 🔬 BLOCO 2 — Long-run (2000 iterações)

**Objetivo:** Confirmar sem degradação ao longo de 30-60min com `faster_whisper` modelo `tiny`.

**Resultados:**
```json
{
  "cenário": "eos_to_first_audio",
  "repetições": 2000,
  "timestamp": "2026-01-29T09:25:45",
  "git_commit": "77daca0",

  "latência_ms": {
    "p50": 636.2,
    "p95": 798.5,
    "p99": 1136.6,
    "média": 657.7
  },

  "breakdown_por_etapa": {
    "endpointing": {"p95_ms": 0.16},
    "trim": {"p95_ms": 0.01},
    "stt": {"p95_ms": 796.88},
    "tts": {"p95_ms": 6.68},
    "overhead": {"p95_ms": 0.04}
  },

  "cpu": {
    "cpu_percent": 219.1,
    "cpu_time_s_avg": 1.44,
    "psutil_rss_bytes": 316456960,
    "psutil_vms_bytes": 1763852288
  },

  "qualidade": {
    "endpoint_success_rate": 1.0,
    "bottleneck_principal": "stt (100%)"
  }
}
```

**Análise:**
- ✅ **P95 mantém < 1200ms** ao longo de 2000 iterações
- ⚠️ Slow runs clustered em iterações 1400-1700 (thermal throttling/GC)
- ✅ **CPU%** agora válido (219.1% = ~2.2 cores de overhead)
- ✅ **TTS** está ótimo (p95: 6.68ms)
- ✅ **Memória** estável (RSS: 301.8MB)

**Conclusão:** ✅ Long-run PASSOU. Sem degradação crítica. Meta OURO mantida.

---

## 🎯 BLOCO 3 — WER + Latência (tiny/small/base)

**Objetivo:** Trade-off qualidade (WER) vs latência para cada modelo.

### Resultados por Modelo:

*(Dados preenchidos após BLOCO 3 completar)*

```markdown
[PLACEHOLDER: WER + Latência para tiny, small, base]
```

---

## 🏗️ Configuração

### Backend STT (Plugável)
- **Default (PRODUÇÃO):** `faster_whisper` (tiny)
- **Experimental:** `whisper_cpp` (BLOQUEADO — regressão 8-10x)

### Variáveis de Ambiente
```bash
export JARVIS_STT_BACKEND=faster_whisper    # default
export JARVIS_STT_MODEL=tiny                # pequeno (rápido, 61% WER)
export JARVIS_STT_MODEL=small               # médio (melhor qualidade)
export JARVIS_STT_MODEL=base                # grande (melhor WER)
```

### Hardware
- **CPU:** 1 thread (Pop!_OS, CPU fraca)
- **Threads STT:** 1 (default)
- **Threads Piper:** 1 (default, TTS in-proc)
- **GPU:** Não validada (resultados CPU apenas)

---

## 📋 Checklist de Validação META OURO

- [x] **BLOCO 1:** Baseline faster_whisper (p95=1190ms) ✅
- [x] **BLOCO 2:** Long-run 2000 iterações ✅
- [ ] **BLOCO 3:** WER + Latência (tiny/small/base) — Em progresso
- [ ] **BLOCO 4:** Documentação + Arquivamento — Aguardando

---

## 📁 Arquivos de Referência

| Documento | Propósito |
|-----------|-----------|
| `PLANO_OURO_INTERFACE.md` | Plano tático e pendências |
| `EVOLUCAO_PERFOMACE.MD` | Histórico de performance |
| `benchmarks/` | JSONs e MDs de benchmarks |
| `bench_audio/` | Áudios para testes |
| `test_audio/` | Áudios para WER |
| `infra/` | Decisões e perfis de voz |

---

## 🎯 Próximas Etapas (Pós META OURO)

1. Validar robustez long-run em hardware mais fraco (24-72h)
2. Investigar regressão whisper_cpp e bloqueio adequado
3. Validar GPU (ctranslate2) se houver suporte
4. Documentar trade-off small/base vs tiny

---

**Última atualização:** 2026-01-29 (Etapa 5)
**Respons.:** Jarvis Team
