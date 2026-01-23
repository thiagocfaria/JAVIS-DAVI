# JARVIS Interface - Instrucoes para Claude Code

## Projeto
Sistema de interface de voz offline para CPU fraca (Pop!_OS).
Objetivo: atingir padrao OURO com p95 < 1200ms para eos_to_first_audio.

## Agentes Disponiveis

Use `@agente` ou leia o arquivo `.claude/agents/[nome].md` para ativar:

| Agente | Papel | Quando Usar |
|--------|-------|-------------|
| `arquiteto` | Desenha mudancas | Antes de implementar |
| `implementador` | Implementa tickets | Durante desenvolvimento |
| `analista` | Analisa benchmarks | Apos rodar benchmarks |
| `revisor` | Code review | Antes de merge |
| `documentador` | Atualiza docs | Apos mudancas |
| `testador` | Cria/roda testes | Junto com implementacao |

## Estrutura do Projeto
```
jarvis/interface/
├── entrada/      # STT, VAD, captura
├── saida/        # TTS (Piper)
├── audio/        # Utilitarios
└── infra/        # Config, profiles
```

## Comandos Essenciais

```bash
# Testes
PYTHONPATH=. pytest -q testes/

# Lint
ruff check jarvis/interface/

# Benchmark principal
PYTHONPATH=. JARVIS_STT_MODEL=tiny python scripts/bench_interface.py stt \
  --audio Documentos/DOC_INTERFACE/bench_audio/voice_clean.wav --repeat 10 --resample

# Verificar deps
python -c "from jarvis.interface.saida.tts import TTSService; print('OK')"

# Gerar bundle para NotebookLM
python scripts/build_notebooklm_bundle.py
```

## Metas OURO
| Metrica | Meta p95 | Status |
|---------|----------|--------|
| eos_to_first_audio | < 1200ms | EM PROGRESSO |
| barge_in_stop | < 80ms | A MEDIR |
| tts_first_audio | < 120ms | ATINGIDO |

## Documentos Importantes
- Plano OURO: `Documentos/DOC_INTERFACE/PLANO_OURO_INTERFACE.md`
- Estado atual: `Documentos/DOC_INTERFACE/CORRECOES_DOCINTERFACE.MD`
- Backlog: `Documentos/DOC_INTERFACE/MELHORIAS_FUTURAS.md`
- Benchmarks: `Documentos/DOC_INTERFACE/bench_history.json`

## Regras do Jogo (Plano OURO)
1. **1 mudanca por vez** - commits pequenos e focados
2. **Sempre rodar** - pytest + benchmark apos mudancas
3. **Sempre registrar** - p50/p95/p99 + config usada
4. **Se p95 piorar > 5%** - reverte
5. **Sem doc curta** - nao mergeia
