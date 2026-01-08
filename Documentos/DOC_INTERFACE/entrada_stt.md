# entrada/stt.py

- Caminho: `jarvis/entrada/stt.py`
- Papel: capturar audio, aplicar VAD/trim e transcrever localmente.
- Onde entra no fluxo: usado pelo orquestrador no modo voz.

## Responsabilidades
- Capturar audio (sounddevice) em SR nativo e reamostrar para 16 kHz.
- VAD streaming quando possivel; fallback para gravacao fixa.
- Coercao de tipos para PCM bytes int16.
- Wake word opcional com filtro de fronteira.
- Trim opcional via Rust (`jarvis_audio`).
- `transcribe_with_vad` usa captura com VAD ate silencio.
- `transcribe_once` usa captura fixa (com VAD streaming se houver).

## Entrada e saida
- Entrada: microfone ou bytes PCM.
- Saida: texto transcrito (str) e opcionalmente `audio_bytes` + `speech_detected`.
- Contrato: PCM int16 mono 16 kHz (little-endian).

## Configuracao (env/config)
- `JARVIS_STT_MODE` (config `stt_mode`)
- `JARVIS_STT_MODEL` e `stt_model_size`
- `JARVIS_STT_LANGUAGE` ("pt" ou "auto")
- `JARVIS_STT_MIN_AUDIO_MS`
- `JARVIS_STT_MIN_PEAK` (limiar de pico quando nao ha VAD/Rust)
- `JARVIS_MIN_AUDIO_SECONDS`
- `JARVIS_AUDIO_DEVICE`
- `JARVIS_AUDIO_CAPTURE_SR`
- `JARVIS_REQUIRE_WAKE_WORD`, `JARVIS_WAKE_WORD`
- `JARVIS_DEBUG`
- `stt_audio_trim_backend` (config)

## Dependencias diretas
- `sounddevice`, `numpy`, `scipy` (reamostra; sem `scipy` a reamostragem falha)
- `faster-whisper`
- `jarvis/voz/vad.py` (StreamingVAD, VoiceActivityDetector)
- `jarvis_audio` (opcional)

## Testes relacionados
- `testes/test_stt_flow.py`
- `testes/test_stt_filters.py`
- `testes/test_stt_rust_trim.py`
- `testes/test_stt_capture_config.py`
- `testes/test_audio_resample.py`

## Comandos uteis
- Smoke: `PYTHONPATH=. python -c "from jarvis.entrada.stt import SpeechToText; print('ok')"`
- Testes STT: `PYTHONPATH=. pytest -q testes/test_stt_flow.py testes/test_stt_filters.py`
- Teste reamostragem: `PYTHONPATH=. pytest -q testes/test_audio_resample.py`
- Build Rust (opcional): `bash scripts/build_rust_audio.sh`

## Qualidade e limites
- Se nao houver fala (VAD/trim), retorna "".
- Limite minimo por `JARVIS_STT_MIN_AUDIO_MS`.
- VAD streaming em `transcribe_with_vad` so e usado quando capture_sr == 16k e device padrao.
- Em `transcribe_once`, streaming tambem so e usado quando capture_sr == 16k e device padrao.
- Se o device nao suporta 16 kHz e `scipy` nao estiver instalado, a reamostragem falha.
- Preflight agora avisa quando `scipy` esta ausente.


## Performance (estimativa)
- Uso esperado: alto (transcricao local).
- Medir: use `/usr/bin/time -v <comando>` e monitore `top`/`htop`.

## Observabilidade
- Debug via `JARVIS_DEBUG=1` (mensagens com prefixo [stt]).

## Problemas conhecidos (hoje)
- Sem AEC/NS/AGC; ruido ambiente pode virar texto.
- Sem `scipy`, a reamostragem falha quando o device nao suporta 16 kHz.
- Sem VAD/Rust, usa limiar simples de pico (pode falhar com fala muito baixa).

## Melhorias sugeridas
- Metrics de duracao por etapa (captura, VAD, transcricao).
- Opcao de AEC/NS/AGC antes do VAD.
- ~~Bloquear streaming quando capture_sr != 16k para evitar inconsistencias.~~ (resolvido)
