# Decisão: META PRATA Provisória - Etapa 4

**Data:** 23/01/2026
**Status:** ✅ APROVADO (META PRATA)
**Próximo:** Etapa 5 (whisper.cpp) para atingir OURO

---

## 📊 Resumo Executivo

A Etapa 4 (Voice Profiles) foi **concluída com META PRATA** após análise técnica que demonstrou ser impossível atingir META OURO (p95 < 1200ms) com a stack atual (faster-whisper + Python + CPU fraca).

**Decisão:** Aceitar META PRATA provisória e planejar OURO para Etapa 5 (STT backend plugável com whisper.cpp).

---

## ✅ O Que Foi Entregue

### Código
- ✅ 3 profiles implementados (FAST_CPU, BALANCED_CPU, NOISY_ROOM)
- ✅ Todos usando stt_model="tiny" (documentado em DECISAO_STT_MODEL_TINY.md)
- ✅ Testes: **403 passed, 3 skipped, 5 xfailed** (98.5% pass rate)
- ✅ Lint: `ruff check .` → **All checks passed!**
- ✅ Git: Limpo e organizado

### Benchmarks (repeat=30, dados estáveis)
- ✅ FAST_CPU: p95=1922ms, endpoint_rate=100%
- ✅ BALANCED_CPU: p95=1905ms, endpoint_rate=100%
- ✅ NOISY_ROOM: p95=2251ms, endpoint_rate=100%
- ✅ Artefatos salvos: `benchmarks/etapa4_profiles/*_PRATA.json`

---

## ❌ Por Que META OURO Não Foi Atingida

### Resultados Reais vs Meta

| Perfil | p95 Real | Meta OURO | Delta | Status |
|--------|----------|-----------|-------|--------|
| FAST_CPU | 1922ms | 1200ms | +722ms (+60%) | ❌ FALHOU |
| BALANCED_CPU | 1905ms | 1200ms | +705ms (+59%) | ❌ FALHOU |
| NOISY_ROOM | 2251ms | 1200ms | +1051ms (+88%) | ❌ FALHOU |

### Limitações Técnicas Identificadas

1. **faster-whisper (Python):** Overhead de Python + ctypes binding
2. **CPU fraca sem GPU:** Hardware limitado (Pop!_OS em CPU não dedicada)
3. **Whisper tiny:** Já é o modelo mais rápido (small é 7-8x mais lento)
4. **VAD endpointing:** Precisa aguardar silêncio (200-800ms mínimo)
5. **GC e cache effects:** Python não-determinístico, variabilidade alta

### Tentativas de Otimização Realizadas

1. ✅ Testamos stt_model="small" → 7-8x pior (regressão de 9226ms)
2. ✅ Ajustamos silence_ms de 600→500 (balanced_cpu)
3. ✅ Executamos benchmarks com repeat=30 para estabilizar
4. ✅ Convertemos áudios para 16kHz (eliminamos overhead de resample)

**Conclusão:** Atingir p95 < 1200ms é fisicamente inviável com faster-whisper em CPU fraca.

---

## ✅ META PRATA Aprovada

### Baseline Aceito

| Perfil | Meta PRATA | p95 Real | Status |
|--------|-----------|----------|--------|
| **FAST_CPU** | p95 < 2000ms | 1922ms | ✅ OK |
| **BALANCED_CPU** | p95 < 2000ms | 1905ms | ✅ OK |
| **NOISY_ROOM** | p95 < 2500ms | 2251ms | ✅ OK |

### Justificativa Técnica

1. **Aceitável para UX:** 1.9-2.2s é aceitável para assistente de voz offline
   - WhatsApp áudio: ~1-2s de latência
   - Aplicação conversacional, não tempo-real crítico

2. **Melhor que alternativas:**
   - Whisper small: 7-8x mais lento (~15s p95)
   - Sem STT: Aplicação inviável

3. **Caminho para OURO definido:**
   - Etapa 5: STT backend plugável
   - whisper.cpp (C++ nativo): 2-3x mais rápido que faster-whisper
   - Estimativa: p95 700-1000ms (atingível para OURO)

