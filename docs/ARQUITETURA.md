# Interface de Entrada/Saída de Voz (fonte única)

Documento único para a interface de voz do Jarvis: como o áudio entra, vira texto, é orquestrado e volta como áudio ou texto na tela.

## Visão geral do pipeline de voz
- Captura microfone em PCM mono 16 kHz (float32 na API do `sounddevice`, convertido para int16).
- VAD opcional (`webrtcvad` + `StreamingVAD`) corta silêncio e evita gravações vazias; fallback para captura de duração fixa.
- Trim opcional em Rust (`jarvis_audio.trim_until_silence`) remove silêncio de borda com pré/pós-roll.
- STT local (`faster-whisper`) gera texto; orquestrador processa e registra telemetria.
- Resposta é falada via TTS local (prioridade Piper → espeak-ng) e também exibida no console/UI.
- Não há wake word hoje: a captura é iniciada por `--voice`/`--voice-loop` ou pelo painel/atalho.

## Interface de Entrada (Input)
- Responsabilidades
  - Gravar 16 kHz mono (int16 LE) via `sounddevice`.
  - Aplicar VAD streaming quando disponível (`voz/vad.py`), com pré-roll de ~200 ms e detecção de silêncio para encerrar.
  - Fazer fallback para duração fixa se o VAD falhar ou gerar áudio curto demais.
  - Normalizar qualquer payload recebido para bytes PCM com `_coerce_pcm_bytes` (aceita bytes, bytearray, memoryview, listas de ints ou frames em bytes).
  - Opcional: trim de silêncio em Rust se `JARVIS_AUDIO_TRIM_BACKEND=rust` e módulo carregado.
  - Só envia para Whisper se detectar fala; grava vazios em telemetria (`voice_empty`) para debug.
- Componentes
  - `entrada/stt.py` (`SpeechToText`): captura, VAD, trim, escrita WAV temporária para o Whisper.
  - `voz/vad.py`: `VoiceActivityDetector` e `StreamingVAD` (webrtcvad + sounddevice/numpy).
  - Dependências: `sounddevice`, `numpy`, `faster-whisper`, `webrtcvad` (opcional), `jarvis_audio` (opcional).

## Interface de Saída (Output)
- Responsabilidades
  - Falar respostas e avisos via TTS local; nunca chama APIs pagas.
  - Priorizar Piper com modelo PT-BR (`JARVIS_PIPER_VOICE`, `JARVIS_PIPER_MODELS_DIR`), cair para espeak-ng se faltar.
  - Permitir modo silencioso (`JARVIS_TTS_MODE=none`) sem quebrar o fluxo.
  - Exibir o mesmo texto no console/UI para acompanhamento manual.
- Componentes
  - `voz/tts.py` (`TextToSpeech`): decide engine, resolve modelo Piper, fallback espeak.
  - `cerebro/orchestrator.py`: orquestra `_say` (print + TTS) e registra eventos.

## Quadro resumido — Entrada vs Saída
| Frente   | O que faz | Componentes | Formato I/O |
| --- | --- | --- | --- |
| Entrada | Captura áudio, aplica VAD/trim, transcreve para texto | `entrada/stt.py`, `voz/vad.py`, opcional `jarvis_audio` | In: PCM int16 LE mono 16 kHz; Out: texto UTF-8 |
| Saída | Converte texto em fala local | `voz/tts.py` | In: texto UTF-8; Out: áudio via Piper/espeak-ng |
| Orquestração | Encaminha texto para planos/execução e devolve resposta | `cerebro/orchestrator.py` | In: texto; Out: texto + telemetria + TTS |

## Diagrama do pipeline de voz
![Pipeline de voz](DIAGRAMA_VOZ_ENTRADA_SAIDA.svg)

- Fluxo direto: Microfone → Captura (sounddevice) → Gates (wake word futuro + VAD + speaker verify) → AEC/NS/AGC (slot futuro) → Trim (Rust `jarvis_audio`, pré/pós-roll) → STT (faster-whisper, idioma `JARVIS_STT_LANGUAGE`) → Orquestrador (planos, policy, telemetria) → TTS (Piper/espeak) → Alto-falante.
- Áudio sempre em PCM int16 mono 16 kHz; conversões e trims não mudam a amostragem.
- VAD corta silêncio antes do trim; se o áudio ficar curto, cai no fallback de duração fixa.
- AEC/NS/AGC ainda não implementados (caixa placeholder), mas o slot está reservado no fluxo.
- Saída sai em paralelo em texto (UI/console) e áudio (Piper/espeak), mantendo o mesmo conteúdo.
- Nenhuma chamada externa: todo caminho é local/self-hosted, com telemetria em `events.jsonl`.

