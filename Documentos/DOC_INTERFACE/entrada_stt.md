# entrada/stt.py

- Caminho: `jarvis/entrada/stt.py`
- Papel: capturar audio, aplicar VAD/trim e transcrever localmente.
- Onde entra no fluxo: usado pelo orquestrador no modo voz.
- Atualizado em: 2026-01-11 (revisado com Silero opcional)

## Responsabilidades
- Capturar audio (sounddevice) em SR nativo e reamostrar para 16 kHz.
- VAD streaming quando possivel; fallback para gravacao fixa.
- Coercao de tipos para PCM bytes int16.
- Wake word opcional com filtro de fronteira.
- Trim opcional via Rust (`jarvis_audio`).
- Aplicar AEC simples (quando habilitado) antes do STT.
- `transcribe_with_vad` usa captura com VAD ate silencio.
- `transcribe_once` usa captura fixa (com VAD streaming se houver).

## Entrada e saida
- Entrada: microfone ou bytes PCM.
- Saida: texto transcrito (str) e opcionalmente `audio_bytes` + `speech_detected`.
- Contrato: PCM int16 mono 16 kHz (little-endian).
- Nota: `transcribe_audio_bytes(...)` permite transcrever audio externo sem acessar microfone.
- Nota: `on_partial` emite texto incremental durante a decodificacao.

## Configuracao (env/config)
- `JARVIS_STT_MODE` (config `stt_mode`)
- `JARVIS_STT_MODEL` e `stt_model_size`
- `JARVIS_STT_REALTIME_MODEL` (modelo separado para parciais)
- `JARVIS_STT_LANGUAGE` ("pt" ou "auto")
- `JARVIS_STT_MIN_AUDIO_MS`
- `JARVIS_STT_MIN_GAP_SECONDS` (debounce entre gravacoes)
- `JARVIS_STT_ALLOWED_LATENCY_MS` (descarta transcricao muito lenta)
- `JARVIS_STT_NORMALIZE_AUDIO` (1 para normalizar audio antes do STT)
- `JARVIS_STT_NORMALIZE_TARGET` (pico alvo, ex: 0.98)
- `JARVIS_STT_NORMALIZE_MAX_GAIN` (limite de ganho)
- `JARVIS_STT_EARLY_TRANSCRIBE_ON_SILENCE` (aceita audio curto quando o VAD detecta fala)
- `JARVIS_STT_MAX_BUFFER_SECONDS` (limite maximo do buffer capturado)
- `JARVIS_VAD_SILENCE_MS` (duracao de silencio para encerrar)
- `JARVIS_VAD_PRE_ROLL_MS` (buffer antes da fala)
- `JARVIS_VAD_POST_ROLL_MS` (buffer depois da fala)
- `JARVIS_VAD_MAX_SECONDS` (limite maximo do streaming VAD)
- `JARVIS_SILERO_DEACTIVITY` (usa Silero para fim de fala)
- `JARVIS_SILERO_SENSITIVITY` (sensibilidade 0-1)
- `JARVIS_SILERO_USE_ONNX` (ativa ONNX quando disponivel)
- `JARVIS_SILERO_AUTO_DOWNLOAD` (baixa o modelo no primeiro uso)
- `JARVIS_WHISPER_VAD_FILTER` (filtro VAD do Whisper)
- `JARVIS_STT_BEAM_SIZE`, `JARVIS_STT_BEST_OF` (qualidade x latencia)
- `JARVIS_STT_TEMPERATURE` (temperatura do Whisper)
- `JARVIS_STT_INITIAL_PROMPT` (prompt inicial para orientar)
- `JARVIS_STT_SUPPRESS_TOKENS` (lista de tokens a suprimir)
- `JARVIS_STT_WARMUP` (1 ativa warmup do modelo)
- `JARVIS_STT_WARMUP_SECONDS` (duracao do warmup)
- `JARVIS_STT_MIN_PEAK` (limiar de pico quando nao ha VAD/Rust)
- `JARVIS_MIN_AUDIO_SECONDS`
- `JARVIS_AUDIO_DEVICE`
- `JARVIS_AUDIO_CAPTURE_SR`
- `JARVIS_REQUIRE_WAKE_WORD`, `JARVIS_WAKE_WORD`
- `JARVIS_DEBUG`
- `JARVIS_STT_METRICS` (1 para logar duracoes)
- `stt_audio_trim_backend` (config)
- `JARVIS_VAD_PREPROCESS` (1 habilita NS/AGC leve antes do VAD)
- `JARVIS_AUDIO_AGC_TARGET_RMS`, `JARVIS_AUDIO_AGC_MAX_GAIN`, `JARVIS_AUDIO_NS_GATE_RMS`
- `JARVIS_AEC_BACKEND` (`simple`/`none`), `JARVIS_AEC_REF_SECONDS`, `JARVIS_AEC_MAX_GAIN`
- `JARVIS_WAKE_WORD_AUDIO` (1 habilita wake word por audio)
- `JARVIS_WAKE_WORD_AUDIO_BACKEND` (`pvporcupine` ou `openwakeword`)
- `JARVIS_PORCUPINE_ACCESS_KEY`, `JARVIS_PORCUPINE_KEYWORD_PATH`, `JARVIS_PORCUPINE_SENSITIVITY`
- `JARVIS_OPENWAKEWORD_MODEL_PATHS`, `JARVIS_OPENWAKEWORD_INFERENCE_FRAMEWORK`
- `JARVIS_OPENWAKEWORD_SENSITIVITY`, `JARVIS_OPENWAKEWORD_AUTO_DOWNLOAD`

