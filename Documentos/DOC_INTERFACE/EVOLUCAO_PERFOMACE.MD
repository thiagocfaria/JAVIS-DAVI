# EVOLUCAO_PERFOMACE.md

Registro de evolucao de performance da interface de entrada/saida de voz.

## Objetivo (bem simples)
- Medir o pior caso e ver se ficou mais rapido ou mais lento.
- Guardar o baseline com comandos, ambiente e metricas (latencia/CPU/RSS).

## Metas de latencia (referencias de mercado)
Estas metas usam como referencia o texto de pesquisa (endpointing e voz em tempo real).
Elas nao sao comparaveis 1:1 com nossos benchmarks atuais (que medem tempo total de STT
em audios de 4s ou 30s). Sao metas de produto para orientar o futuro:

### Metas para STT (EoS -> texto final)
| Nivel | Meta (ms) | Referencia usada |
| --- | --- | --- |
| Media | 800 | P90 endpointing ~740 ms (Google, baseline) |
| Boa | 500 | faixa 270-570 ms (endpointing melhorado) |
| Otima | 300 | P50 endpointing ~300 ms (Alexa, transactional) |
| Excelente | 200 | abaixo do melhor reportado (meta agressiva) |

### Metas para fala (EoS -> primeiro audio do assistente)
| Nivel | Meta (s) | Referencia usada |
| --- | --- | --- |
| Media | 2.0 | medias de assistentes de mercado (Siri ~2.0s) |
| Boa | 1.6 | medias de assistentes de mercado (Alexa ~1.6s) |
| Otima | 1.2 | medias de assistentes de mercado (Google ~1.2s) |
| Excelente | 0.9 | abaixo do melhor reportado |

### Sugestoes para chegar nas metas
- Streaming em tudo: STT, LLM e TTS (parciais + fala iniciando antes do fim).
- Endpointing inteligente: menor silencio com protecao contra corte de fala.
- Prefetch com parciais: preparar resposta antes do final do turno.
- Transporte realtime (WebRTC) para reduzir jitter.
- Decoding acelerado (speculative / multi-token) no "cerebro".
- Medicao padrao EoS->texto e EoS->fala (instrumentar logs).

## Resumo rapido (em linguagem facil)
- O sistema tem 4 etapas: VAD (ouvir), STT (entender), Speaker (confirmar) e TTS (responder).
- Rodada 4 (2026-01-11, 22.05k + resample): STT melhorou para ~14,2s (comparacao mais justa com rodadas anteriores 22.05k).
- Rodada 3 (2026-01-11, 16k): STT ficou mais lento (~61,9s) porque o teste incluiu cold start (carregamento do modelo).
- Speaker voltou a medir custo real (2,3s a 3,7s) porque o encoder foi carregado; quando esta "rapido demais" o resultado nao e representativo.
- Comparacoes 1:1 exigem o mesmo tipo de audio e o mesmo modo de aquecimento (cold vs warm).
- RealtimeSTT foi integrado como backend opcional (JARVIS_STT_STREAMING=1); streaming foi medido com feed de audio curto, mas falta medir ao vivo (microfone real).
- Voz real (2026-01-12, 4s): STT ficou ~5,7s em silencio e ~8,6s com TV ligada; VAD ficou ~1ms em ambos.
- Voz real (2026-01-13, 4s): STT caiu para ~3,5s em silencio e ~4,0s com TV ligada; VAD ~0,7ms.
- Tentativa com parametros “fast” (2026-01-13): STT piorou para ~9,0s; manter default.
- Endpointing offline (2026-01-13, VAD com silencio 400ms): ~390ms em silencio e com TV.
- Comparacao endpointing (2026-01-13): 250ms -> 240ms (clean/noise), 400ms -> 390ms, 800ms -> 780ms clean e falha no noise (endpoint_reached=false).
- Ruido (2026-01-13): normalize_audio e VAD agressivo pioraram o STT em ruido (8s vs 4s); manter default.
- Rodada 5 (2026-01-13, espeak 30s): STT ~38,7s (pior que rodada 4); GPU probe retornou `gpu_available=false` porque `nvidia-smi` nao estava disponivel.

## Benchmark de voz real (curto, microfone)
Objetivo: medir STT/VAD em fala real curta (4s), comparando ambiente silencioso vs TV ligada.  
Metodo: `scripts/auto_voice_bench.py` + `scripts/bench_interface.py` (com resample 44.1k -> 16k).

