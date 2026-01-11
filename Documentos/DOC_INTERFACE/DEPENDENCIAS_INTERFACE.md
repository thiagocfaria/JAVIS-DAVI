# Dependencias da interface (entrada/saida)

Este documento lista todas as dependencias usadas pela interface de voz/texto, com o papel de cada uma e como instalar.

## Python (pip)
- `sounddevice` - captura de audio do microfone.
  - Para que serve: grava o audio direto do dispositivo de entrada.
  - Como usa: `SpeechToText._record_fixed_duration`; escolha com `JARVIS_AUDIO_DEVICE` e `JARVIS_AUDIO_CAPTURE_SR`.
  - Instalar: `pip install sounddevice`
  - Linux: pode exigir `libportaudio2`, `portaudio19-dev` e `libasound2-dev`.
  - Se a importacao travar, instale as libs acima e reinicie o processo.
- `numpy` - buffer de audio e conversoes.
  - Para que serve: transformar PCM int16 em float32 e vice-versa.
  - Como usa: `jarvis/entrada/stt.py` e `jarvis/voz/vad.py` para conversao de buffers e AEC simples.
  - Instalar: `pip install numpy`
- `scipy` - reamostragem (quando o microfone nao suporta 16 kHz).
  - Para que serve: reamostrar audio de 44.1k/48k para 16k.
  - Como usa: `resample_poly` em `jarvis/entrada/stt.py` quando `capture_sr != 16000`.
  - Instalar: `pip install scipy`
- `webrtcvad` - VAD leve para detectar fala.
  - Para que serve: decidir onde ha fala vs. silencio.
  - Como usa: auto em `jarvis/voz/vad.py` quando instalado.
  - Instalar: `pip install webrtcvad`
- `faster-whisper` - STT local (transcricao).
  - Para que serve: transcrever audio localmente sem API externa.
  - Como usa: `SpeechToText._transcribe_local` com `JARVIS_STT_MODEL` e `JARVIS_STT_LANGUAGE`.
  - Instalar: `pip install faster-whisper`
- `resemblyzer` - speaker verification (opcional).
  - Para que serve: confirmar se a voz e do locutor autorizado.
  - Como usa: `JARVIS_SPK_VERIFY=1` + comando "cadastrar voz" para salvar voiceprint.
  - Instalar: `pip install resemblyzer`
- `cryptography` - criptografar voiceprint (opcional).
  - Para que serve: proteger o voiceprint salvo em disco.
  - Como usa: `JARVIS_SPK_VOICEPRINT_PASSPHRASE` ativa criptografia do voiceprint.
  - Instalar: `pip install cryptography`
- `pynput` - atalho global (opcional).
  - Para que serve: escutar atalho global para abrir a Chat UI.
  - Como usa: `JARVIS_CHAT_SHORTCUT_COMBO` (padrao `ctrl+shift+j`) em `jarvis/entrada/shortcut.py`.
  - Instalar: `pip install pynput`
  - Alternativa sem pynput: `JARVIS_CHAT_SHORTCUT_FILE` + atalho do sistema (`touch`).
- `watchdog` - atualizar chat UI por evento (opcional).
  - Para que serve: refletir mudancas no log/inbox sem polling pesado.
  - Como usa: `jarvis/entrada/chat_ui.py` monitora arquivos quando instalado.
  - Instalar: `pip install watchdog`
- `py-spy` - diagnostico profundo de CPU (opcional).
  - Para que serve: inspecionar gargalos de CPU em runtime.
  - Como usa: `py-spy top` ou `py-spy record -o profile.svg -- <comando>`.
  - Instalar: `pip install py-spy`
- `psutil` - coleta de CPU/RAM no benchmark (opcional).
  - Para que serve: medir CPU/RAM durante benchmark.
  - Como usa: `scripts/bench_interface.py` coleta metricas quando instalado.
  - Instalar: `pip install psutil`
- `pvporcupine` - wake word por audio (opcional).
  - Para que serve: detectar "Jarvis" no audio antes da transcricao.
  - Como usa: `JARVIS_WAKE_WORD_AUDIO=1` + `JARVIS_PORCUPINE_ACCESS_KEY` (ou `JARVIS_PORCUPINE_KEYWORD_PATH`).
  - Instalar: `pip install pvporcupine`
- `openwakeword` - wake word por audio (opcional, backend alternativo).
  - Para que serve: detectar wake word usando modelos locais (OpenWakeWord).
  - Como usa: `JARVIS_WAKE_WORD_AUDIO=1` + `JARVIS_WAKE_WORD_AUDIO_BACKEND=openwakeword` + `JARVIS_OPENWAKEWORD_MODEL_PATHS`.
  - Instalar: `pip install openwakeword`
- `torch` - Silero deactivity (opcional).
  - Para que serve: detectar fim de fala com mais robustez em ruido.
  - Como usa: `JARVIS_SILERO_DEACTIVITY=1` + `JARVIS_SILERO_AUTO_DOWNLOAD=1` (primeiro uso baixa pesos).
  - Instalar: `pip install torch`
- `onnxruntime` - Silero via ONNX (opcional).
  - Para que serve: acelerar Silero no CPU quando `JARVIS_SILERO_USE_ONNX=1`.
  - Instalar: `pip install onnxruntime`
- `pytest` - runner de testes.
  - Para que serve: rodar a suite automatizada da interface.
  - Como usa: `PYTHONPATH=. pytest -q testes/`
  - Instalar: `pip install pytest`
- `pytest-xdist` - paralelizar testes (opcional).
  - Para que serve: rodar testes em paralelo em maquinas com muitos cores.
  - Como usa: `PYTHONPATH=. pytest -q -n auto testes/`
  - Instalar: `pip install pytest-xdist`
