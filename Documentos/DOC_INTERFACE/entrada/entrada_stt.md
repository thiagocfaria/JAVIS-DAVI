# interface/entrada/stt.py

- Caminho: `jarvis/interface/entrada/stt.py`
- Papel: capturar audio, aplicar VAD/trim e transcrever localmente (backend plugável).
- Onde entra no fluxo: usado pelo orquestrador no modo voz.
- Atualizado em: 2026-01-28 (backend padrão faster_whisper tiny; whisper_cpp bloqueado; warmup implementado)

## Responsabilidades
- Capturar audio (sounddevice) em SR nativo e reamostrar para 16 kHz.
- VAD streaming quando possivel; fallback para gravacao fixa.
- Coercao de tipos para PCM bytes int16.
- Wake word opcional com filtro de fronteira e/ou audio.
- Trim opcional via Rust (`jarvis_audio`) e trim por VAD.
- `transcribe_with_vad` usa captura com VAD ate silencio.
- `transcribe_once` usa captura fixa (com VAD streaming se houver).

## Entrada e saida
- Entrada: microfone ou bytes PCM.
- Saida: texto transcrito (str) e opcionalmente `audio_bytes` + `speech_detected`.
- Contrato: PCM int16 mono 16 kHz (little-endian).
- Nota: `transcribe_audio_bytes(...)` permite transcrever audio externo sem acessar microfone.
- Nota: `on_partial` emite texto incremental durante a decodificacao.

## Configuracao (env/config)
### Basico
- `JARVIS_STT_MODE` (config `stt_mode`)
- `JARVIS_STT_BACKEND` (`faster_whisper` default; `whisper_cpp` bloqueado; `ctranslate2` opcional)
- `JARVIS_STT_MODEL` (tamanho do modelo; default varia com `JARVIS_STT_PROFILE`)
- `JARVIS_STT_PROFILE` (`fast|low_latency|turbo`) - aplica defaults mais rapidos
- `JARVIS_STT_LATENCY_MODE=1` (atalho para perfil rapido)
- `JARVIS_STT_LANGUAGE` ("pt" ou "auto")
- `JARVIS_STT_WARMUP`, `JARVIS_STT_WARMUP_SECONDS`
- `JARVIS_DEBUG`, `JARVIS_STT_METRICS`
- `JARVIS_STT_COMMAND_MODE=1` (modo comando; usa modelo menor + fallback)
- `JARVIS_STT_COMMAND_MODEL` (default "tiny")
- `JARVIS_STT_COMMAND_FALLBACK_MODEL` (default "small")
- `JARVIS_STT_COMMAND_BIAS` (lista de frases esperadas, separadas por `,` ou `|`)
- `JARVIS_STT_COMMAND_BIAS_THRESHOLD` (limiar de similaridade; default 0.82)
- `JARVIS_STT_CONFIRM_LOW_CONFIDENCE=1` (pede confirmacao quando confianca baixa)
- `JARVIS_STT_CONFIDENCE_MIN` (limiar de confianca; default 0.65)

### Device / CPU-GPU (adaptativo)
- `JARVIS_STT_DEVICE` (`auto|cpu|cuda`) - default `auto`
- `JARVIS_STT_GPU_ALLOWED` (default true)
- `JARVIS_STT_GPU_FORCE` (default false)
- `JARVIS_STT_COMPUTE_TYPE` (override do compute type; ex: `int8`, `int8_float16`)

### Captura e limites
- `JARVIS_AUDIO_DEVICE`, `JARVIS_AUDIO_CAPTURE_SR`
- `JARVIS_AUDIO_PREFER_16K=1` (tenta capturar direto em 16 kHz quando suportado)
- `JARVIS_MIN_AUDIO_SECONDS`, `JARVIS_STT_MIN_AUDIO_MS`
- `JARVIS_STT_MAX_BUFFER_SECONDS` (limite maximo do buffer)
- `JARVIS_STT_MIN_GAP_SECONDS` (debounce entre gravacoes)
- `JARVIS_STT_ALLOWED_LATENCY_MS` (descarta transcricao muito lenta)
- `JARVIS_STT_NORMALIZE_AUDIO`, `JARVIS_STT_NORMALIZE_TARGET`, `JARVIS_STT_NORMALIZE_MAX_GAIN`

