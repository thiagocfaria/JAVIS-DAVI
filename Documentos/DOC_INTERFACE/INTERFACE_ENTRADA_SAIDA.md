# Interface entrada/saida (documento unico)

Este documento e a fonte principal da interface de entrada/saida do Jarvis. Ele resume o fluxo, os contratos e aponta para os docs individuais de cada modulo.
Atualizado em: 2026-01-14.

## Escopo desta interface
- Entrada: captura de voz, VAD, STT, wake word, follow-up e entrada por UI/arquivo.
- Saida: TTS local e logs/feedback visivel.
- Comunicacao: inbox/log e contrato de mensagens.
- Adapters: padronizam wake word e speaker verification.

## Visao geral do fluxo
1) Voz entra via microfone (sounddevice) e vira PCM int16 16k.
2) VAD corta silencio (endpointing); opcionalmente Silero melhora fim de fala e trim Rust remove bordas.
3) STT local transcreve para texto (opcional: RealtimeSTT para streaming/parciais).
4) Texto segue para o orquestrador (fora deste escopo).
5) Saida: texto no log/UI e voz via TTS local.
6) UI/atalho/arquivo tambem injetam texto no fluxo.

## Tabela entrada vs saida
| Frente | O que faz | Formato | Modulos principais |
| --- | --- | --- | --- |
| Entrada | Captura audio, VAD/trim, STT, wake word | PCM int16 mono 16k -> texto | `jarvis/interface/entrada/stt.py`, `jarvis/interface/entrada/vad.py` |
| Entrada (texto) | UI/painel/arquivo | texto UTF-8 | `jarvis/interface/entrada/chat_ui.py`, `jarvis/interface/entrada/gui_panel.py`, `jarvis/interface/infra/chat_inbox.py` |
| Saida | TTS local + log | texto -> audio | `jarvis/interface/saida/tts.py`, `jarvis/interface/infra/chat_log.py` |

## Mapa para migracao da interface
Objetivo: consolidar tudo que e interface em `jarvis/interface/` mantendo limites claros com core/orchestrator.

### Candidatos a interface (mover)
- Entrada (voz): `jarvis/interface/entrada/stt.py`, `jarvis/interface/audio/audio_utils.py`
- Entrada (texto/UI): `jarvis/interface/entrada/app.py`, `jarvis/interface/entrada/chat_ui.py`, `jarvis/interface/entrada/gui_panel.py`, `jarvis/interface/entrada/shortcut.py`, `jarvis/interface/entrada/followup.py`, `jarvis/interface/entrada/preflight.py`
- Voz: `jarvis/interface/saida/tts.py`, `jarvis/interface/entrada/vad.py`, `jarvis/interface/entrada/speaker_verify.py`
- Adapters de voz: `jarvis/voz/adapters/*.py`
- Comunicacao de interface: `jarvis/comunicacao/chat_inbox.py`, `jarvis/comunicacao/chat_log.py`

### Limites (nao mover)
- Orquestracao e core: `jarvis/cerebro/orchestrator.py`, `jarvis/cerebro/config.py`, `jarvis/cerebro/llm.py`
- Telemetria global: `jarvis/telemetria/*` (somente consumida pela interface)
- Seguranca: `jarvis/seguranca/*` (kill switch e politicas)

## Contratos de dados (obrigatorios)
- Audio sempre em PCM int16 little-endian, mono, 16 kHz.
- Nunca passar lista direto para WAV/trim: use `coerce_pcm_bytes`.
- VAD espera frames de 10/20/30 ms no mesmo formato.
- WAV so aparece no fallback do STT (arquivo temporario) e nos benchmarks; o fluxo preferencial e PCM bruto.

## Performance e latencia (como medir)
- STT e TTS sao as partes mais pesadas; VAD e leve/moderado.
- Medir latencia: use `scripts/bench_interface.py` (STT/VAD/endpointing/TTS).
- Medir voz real: use `scripts/auto_voice_bench.py` (gera WAV + JSON).
- Resultados ficam em `Documentos/DOC_INTERFACE/bench_audio` e `Documentos/DOC_INTERFACE/bench_history.json`.
- GPU so e relevante quando o backend usar GPU (padrao e CPU).

