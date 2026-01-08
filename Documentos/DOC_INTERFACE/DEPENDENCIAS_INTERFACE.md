# Dependencias da interface (entrada/saida)

Este documento lista todas as dependencias usadas pela interface de voz/texto, com o papel de cada uma e como instalar.

## Python (pip)
- `sounddevice` - captura de audio do microfone.
  - Instalar: `pip install sounddevice`
  - Linux: pode exigir `libportaudio2` ou `portaudio19-dev`.
- `numpy` - buffer de audio e conversoes.
  - Instalar: `pip install numpy`
- `scipy` - reamostragem (quando o microfone nao suporta 16 kHz).
  - Instalar: `pip install scipy`
- `webrtcvad` - VAD leve para detectar fala.
  - Instalar: `pip install webrtcvad`
- `faster-whisper` - STT local (transcricao).
  - Instalar: `pip install faster-whisper`
- `resemblyzer` - speaker verification (opcional).
  - Instalar: `pip install resemblyzer`
- `pynput` - atalho global (opcional).
  - Instalar: `pip install pynput`
- `py-spy` - diagnostico profundo de CPU (opcional).
  - Instalar: `pip install py-spy`

## Sistema (binarios)
- `piper` - TTS neural local.
  - Ver instrucoes em `jarvis/voz/tts.py`.
- `espeak-ng` - TTS fallback.
  - Instalar (Ubuntu): `sudo apt install espeak-ng`
- `aplay` - playback de audio (ALSA).
  - Instalar (Ubuntu): `sudo apt install alsa-utils`
- `python3-tk` - tkinter para UI (chat/painel).
  - Instalar (Ubuntu): `sudo apt install python3-tk`

## Opcionais (Rust)
- `jarvis_audio` - trim/speech check em Rust (opcional).
  - Build: `scripts/build_rust_audio.sh`

## Variaveis de ambiente relevantes
- `JARVIS_STT_MODE`, `JARVIS_TTS_MODE`
- `JARVIS_STT_MODEL`, `JARVIS_STT_LANGUAGE`
- `JARVIS_AUDIO_DEVICE`, `JARVIS_AUDIO_CAPTURE_SR`
- `JARVIS_MIN_AUDIO_SECONDS`, `JARVIS_STT_MIN_AUDIO_MS`
- `JARVIS_PIPER_MODELS_DIR`, `JARVIS_PIPER_VOICE`
- `JARVIS_SPK_VERIFY`, `JARVIS_SPK_THRESHOLD`, `JARVIS_CONFIG_DIR`

## Comandos de verificacao rapida
- Preflight: `PYTHONPATH=. python -m jarvis.entrada.app --preflight`
- STT deps: `python -c "from jarvis.entrada.stt import check_stt_deps; print(check_stt_deps())"`
- TTS deps: `python -c "from jarvis.voz.tts import check_tts_deps; print(check_tts_deps())"`
- Profiling (py-spy): `py-spy --version`