### Rodada 1 (2026-01-12 22:17)
| Cenario | Latencia media (ms) | p50 (ms) | p95 (ms) | CPU avg (s) |
| --- | --- | --- | --- | --- |
| STT (silencio) | 5748 | 6078 | 6685 | 14.681 |
| STT (TV ligada) | 8615 | 8356 | 13325 | 16.676 |
| VAD (silencio) | 1.4 | 0.7 | 10.3 | 0.001 |
| VAD (TV ligada) | 0.9 | 0.9 | 1.4 | 0.001 |

### Rodada 2 (2026-01-13 01:27)
| Cenario | Latencia media (ms) | p50 (ms) | p95 (ms) | CPU avg (s) |
| --- | --- | --- | --- | --- |
| STT (silencio) | 3532 | 3914 | 4606 | 10.707 |
| STT (TV ligada) | 3989 | 4088 | 4625 | 11.755 |
| VAD (silencio) | 0.7 | 0.7 | 1.1 | 0.001 |
| VAD (TV ligada) | 0.6 | 0.6 | 0.7 | 0.001 |

### Rodada 3 (2026-01-13, parametros “fast”)
| Cenario | Latencia media (ms) | p50 (ms) | p95 (ms) | CPU avg (s) | Nota |
| --- | --- | --- | --- | --- | --- |
| STT (silencio) | 9676 | 7927 | 21672 | 18.771 | piorou |
| STT (TV ligada) | 8950 | 7961 | 16711 | 19.021 | piorou |

### Rodada 4 (2026-01-13, endpointing offline)
| Cenario | Endpointing medio (ms) | p50 (ms) | p95 (ms) | Config |
| --- | --- | --- | --- | --- |
| Endpointing (silencio) | 390 | 390 | 390 | `JARVIS_VAD_SILENCE_MS=400` |
| Endpointing (TV ligada) | 390 | 390 | 390 | `JARVIS_VAD_SILENCE_MS=400` |

### Rodada 4b (2026-01-13, endpointing compare)
| Silencio (ms) | Endpointing (silencio) | Endpointing (TV ligada) | Observacao |
| --- | --- | --- | --- |
| 250 | 240 | 240 | ok |
| 400 | 390 | 390 | ok (baseline) |
| 800 | 780 | 3* | noise nao atingiu endpoint (endpoint_reached=false) |

*Em noise com 800ms, o endpoint nao foi atingido; o valor baixo e efeito do fallback.*

### Rodada 5a (2026-01-13, ruido profile compare)
| Perfil | STT ruido (ms) | p50 (ms) | p95 (ms) | Nota |
| --- | --- | --- | --- | --- |
| baseline | 3989 | 4088 | 4625 | referencia |
| normalize_audio=1 | 8288 | 8318 | 8870 | piorou |
| vad_aggr=3 | 8118 | 8253 | 8997 | piorou |
| normalize + aggr=3 | 8578 | 8562 | 9126 | piorou |

### Rodada 6 (2026-01-15, re-run com WAVs gravados)
| Cenario | Latencia media (ms) | p50 (ms) | p95 (ms) | CPU avg (s) | Nota |
| --- | --- | --- | --- | --- | --- |
| STT (silencio) | 8463 | 8588 | 9345 | 17.84 | default (sem `JARVIS_STT_MODEL` -> `small`) |
| STT (TV ligada) | 9550 | 9735 | 10132 | 17.79 | default (sem `JARVIS_STT_MODEL` -> `small`) |
| STT (silencio) | 1529 | 1364 | 2254 | 5.45 | `JARVIS_STT_MODEL=tiny` |
| STT (TV ligada) | 1636 | 1604 | 2222 | 5.74 | `JARVIS_STT_MODEL=tiny` |
| VAD (silencio) | 1.37 | 0.75 | 9.56 | 0.001 | ok |
| VAD (TV ligada) | 0.69 | 0.66 | 1.03 | 0.001 | ok |

### Leitura simples
- Com ruido (TV), o STT ficou ~2,9s mais lento (≈ +50%).
- O VAD quase nao mudou (permaneceu ~1ms).
- Parametros “fast” (beam/best/temp/warmup) pioraram a latencia em voz real curta; nao aplicar como default.
- Endpointing ficou em ~390ms com `JARVIS_VAD_SILENCE_MS=400` (13 frames de 30ms). Para reduzir, baixar o silencio, com risco de cortar fala.
- Em comparacao direta, 250ms entregou ~240ms (clean/noise). 800ms falhou no noise (endpoint_reached=false), entao nao e seguro em ambiente ruidoso.
- Ruido alto: normalize_audio e VAD agressivo nao ajudaram no audio com TV; manter default e buscar AEC/NS dedicados.
- Esses numeros nao sao comparaveis com o baseline de 30s; servem apenas para ver impacto do ruido em fala curta real.
- Comparando 2026-01-12 -> 2026-01-13, o STT melhorou ~38% (silencio) e ~54% (TV ligada).