## Limites de gravacao (env)
- `JARVIS_VOICE_MAX_SECONDS` (padrao 30, clamp 3..120) - limite do comando de voz.
- `JARVIS_VOICE_ENROLL_MAX_SECONDS` (padrao 12, clamp 5..60) - limite para cadastro de voz.

## Documentos por modulo (link direto)
### Entrada (voz)
- [interface/entrada/stt.py](./entrada_stt.md)
- [interface/audio/audio_utils.py](./entrada_audio_utils.md)
- [interface/entrada/vad.py](./voz_vad.md)
- [voz/adapters/vad_silero.py](./voz_adapters_vad_silero.md)
- [interface/entrada/followup.py](./entrada_followup.md)
- [voz/adapters/wakeword_text.py](./voz_adapters_wakeword_text.md)
- [voz/adapters/wakeword_porcupine.py](./voz_adapters_wakeword_porcupine.md)
- [voz/adapters/wakeword_openwakeword.py](./voz_adapters_wakeword_openwakeword.md)
- [voz/adapters/base.py](./voz_adapters_base.md)
- [voz/adapters/stt_realtimestt.py](./voz_adapters_stt_realtimestt.md)

### Entrada (texto/UI)
- [interface/entrada/app.py](./entrada_app.md)
- [interface/entrada/chat_ui.py](./entrada_chat_ui.md)
- [interface/entrada/gui_panel.py](./entrada_gui_panel.md)
- [interface/entrada/shortcut.py](./entrada_shortcut.md)
- [interface/infra/chat_inbox.py](./comunicacao_chat_inbox.md)

### Saida
- [interface/saida/tts.py](./voz_tts.md)
- [interface/infra/chat_log.py](./comunicacao_chat_log.md)

### Speaker verification
- [interface/entrada/speaker_verify.py](./voz_speaker_verify.md)
- [voz/adapters/speaker_resemblyzer.py](./voz_adapters_speaker_resemblyzer.md)

### Comunicacao e contratos
- [comunicacao/protocolo.py](./comunicacao_protocolo.md)

## Dependencias e testes
- [Dependencias da interface](./DEPENDENCIAS_INTERFACE.md)
- [Testes automatizados](./TESTES_INTERFACE.md)
- [Testes manuais (roteiro)](./TESTE_MANUAL.md)
- [Testes realizados (registro)](./TESTES_REALISADOS_INTERFACE.MD)
- [Benchmark/diagnostico](./benchmark_interface.md)
- [Evolucao de performance](./EVOLUCAO_PERFOMACE.MD)

## Observabilidade e debug
- Logs locais: `~/.jarvis/chat.log` e `~/.jarvis/events.jsonl`.
- Telemetria de voz: evento `voice_stage_metrics` em `events.jsonl` com `capture_ms`, `vad_ms`, `endpoint_ms`, `stt_ms`, `llm_ms`, `tts_ms`, `play_ms` e `p95` (rolling, ultimas ~200 amostras).
- Alguns campos podem vir `null` quando a etapa nao ocorre (ex.: sem fala, STT streaming).
- Debug basico: `JARVIS_DEBUG=1` (STT, speaker verify, orchestrator).
- Metrics: `JARVIS_STT_METRICS=1`, `JARVIS_VAD_METRICS=1`.

## Como manter este documento
- Sempre que um modulo entrar/sair da interface, atualize a lista acima.
- Cada modulo deve ter um doc proprio com: contratos, deps, testes e comandos.
- Benchmarks e resultados devem ser registrados em `bench_history.json` + `TESTES_REALISADOS_INTERFACE.MD`.
- **Ordem ideal de baseline**: Rodar baseline logo apos mudancas criticas (ex.: consolidacao de VAD) para deteccao precoce de regressoes. Ver `benchmark_interface.md` para detalhes.