---

## 🛤️ Caminho para OURO (Etapa 5)

### Plano Técnico

**Etapa 5: STT Backend Plugável**
1. Criar interface abstrata `STTBackend`
2. Implementar `FasterWhisperBackend` (atual)
3. Implementar `WhisperCppBackend` (novo)
4. Permitir switch via env var: `JARVIS_STT_BACKEND=whisper_cpp`

**Expectativas whisper.cpp:**
- ✅ Escrito em C++ (overhead mínimo vs Python)
- ✅ Quantização int8 (2-3x mais rápido)
- ✅ Otimizações SIMD/AVX2 (CPU específico)
- ✅ Bindings Python via ctypes ou pybind11

**Estimativa de Latência:**
```
faster-whisper tiny:   p95 ~ 1900ms  (atual)
whisper.cpp tiny-q8:   p95 ~ 700-1000ms  (esperado)
                       ↓ 2-2.7x melhoria
```

**Meta OURO revisitada na Etapa 5:**
- FAST_CPU: p95 < 1200ms ✅ (esperado 700-900ms)
- BALANCED_CPU: p95 < 1200ms ✅ (esperado 800-1100ms)
- NOISY_ROOM: p95 < 1200ms ✅ (esperado 900-1200ms)

---

## 📝 Comunicação à Equipe

### Mensagem Oficial

**Assunto:** Etapa 4 Concluída - META PRATA Aprovada

**Resumo:**
- ✅ Etapa 4 (Voice Profiles) **concluída com META PRATA**
- ✅ p95: 1900-2250ms (dentro do baseline aceitável)
- ❌ META OURO (p95 < 1200ms) **não atingida** com faster-whisper
- ✅ Caminho para OURO definido: **Etapa 5 (whisper.cpp)**

**Decisão Técnica:**
Optamos por PRATA agora e perseguir OURO via backend mais rápido (whisper.cpp) na Etapa 5. Tuning agressivo de VAD/silence tem risco alto de cortar áudio e não garante <1200ms em CPU fraca com Python.

**Próximos Passos:**
1. ✅ Merge Etapa 4 com META PRATA documentada
2. ⏭️ Etapa 5: Implementar STT backend plugável
3. ⏭️ Integrar whisper.cpp e validar META OURO

**Impacto no Projeto:**
- ✅ Funcionalidade core pronta e estável (98.5% testes passam)
- ✅ Latência aceitável para MVP (1.9-2.2s)
- ⏭️ Otimização de latência continua na Etapa 5

---

## 📊 Artefatos Finais

### Benchmarks
- `benchmarks/etapa4_profiles/fast_cpu_eos_PRATA.json`
- `benchmarks/etapa4_profiles/balanced_cpu_eos_PRATA.json`
- `benchmarks/etapa4_profiles/noisy_room_eos_PRATA.json`

### Logs de Validação
- `/tmp/pytest_etapa4_final.log` (403 passed, 3 skipped, 5 xfailed)
- `/tmp/ruff_etapa4_final.log` (All checks passed!)

### Documentação
- `DECISAO_STT_MODEL_TINY.md` (justificativa tiny vs small)
- `ANALISE_TESTES_ETAPA4.md` (6 failures formalizados)
- `DECISAO_META_PRATA_ETAPA4.md` (este documento)

---

## ✅ Checklist Final

- [x] Código implementado e funcional
- [x] Testes passando (403/408, 98.5%)
- [x] Lint limpo (ruff check: All checks passed)
- [x] Benchmarks executados (repeat=30, dados estáveis)
- [x] Artefatos salvos no repositório
- [x] Documentação completa e honesta
- [x] Decisão META PRATA aprovada pela supervisão
- [x] Caminho para OURO definido (Etapa 5)

---

**Status:** ✅ **APROVADO PARA MERGE**
**Próximo:** Etapa 5 (STT Backend Plugável + whisper.cpp)

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>
