# Interface entrada/saida (documento unico)

Este documento define a API publica oficial da interface do Jarvis. Os caminhos listados aqui sao os unicos caminhos estaveis para consumo por orquestrador, scripts e testes.
Atualizado em: 2026-03-23.

## Escopo desta interface
- Entrada: captura de voz, VAD, STT, wake word, follow-up e UI textual.
- Saida: TTS local e feedback visivel.
- Infra: inbox/log de interface e presets de perfil de voz.
- Audio: contratos e utilitarios compartilhados de PCM.

## Caminhos oficiais e estaveis

### Entrada (`jarvis.interface.entrada`)
- `jarvis.interface.entrada.stt` - `SpeechToText`, `STTError`, `apply_wake_word_filter`, `check_stt_deps`, `resample_audio_float`.
- `jarvis.interface.entrada.followup` - `FollowUpSession`.
- `jarvis.interface.entrada.vad` - `VoiceActivityDetector`, `StreamingVAD`, `resolve_vad_aggressiveness`, `check_vad_available`.
- `jarvis.interface.entrada.speaker_verify` - `enroll_speaker`, `verify_speaker`, `load_voiceprint`.
- `jarvis.interface.entrada.adapters.*` - adapters de wake word, Silero, RealtimeSTT e speaker verification quando o consumidor precisar do modulo especifico.

### Saida (`jarvis.interface.saida`)
- `jarvis.interface.saida.tts` - `TextToSpeech`, `check_tts_deps`.

### Audio (`jarvis.interface.audio`)
- `jarvis.interface.audio.audio_utils` - `SAMPLE_RATE`, `BYTES_PER_SAMPLE`, `coerce_pcm_bytes`.

### Infra (`jarvis.interface.infra`)
- `jarvis.interface.infra.chat_inbox` - `ChatInbox`, `append_line`.
- `jarvis.interface.infra.chat_log` - `ChatLog`.
- `jarvis.interface.infra.voice_profile` - `auto_configure_voice_profile`.

## API agregada por pacote
Para imports curtos, os pacotes abaixo reexportam a API oficial sem mudar o contrato:
- `jarvis.interface.entrada`
- `jarvis.interface.saida`
- `jarvis.interface.audio`
- `jarvis.interface.infra`
- `jarvis.interface`

Prefira os modulos explicitos quando o contrato depender de uma implementacao especifica. Use a API agregada apenas para imports de alto nivel.

## Mapeamento dos imports publicos revisados

### Orquestrador
- `jarvis.cerebro.orchestrator` agora consome `jarvis.interface.entrada.followup`, `jarvis.interface.entrada.stt`, `jarvis.interface.entrada.adapters.speaker_resemblyzer`, `jarvis.interface.audio.audio_utils` e `jarvis.interface.infra.chat_log`.

### Scripts
- `scripts/bench_interface.py`
  - `jarvis.entrada.stt` -> `jarvis.interface.entrada.stt`
  - `jarvis.voz.vad` -> `jarvis.interface.entrada.vad`
  - `jarvis.voz.tts` -> `jarvis.interface.saida.tts`
  - `jarvis.voz.adapters` -> `jarvis.interface.entrada.adapters`
  - `jarvis.voz.speaker_verify` -> `jarvis.interface.entrada.speaker_verify`
- `scripts/measure_local_weights.py`
  - `jarvis.comunicacao.chat_log` -> `jarvis.interface.infra.chat_log`

### Testes
- Nesta arvore nao ha diretório `tests/` versionado no momento. O inventario acima cobre os imports publicos encontrados em scripts e orquestrador.

## Wrappers de compatibilidade temporaria
Os caminhos legados abaixo continuam existindo apenas como camada fina de compatibilidade, sem logica propria:
- `jarvis.entrada.*`
- `jarvis.voz.tts`
- `jarvis.voz.vad`
- `jarvis.voz.speaker_verify`
- `jarvis.comunicacao.chat_inbox`
- `jarvis.comunicacao.chat_log`

Esses wrappers nao sao caminhos oficiais novos. Eles existem somente para evitar quebra imediata durante a migracao.

## Inventario de deprecacoes
O inventario com caminhos legados, substitutos oficiais e prazo de remocao esta em [DEPRECACOES_INTERFACE.md](./DEPRECACOES_INTERFACE.md).

## Contratos obrigatorios
- Audio sempre em PCM int16 little-endian, mono, 16 kHz.
- Nunca passar lista direto para WAV/trim: use `coerce_pcm_bytes`.
- VAD espera frames de 10/20/30 ms no mesmo formato.
- O fluxo preferencial trabalha com PCM bruto; WAV fica restrito a fallback e benchmarks.

## Visao geral do fluxo
1. Voz entra via microfone e vira PCM int16 16 kHz.
2. VAD corta silencio e pode acionar adapters especializados.
3. STT local transcreve para texto e aplica wake word/follow-up.
4. O orquestrador consome o texto fora deste escopo.
5. A resposta sai por TTS e por infra de log/UI.
6. UI, atalhos e inbox tambem injetam texto no mesmo fluxo oficial.

## Documentos por modulo
### Entrada
- [interface/entrada/stt.py](./entrada_stt.md)
- [interface/audio/audio_utils.py](./entrada_audio_utils.md)
- [interface/entrada/vad.py](./voz_vad.md)
- [interface/entrada/followup.py](./entrada_followup.md)
- [interface/entrada/app.py](./entrada_app.md)
- [interface/entrada/chat_ui.py](./entrada_chat_ui.md)
- [interface/entrada/gui_panel.py](./entrada_gui_panel.md)
- [interface/entrada/shortcut.py](./entrada_shortcut.md)

### Saida e infra
- [interface/saida/tts.py](./voz_tts.md)
- [interface/infra/chat_inbox.py](./comunicacao_chat_inbox.md)
- [interface/infra/chat_log.py](./comunicacao_chat_log.md)
- [interface/entrada/speaker_verify.py](./voz_speaker_verify.md)

### Adapters oficiais expostos pela interface
- [interface adapters / vad_silero](./voz_adapters_vad_silero.md)
- [interface adapters / wakeword_text](./voz_adapters_wakeword_text.md)
- [interface adapters / wakeword_porcupine](./voz_adapters_wakeword_porcupine.md)
- [interface adapters / wakeword_openwakeword](./voz_adapters_wakeword_openwakeword.md)
- [interface adapters / base](./voz_adapters_base.md)
- [interface adapters / stt_realtimestt](./voz_adapters_stt_realtimestt.md)
- [interface adapters / speaker_resemblyzer](./voz_adapters_speaker_resemblyzer.md)

## Dependencias e validacao
- [Dependencias da interface](./DEPENDENCIAS_INTERFACE.md)
- [Testes automatizados](./TESTES_INTERFACE.md)
- [Testes manuais (roteiro)](./TESTE_MANUAL.md)
- [Testes realizados (registro)](./TESTES_REALISADOS_INTERFACE.MD)
- [Benchmark/diagnostico](./benchmark_interface.md)
- [Evolucao de performance](./EVOLUCAO_PERFOMACE.MD)

## Regra de manutencao
- Qualquer novo consumidor deve importar apenas de `jarvis.interface.*`.
- Qualquer novo wrapper legado deve ser excepcional, fino e com prazo de remocao registrado.
- Sempre que um import oficial mudar, atualize este documento e o inventario de deprecacoes na mesma alteracao.
