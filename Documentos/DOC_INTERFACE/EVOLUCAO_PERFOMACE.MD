# EVOLUCAO_PERFOMACE.md

Registro de evolucao de performance da interface de entrada/saida de voz.

## Objetivo (bem simples)
- Medir o pior caso e ver se ficou mais rapido ou mais lento.
- Guardar o baseline com comandos, ambiente e metricas (latencia/CPU/RSS).

## Resumo rapido (em linguagem facil)
- O sistema tem 4 etapas: VAD (ouvir), STT (entender), Speaker (confirmar) e TTS (responder).
- No baseline de 2026-01-11, o STT ficou mais lento que 2026-01-10; o VAD subiu um pouco; o TTS ficou mais rapido.
- O benchmark de Speaker nao e representativo se nao houver voiceprint (neste teste retornou rapido demais).
- A comparacao ainda nao e 1:1 porque o audio foi gerado agora (espeak-ng 22.05k com resample).

## Evolucao visual (ms, menor e melhor)
Legenda: barra maior = mais lento. Comparacao indicativa (audio diferente).

STT
2026-01-11 | ########################################### 44217
2026-01-10 | #################               13598
2026-01-07 | ############################### 23231

VAD
2026-01-11 | ########                        8,29
2026-01-10 | #####                           4,55
2026-01-07 | ##########                      9,69

Speaker
2026-01-11 | #                               0,05*
2026-01-10 | #######                         637
2026-01-07 | ############################    3102

TTS
2026-01-11 | ###                             1,46
2026-01-10 | #####                           2,41
2026-01-07 | #########                       4,67

*Speaker 2026-01-11: tempo muito baixo pode indicar falta de voiceprint (nao representa a verificacao real).*

## Sinais de ganho (indicativos)
- STT: 13598 ms -> 44217 ms (piorou ~30,6s).
- VAD: 4,55 ms -> 8,29 ms (piorou ~3,7 ms).
- Speaker: 637 ms -> 0,05 ms (nao representativo; possivel falta de voiceprint).
- TTS: 2,41 ms -> 1,46 ms (melhorou ~0,95 ms).
- Nota: comparacao nao e 1:1 porque o audio foi gerado agora (espeak-ng 22.05k + resample).

## Baseline atual (pior caso)
- Data: 2026-01-11
- Metodo: `scripts/bench_interface.py` com audio espeak-ng (22.05 kHz) reamostrado para 16 kHz (`--resample`), 30s.
- Audio: `/tmp/jarvis_bench_30s.wav`
- Repeticoes: STT=1, VAD=5, Speaker=3, TTS=3
- Observacao 1: TTS mede apenas o custo de iniciar processo (speak nao bloqueia).
- Observacao 2: Speaker pode nao ser representativo sem voiceprint (ver nota nos resultados).
- Historico bruto (JSON unico): `bench_history.json`

### Resultados (pior caso 30s)
| Cenario | Latencia media (ms) | p50 (ms) | p95 (ms) | CPU avg (s) | RSS (KB) |
| --- | --- | --- | --- | --- | --- |
| STT | 44216.84 | 44216.84 | 44216.84 | 79.0837 | 1735028 |
| VAD | 8.29 | 6.70 | 12.73 | 0.0059 | 617312 |
| Speaker (JARVIS_SPK_VERIFY=1) | 0.05 | 0.03 | 0.13 | 0.0001 | 578968 |
| TTS (local) | 1.46 | 1.42 | 1.66 | 0.0008 | 98664 |

## Baseline anterior (pior caso)
- Data: 2026-01-10
- Metodo: `scripts/bench_interface.py` com audio espeak repetido, 16 kHz mono (30s).
- Audio: `/tmp/jarvis_bench_30s.wav`
- Repeticoes: STT=1, VAD=5, Speaker=3, TTS=3
- Observacao 1: TTS mede apenas o custo de iniciar processo (speak nao bloqueia).
- Observacao 2: import do `sounddevice` travou no ambiente; usei stub apenas para STT/VAD no benchmark (nao altera esses cenarios).
- Historico bruto (JSON unico): `bench_history.json`

