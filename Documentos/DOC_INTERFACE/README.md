# DOC_INTERFACE - Documentação da Interface de Entrada/Saída

Documentação técnica do sistema de interface de voz offline do Jarvis (Pop!_OS, CPU fraca).

## Estrutura de Pastas

A documentação está organizada espelhando a arquitetura do código em `jarvis/interface/`:

```
DOC_INTERFACE/
├── entrada/          # Documentação de componentes de entrada
│   ├── entrada_stt.md              # STT (Speech-to-Text)
│   ├── entrada_app.md              # Aplicação entrada
│   ├── entrada_preflight.md        # Verificação pré-voo
│   ├── voz_vad.md                  # VAD (Voice Activity Detection)
│   ├── voz_speaker_verify.md       # Verificação de speaker
│   ├── voz_adapters_*.md           # Adaptadores (RealtimeSTT, Silero, etc.)
│   └── terceiros_realtimestt.md    # Integração RealtimeSTT
│
├── saida/            # Documentação de componentes de saída
│   └── voz_tts.md                  # TTS (Text-to-Speech) - Piper
│
├── audio/            # Documentação de utilitários de áudio
│   └── entrada_audio_utils.md      # Utilidades de áudio
│
├── infra/            # Documentação de infraestrutura
│   ├── comunicacao_chat_inbox.md   # Chat inbox
│   ├── comunicacao_chat_log.md     # Chat log
│   └── comunicacao_protocolo.md    # Protocolos de comunicação
│
├── bench_audio/      # Áudios de referência para benchmarks
├── test_audio/       # Áudios de teste
│
└── [raiz]/           # Documentos de alto nível
    ├── PLANO_OURO_INTERFACE.md           # Plano para atingir métricas OURO
    ├── CORRECOES_DOCINTERFACE.MD         # Correções e estado atual
    ├── MELHORIAS_FUTURAS.md              # Backlog de melhorias
    ├── benchmark_interface.md            # Documentação de benchmarks
    ├── DIAGRAMA_INTERFACE.md             # Diagrama de arquitetura
    ├── DIAGRAMA_INTERFACE.svg            # Diagrama visual
    ├── bench_history.json                # Histórico de benchmarks
    ├── EVOLUCAO_PERFOMACE.MD             # Evolução de performance
    └── DEPENDENCIAS_INTERFACE.md         # Dependências do sistema
```

## Documentos Principais

### Por onde começar
1. **PLANO_OURO_INTERFACE.md** - Roadmap executável com agentes Claude
2. **DIAGRAMA_INTERFACE.md** - Visão arquitetural do sistema
3. **CORRECOES_DOCINTERFACE.MD** - Estado atual e baseline

### Componentes Críticos
- **entrada/entrada_stt.md** - STT (Whisper) com warmup implementado
- **saida/voz_tts.md** - TTS (Piper) com warmup implementado
- **benchmark_interface.md** - Benchmarks e métricas (META OURO atingida)

## Status Atual (22/01/2026 - Etapa 1)

### ✅ META OURO ATINGIDA
- **eos_to_first_audio p95:** 1077ms (meta: < 1200ms, margem: 10.3%)
- **Warmup STT+TTS:** Implementado e funcionando
- **Bottleneck identificado:** STT é responsável por ~88% do tempo total

### 🔴 Pendências Críticas
- **barge_in_stop_ms p95:** 1005ms (meta OURO: < 80ms) - REQUER CORREÇÃO
- **Causa:** `_terminate_process()` bloqueia até 1s esperando processo terminar

## Metas de Performance

### PRATA
- `eos_to_first_audio_ms` p95 ≤ 1200–1500ms ✅
- `barge_in_stop_ms` p95 ≤ 120ms 🔴
- `decision_to_tts_first_audio_ms` p95 ≤ 200ms

### OURO
- `eos_to_first_audio_ms` p95 ≤ 900–1200ms ✅
- `barge_in_stop_ms` p95 ≤ 80ms 🔴
- `decision_to_tts_first_audio_ms` p95 ≤ 120ms
- Estabilidade 24–72h

## Comandos Úteis

### Testes
```bash
PYTHONPATH=. pytest -q testes/
```

### Lint
```bash
ruff check jarvis/interface/
```

### Benchmark Principal (com warmup)
```bash
PYTHONPATH=. JARVIS_STT_MODEL=tiny python scripts/bench_interface.py \
  eos_to_first_audio \
  --audio Documentos/DOC_INTERFACE/bench_audio/voice_clean.wav \
  --text "ok" \
  --repeat 20 \
  --resample
```

### Benchmark Barge-in
```bash
PYTHONPATH=. python scripts/bench_interface.py barge_in \
  --text "Esta é uma frase longa para testar o barge-in" \
  --repeat 20
```

## Agentes Claude Disponíveis

Use `@agente` ou leia o arquivo `.claude/agents/[nome].md` para ativar:

| Agente | Papel | Quando Usar |
|--------|-------|-------------|
| `arquiteto` | Desenha mudanças | Antes de implementar |
| `implementador` | Implementa tickets | Durante desenvolvimento |
| `analista` | Analisa benchmarks | Após rodar benchmarks |
| `revisor` | Code review | Antes de merge |
| `documentador` | Atualiza docs | Após mudanças |
| `testador` | Cria/roda testes | Junto com implementação |

## Regras do Jogo (Plano OURO)

1. **1 mudança por vez** - commits pequenos e focados
2. **Sempre rodar** - pytest + benchmark após mudanças
3. **Sempre registrar** - p50/p95/p99 + config usada
4. **Se p95 piorar > 5%** - reverte
5. **Sem doc curta** - não mergeia

## Histórico de Mudanças

### Etapa 1 (22/01/2026)
- ✅ Implementado warmup STT (`_get_whisper_model(realtime=False)` + transcription warmup)
- ✅ Implementado warmup TTS (`tts.speak(reply_text[:20])`)
- ✅ META OURO atingida: p95 = 1077ms < 1200ms
- ✅ Reorganização da documentação em pastas (entrada/, saida/, audio/, infra/)
- 🔴 Identificado problema crítico: barge_in p95 = 1005ms (requer correção urgente)
