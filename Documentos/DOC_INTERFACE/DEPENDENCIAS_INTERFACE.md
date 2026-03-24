# Dependencias da interface (entrada/saida)

**Atualizado em:** 2026-01-19

Este documento lista todas as dependencias usadas pela interface de voz/texto, com o papel de cada uma e como instalar.

## Politica de GPU (CPU-first)
- O Jarvis deve funcionar 100% em CPU (modo padrao).
- GPU e opcional: melhora latencia em modelos grandes, mas nao e requisito.
- Em GPU fraca/antiga, manter CPU como default e usar modelos pequenos.
- Registracao obrigatoria nos benchmarks: "GPU indisponivel -> CPU-only".

## Python (pip)
- `sounddevice` - captura de audio do microfone.
  - Para que serve: grava o audio direto do dispositivo de entrada.
  - Como usa: `SpeechToText._record_fixed_duration`; escolha com `JARVIS_AUDIO_DEVICE` e `JARVIS_AUDIO_CAPTURE_SR`.
  - Instalar: `pip install sounddevice`
  - Linux: pode exigir `libportaudio2`, `portaudio19-dev` e `libasound2-dev`.
  - Se a importacao travar, instale as libs acima e reinicie o processo.
- `numpy` - buffer de audio e conversoes.
  - Para que serve: transformar PCM int16 em float32 e vice-versa.
- Como usa: `jarvis/interface/entrada/stt.py` e `jarvis/interface/entrada/vad.py` para conversao de buffers e AEC/AGC/NS simples.
  - Instalar: `pip install numpy`
- `scipy` - reamostragem (quando o microfone nao suporta 16 kHz).
  - Para que serve: reamostrar audio de 44.1k/48k para 16k.
- Como usa: `resample_poly` em `jarvis/interface/entrada/stt.py` quando `capture_sr != 16000`.
  - Instalar: `pip install scipy`
- `webrtcvad` - VAD leve para detectar fala.
  - Para que serve: decidir onde ha fala vs. silencio.
- Como usa: auto em `jarvis/interface/entrada/vad.py` quando instalado.
  - Instalar: `pip install webrtcvad`
- `faster-whisper` - STT local (transcricao).
  - Para que serve: transcrever audio localmente sem API externa.
  - Como usa: `SpeechToText._transcribe_local` com `JARVIS_STT_MODEL` e `JARVIS_STT_LANGUAGE`.
  - Instalar: `pip install faster-whisper`
- `RealtimeSTT` - STT streaming (opcional).
  - Para que serve: transcricao em tempo real com callbacks parciais.
- Como usa: `JARVIS_STT_STREAMING=1` habilita o backend no `jarvis/interface/entrada/stt.py`.
  - Fonte: `pip install RealtimeSTT` (preferencial) **ou** copia vendorizada em `jarvis/third_party/realtimestt` (offline).
  - Fallback de transicao: clone em `jarvis/REPOSITORIOS_CLONAR/realtimestt` (pode ser removido quando a copia vendorizada estiver validada).
  - Downloads: por seguranca o Jarvis seta `HF_HUB_OFFLINE=1` durante a inicializacao do RealtimeSTT (evita baixar modelos em runtime).
    - Para permitir downloads (quando voce souber o que esta fazendo): `JARVIS_ALLOW_MODEL_DOWNLOADS=1`.
- `pyaudio` - captura de audio para RealtimeSTT (opcional).
  - Para que serve: entrada de microfone dentro do RealtimeSTT.
  - Como usa: necessario quando `JARVIS_STT_STREAMING=1` e o streaming usa microfone.
  - Instalar: `pip install pyaudio`
  - Linux: pode exigir `portaudio19-dev` e `python3-dev`.
- `halo` - spinner do RealtimeSTT (opcional, mas importado por padrao).
  - Para que serve: animacao de estado durante captura/transcricao.
  - Como usa: dependencia indireta do RealtimeSTT.
  - Instalar: `pip install halo`
- `websocket-client` - cliente websocket do RealtimeSTT (opcional).
  - Para que serve: suporte ao modo client/server do RealtimeSTT.
  - Como usa: dependencia indireta do RealtimeSTT.
  - Instalar: `pip install websocket-client`
- `torchaudio` - Silero VAD usado pelo RealtimeSTT.
  - Para que serve: modelo de VAD usado internamente pelo RealtimeSTT.
  - Como usa: necessario quando RealtimeSTT inicializa o Silero VAD.
  - Instalar: `pip install torchaudio`
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
- Como usa: `JARVIS_CHAT_SHORTCUT_COMBO` (padrao `ctrl+shift+j`) em `jarvis/interface/entrada/shortcut.py`.
  - Instalar: `pip install pynput`
  - Alternativa sem pynput: `JARVIS_CHAT_SHORTCUT_FILE` + atalho do sistema (`touch`).
