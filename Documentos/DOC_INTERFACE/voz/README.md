# Docs da camada jarvis/voz/

- Papel: documentar os adapters e módulos de compatibilidade em `jarvis/voz/` que o STT/wake word usam (Porcupine, OpenWakeWord, Silero VAD, RealtimeSTT, Resemblyzer).
- Por que separado de `entrada/`? O código real está em `jarvis/voz/` (mantém compatibilidade retro) enquanto `jarvis/interface/entrada/` usa esses adapters. Manter esta pasta evita misturar com a saída (`jarvis/interface/saida/`) e reflete a árvore do código.

## Arquivos
- `adapters/voz_adapters_*.md` — cada adapter (wake word, VAD Silero, RealtimeSTT recorder, speaker verification).
- `terceiros_realtimestt.md` — cópia vendorizada do RealtimeSTT e como habilitar/validar.

## Quando atualizar
- Sempre que mudar um adapter em `jarvis/voz/adapters/*.py` ou o bundle vendorizado em `jarvis/third_party/realtimestt`.