### Resultados (pior caso 30s)
| Cenario | Latencia media (ms) | p50 (ms) | p95 (ms) | CPU avg (s) | RSS (KB) |
| --- | --- | --- | --- | --- | --- |
| STT | 13597.57 | 13597.57 | 13597.57 | 38.1461 | 1249704 |
| VAD | 4.55 | 4.45 | 5.21 | 0.0045 | 607236 |
| Speaker (JARVIS_SPK_VERIFY=1) | 637.05 | 402.19 | 1928.65 | 1.7605 | 760536 |
| TTS (local) | 2.41 | 0.66 | 10.35 | 0.0003 | 98376 |

## Baseline anterior (pior caso)
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

## Rodada anterior (incompleta: deps ausentes)
- Data: 2026-01-08
- Metodo: `scripts/bench_interface.py` com audio espeak repetido (30s).
- Observacao: faltam deps de STT/speaker (`faster-whisper`, `resemblyzer`, `webrtcvad`, `numpy`, `sounddevice`, `scipy`).  
  Resultado: STT/speaker nao representam o pior caso real.

### Resultados (30s)
| Cenario | Latencia media (ms) | p50 (ms) | p95 (ms) | CPU avg (s) | RSS (KB) |
| --- | --- | --- | --- | --- | --- |
| STT (sem deps) | 57.25 | 57.25 | 57.25 | 0.0452 | 31892 |
| VAD | 79.89 | 78.40 | 136.56 | 0.0526 | 32016 |
| Speaker (sem deps) | 0.01 | 0.01 | 0.04 | 0.0000 | 32188 |
| TTS (local) | 1.05 | 0.88 | 2.05 | 0.0006 | 32216 |

## Ambiente
- SO: Linux
- Python: .venv (local)
- Dependencias chave: numpy, scipy, sounddevice, webrtcvad, faster-whisper, resemblyzer, pynput, py-spy
- TTS: espeak-ng presente; piper ausente

## Como medimos (comandos)
- STT: `PYTHONPATH=. .venv/bin/python scripts/bench_interface.py stt --audio /tmp/jarvis_bench_30s.wav --repeat 1`  
  (no ultimo baseline, o import de `sounddevice` travou; usei stub via wrapper python)
- VAD: `PYTHONPATH=. .venv/bin/python scripts/bench_interface.py vad --audio /tmp/jarvis_bench_30s.wav --repeat 5`  
  (idem: stub de `sounddevice` apenas para o benchmark)
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
- Import de `sounddevice` travou no ambiente; stub usado apenas para benchmark (nao afeta VAD/STT nesses cenarios).
- `psutil` estava ausente no baseline 2026-01-10; foi instalado nesta etapa para proximas rodadas com metricas completas.
- Baseline 2026-01-11 usou audio espeak-ng 22.05k com `--resample` (nao e 1:1 com 16k nativo).
- Baseline 2026-01-11 de Speaker pode estar invalido se nao houver voiceprint cadastrado.

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
- 2026-01-08: StreamingVAD agora aceita device configurado.
- 2026-01-08: adapters agora validam audio PCM int16 e sample_rate.
- 2026-01-08: STT ganhou wake word por audio opcional (Porcupine) antes da transcricao.
- 2026-01-10: AEC simples (com referencia de playback) passou a existir; sem benchmark novo ainda.
- 2026-01-11: STT passou a transcrever audio curto quando o VAD detecta fala (reduz espera em comandos curtos); sem benchmark novo.
- 2026-01-11: STT agora corta audio acima do limite configurado para evitar overflow; sem benchmark novo.
- 2026-01-11: STT passou a aceitar audio externo via `transcribe_audio_bytes`; sem benchmark novo.