## Dependencias diretas
- `sounddevice`, `numpy`, `scipy` (reamostra; sem `scipy` a reamostragem falha)
- `faster-whisper`
- `jarvis/voz/vad.py` (StreamingVAD, VoiceActivityDetector)
- `jarvis_audio` (opcional)
- `torch` (opcional, Silero deactivity)

## Testes relacionados
- `testes/test_stt_flow.py`
- `testes/test_stt_filters.py`
- `testes/test_stt_rust_trim.py`
- `testes/test_stt_capture_config.py`
- `testes/test_audio_resample.py`
- `testes/teste_stt_gap_latency.py`
- `testes/test_stt_streaming_controls.py`
- `testes/test_stt_silero_deactivity.py`

## Comandos uteis
- Smoke: `PYTHONPATH=. python -c "from jarvis.entrada.stt import SpeechToText; print('ok')"`
- Testes STT: `PYTHONPATH=. pytest -q testes/test_stt_flow.py testes/test_stt_filters.py`
- Teste reamostragem: `PYTHONPATH=. pytest -q testes/test_audio_resample.py`
- Build Rust (opcional): `bash scripts/build_rust_audio.sh`

## Qualidade e limites
- Se nao houver fala (VAD/trim), retorna "".
- Limite minimo por `JARVIS_STT_MIN_AUDIO_MS`.
- Se `JARVIS_AUDIO_CAPTURE_SR` nao estiver definido, usa `default_samplerate` do device.
- Em `transcribe_with_vad`, streaming so e usado quando capture_sr == 16 kHz **e** `JARVIS_AUDIO_DEVICE` nao esta definido; caso contrario, usa gravacao fixa (respeita device).
- Em `transcribe_once`, streaming so e usado quando capture_sr == 16 kHz **e** `JARVIS_AUDIO_DEVICE` nao esta definido.
- `JARVIS_STT_MIN_GAP_SECONDS` evita disparos em sequencia (debounce).
- `JARVIS_STT_ALLOWED_LATENCY_MS` descarta transcricao acima do limite.
- `JARVIS_STT_NORMALIZE_AUDIO` normaliza o audio antes do STT (nao afeta o VAD).
- `JARVIS_STT_EARLY_TRANSCRIBE_ON_SILENCE` permite transcrever audio abaixo do minimo quando o VAD detecta fala.
- `JARVIS_STT_MAX_BUFFER_SECONDS` corta o audio acima do limite para evitar overflow.
- `on_partial` recebe parciais por segmento (nao enquanto fala).
- Se o device nao suporta 16 kHz e `scipy` nao estiver instalado, a reamostragem falha.
- Wake word por audio via OpenWakeWord exige modelos (env `JARVIS_OPENWAKEWORD_MODEL_PATHS` ou auto-download).
- Silero deactivity exige `torch` e pode baixar o modelo no primeiro uso.
- Preflight agora avisa quando `scipy` esta ausente.
- `sounddevice` e importado de forma lazy; benchmarks ou transcricao de arquivo nao dependem do backend de audio.
- Para captura real, `sounddevice` requer PortAudio/ALSA (instalar libs do sistema se a importacao travar).
- Se o trim em Rust indicar fala, o STT pula a rechecagem de VAD para evitar falso negativo em audio curto.


## Performance (estimativa)
- Uso esperado: alto (transcricao local).
- Medir: use `/usr/bin/time -v <comando>` e monitore `top`/`htop`.

## Observabilidade
- Debug via `JARVIS_DEBUG=1` (mensagens com prefixo [stt]).
- Metrics via `JARVIS_STT_METRICS=1` (duracao de captura/transcricao).

## Problemas conhecidos (hoje)
- AEC simples depende de referencia de playback (so existe quando o TTS gera audio).
- AEC simples funciona apenas em 16 kHz (audio e reamostrado antes de aplicar).
- Sem `scipy`, a reamostragem falha quando o device nao suporta 16 kHz.
- Sem VAD/Rust, usa limiar simples de pico (pode falhar com fala muito baixa).

## Melhorias sugeridas
- ~~Bloquear streaming quando capture_sr != 16k para evitar inconsistencias.~~ (resolvido)