## Evolucao visual (ms, menor e melhor)
Legenda: barra maior = mais lento. Comparacao indicativa (audio diferente).

STT
2026-01-13 (r5) | ######################################## 38724
2026-01-11 (r4) | ######################          14203
2026-01-11 (r3) | ############################################################# 61913
2026-01-11 (r2) | ################################### 33115
2026-01-11 (r1) | ########################################### 44217
2026-01-10      | #################               13598
2026-01-07      | ############################### 23231

VAD
2026-01-13 (r5) | #####                           5,21
2026-01-11 (r4) | ########                        8,98
2026-01-11 (r3) | ##########                      10,88
2026-01-11 (r2) | #####                           4,89
2026-01-11 (r1) | ########                        8,29
2026-01-10      | #####                           4,55
2026-01-07      | ##########                      9,69

Speaker
2026-01-11 (r4) | #######################         2315
2026-01-11 (r3) | ############################    3764
2026-01-11 (r2) | #                               0,05*
2026-01-11 (r1) | #                               0,05*
2026-01-10      | #######                         637
2026-01-07      | ############################    3102

TTS
2026-01-11 (r4) | #                               0,57
2026-01-11 (r3) | #####                           2,90
2026-01-11 (r2) | #                               0,46
2026-01-11 (r1) | ###                             1,46
2026-01-10      | #####                           2,41
2026-01-07      | #########                       4,67

*Speaker 2026-01-11: tempo muito baixo pode indicar falta de voiceprint (nao representa a verificacao real).*

## Sinais de ganho (indicativos)
- STT (comparacao 1:1 22.05k): 33115 ms -> 14203 ms (melhorou ~18,9s).
- VAD: 4,89 ms -> 8,98 ms (piorou ~4,1 ms).
- Speaker: 0,05 ms -> 2315 ms (agora representativo; encoder foi carregado).
- TTS: 0,46 ms -> 0,57 ms (quase igual).
- Nota: a rodada 3 usa audio 16k (sem resample) e cold start; comparar com cautela.

## Baseline atual (pior caso)
 Data: 2026-01-11 (rodada 4)
- Metodo: `scripts/bench_interface.py` com audio espeak-ng (22.05 kHz) reamostrado para 16 kHz (`--resample`), 30s.
- Audio: `/tmp/jarvis_bench_30s_22050.wav`
- Repeticoes: STT=1, VAD=5, Speaker=3, TTS=3
- Observacao 1: STT usa modelo padrao (sem override) e inclui cold start do processo.
- Observacao 2: TTS mede apenas o custo de iniciar processo (speak nao bloqueia).
- Observacao 3: Speaker e representativo porque o encoder foi carregado (pode variar se nao houver voiceprint).
- Historico bruto (JSON unico): `bench_history.json`

### Resultados (pior caso 30s)
| Cenario | Latencia media (ms) | p50 (ms) | p95 (ms) | CPU avg (s) | RSS (KB) |
| --- | --- | --- | --- | --- | --- |
| STT | 14202.52 | 14202.52 | 14202.52 | 23.9219 | 1352228 |
| VAD | 8.98 | 7.94 | 13.03 | 0.0066 | 618784 |
| Speaker (JARVIS_SPK_VERIFY=1) | 2314.88 | 344.10 | 11002.12 | 1.5858 | 764276 |
| TTS (local) | 0.57 | 0.54 | 0.94 | 0.0003 | 99056 |

## Rodada 5 (espeak 30s, probe de GPU)
 Data: 2026-01-13
- Metodo: `scripts/bench_interface.py` com audio espeak-ng (22.05 kHz) reamostrado para 16 kHz (`--resample`), 30s.
- Audio: `/tmp/jarvis_bench_30s.wav`
- Repeticoes: STT=1, VAD=5
- Observacao 1: nao comparavel 1:1 com rodada 4 (audio sintetico diferente).
- Observacao 2: `gpu_available=false` (sem `nvidia-smi` no ambiente).

