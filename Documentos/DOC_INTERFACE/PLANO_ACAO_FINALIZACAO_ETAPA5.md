# Plano de Ação — Finalização Etapa 5

**Data:** 2026-01-29
**Status:** 🔴 VALIDAÇÃO INCOMPLETA — 3 pendências críticas

---

## 🎯 Objetivo
Resolver erros críticos encontrados na validação e deixar META OURO 100% pronto para produção.

---

## 📋 Ações Prioritárias

### ✅ Ação 1: Corrigir Documentação (JÁ FEITO)
**Status:** ✅ COMPLETO

Commit: `ea5aecd`

Corrigido:
- [x] p99: 0.0ms → 1136.6ms
- [x] WER: tabela vs texto inconsistente
- [x] Degradação: documentada com aviso crítico
- [x] System metrics: marcado como null/pendente

---

### 🔴 Ação 2: Re-rodar BLOCO 2 com add_system_metrics.py (CRÍTICA)
**Status:** ⏳ PENDENTE

**Problema:**
```json
"pre_run_temp_celsius": null,
"pre_run_load_avg": null
```

**Solução:**
1. Re-executar benchmark long-run
2. Aplicar `add_system_metrics.py` para coleta de temperatura/carga

**Comandos:**
```bash
cd /srv/DocumentosCompartilhados/Jarvis

# Step 1: Re-rodar long-run (2000 iterações)
JARVIS_STT_BACKEND=faster_whisper JARVIS_STT_MODEL=tiny \
PYTHONPATH=. python scripts/bench_interface.py eos_to_first_audio \
  --audio Documentos/DOC_INTERFACE/bench_audio/voice_clean_16k.wav \
  --text "ola jarvis" \
  --repeat 2000 \
  --json Documentos/DOC_INTERFACE/benchmarks/longrun_2000_iter_v2.json

# Step 2: Adicionar system metrics ao JSON
python scripts/add_system_metrics.py \
  Documentos/DOC_INTERFACE/benchmarks/longrun_2000_iter_v2.json

# Step 3: Analisar resultado
python scripts/analyze_longrun.py \
  Documentos/DOC_INTERFACE/benchmarks/longrun_2000_iter_v2.json
```

**Tempo estimado:** 30-60 minutos

**Resultado esperado:**
- JSON com pre_run_temp_celsius e pre_run_load_avg preenchidos
- Análise de degradação com contexto de temperatura/carga

---

### 🔴 Ação 3: Investigar e Documentar Degradação (CRÍTICA)
**Status:** ⏳ PENDENTE

**Problema identificado:**
```
⚠️  DEGRADATION DETECTED: Slow runs clustered in late iterations
   Late runs: 10/10 (> 70%)
```

**O que precisa:**
1. Entender causa raiz (thermal throttling? GC? Outra?)
2. Definir se é aceitável para produção
3. Se não aceitável, ajustar configuração ou reiniciar

**Investigação recomendada:**
```bash
# Analisar outliers do long-run
python scripts/analyze_longrun.py \
  Documentos/DOC_INTERFACE/benchmarks/longrun_2000_iter_v2.json > /tmp/analysis.txt

# Verificar se há dados em ./out/
ls -lah ./out/bench_outliers*/

# Considerar re-rodar com:
# - Outras configurações de CPU
# - Diferentes threads count
# - Diferentes modelos STT
```

**Documentar em:** README_FINAL.md + CORRECOES_BLOCO4_ETAPA5.md

---

### 🟡 Ação 4: Revisar Deletions de Etapa 4 (MÉDIA PRIORIDADE)
**Status:** ⏳ PENDENTE

**Problema:**
Commit `80cbb14` deletou 19 arquivos da Etapa 4:
- DECISAO_STT_MODEL_TINY.md
- DIAGRAMA_ARQUITETURA.md
- MELHORIAS_FUTURAS.md
- E outros 16 arquivos

Isto não era escopo da validação Etapa 5.

**Opção A: Reverter (RECOMENDADO)**
```bash
git revert 80cbb14 -m 1
git commit -m "revert: restore deleted Etapa 4 files for historical reference"
```

**Opção B: Justificar em novo commit**
```bash
# Análise dos arquivos deletados
git show 80cbb14 --name-status | grep "^D" > /tmp/deletions.txt

# Criar novo commit com reasoning
git commit -m "docs: explicitly archive Etapa 4 files

Deletions intentional per requirement XYZ:
  - File1: reason
  - File2: reason
  ...
"
```

**Recomendação:** Opção A (mais simples, preserva histórico)

---

## ✅ Ações Completadas

| Ação | Commit | Status |
| --- | --- | --- |
| Corrigir documentação | ea5aecd | ✅ |
| Documentar problemas | ea5aecd | ✅ |
| Criar checklist | ea5aecd | ✅ |

---

## 📊 Timeline de Execução

```
Agora (29/01, ~07:00)
│
├─ Ação 1: Documentação ✅ PRONTO
│
├─ Ação 2: Re-rodar BLOCO 2 ⏳ (30-60 min)
│           └─ Aplicar add_system_metrics.py
│
├─ Ação 3: Investigar degradação ⏳ (15-30 min)
│           └─ Documentar causa raiz
│
├─ Ação 4: Revisar deletions ⏳ (5-10 min)
│           └─ Reverter ou justificar
│
└─ Final: Novo commit com tudo ✅
           └─ Marcar como "CONCLUÍDO"

Total: ~1.5 - 2 horas
```

---

## 🎯 Definição de "Completo"

Validação será considerada **100% CONCLUÍDA** quando:

- [x] BLOCO 2 rodou com 2000 iterações
- [x] BLOCO 3 completou WER + latência
- [x] BLOCO 4 documentação gerada sem erros
- [ ] System metrics coletados (Ação 2)
- [ ] Degradação investigada e justificada (Ação 3)
- [ ] Deletions de Etapa 4 revistos (Ação 4)
- [ ] README_FINAL.md atualizado com v2
- [ ] Novo commit marcando "VALIDAÇÃO COMPLETA"
- [ ] Nenhuma pendência aberta

---

## 🚀 Próximo Passo

**AGORA:** Executar Ação 2 (re-rodar BLOCO 2 com add_system_metrics.py)

```bash
# Execute o comando acima para começar
```

---

**Responsável:** Usuário
**Deadline:** Quanto antes possível
**Bloqueio:** Nenhum merge/deploy até 100% completo

---

**Data criação:** 2026-01-29 07:05:00 UTC
**Versão:** 1.0