## Regras de qualidade
- Sempre trabalhar em PCM int16 little-endian, mono, 16 kHz; não misturar listas/dtypes sem passar por `_coerce_pcm_bytes`.
- Não passar listas diretamente para trim/WAV: normalize para `bytes` antes de chamar `jarvis_audio` ou escrever `.wav`.
- Trim em Rust só com áudio bruto (sem contêiner WAV); VAD espera frames de 10/20/30 ms no mesmo formato.
- Mantém pré-roll/pós-roll mínimos (200 ms) para não cortar sílabas; evite alterar amostragem na mão.
- `stt_mode` e `tts_mode` devem ser locais (`local`) para manter a promessa 100% self-hosted.

## Integração Rust (jarvis_audio)
- Onde entra: `SpeechToText._trim_audio` chama `jarvis_audio.trim_until_silence` quando `JARVIS_AUDIO_TRIM_BACKEND=rust` e o módulo está importável.
- Contrato de tipos: recebe `bytes`/`bytearray`/`memoryview` contendo PCM int16 LE mono a 16 kHz; internamente corta em frames de 20 ms com pré-roll 200 ms, pós-roll 200 ms e parada após 300 ms de silêncio.
- Retorno: `(trimmed_bytes, speech_detected: bool, stats: dict)`; se `speech_detected=False`, o STT ignora a transcrição.
- Build/teste: `scripts/build_rust_audio.sh` instala via maturin. Cobertura em `testes/teste_stt_rust_trim.py` (trim bloqueia silêncio, normaliza lista/frames para bytes) e no fluxo de VAD (`testes/teste_vad_pre_roll.py`, `testes/teste_stt_flow.py`).

## Observabilidade
- Telemetria local em `~/.jarvis/events.jsonl` (ver `Telemetria`/`Telemetry`): eventos `voice_empty`, `voice_error`, `command.*`, `plan.*`, `action_*`.
- Flags úteis
  - `JARVIS_DEBUG_VOICE=1`: imprime tamanhos/tipos dos buffers de áudio e stacktraces de STT.
  - `JARVIS_VOICE_LOOP_SLEEP_MS` (default 150 ms): cadência do `--voice-loop`.
  - `JARVIS_STT_MODE` (`local/auto/none`), `JARVIS_STT_MODEL`, `JARVIS_AUDIO_TRIM_BACKEND` (`none`/`rust`).
  - `JARVIS_MIN_AUDIO_SECONDS` (default 1.2s) para definir o mínimo antes do fallback, `JARVIS_STT_LANGUAGE` (default `pt`), `JARVIS_WHISPER_VAD_FILTER` (0/1) para passar ao Whisper.
  - `JARVIS_TTS_MODE` (`local`/`none`), `JARVIS_PIPER_VOICE`, `JARVIS_PIPER_MODELS_DIR`.
- Checks: `python -m jarvis.app --preflight` ou `--preflight --preflight-strict` validam STT/TTS e avisam se o trim em Rust não carregou.

## Checklist (status/prioridade)
- Wake word: **faltando** (alta) — captura é acionada manualmente (`--voice`, `--voice-loop`, painel/atalho).
- VAD (webrtcvad): **ok** (média) — streaming + fallback fixo, pré-roll/pós-roll cobertos nos testes.
- AEC/NS/AGC: **faltando** (alta) — nenhum cancelamento de eco/supressão/ganho automático embutido.
- Speaker ID: **faltando** (média) — não há identificação/whitelist de locutor.
- STT local (faster-whisper): **ok** (média) — suporta `stt_mode=local/auto`, trim opcional em Rust.
- TTS local (Piper/espeak-ng): **ok** (baixa) — Piper preferido, espeak-ng fallback, modo silencioso disponível.
- Beeps/earcons: **faltando** (baixa) — sem sons de início/fim de captura.
- Logs/telemetria: **ok** (média) — `events.jsonl`, flags de debug, métricas de voz registradas.
- Trim Rust: **ok opcional** (baixa) — precisa instalar `jarvis_audio`; fallback é trim None.