### VAD / endpointing
- `JARVIS_VAD_STRATEGY` (`webrtc|silero|whisper|realtimestt`) escolhe um unico VAD e desliga os outros.
- `JARVIS_VAD_SILENCE_MS` (padrao 400 ms)
- `JARVIS_VAD_PRE_ROLL_MS` (padrao 200 ms)
- `JARVIS_VAD_POST_ROLL_MS` (padrao 200 ms)
- `JARVIS_VAD_MAX_SECONDS` (padrao 30 s)
- `JARVIS_VAD_AGGRESSIVENESS` (definido em `interface/entrada/vad.py`)
- `JARVIS_STT_EARLY_TRANSCRIBE_ON_SILENCE` (default false)
- `JARVIS_STT_TRIM_VAD` (default true)
- `JARVIS_FORCE_SPEECH_OK` (ignora "sem fala" quando necessario)
- `JARVIS_AUDIO_TRIM_BACKEND` (`none|rust`)

### Streaming (RealtimeSTT opcional, único que gera parciais)
- `JARVIS_STT_STREAMING=1`
- `JARVIS_STT_STREAMING_BACKEND` (`realtimestt`)
- `JARVIS_STT_STREAMING_FORCE_START` (default true)
- `JARVIS_STT_STREAMING_MAX_SECONDS` (default 6)
- `JARVIS_STT_STREAMING_REUSE_RECORDER` (default true; reduz overhead entre chamadas de voz)
- `JARVIS_STT_STREAMING_SILERO` (default false; quando 1, habilita Silero dentro do RealtimeSTT)
- `JARVIS_STT_STREAMING_USE_MICROPHONE=0` (usa fonte externa no RealtimeSTT)
- `JARVIS_STT_REALTIME_MODEL` (modelo separado para parciais)
- `JARVIS_SILERO_DEACTIVITY`, `JARVIS_SILERO_SENSITIVITY`
- `JARVIS_SILERO_USE_ONNX`, `JARVIS_SILERO_AUTO_DOWNLOAD`
- Observação: parciais/overlap só existem com backend streaming (RealtimeSTT). O backend padrão `faster_whisper` roda offline e não emite parciais.

### Wake word
- `JARVIS_REQUIRE_WAKE_WORD`, `JARVIS_WAKE_WORD`
- `JARVIS_WAKE_WORD_AUDIO`, `JARVIS_WAKE_WORD_AUDIO_BACKEND`
- `JARVIS_WAKE_WORD_AUDIO_STRICT` (quando 1, bloqueia o comando se o audio nao detectar a wake word; quando 0, nao bloqueia)
- `JARVIS_WAKE_WORD_AUDIO_TEXT_FALLBACK=1` (se o gate por audio falhar, ainda valida pelo texto)
- `JARVIS_PORCUPINE_ACCESS_KEY`, `JARVIS_PORCUPINE_KEYWORD_PATH`, `JARVIS_PORCUPINE_SENSITIVITY`
- `JARVIS_OPENWAKEWORD_MODEL_PATHS`, `JARVIS_OPENWAKEWORD_INFERENCE_FRAMEWORK`
- `JARVIS_OPENWAKEWORD_SENSITIVITY`, `JARVIS_OPENWAKEWORD_AUTO_DOWNLOAD`

