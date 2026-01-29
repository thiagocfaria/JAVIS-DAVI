# Dependências da interface (entrada/saída)

**Atualizado:** 2026-01-28 — Default atual: STT via `faster-whisper` (tiny); `pywhispercpp` bloqueado por regressão. TTS via Piper in-proc.

## Política de GPU
- CPU-first obrigatório; GPU é opcional. Registre nos benchmarks se rodou CPU-only ou GPU.

## Python (pip)
**Core voz**
- `sounddevice` — captura do microfone. (Ubuntu: `libportaudio2`, `portaudio19-dev`, `libasound2-dev`).
- `numpy` — buffers/conversões; `scipy` — reamostragem 44.1k/48k→16k.
- `webrtcvad` — VAD leve (usado automaticamente).
- `faster-whisper` — backend STT padrão (ctranslate2 CPU/GPU opcional).
- `pywhispercpp` — backend STT experimental (whisper.cpp CPU) **bloqueado**; modelos em `~/.cache/whisper`.

**Streaming STT (opcional)**
- `RealtimeSTT` — backend streaming com parciais. Preferir `pip install RealtimeSTT`; cópia vendorizada em `jarvis/third_party/realtimestt` (offline).
- `pyaudio` (mic), `halo`, `websocket-client`, `torchaudio` (Silero interno) — dependências indiretas.

**TTS**
- `piper-tts` — backend Piper Python/in-proc (instala também o binário `piper` em `.venv/bin/piper`). Fallback espeak-ng (binário do sistema).

**Wake word / speaker / AEC (opcionais)**
- `pvporcupine` ou `openwakeword` — wake word por áudio.
- `resemblyzer` — speaker verification; `cryptography` — voiceprint criptografado.
- `pynput` — atalho global; `watchdog` — UI reativa; `speexdsp` / `webrtc-audio-processing` / `torch` / `onnxruntime` — AEC/NS/VAD alternativos.

**Bench/QA**
- `psutil`, `py-spy`; `pytest`, `ruff`, `black` (core); `pytest-xdist`, `pytest-repeat` (opcionais).

## Sistema (binários)
- `piper` — TTS neural local. Modelos em `storage/models/piper` (recomendado) ou `~/.local/share/piper-models`. Opcional `JARVIS_PIPER_BIN` e `JARVIS_PIPER_MODEL`.
- `espeak-ng` — fallback de TTS. `sudo apt install espeak-ng`.
- `aplay` — playback ALSA. `sudo apt install alsa-utils`.
- `python3-tk` — UI (chat/painel). `sudo apt install python3-tk`.
- `nvidia-smi` — métricas de GPU para bench (se usar GPU).

## Opcionais (Rust)
- `jarvis_audio` — trim/speech check em Rust. Habilita com `JARVIS_AUDIO_TRIM_BACKEND=rust`; build: `scripts/build_rust_audio.sh`.

## Variáveis de ambiente úteis (amostra)
- STT/TTS: `JARVIS_STT_MODE`, `JARVIS_STT_MODEL`, `JARVIS_STT_BACKEND` (`whisper_cpp|faster_whisper|ctranslate2`), `JARVIS_STT_LANGUAGE`, `JARVIS_STT_STREAMING`, `JARVIS_STT_STREAMING_BACKEND`, `JARVIS_TTS_MODE`, `JARVIS_TTS_ENGINE`, `JARVIS_PIPER_MODELS_DIR`, `JARVIS_PIPER_VOICE`.
- VAD/Audio: `JARVIS_AUDIO_DEVICE`, `JARVIS_AUDIO_CAPTURE_SR`, `JARVIS_VAD_STRATEGY`, `JARVIS_VAD_AGGRESSIVENESS`, `JARVIS_VAD_SILENCE_MS`, `JARVIS_VAD_PRE_ROLL_MS`, `JARVIS_VAD_POST_ROLL_MS`.
- Wake word/Speaker: `JARVIS_WAKE_WORD_AUDIO`, `JARVIS_WAKE_WORD_AUDIO_BACKEND`, `JARVIS_PORCUPINE_ACCESS_KEY`, `JARVIS_OPENWAKEWORD_MODEL_PATHS`, `JARVIS_SPK_VERIFY`, `JARVIS_SPK_THRESHOLD`, `JARVIS_SPK_VOICEPRINT_PASSPHRASE`.
- AEC/NS/AGC: `JARVIS_AEC_BACKEND`, `JARVIS_AEC_REF_SECONDS`, `JARVIS_AEC_MAX_GAIN`, `JARVIS_AUDIO_AGC_TARGET_RMS`.
- Métricas/bench: `JARVIS_STT_METRICS`, `JARVIS_VAD_METRICS`, `JARVIS_TTS_WARMUP`, `JARVIS_BENCH_PHASE1`, `JARVIS_ALLOW_MODEL_DOWNLOADS` (para RealtimeSTT baixar modelos).

## Verificações rápidas
- Preflight: `PYTHONPATH=. python -m jarvis.interface.entrada.app --preflight --preflight-profile voice`
- STT deps: `python -c "from jarvis.interface.entrada.stt import check_stt_deps; print(check_stt_deps())"`
- TTS deps: `python -c "from jarvis.interface.saida.tts import check_tts_deps; print(check_tts_deps())"`
- Bench STT: `PYTHONPATH=. python scripts/bench_interface.py stt --audio Documentos/DOC_INTERFACE/bench_audio/voice_clean.wav --repeat 3 --resample`