### Resultados (rodada 5)
| Cenario | Latencia media (ms) | p50 (ms) | p95 (ms) | CPU avg (s) | RSS (KB) |
| --- | --- | --- | --- | --- | --- |
| STT | 38723.81 | 38723.81 | 38723.81 | 78.1962 | 1413100 |
| VAD | 5.21 | 5.26 | 6.00 | 0.0052 | 615276 |

## Baseline anterior (pior caso, rodada 3)
- Data: 2026-01-11 (rodada 3)
- Metodo: `scripts/bench_interface.py` com audio 16 kHz (warmup do RealtimeSTT repetido), 30s.
- Audio: `/tmp/jarvis_bench_30s.wav`
- Repeticoes: STT=1, VAD=5, Speaker=3, TTS=3
- Observacao 1: STT usa modelo tiny e inclui cold start (carregamento do modelo).
- Observacao 2: TTS mede apenas o custo de iniciar processo (speak nao bloqueia).
- Observacao 3: Speaker e representativo porque o encoder foi carregado (pode variar se nao houver voiceprint).
- Historico bruto (JSON unico): `bench_history.json`

### Resultados (pior caso 30s)
| Cenario | Latencia media (ms) | p50 (ms) | p95 (ms) | CPU avg (s) | RSS (KB) |
| --- | --- | --- | --- | --- | --- |
| STT | 61912.72 | 61912.72 | 61912.72 | 101.0413 | 845000 |
| VAD | 10.88 | 11.84 | 13.41 | 0.0060 | 607408 |
| Speaker (JARVIS_SPK_VERIFY=1) | 3764.58 | 832.60 | 16897.28 | 2.0882 | 759684 |
| TTS (local) | 2.90 | 0.77 | 12.58 | 0.0004 | 98468 |

## Baseline anterior (pior caso, rodada 2)
- Data: 2026-01-11 (rodada 2)
- Metodo: `scripts/bench_interface.py` com audio espeak-ng (22.05 kHz) reamostrado para 16 kHz (`--resample`), 30s.
- Audio: `/tmp/jarvis_bench_30s.wav`
- Repeticoes: STT=1, VAD=5, Speaker=3, TTS=3
- Observacao 1: TTS mede apenas o custo de iniciar processo (speak nao bloqueia).
- Observacao 2: Speaker pode nao ser representativo sem voiceprint (ver nota nos resultados).
- Historico bruto (JSON unico): `bench_history.json`

### Resultados (pior caso 30s)
| Cenario | Latencia media (ms) | p50 (ms) | p95 (ms) | CPU avg (s) | RSS (KB) |
| --- | --- | --- | --- | --- | --- |
| STT | 33115.35 | 33115.35 | 33115.35 | 83.6201 | 1725808 |
| VAD | 4.89 | 4.89 | 4.97 | 0.0049 | 617924 |
| Speaker (JARVIS_SPK_VERIFY=1) | 0.05 | 0.03 | 0.13 | 0.0000 | 579536 |
| TTS (local) | 0.46 | 0.37 | 0.90 | 0.0003 | 98856 |

## Baseline anterior (pior caso, rodada 1)
- Data: 2026-01-11 (rodada 1)
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
- Streaming opcional: RealtimeSTT + pyaudio (quando habilitado)
- RealtimeSTT streaming (deps extras): openwakeword, halo, websocket-client, torchaudio (Silero).

## Medicao fria vs quente (STT, audio curto)
- Audio: `warmup_audio.wav` (1.62s)
- Cold: ~2.924s
- Warm: ~2.003s
- Ganho estimado: ~0.92s (cache do modelo evita custo de carregamento).

## Streaming simulado (RealtimeSTT, feed de audio)
- Audio: `warmup_audio.wav` (1.62s)
- Tempo total (feed + transcricao): 4.577s
- Latencia aproximada (total - duracao): ~2.96s
- Observacao: simulacao usa `feed_audio` e `recorder.start/stop`, nao substitui teste ao vivo com microfone.

