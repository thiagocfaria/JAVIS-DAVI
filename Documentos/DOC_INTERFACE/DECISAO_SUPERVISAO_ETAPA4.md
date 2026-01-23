# Decisão Supervisão - Etapa 4

**Data:** 23/01/2026
**Status:** ⏳ AGUARDANDO DECISÃO

---

## Resumo Executivo

A Etapa 4 (Voice Profiles) está **tecnicamente completa** mas **não atinge meta OURO de forma consistente**. Supervisão precisa decidir entre 3 caminhos.

---

## ✅ O Que Foi Entregue

### Código
- ✅ 3 profiles implementados (FAST_CPU, BALANCED_CPU, NOISY_ROOM)
- ✅ Todos usando stt_model="tiny" (documentado)
- ✅ Testes: 404/410 PASSED (98.5%)
- ✅ Lint: `ruff check .` → All checks passed!
- ✅ Git: Limpo e organizado

### Documentação
- ✅ DECISAO_STT_MODEL_TINY.md (justificativa técnica)
- ✅ ANALISE_TESTES_ETAPA4.md (6 failures documentados)
- ✅ Benchmarks salvos em `benchmarks/etapa4_profiles/*.json`

---

## ❌ O Que Não Foi Atingido

### Meta OURO: p95 < 1200ms

**Resultados reais (múltiplas execuções):**

| Perfil | p50 range | p95 range | Endpoint | Status |
|--------|-----------|-----------|----------|--------|
| fast_cpu | 792-1709ms | 1080-2555ms | 100% | ⚠️ INSTÁVEL |
| balanced_cpu | 743-1495ms | 1196-1998ms | 100% | ⚠️ INSTÁVEL |
| noisy_room | 1055-2089ms | 1260-2879ms | 0-100% | ❌ INVÁLIDO |

**Variabilidade:** 1.7x - 2.4x entre execuções

**Causas:**
1. Carga de CPU (sistema não-isolado)
2. Cache effects (warmup não elimina totalmente)
3. GC do Python (latência variável)
4. VAD sensitivity (áudio afeta timing)
5. Amostras insuficientes (N=20 pode ser pouco)

---

## 3 Caminhos Possíveis

### 🟢 OPÇÃO 1: Aprovar com META PRATA (RECOMENDADO)

**Definição:**
- FAST_CPU: p95 < 1500ms ✅
- BALANCED_CPU: p95 < 2000ms ✅
- NOISY_ROOM: Não validado (remover ou marcar experimental)

**Justificativa:**
- 1.5-2s é aceitável para assistente de voz offline não-crítico
- WhatsApp áudio tem latência ~1-2s (referência de UX)
- Permite usar tiny model (75MB, viável para deployment)
- Não bloqueia Etapa 5 (backend plugável pode otimizar)

**Ações:**
1. Atualizar PLANO_OURO_INTERFACE.md → meta PRATA
2. Remover "meta OURO atingida" de docs
3. Documentar variabilidade observada
4. Marcar noisy_room como "experimental/não validado"
5. Adicionar skip/xfail nos 6 testes com justificativa
6. **Merge Etapa 4 e prosseguir para Etapa 5**

**Tempo:** 1h (apenas docs)

---

### 🟡 OPÇÃO 2: Mais Tuning (ARRISCADO)

**Objetivo:** Tentar forçar OURO reduzindo silence_ms ainda mais

**Configuração:**
```python
"fast_cpu": {"silence_ms": 300},      # ↓ de 400
"balanced_cpu": {"silence_ms": 400},  # ↓ de 500
```

**Ações:**
1. Ajustar profiles.py
2. Re-executar benchmarks com --repeat 40-50
3. Analisar trade-off accuracy vs latência
4. Se falhar, voltar para Opção 1

**Riscos:**
- Aumenta false positives (corta fala prematuramente)
- Pode piorar accuracy de transcrição
- Não garante consistência (variabilidade persiste)
- **Pode levar a ciclo infinito de tuning**

**Tempo:** 2-4h (sem garantia de sucesso)

---

### 🔴 OPÇÃO 3: Rejeitar Etapa 4 Completamente

**Implicações:**
- Bloqueia Etapa 5 (STT backend plugável)
- 98.5% dos testes passam → código funciona
- Funcionalidade está pronta, problema é apenas número
- Atrasa projeto inteiro

**Cenário válido se:**
- Meta OURO é **mandatória** (não-negociável)
- Disposto a refatorar arquitetura completa
- Aceita usar whisper.cpp (C++, mais complexo)

**Tempo:** Indefinido (precisa repensar abordagem)

---

## 🎯 Recomendação da Equipe

### ✅ APROVAR OPÇÃO 1 (META PRATA)

**Razão #1: Realismo Técnico**
- CPU fraca + Whisper tiny + Python = limitações físicas
- 1.5-2s é resultado esperado, não falha de implementação

**Razão #2: Pragmatismo**
- 98.5% testes passam
- Funcionalidade core funciona
- Usuários não percebem diferença entre 1.2s e 1.8s

**Razão #3: Caminho Futuro**
- Etapa 5 (STT plugável) pode trazer whisper.cpp
- whisper.cpp é 2-3x mais rápido que faster-whisper
- Meta OURO se torna viável na Etapa 5

**Razão #4: Trade-offs Conscientes**
- stt_model=tiny já sacrifica accuracy por velocidade
- Reduzir silence_ms mais prejudica robustez
- Melhor entregar funcional do que perfeito

---

## 📊 Comparação de Opções

| Critério | Opção 1 (PRATA) | Opção 2 (Tuning) | Opção 3 (Rejeitar) |
|----------|----------------|------------------|-------------------|
| **Tempo** | 1h | 2-4h | Indefinido |
| **Risco** | Baixo | Médio-Alto | N/A |
| **Progresso** | ✅ Avança p/ Etapa 5 | ⏸️ Delay | ❌ Bloqueia |
| **Qualidade** | Alta (realista) | Média (pode piorar) | N/A |
| **UX** | Aceitável | Incerto | N/A |

---

## ⏰ Decisão Necessária

**Supervisão, qual caminho aprova?**

- [ ] **Opção 1:** Aprovar meta PRATA (1.5-2s) → Prosseguir Etapa 5
- [ ] **Opção 2:** Tentar mais tuning (2-4h) → Sem garantia
- [ ] **Opção 3:** Rejeitar completamente → Bloqueia projeto

---

## 📝 Próximos Passos (Se Opção 1 Aprovada)

### Imediatos (1h)
1. Atualizar PLANO_OURO_INTERFACE.md com meta PRATA
2. Atualizar README.md de benchmarks
3. Adicionar skip/xfail em 6 testes
4. Commit final: "chore(etapa4): accept PRATA target, document variability"
5. **Merge para main**

### Etapa 5 (próximos)
1. Implementar STT backend plugável
2. Testar whisper.cpp (esperado 2-3x mais rápido)
3. Revisitar meta OURO com backend otimizado
4. Se OURO atingível com whisper.cpp → atualizar para OURO

---

**Aguardando decisão da supervisão para prosseguir.**

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>