- `watchdog` - atualizar chat UI por evento (opcional).
  - Para que serve: refletir mudancas no log/inbox sem polling pesado.
- Como usa: `jarvis/interface/entrada/chat_ui.py` monitora arquivos quando instalado.
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
- `speexdsp` - AEC (cancelamento de eco) via Speex (opcional).
  - Para que serve: cancelar eco do TTS capturado pelo microfone.
  - Como usa: `JARVIS_AEC_BACKEND=speex` habilita o backend Speex.
  - Instalar: `pip install speexdsp`
  - Requisito sistema: `sudo apt install swig libspeexdsp-dev`
- `webrtc-audio-processing` - AEC via WebRTC (opcional).
  - Para que serve: cancelamento de eco e processamento de audio avancado.
  - Como usa: `JARVIS_AEC_BACKEND=webrtc` habilita o backend WebRTC.
  - Instalar: `pip install webrtc-audio-processing`
  - Requisito sistema: `sudo apt install swig libspeexdsp-dev`
- `piper-tts` - TTS Piper via Python (opcional, recomendado).
  - Para que serve: backend Python do Piper (modelo carregado em memoria, menor TTFA).
  - Como usa: `JARVIS_PIPER_BACKEND=python` usa o backend Python em vez de CLI.
  - Instalar: `pip install piper-tts`
  - Nota: instala automaticamente o binario `piper` em `.venv/bin/piper`.
- `pytest` - runner de testes.
  - Para que serve: rodar a suite automatizada da interface.
  - Como usa: `PYTHONPATH=. pytest -q testes/`
  - Instalar: `pip install pytest`
- `ruff` - lint rapido.
  - Para que serve: verificar estilo/erros de codigo.
  - Como usa: `./.venv/bin/ruff check .`
  - Instalar: `pip install ruff`
- `black` - formatador.
  - Para que serve: verificar formatacao consistente.
  - Como usa: `./.venv/bin/black --check .`
  - Instalar: `pip install black`
- `pytest-xdist` - paralelizar testes (opcional).
  - Para que serve: rodar testes em paralelo em maquinas com muitos cores.
  - Como usa: `PYTHONPATH=. pytest -q -n auto testes/`
  - Instalar: `pip install pytest-xdist`
- `pytest-repeat` - repetir testes (opcional).
  - Para que serve: stress test (rodar o mesmo teste varias vezes).
  - Como usa: `PYTHONPATH=. pytest -q --count 20 testes/test_stt_flow.py`
  - Instalar: `pip install pytest-repeat`

## Sistema (binarios)
- `piper` - TTS neural local (voz humanizada).
  - Para que serve: gerar fala local de maior qualidade (voz natural/humanizada).
  - Como usa: `JARVIS_TTS_MODE=local`, `JARVIS_PIPER_MODELS_DIR` e `JARVIS_PIPER_VOICE`.
  - Padrao recomendado (portavel no repo): colocar modelos em `storage/models/piper/` e usar `JARVIS_PIPER_MODELS_DIR=storage/models/piper`.
  - O sistema procura o binario em: `.venv/bin/piper` (quando instalado via `pip install piper-tts`), PATH, `~/.local/bin/piper`, `/usr/local/bin/piper`, `/usr/bin/piper`, `~/bin/piper`.
  - Opcional: `JARVIS_PIPER_BIN` (caminho explicito do binario) e `JARVIS_PIPER_MODEL` (caminho completo do `.onnx`).
  - Se nao encontrar, usa espeak-ng automaticamente (voz robotica).
  - Instalacao:
    1. Baixar de: https://github.com/rhasspy/piper/releases
    2. Colocar em `~/.local/bin/` ou adicionar ao PATH
    3. Baixar modelo: `mkdir -p ~/.local/share/piper-models && cd ~/.local/share/piper-models && wget https://huggingface.co/rhasspy/piper-voices/resolve/main/pt/pt_BR/faber/medium/pt_BR-faber-medium.onnx`
  - Ver instrucoes completas em `Documentos/DOC_INTERFACE/voz_tts.md`.
- `espeak-ng` - TTS fallback (voz robotica).
  - Para que serve: fallback quando Piper nao esta disponivel ou modelo nao encontrado.
  - Sempre disponivel quando instalado (sistema tenta Piper primeiro, depois espeak-ng).
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
- Como usa: `JARVIS_AUDIO_TRIM_BACKEND=rust` habilita o trim em `jarvis/interface/entrada/stt.py`.
  - Build: `scripts/build_rust_audio.sh`

