# Changelog - Reorganização DOC_INTERFACE (Etapa 1)

**Data:** 22/01/2026
**Responsável:** ARQUITETO_IO (Claude Code)

## Sumário

Reorganização completa da documentação em `DOC_INTERFACE/` para espelhar a arquitetura do código em `jarvis/interface/` e atualização dos documentos principais para refletir o estado atual após a implementação do warmup STT+TTS.

## 1. Reorganização da Estrutura de Pastas

### Antes
```
DOC_INTERFACE/
├── [todos os .md soltos na raiz - 36 arquivos]
├── bench_audio/
└── test_audio/
```

### Depois
```
DOC_INTERFACE/
├── entrada/          # 17 arquivos de componentes de entrada
├── saida/            # 1 arquivo de componentes de saída
├── audio/            # 1 arquivo de utilitários de áudio
├── infra/            # 3 arquivos de infraestrutura
├── bench_audio/      # (mantido)
├── test_audio/       # (mantido)
└── [raiz]/           # 14 arquivos de alto nível
```

### Arquivos Movidos

#### entrada/ (17 arquivos)
- entrada_app.md
- entrada_audio_utils.md → **movido para audio/**
- entrada_chat_ui.md
- entrada_followup.md
- entrada_gui_panel.md
- entrada_preflight.md
- entrada_shortcut.md
- entrada_stt.md ✅ **ATUALIZADO**
- terceiros_realtimestt.md
- voz_adapters_base.md
- voz_adapters_speaker_resemblyzer.md
- voz_adapters_stt_realtimestt.md
- voz_adapters_vad_silero.md
- voz_adapters_wakeword_openwakeword.md
- voz_adapters_wakeword_porcupine.md
- voz_adapters_wakeword_text.md
- voz_speaker_verify.md
- voz_vad.md

#### saida/ (1 arquivo)
- voz_tts.md ✅ **ATUALIZADO**

#### audio/ (1 arquivo)
- entrada_audio_utils.md (movido de entrada/)

#### infra/ (3 arquivos)
- comunicacao_chat_inbox.md
- comunicacao_chat_log.md
- comunicacao_protocolo.md

#### raiz/ (14 arquivos - docs de alto nível)
- auto_config_voz.md
- benchmark_interface.md ✅ **ATUALIZADO**
- DEPENDENCIAS_INTERFACE.md
- DIAGRAMA_ARQUITETURA.md
- DIAGRAMA_INTERFACE.md
- GUIA_CLAUDE.md
- INTERFACE_ENTRADA_SAIDA.md
- MELHORIAS_FUTURAS.md
- orchestrator_voice.md
- PLANO_OURO_INTERFACE.md
- README.md ✅ **NOVO**
- repositorios_interface.md
- TESTE_MANUAL.md
- TESTES_INTERFACE.md

#### raiz/ (outros arquivos importantes)
- bench_history.json
- CORRECOES_DOCINTERFACE.MD
- DIAGRAMA_INTERFACE.svg
- EVOLUCAO_PERFOMACE.MD
- TESTES_REALISADOS_INTERFACE.MD
- TESTES_VOZ_SEM_MICROFONE.MD

## 2. Documentos Atualizados

### entrada/entrada_stt.md
**Mudanças:**
- Atualizado "Atualizado em" para 22/01/2026
- Adicionada seção "Warmup (implementado - Etapa 1)" documentando:
  - `_get_whisper_model(realtime=False)` + warmup transcription (linhas 658-674)
  - Benefício: evita p95 dominado por cold start
  - Uso: `--no-warmup` para desabilitar
  - Impacto medido: p95 de ~1500ms → 1077ms (META OURO atingida)
- Adicionado em "Melhorias sugeridas": "Implementar warmup STT no benchmark" marcado como resolvido

### saida/voz_tts.md
**Mudanças:**
- Atualizado "Atualizado em" para 22/01/2026
- Adicionada seção "Warmup (implementado - Etapa 1)" documentando:
  - `tts.speak(reply_text[:20])` (linhas 676-680)
  - Benefício: pré-carrega modelo Piper
  - Impacto: p95 reduzido de ~1500ms para 1077ms (combinado com warmup STT)
- Atualizada seção "Problemas conhecidos" com:
  - Barge-in lento: p95 de ~1005ms vs meta de 80ms
  - Causa raiz: `proc.wait(timeout=1)` em `_terminate_process()`
  - Correção necessária documentada
- Adicionado em "Melhorias sugeridas":
  - "Implementar warmup TTS no benchmark" marcado como resolvido
  - Correção de `_terminate_process()` prioridade P0

### benchmark_interface.md
**Mudanças:**
- Atualizado "Atualizado em" para 22/01/2026
- Adicionado `barge_in` nos cenários disponíveis
- Adicionadas flags de CLI: `--no-warmup`, `--print-text`, `--require-wake-word`
- Adicionada seção "Warmup (implementado - Etapa 1)" com detalhes da implementação
- Adicionada seção "Resultados Atuais (22/01/2026)" com:
  - eos_to_first_audio: p95 = 1077ms ✅ META OURO
  - Breakdown por etapa mostrando STT como bottleneck (88%)
  - barge_in: p95 = 1005ms 🔴 CRÍTICO
  - Causa raiz e correção necessária
- Atualizada seção "Problemas conhecidos" com detalhes dos problemas atuais
- Atualizada seção "Melhorias sugeridas" marcando itens resolvidos e priorizando correções

### README.md (NOVO)
**Conteúdo:**
- Visão geral da estrutura de pastas
- Mapa de navegação dos documentos
- Status atual (META OURO atingida)
- Pendências críticas (barge-in)
- Metas de performance (PRATA e OURO)
- Comandos úteis
- Agentes Claude disponíveis
- Regras do jogo (Plano OURO)
- Histórico de mudanças da Etapa 1

### CHANGELOG_REORGANIZACAO.md (NOVO)
Este documento.

## 3. Estado Atual do Sistema (22/01/2026)

### ✅ META OURO ATINGIDA
- **eos_to_first_audio p95:** 1077ms < 1200ms (margem: 10.3%)
- **Warmup STT+TTS:** Implementado e funcionando
- **Documentação:** Reorganizada e atualizada

### 🔴 Pendências Críticas
- **barge_in_stop_ms p95:** 1005ms (meta OURO: < 80ms)
- **Causa:** `_terminate_process()` em `jarvis/interface/saida/tts.py:618` bloqueia até 1s
- **Correção:** Remover `proc.wait()` e usar `kill()` fire-and-forget

### Breakdown de Performance (p95)
| Etapa        | Tempo (ms) | % do Total |
|--------------|------------|------------|
| endpointing  | 0.23       | 0.02%      |
| trim         | 0.02       | 0.00%      |
| **stt**      | **945.87** | **87.8%**  |
| tts          | 209.34     | 19.4%      |
| overhead     | 0.37       | 0.03%      |
| **TOTAL**    | **1076.67**| **100%**   |

## 4. Próximos Passos

### Prioridade P0 (Crítico)
- [ ] Corrigir `_terminate_process()` em `jarvis/interface/saida/tts.py` para barge-in < 80ms
- [ ] Validar correção com benchmark: `barge_in_stop_ms` p95 < 80ms

### Prioridade P1 (Alta)
- [ ] Validar estabilidade do p95 em produção por 24h
- [ ] Documentar correção do barge-in em CHANGELOG

### Prioridade P2 (Média)
- [ ] Considerar modelo `tiny.en` se áudio for sempre inglês
- [ ] Renomear campos agregados `tts_ms_p50` para `tts_total_ms_p50` (clareza)

### Prioridade P3 (Baixa)
- [ ] Explorar otimizações adicionais no STT (bottleneck de 88%)
- [ ] Considerar backends alternativos (Moonshine ONNX, whisper.cpp)

## 5. Comandos de Verificação

### Verificar estrutura
```bash
ls -la /srv/DocumentosCompartilhados/Jarvis/Documentos/DOC_INTERFACE/{entrada,saida,audio,infra}/
```

### Verificar documentos atualizados
```bash
grep "2026-01-22" /srv/DocumentosCompartilhados/Jarvis/Documentos/DOC_INTERFACE/entrada/entrada_stt.md
grep "2026-01-22" /srv/DocumentosCompartilhados/Jarvis/Documentos/DOC_INTERFACE/saida/voz_tts.md
grep "2026-01-22" /srv/DocumentosCompartilhados/Jarvis/Documentos/DOC_INTERFACE/benchmark_interface.md
```

### Rodar benchmark
```bash
PYTHONPATH=. JARVIS_STT_MODEL=tiny python scripts/bench_interface.py \
  eos_to_first_audio \
  --audio Documentos/DOC_INTERFACE/bench_audio/voice_clean.wav \
  --text "ok" \
  --repeat 20 \
  --resample
```

## 6. Lições Aprendidas

1. **Organização espelha código:** Facilita navegação e manutenção
2. **Warmup é crítico:** Redução de 28% no p95 (1500ms → 1077ms)
3. **Identificação precoce:** Benchmark de barge-in revelou problema crítico antes de produção
4. **Documentação viva:** Documentos devem refletir estado atual, não ideal

## Assinaturas

**Implementado por:** ARQUITETO_IO (Claude Code)
**Revisado por:** (Pendente)
**Data:** 22/01/2026
**Commit:** (Pendente)