- `pytest-repeat` - repetir testes (opcional).
  - Para que serve: stress test (rodar o mesmo teste varias vezes).
  - Como usa: `PYTHONPATH=. pytest -q --count 20 testes/test_stt_flow.py`
  - Instalar: `pip install pytest-repeat`

## Sistema (binarios)
- `piper` - TTS neural local.
  - Para que serve: gerar fala local de maior qualidade.
  - Como usa: `JARVIS_TTS_MODE=local`, `JARVIS_PIPER_MODELS_DIR` e `JARVIS_PIPER_VOICE`.
  - Ver instrucoes em `jarvis/voz/tts.py`.
- `espeak-ng` - TTS fallback.
  - Para que serve: fallback quando Piper nao esta disponivel.
  - Instalar (Ubuntu): `sudo apt install espeak-ng`
- `aplay` - playback de audio (ALSA).
  - Para que serve: tocar audio gerado no Linux.
  - Instalar (Ubuntu): `sudo apt install alsa-utils`
- `python3-tk` - tkinter para UI (chat/painel).
  - Para que serve: janela do chat/painel no modo local.
  - Instalar (Ubuntu): `sudo apt install python3-tk`
- `nvidia-smi` - metricas de GPU no benchmark (opcional).
  - Para que serve: coletar VRAM/uso de GPU no benchmark.
  - Disponivel no pacote do driver NVIDIA.

## Opcionais (Rust)
- `jarvis_audio` - trim/speech check em Rust (opcional).
  - Para que serve: cortar silencio e checar fala com performance.
  - Como usa: `JARVIS_AUDIO_TRIM_BACKEND=rust` habilita o trim em `jarvis/entrada/stt.py`.
  - Build: `scripts/build_rust_audio.sh`

## Variaveis de ambiente relevantes
- `JARVIS_STT_MODE`, `JARVIS_TTS_MODE`
- `JARVIS_STT_MODEL`, `JARVIS_STT_REALTIME_MODEL`, `JARVIS_STT_LANGUAGE`
- `JARVIS_AUDIO_DEVICE`, `JARVIS_AUDIO_CAPTURE_SR`
- `JARVIS_MIN_AUDIO_SECONDS`, `JARVIS_STT_MIN_AUDIO_MS`
- `JARVIS_STT_MIN_GAP_SECONDS`, `JARVIS_STT_ALLOWED_LATENCY_MS`
- `JARVIS_STT_EARLY_TRANSCRIBE_ON_SILENCE`, `JARVIS_STT_MAX_BUFFER_SECONDS`
- `JARVIS_STT_NORMALIZE_AUDIO`, `JARVIS_STT_NORMALIZE_TARGET`, `JARVIS_STT_NORMALIZE_MAX_GAIN`
- `JARVIS_VAD_SILENCE_MS`, `JARVIS_VAD_PRE_ROLL_MS`, `JARVIS_VAD_POST_ROLL_MS`, `JARVIS_VAD_MAX_SECONDS`
- `JARVIS_WHISPER_VAD_FILTER`, `JARVIS_STT_BEAM_SIZE`, `JARVIS_STT_BEST_OF`
- `JARVIS_STT_TEMPERATURE`, `JARVIS_STT_INITIAL_PROMPT`, `JARVIS_STT_SUPPRESS_TOKENS`
- `JARVIS_STT_WARMUP`, `JARVIS_STT_WARMUP_SECONDS`
- `JARVIS_PIPER_MODELS_DIR`, `JARVIS_PIPER_VOICE`
- `JARVIS_SPK_VERIFY`, `JARVIS_SPK_THRESHOLD`, `JARVIS_CONFIG_DIR`
- `JARVIS_SPK_VOICEPRINT_PASSPHRASE`
- `JARVIS_WAKE_WORD_AUDIO`, `JARVIS_PORCUPINE_ACCESS_KEY`
- `JARVIS_PORCUPINE_KEYWORD_PATH`, `JARVIS_PORCUPINE_SENSITIVITY`
- `JARVIS_WAKE_WORD_AUDIO_BACKEND`, `JARVIS_OPENWAKEWORD_MODEL_PATHS`
- `JARVIS_OPENWAKEWORD_INFERENCE_FRAMEWORK`, `JARVIS_OPENWAKEWORD_SENSITIVITY`
- `JARVIS_OPENWAKEWORD_AUTO_DOWNLOAD`
- `JARVIS_SILERO_DEACTIVITY`, `JARVIS_SILERO_SENSITIVITY`
- `JARVIS_SILERO_USE_ONNX`, `JARVIS_SILERO_AUTO_DOWNLOAD`
- `JARVIS_AEC_BACKEND`, `JARVIS_AEC_REF_SECONDS`, `JARVIS_AEC_MAX_GAIN`

## Comandos de verificacao rapida
- Preflight: `PYTHONPATH=. python -m jarvis.entrada.app --preflight`
- STT deps: `python -c "from jarvis.entrada.stt import check_stt_deps; print(check_stt_deps())"`
- TTS deps: `python -c "from jarvis.voz.tts import check_tts_deps; print(check_tts_deps())"`
- Profiling (py-spy): `py-spy --version`

## Status local (2026-01-10)
- Python (venv) OK: `sounddevice`, `numpy`, `scipy`, `webrtcvad`, `faster-whisper`, `resemblyzer`, `cryptography`, `pynput`, `watchdog`, `psutil`, `pvporcupine`, `pytest`.
- Python (venv) OK (perf): `py-spy`.
- Sistema OK: `espeak-ng`, `aplay`, `python3-tk`, `nvidia-smi`, `libportaudio` (PortAudio).
- Sistema pendente (opcional): `piper` (TTS neural).
- Python pendente (opcional): `torch`/`onnxruntime` (Silero deactivity).
