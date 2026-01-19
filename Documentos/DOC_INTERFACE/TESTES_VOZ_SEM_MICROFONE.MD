# Testes de voz **sem microfone** (replay via WAV)

Objetivo: validar STT/VAD/TTS e medir latência **sem depender** de microfone, ruído do ambiente, ALSA/Pulse/PipeWire, etc.

Arquivos de áudio já disponíveis no repo:
- `Documentos/DOC_INTERFACE/bench_audio/voice_clean.wav` (fala mais “limpa”)
- `Documentos/DOC_INTERFACE/bench_audio/voice_noise.wav` (fala com mais ruído)

> Esses WAVs estão em `44.1kHz` e o benchmark consegue reamostrar para `16kHz` com `--resample`.

## Regras (para comparar 1:1)
- Rodar sempre com o mesmo `repeat` (ex.: 20) quando for comparar “antes vs depois”.
- Registrar ambiente (CPU/OS, se STT já está em cache, etc.).
- Rodar 2 vezes e anotar se o p95 varia muito (instabilidade).

## 1) STT (latência + “o que ele transcreveu”)
Obs: por padrão o benchmark faz **warmup** do STT antes de medir (para simular “serviço já rodando”).
Se quiser medir “cold start” (carregar modelo no tempo), use `--no-warmup`.

Comando (fala limpa):
- `PYTHONPATH=. ./.venv/bin/python scripts/bench_interface.py stt --audio Documentos/DOC_INTERFACE/bench_audio/voice_clean.wav --repeat 10 --resample --print-text`

O que você deve ver:
- JSON com `latency_ms_p50/p95`
- `transcribed_text_last` com o texto final reconhecido

Comando (fala com ruído):
- `PYTHONPATH=. ./.venv/bin/python scripts/bench_interface.py stt --audio Documentos/DOC_INTERFACE/bench_audio/voice_noise.wav --repeat 10 --resample --print-text`

## 2) VAD / endpointing (fim da fala)
Comando (fala limpa):
- `PYTHONPATH=. ./.venv/bin/python scripts/bench_interface.py endpointing --audio Documentos/DOC_INTERFACE/bench_audio/voice_clean.wav --repeat 20 --resample`

O que você deve ver:
- JSON com `endpoint_reached_rate` (quanto mais perto de 1.0, melhor)
- `endpoint_ms_p50/p95` (quanto menor, melhor; sem cortar fala)

## 3) Pipeline “EoS -> primeiro áudio” (latência percebida)
Esse benchmark simula:
1) áudio termina (EoS)
2) STT roda em cima do áudio (já reamostrado/trim)
3) TTS fala uma resposta curta (ex.: “ok”)

Comando (fala limpa):
- `PYTHONPATH=. ./.venv/bin/python scripts/bench_interface.py eos_to_first_audio --audio Documentos/DOC_INTERFACE/bench_audio/voice_clean.wav --text \"ok\" --repeat 20 --resample`

O que você deve ver (JSON):
- `eos_to_first_audio_ms_p50/p95` (quanto menor, melhor)
- `stt_ms_p50` (tempo do STT)
- `tts_first_audio_ms_p50` (TTFA do TTS)
- (se habilitado) `eos_to_ack_ms_p50/p95` ou `eos_to_phase1_ms_p50/p95`

## 4) “Passou / não passou” (checklist)
- [ ] STT (clean): `transcribed_text_last` parece correto (não é texto aleatório)
- [ ] STT (noise): ainda é aceitável (pode errar um pouco, mas não “viaja” sempre)
- [ ] Endpointing: `endpoint_reached_rate` alto (ideal: >= 0.9)
- [ ] EoS->first audio: caiu ou manteve (não piorou) após mudanças

## Importante (limitações)
- Esses testes **não** validam captação real (microfone), eco, TV ligada, teclado, etc.
- Eles servem para validar o “motor” (STT/VAD/TTS/pipeline) e comparar mudanças de código com o mínimo de variáveis externas.