## Como medimos (comandos)
- STT: `PYTHONPATH=. .venv/bin/python scripts/bench_interface.py stt --audio /tmp/jarvis_bench_30s.wav --repeat 1 --json /tmp/bench_stt.json --resample`
- VAD: `PYTHONPATH=. .venv/bin/python scripts/bench_interface.py vad --audio /tmp/jarvis_bench_30s.wav --repeat 5 --json /tmp/bench_vad.json --resample`
- Speaker: `PYTHONPATH=. JARVIS_CONFIG_DIR=/tmp/jarvis_bench_config JARVIS_SPK_VERIFY=1 .venv/bin/python scripts/bench_interface.py speaker --audio /tmp/jarvis_bench_30s.wav --repeat 3 --json /tmp/bench_speaker.json --resample`
- TTS: `PYTHONPATH=. .venv/bin/python scripts/bench_interface.py tts --text "ola jarvis, teste de desempenho de voz" --repeat 3 --json /tmp/bench_tts.json`
- Profiling (opcional): `py-spy record -o profile.svg -- python scripts/bench_interface.py stt --audio /tmp/jarvis_bench_30s.wav`
- Medicao cold/warm (STT curto):
```
JARVIS_STT_MODEL=tiny JARVIS_STT_LANGUAGE=pt PYTHONPATH=. .venv/bin/python - <<'PY'
import time
import wave
from pathlib import Path
from jarvis.cerebro.config import load_config
from jarvis.entrada.stt import SpeechToText

wav_path = Path('jarvis/REPOSITORIOS_CLONAR/realtimestt/RealtimeSTT/warmup_audio.wav')
with wave.open(str(wav_path), 'rb') as f:
    frames = f.readframes(f.getnframes())

stt = SpeechToText(load_config())

start = time.perf_counter()
_ = stt._transcribe_audio_bytes(frames, require_wake_word=False, skip_speech_check=False)
mid = time.perf_counter()
_ = stt._transcribe_audio_bytes(frames, require_wake_word=False, skip_speech_check=False)
end = time.perf_counter()

print({'audio': str(wav_path), 'cold_s': round(mid - start, 3), 'warm_s': round(end - mid, 3)})
PY
```
- Streaming simulado (RealtimeSTT):
```
PYTHONPATH=. .venv/bin/python - <<'PY'
import json
import sys
import time
import wave
from pathlib import Path

sys.path.insert(0, 'jarvis/REPOSITORIOS_CLONAR/realtimestt')
from RealtimeSTT import AudioToTextRecorder

wav_path = Path('jarvis/REPOSITORIOS_CLONAR/realtimestt/RealtimeSTT/warmup_audio.wav')
with wave.open(str(wav_path), 'rb') as f:
    frames = f.readframes(f.getnframes())
    sr = f.getframerate()
    channels = f.getnchannels()
    sampwidth = f.getsampwidth()

if channels != 1 or sampwidth != 2 or sr != 16000:
    raise SystemExit('audio deve ser mono 16k int16')

duration_s = len(frames) / (sr * sampwidth)

recorder = AudioToTextRecorder(
    use_microphone=False,
    spinner=False,
    device='cpu',
    model='tiny',
    language='pt',
    enable_realtime_transcription=True,
    use_main_model_for_realtime=False,
    realtime_model_type='tiny',
    silero_deactivity_detection=False,
    faster_whisper_vad_filter=True,
    normalize_audio=False,
    min_length_of_recording=0.1,
    post_speech_silence_duration=0.2,
    min_gap_between_recordings=0.0,
)

chunk_ms = 100
chunk_size = int(sr * (chunk_ms / 1000.0) * sampwidth)

recorder.start()
start_ts = time.perf_counter()

for i in range(0, len(frames), chunk_size):
    recorder.feed_audio(frames[i:i+chunk_size])
    time.sleep(chunk_ms / 1000.0)

recorder.stop()
text = recorder.text()
end_ts = time.perf_counter()

recorder.shutdown()

elapsed = end_ts - start_ts
approx_latency = max(0.0, elapsed - duration_s)

result = {
    'audio': str(wav_path),
    'duration_s': round(duration_s, 3),
    'elapsed_s': round(elapsed, 3),
    'approx_latency_s': round(approx_latency, 3),
    'text_preview': (text or '')[:120],
}
print(json.dumps(result, ensure_ascii=True, indent=2))
PY
```

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
- Baseline 2026-01-11 (rodada 2) usou audio espeak-ng 22.05k com `--resample` (nao e 1:1 com 16k nativo).
- Baseline 2026-01-11 (rodadas 1/2) de Speaker pode estar invalido se nao houver voiceprint cadastrado.
- RealtimeSTT exige deps extras (openwakeword/halo/websocket-client/torchaudio); sem elas, a inicializacao falha.

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
- 2026-01-11: RealtimeSTT integrado como backend opcional; streaming ainda sem benchmark dedicado.
