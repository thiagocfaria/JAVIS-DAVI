# benchmark_interface.md

- Caminho: `scripts/bench_interface.py`
- Papel: medir latencia, CPU e memoria de cenarios da interface de voz.
- Onde entra no fluxo: ferramenta de diagnostico (nao usada em producao).

## Responsabilidades
- Rodar cenarios controlados (STT, VAD, TTS, speaker verify).
- Medir tempo medio/p50/p95, CPU time e RSS.
- Gerar saida JSON para arquivar resultados.

## Entrada e saida
- Entrada: WAV 16 kHz mono para STT/VAD/speaker; texto para TTS.
- Saida: JSON com metricas (latencia, CPU, RSS).

## Configuracao (CLI)
- `scenario`: `stt|vad|tts|speaker`
- `--audio <arquivo.wav>`
- `--text "frase"`
- `--repeat N`
- `--tts-mode local|none`
- `--json saida.json`

## Dependencias diretas
- Stdlib (argparse, wave, resource, time)
- Requisitos do proprio modulo (STT/VAD/TTS/speaker)

## Testes relacionados
- Sem testes automatizados (script manual).

## Comandos uteis
- STT: `PYTHONPATH=. python scripts/bench_interface.py stt --audio samples/voz_16k.wav --repeat 5`
- VAD: `PYTHONPATH=. python scripts/bench_interface.py vad --audio samples/voz_16k.wav --repeat 10`
- TTS: `PYTHONPATH=. python scripts/bench_interface.py tts --text "ola" --repeat 3`
- Speaker: `PYTHONPATH=. python scripts/bench_interface.py speaker --audio samples/voz_16k.wav --repeat 5`
- Salvar JSON: `PYTHONPATH=. python scripts/bench_interface.py stt --audio samples/voz_16k.wav --json bench.json`
- Profiling profundo (py-spy): `py-spy record -o profile.svg -- python scripts/bench_interface.py stt --audio samples/voz_16k.wav`

## Qualidade e limites
- WAV deve ser mono 16 kHz; caso contrario o script falha.
- Resultados variam por maquina e ambiente (usar varias repeticoes).

## Performance (estimativa)
- Uso esperado: depende do scenario (STT/TTS sao mais pesados).
- Medir: comparar p50/p95 e RSS entre execucoes.

## Observabilidade
- Saida JSON e opcionalmente arquivo `--json`.

## Problemas conhecidos (hoje)
- Nao mede GPU de forma direta.
- Nao faz reamostragem automatica quando o audio nao e 16 kHz.

## Melhorias sugeridas
- Adicionar opcao de reamostragem usando `scipy` quando necessario.
- Integrar coleta de CPU/RAM via `psutil`.
