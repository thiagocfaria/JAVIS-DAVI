# benchmark_interface.md

- Caminho: `scripts/bench_interface.py`
- Papel: medir latencia, CPU e memoria de cenarios da interface de voz.
- Onde entra no fluxo: ferramenta de diagnostico (nao usada em producao).
- Atualizado em: 2026-01-13 (inclui endpointing offline)

## Responsabilidades
- Rodar cenarios controlados (STT, VAD, endpointing, TTS, speaker verify).
- Medir tempo medio/p50/p95, CPU time e RSS.
- Gerar saida JSON para arquivar resultados (inclui CPU/RAM via psutil quando disponivel).

## Entrada e saida
- Entrada: WAV 16 kHz mono para STT/VAD/speaker; texto para TTS.
- Saida: JSON com metricas (latencia, CPU, RSS).

## Configuracao (CLI)
- `scenario`: `stt|vad|endpointing|tts|speaker`
- `--audio <arquivo.wav>`
- `--text "frase"`
- `--repeat N`
- `--tts-mode local|none`
- `--json saida.json`
- `--resample` (reamostra para 16 kHz quando o WAV nao esta em 16 kHz)
- `--gpu` (coleta metricas de GPU via `nvidia-smi`, se disponivel)

## Dependencias diretas
- Stdlib (argparse, wave, resource, time)
- Requisitos do proprio modulo (STT/VAD/TTS/speaker)
- `psutil` (opcional; CPU/RAM por processo)
- `scipy`/`numpy` (opcional; reamostragem)

## Testes relacionados
- `testes/test_bench_interface.py` (valida reamostragem e leitura de WAV).

## Comandos uteis
- STT: `PYTHONPATH=. python scripts/bench_interface.py stt --audio samples/voz_16k.wav --repeat 5`
- STT (com reamostragem): `PYTHONPATH=. python scripts/bench_interface.py stt --audio samples/voz_44k.wav --resample --repeat 5`
- STT (com GPU): `PYTHONPATH=. python scripts/bench_interface.py stt --audio samples/voz_16k.wav --gpu --repeat 5`
- VAD: `PYTHONPATH=. python scripts/bench_interface.py vad --audio samples/voz_16k.wav --repeat 10`
- Endpointing: `PYTHONPATH=. python scripts/bench_interface.py endpointing --audio samples/voz_16k.wav --repeat 10`
- TTS: `PYTHONPATH=. python scripts/bench_interface.py tts --text "ola" --repeat 3`
- Speaker: `PYTHONPATH=. python scripts/bench_interface.py speaker --audio samples/voz_16k.wav --repeat 5`
- Salvar JSON: `PYTHONPATH=. python scripts/bench_interface.py stt --audio samples/voz_16k.wav --json bench.json`
- Profiling profundo (py-spy): `py-spy record -o profile.svg -- python scripts/bench_interface.py stt --audio samples/voz_16k.wav`

## Auto-benchmark (voz real via microfone)
- Script: `scripts/auto_voice_bench.py`
- Faz: grava 1 amostra limpa e 1 com ruido, roda STT/VAD/endpointing e gera JSONs.
- Exemplo: `python scripts/auto_voice_bench.py --device 6 --with-noise --output-dir Documentos/DOC_INTERFACE/bench_audio --phrase "oi jarvis teste automatico" --seconds 4`

## Baseline padronizado (clean/noise)
Objetivo: ter um baseline repetivel usando as gravacoes `bench_audio/voice_clean.wav` e `bench_audio/voice_noise.wav`.

- STT (recomendado fixar o modelo para comparar 1:1): `PYTHONPATH=. JARVIS_STT_MODEL=tiny ./.venv/bin/python scripts/bench_interface.py stt --audio Documentos/DOC_INTERFACE/bench_audio/voice_clean.wav --repeat 5 --resample --json Documentos/DOC_INTERFACE/bench_audio/voice_clean.stt.<data>.json`
- VAD: `PYTHONPATH=. ./.venv/bin/python scripts/bench_interface.py vad --audio Documentos/DOC_INTERFACE/bench_audio/voice_clean.wav --repeat 10 --resample --json Documentos/DOC_INTERFACE/bench_audio/voice_clean.vad.<data>.json`
- Endpointing: `PYTHONPATH=. ./.venv/bin/python scripts/bench_interface.py endpointing --audio Documentos/DOC_INTERFACE/bench_audio/voice_clean.wav --repeat 10 --resample --json Documentos/DOC_INTERFACE/bench_audio/voice_clean.endpointing.<data>.json`
- Registro: atualizar `Documentos/DOC_INTERFACE/EVOLUCAO_PERFOMACE.MD` e anexar um record em `Documentos/DOC_INTERFACE/bench_history.json` (ver `scripts/bench_history_append.py`).

## Qualidade e limites
- WAV deve ser mono 16 kHz; ou use `--resample` para converter automaticamente (requer scipy).
- Resultados variam por maquina e ambiente (usar varias repeticoes).
- `bench_interface.py` roda apenas com arquivos WAV (nao requer `sounddevice`).
- `auto_voice_bench.py` exige `sounddevice`/`numpy` para gravar do microfone.

## Performance (estimativa)
- Uso esperado: depende do scenario (STT/TTS sao mais pesados).
- Medir: comparar p50/p95 e RSS entre execucoes.

## Observabilidade
- Saida JSON e opcionalmente arquivo `--json`.
- Campos extras quando `psutil` existe: `psutil_cpu_percent`, `psutil_rss_bytes`, `psutil_vms_bytes`.
- Campos extras quando `--gpu` e `nvidia-smi` existem: `gpu_util_percent`, `gpu_mem_used_mb`, `gpu_mem_total_mb`.

## Problemas conhecidos (hoje)
- (nenhum no momento)

## Melhorias sugeridas
- (nenhuma pendente relevante no momento)
