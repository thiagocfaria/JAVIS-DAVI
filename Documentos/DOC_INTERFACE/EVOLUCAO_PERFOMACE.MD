# EVOLUCAO_PERFOMACE.md

Registro de evolucao de performance da interface de entrada/saida de voz.

## Objetivo
- Medir o pior caso de producao e acompanhar ganhos/retrocesso ao longo do tempo.
- Guardar baseline com comandos, ambiente e metricas (latencia/CPU/RSS).

## Baseline atual (pior caso)
- Data: 2026-01-07
- Metodo: `scripts/bench_interface.py` com audio sintetico 16 kHz mono (30s).
- Audio: `/tmp/jarvis_bench_30s.wav`
- Repeticoes: STT=1, VAD=5, Speaker=3, TTS=3
- Observacao: TTS mede apenas o custo de iniciar processo (speak nao bloqueia).
- Historico bruto (JSON unico): `bench_history.json`

### Resultados (pior caso 30s)
| Cenario | Latencia media (ms) | p50 (ms) | p95 (ms) | CPU avg (s) | RSS (KB) |
| --- | --- | --- | --- | --- | --- |
| STT | 23231.06 | 23231.06 | 23231.06 | 29.9633 | 1235104 |
| VAD | 9.69 | 11.45 | 13.96 | 0.0061 | 641144 |
| Speaker (JARVIS_SPK_VERIFY=1) | 3102.79 | 690.05 | 13826.84 | 2.3698 | 772616 |
| TTS (local) | 4.67 | 6.10 | 7.59 | 0.0005 | 24900 |

## Ambiente
- SO: Linux
- Python: .venv (local)
- Dependencias chave: numpy, scipy, sounddevice, webrtcvad, faster-whisper, resemblyzer, pynput, py-spy
- TTS: espeak-ng presente; piper ausente

## Comandos usados
- STT: `PYTHONPATH=. .venv/bin/python scripts/bench_interface.py stt --audio /tmp/jarvis_bench_30s.wav --repeat 1`
- VAD: `PYTHONPATH=. .venv/bin/python scripts/bench_interface.py vad --audio /tmp/jarvis_bench_30s.wav --repeat 5`
- Speaker: `PYTHONPATH=. JARVIS_CONFIG_DIR=/tmp/jarvis_bench_config JARVIS_SPK_VERIFY=1 .venv/bin/python scripts/bench_interface.py speaker --audio /tmp/jarvis_bench_30s.wav --repeat 3`
- TTS: `PYTHONPATH=. .venv/bin/python scripts/bench_interface.py tts --text "ola jarvis, ..." --repeat 3`
- Profiling (opcional): `py-spy record -o profile.svg -- python scripts/bench_interface.py stt --audio /tmp/jarvis_bench_30s.wav`

## Formato do JSON (bench_history.json)
- Arquivo unico com um array `history`.
- Cada item representa uma rodada completa (baseline + commands + results).
- Campos minimos recomendados:
  - `record_id`: id unico da rodada.
  - `created_at`: data (YYYY-MM-DD).
  - `baseline`: informacoes do ambiente e do audio.
  - `commands`: comandos exatos usados.
  - `results`: lista de cenarios e metricas.

Exemplo minimo de registro:
```json
{
  "record_id": "baseline_2026-01-07_pior_caso_30s",
  "created_at": "2026-01-07",
  "baseline": {"audio": "/tmp/voz.wav", "duration_s": 30},
  "commands": {"stt": "PYTHONPATH=. ..."},
  "results": [{"scenario": "stt", "latency_ms_avg": 123.4}]
}
```

## Como anexar nova rodada no historico
- Crie um JSON de registro (mesmo formato acima), por exemplo: `/tmp/bench_record.json`
- Anexe ao historico:
  - `PYTHONPATH=. .venv/bin/python scripts/bench_history_append.py --record /tmp/bench_record.json`

## Limites e notas
- STT e Speaker sao os maiores consumidores (modelo e embedding).
- TTS mede apenas o custo de spawn; nao mede duracao real de fala.
- RSS depende do modelo e do cache de libs (varia por execucao).

## Proximos passos
- Repetir baseline com audio real gravado em producao.
- Comparar historico usando o JSON salvo (ver arquivo acima).
- Adicionar reamostragem automatica e medir impacto (ver checklist).

## Atualizacoes recentes (sem benchmark)
- 2026-01-08: chat_ui passou a ler o tail do log por blocos (evita carregar o arquivo inteiro).
- 2026-01-08: speaker_verify/adapter passaram a usar cache de voiceprint (reduz IO).
- 2026-01-08: gui_panel passou a alternar STOP para cancelamento de comandos.
- 2026-01-08: follow-up agora limita quantidade de comandos por janela.
- 2026-01-08: TTS agora serializa chamadas (evita sobreposicao de audio).