### Whisper tuning e fallback
- `JARVIS_WHISPER_VAD_FILTER`
- `JARVIS_STT_BEAM_SIZE`, `JARVIS_STT_BEST_OF`
- `JARVIS_STT_TEMPERATURE`
- `JARVIS_STT_INITIAL_PROMPT`, `JARVIS_STT_SUPPRESS_TOKENS`
- `JARVIS_STT_RETRY_AUTO_LANGUAGE` (default true)
- `JARVIS_STT_FALLBACK_MODEL`, `JARVIS_STT_RETRY_FALLBACK_MODEL`
- `JARVIS_STT_MIN_PEAK` (fallback sem VAD/Rust)

## Dependencias diretas
- `sounddevice`, `numpy`, `scipy` (reamostra; sem `scipy` a reamostragem falha)
- Backends STT: `pywhispercpp` (default), `faster-whisper` (alternativo/ctranslate2)
- `jarvis/voz/vad.py` (StreamingVAD, VoiceActivityDetector)
- `jarvis_audio` (opcional)
- `RealtimeSTT` + `pyaudio` (opcional, streaming com parciais)
- `pvporcupine` / `openwakeword` (opcional, wake word por audio)
- `torch` (opcional, Silero deactivity)

## Testes relacionados
- `testes/test_stt_flow.py`
- `testes/test_stt_filters.py`
- `testes/test_stt_rust_trim.py`
- `testes/test_stt_realtimestt_backend.py`
- `testes/test_stt_capture_config.py`
- `testes/test_audio_resample.py`
- `testes/teste_stt_gap_latency.py`
- `testes/test_stt_streaming_controls.py`
- `testes/test_stt_silero_deactivity.py`

## Comandos uteis
- Smoke: `PYTHONPATH=. python -c "from jarvis.interface.entrada.stt import SpeechToText; print('ok')"`
- Testes STT: `PYTHONPATH=. pytest -q testes/test_stt_flow.py testes/test_stt_filters.py`
- Teste reamostragem: `PYTHONPATH=. pytest -q testes/test_audio_resample.py`
- Build Rust (opcional): `bash scripts/build_rust_audio.sh`

## Qualidade e limites
- Se nao houver fala (VAD/trim), retorna "".
- Limite minimo por `JARVIS_STT_MIN_AUDIO_MS`.
- Se `JARVIS_AUDIO_CAPTURE_SR` nao estiver definido, usa `default_samplerate` do device.
- `transcribe_with_vad` tenta streaming VAD quando o webrtc esta ativo e o `capture_sr` e suportado (8/16/32/48 kHz); se `capture_sr!=16000`, grava no SR nativo e reamostra para 16 kHz antes do STT.
- `transcribe_once` tenta streaming VAD quando disponivel, mas pode cair no fallback fixo se o audio ficar curto.
- Se a transcricao em memoria falhar, o STT usa WAV temporario como fallback.
- Se `JARVIS_VAD_STRATEGY` for `silero` ou `whisper`, o StreamingVAD (webrtc) fica desativado: o STT grava por duracao fixa e aplica o trim/filtro depois (Silero ou `vad_filter` do Whisper).
- Se `JARVIS_VAD_STRATEGY` for `realtimestt`, o STT tenta streaming via RealtimeSTT; se o backend nao estiver disponivel, cai para gravacao fixa sem StreamingVAD.
- No RealtimeSTT, `JARVIS_STT_STREAMING_FORCE_START=1` inicia gravacao sem esperar o gate do Silero; o fim da fala continua usando VAD/Silero.
- No RealtimeSTT, `JARVIS_VAD_SILENCE_MS` menor + `JARVIS_STT_EARLY_TRANSCRIBE_ON_SILENCE=1` reduzem a latencia de fechamento; `post_speech_silence` minimo 0.2s.
- `JARVIS_STT_MIN_GAP_SECONDS` evita disparos em sequencia (debounce).
- `JARVIS_STT_ALLOWED_LATENCY_MS` descarta transcricao acima do limite.
- `JARVIS_STT_NORMALIZE_AUDIO` normaliza o audio antes do STT (nao afeta o VAD).
- `JARVIS_STT_EARLY_TRANSCRIBE_ON_SILENCE` permite transcrever audio abaixo do minimo quando o VAD detecta fala.
- `JARVIS_STT_MAX_BUFFER_SECONDS` corta o audio acima do limite para evitar overflow.
- `on_partial` recebe parciais durante a decodificacao; em streaming pode aparecer enquanto voce fala, em batch sai por segmento.
- Se o device nao suporta 16 kHz e `scipy` nao estiver instalado, a reamostragem falha.
- Wake word por audio via OpenWakeWord exige modelos (env `JARVIS_OPENWAKEWORD_MODEL_PATHS` ou auto-download).
- Silero deactivity exige `torch` e pode baixar o modelo no primeiro uso.
- Preflight avisa quando `scipy` esta ausente.
- Para captura real, `sounddevice` requer PortAudio/ALSA (instalar libs do sistema se a importacao travar).
- Se o trim em Rust retornar `None` ou formato invalido, o STT ignora o trim e usa o audio original (evita erro em runtime).
- Se o trim em Rust indicar fala, o STT pula a rechecagem de VAD para evitar falso negativo em audio curto.

