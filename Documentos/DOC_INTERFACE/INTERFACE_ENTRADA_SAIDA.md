# Interface entrada/saida (documento unico)

Este documento e a fonte principal da interface de entrada/saida do Jarvis. Ele resume o fluxo, os contratos e aponta para os docs individuais de cada modulo.

## Escopo desta interface
- Entrada: captura de voz, VAD, STT, wake word, follow-up e entrada por UI/arquivo.
- Saida: TTS local e logs/feedback visivel.
- Comunicacao: inbox/log e contrato de mensagens.
- Adapters: padronizam wake word e speaker verification.

## Visao geral do fluxo
1) Voz entra via microfone (sounddevice) e vira PCM int16 16k.
2) VAD corta silencio; opcionalmente trim Rust remove bordas.
3) STT local transcreve para texto.
4) Texto segue para o orquestrador (fora deste escopo).
5) Saida: texto no log/UI e voz via TTS local.
6) UI/atalho/arquivo tambem injetam texto no fluxo.

## Tabela entrada vs saida
| Frente | O que faz | Formato | Modulos principais |
| --- | --- | --- | --- |
| Entrada | Captura audio, VAD/trim, STT, wake word | PCM int16 mono 16k -> texto | `jarvis/entrada/stt.py`, `jarvis/voz/vad.py` |
| Entrada (texto) | UI/painel/arquivo | texto UTF-8 | `jarvis/entrada/chat_ui.py`, `jarvis/entrada/gui_panel.py`, `jarvis/comunicacao/chat_inbox.py` |
| Saida | TTS local + log | texto -> audio | `jarvis/voz/tts.py`, `jarvis/comunicacao/chat_log.py` |

## Contratos de dados (obrigatorios)
- Audio sempre em PCM int16 little-endian, mono, 16 kHz.
- Nunca passar lista direto para WAV/trim: use `coerce_pcm_bytes`.
- VAD espera frames de 10/20/30 ms no mesmo formato.

## Performance e latencia (como medir)
- STT e TTS sao as partes mais pesadas; VAD e leve/moderado.
- Medir CPU/RAM: use `/usr/bin/time -v <comando>` + `top`/`htop`.
- Medir latencia: capture timestamps no log e compare inicio/fim do comando.
- GPU: so relevante se algum engine usar GPU (nao e o caso no fluxo padrao).

## Limites de gravacao (env)
- `JARVIS_VOICE_MAX_SECONDS` (padrao 30, clamp 3..120) - limite do comando de voz.
- `JARVIS_VOICE_ENROLL_MAX_SECONDS` (padrao 12, clamp 5..60) - limite para cadastro de voz.

## Documentos por modulo (link direto)
### Entrada (voz)
- [entrada/stt.py](./entrada_stt.md)
- [entrada/audio_utils.py](./entrada_audio_utils.md)
- [voz/vad.py](./voz_vad.md)
- [entrada/followup.py](./entrada_followup.md)
- [voz/adapters/wakeword_text.py](./voz_adapters_wakeword_text.md)
- [voz/adapters/base.py](./voz_adapters_base.md)

### Entrada (texto/UI)
- [entrada/app.py](./entrada_app.md)
- [entrada/chat_ui.py](./entrada_chat_ui.md)
- [entrada/gui_panel.py](./entrada_gui_panel.md)
- [entrada/shortcut.py](./entrada_shortcut.md)
- [comunicacao/chat_inbox.py](./comunicacao_chat_inbox.md)

### Saida
- [voz/tts.py](./voz_tts.md)
- [comunicacao/chat_log.py](./comunicacao_chat_log.md)

### Speaker verification
- [voz/speaker_verify.py](./voz_speaker_verify.md)
- [voz/adapters/speaker_resemblyzer.py](./voz_adapters_speaker_resemblyzer.md)

### Comunicacao e contratos
- [comunicacao/protocolo.py](./comunicacao_protocolo.md)

## Dependencias e testes
- [Dependencias da interface](./DEPENDENCIAS_INTERFACE.md)
- [Testes da interface](./TESTES_INTERFACE.md)

## Observabilidade e debug
- Logs locais: `~/.jarvis/chat.log` e `~/.jarvis/events.jsonl`.
- Debug basico: `JARVIS_DEBUG=1` (STT, speaker verify, orchestrator).

## Como manter este documento
- Sempre que um modulo entrar/sair da interface, atualize a lista acima.
- Cada modulo deve ter um doc proprio com: contratos, deps, testes e comandos.