## Variaveis de ambiente relevantes
- `JARVIS_STT_MODE`, `JARVIS_TTS_MODE`, `JARVIS_STT_PROFILE`
- `JARVIS_STT_STREAMING`, `JARVIS_STT_STREAMING_BACKEND`
- `JARVIS_STT_STREAMING_FORCE_START`, `JARVIS_STT_STREAMING_MAX_SECONDS`
- `JARVIS_STT_MODEL`, `JARVIS_STT_REALTIME_MODEL`, `JARVIS_STT_FALLBACK_MODEL`
- `JARVIS_STT_LANGUAGE`, `JARVIS_STT_RETRY_AUTO_LANGUAGE`, `JARVIS_STT_RETRY_FALLBACK_MODEL`
- `JARVIS_AUDIO_DEVICE`, `JARVIS_AUDIO_CAPTURE_SR`
- `JARVIS_MIN_AUDIO_SECONDS`, `JARVIS_STT_MIN_AUDIO_MS`, `JARVIS_STT_MIN_PEAK`
- `JARVIS_STT_MIN_GAP_SECONDS`, `JARVIS_STT_ALLOWED_LATENCY_MS`
- `JARVIS_STT_EARLY_TRANSCRIBE_ON_SILENCE`, `JARVIS_STT_MAX_BUFFER_SECONDS`
- `JARVIS_STT_NORMALIZE_AUDIO`, `JARVIS_STT_NORMALIZE_TARGET`, `JARVIS_STT_NORMALIZE_MAX_GAIN`
- `JARVIS_STT_TRIM_VAD`, `JARVIS_FORCE_SPEECH_OK`
- `JARVIS_AUDIO_TRIM_BACKEND`
- `JARVIS_WHISPER_VAD_FILTER`, `JARVIS_STT_BEAM_SIZE`, `JARVIS_STT_BEST_OF`
- `JARVIS_STT_TEMPERATURE`, `JARVIS_STT_INITIAL_PROMPT`, `JARVIS_STT_SUPPRESS_TOKENS`
- `JARVIS_STT_WARMUP`, `JARVIS_STT_WARMUP_SECONDS`, `JARVIS_STT_METRICS`
- `JARVIS_VAD_AGGRESSIVENESS`, `JARVIS_VAD_METRICS`
- `JARVIS_VAD_STRATEGY` (webrtc|silero|whisper|realtimestt)
- `JARVIS_VAD_SILENCE_MS`, `JARVIS_VAD_PRE_ROLL_MS`, `JARVIS_VAD_POST_ROLL_MS`, `JARVIS_VAD_MAX_SECONDS`
- `JARVIS_PIPER_MODELS_DIR`, `JARVIS_PIPER_VOICE`
- `JARVIS_SPK_VERIFY`, `JARVIS_SPK_THRESHOLD`, `JARVIS_CONFIG_DIR`
- `JARVIS_SPK_VOICEPRINT_PASSPHRASE`
- `JARVIS_WAKE_WORD_AUDIO`, `JARVIS_WAKE_WORD_AUDIO_STRICT`
- `JARVIS_PORCUPINE_ACCESS_KEY`
- `JARVIS_PORCUPINE_KEYWORD_PATH`, `JARVIS_PORCUPINE_SENSITIVITY`
- `JARVIS_WAKE_WORD_AUDIO_BACKEND`, `JARVIS_OPENWAKEWORD_MODEL_PATHS`
- `JARVIS_OPENWAKEWORD_INFERENCE_FRAMEWORK`, `JARVIS_OPENWAKEWORD_SENSITIVITY`
- `JARVIS_OPENWAKEWORD_AUTO_DOWNLOAD`
- `JARVIS_SILERO_DEACTIVITY`, `JARVIS_SILERO_SENSITIVITY`
- `JARVIS_SILERO_USE_ONNX`, `JARVIS_SILERO_AUTO_DOWNLOAD`
- `JARVIS_AEC_BACKEND`, `JARVIS_AEC_REF_SECONDS`, `JARVIS_AEC_MAX_GAIN`
- `JARVIS_AUDIO_AGC_TARGET_RMS`, `JARVIS_AUDIO_AGC_MAX_GAIN`
- `JARVIS_AUDIO_NS_GATE_RMS`

## Comandos de verificacao rapida
- Preflight: `PYTHONPATH=. python -m jarvis.interface.entrada.app --preflight`
- STT deps: `python -c "from jarvis.interface.entrada.stt import check_stt_deps; print(check_stt_deps())"`
- TTS deps: `python -c "from jarvis.interface.saida.tts import check_tts_deps; print(check_tts_deps())"`
- Profiling (py-spy): `py-spy --version`

## Status local (verificar antes de testar)
- Rode preflight: `PYTHONPATH=. python -m jarvis.interface.entrada.app --preflight --preflight-profile voice`
- Rode o benchmark: `PYTHONPATH=. python scripts/bench_interface.py stt --audio Documentos/DOC_INTERFACE/bench_audio/voice_clean.wav --repeat 3 --resample`
- Registre resultados em `Documentos/DOC_INTERFACE/TESTES_REALISADOS_INTERFACE.MD`.