## Wake word (texto) - comportamento
- Quando `JARVIS_REQUIRE_WAKE_WORD=1`, o texto precisa conter a wake word no **inicio** (aceita prefixos simples como `oi/ola/ei/hey` antes de `jarvis`).
- O filtro remove a wake word do texto e devolve apenas o comando (ex.: `"jarvis, abrir navegador"` -> `"abrir navegador"`).
- Se a transcricao contiver **apenas** a wake word (sem comando depois), o texto filtrado vira vazio; o orquestrador pode tratar isso como "acordar" e ouvir o comando em seguida (ver `Documentos/DOC_INTERFACE/TESTE_MANUAL.md`).
 - Quando `JARVIS_WAKE_WORD_AUDIO_TEXT_FALLBACK=1`, o gate por audio nao bloqueia a transcricao se a wake word for encontrada no texto.


## Performance (estimativa)
- Uso esperado: alto (transcricao local).
- Medir: use `/usr/bin/time -v <comando>` e monitore `top`/`htop`.

## Observabilidade
- Debug via `JARVIS_DEBUG=1` (mensagens com prefixo [stt]).
- Metrics via `JARVIS_STT_METRICS=1` (duracao de captura/transcricao).
- `SpeechToText.get_last_metrics()` expoe `capture_ms`, `vad_ms`, `endpoint_ms`, `stt_ms` do ultimo ciclo.
- Parciais opcionais: `JARVIS_STT_PARTIALS_LOG=1` escreve parciais no `chat_log`, `JARVIS_STT_PARTIALS_STDOUT=1` imprime no stdout.
- `SpeechToText.get_last_confidence()` expoe a confianca (0..1) do ultimo comando com bias.

## Warmup (implementado - Etapa 1)
- **Warmup STT:** `_get_whisper_model(realtime=False)` e warmup transcription com audio curto implementados em `scripts/bench_interface.py` (linhas 658-674).
- **Beneficio:** Evita que o p95 seja dominado pelo primeiro carregamento do modelo (cold start).
- **Uso:** `--no-warmup` desabilita o warmup (útil para medir cold start isoladamente).
- **Impacto medido:** Redução significativa em outliers; p95 passou de ~1500ms para **~1190ms** (META OURO atingida no limite com faster_whisper).

## Problemas conhecidos (hoje)
- AEC simples depende de referencia de playback (so existe quando o TTS gera audio).
- AEC simples funciona apenas em 16 kHz (audio e reamostrado antes de aplicar).
- Sem `scipy`, a reamostragem falha quando o device nao suporta 16 kHz.
- Sem VAD/Rust, usa limiar simples de pico (pode falhar com fala muito baixa).

## Melhorias sugeridas
- ~~Bloquear streaming quando capture_sr != 16k para evitar inconsistencias.~~ (resolvido)
- ~~Implementar warmup STT no benchmark.~~ (resolvido - Etapa 1)
