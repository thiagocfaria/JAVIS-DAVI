# Melhorias Futuras - Interface de Voz do Jarvis

**Criado em:** 2026-01-20
**Status:** Pesquisa concluida, implementacao pendente

---

## RESUMO DO ESTADO ATUAL

### O que funciona:
- **257 testes passando** (incluindo Wayland/Pop!_OS)
- **STT**: faster-whisper com modelo tiny (~630ms latencia)
- **TTS**: Piper com voz pt_BR-faber-medium (~53ms primeiro audio)
- **VAD**: webrtcvad funcionando
- **Latencia p50**: ~507ms (excelente)
- **Latencia p95**: ~2091ms (acima da meta de 1600ms)

### Problemas identificados:
1. p95 alto devido a variabilidade ocasional (cold start, GC, outliers)
2. Modelo tiny pode alucinar com prompt inicial muito forte
3. Falta validacao em maquinas mais fracas

---

## MELHORIAS PRIORITARIAS

### 1. Reduzir p95 com Moonshine ONNX

**Por que:** Moonshine e 5-15x mais rapido que Whisper com modelos menores.

**Como implementar:**
```bash
# Instalar
pip install useful-moonshine-onnx@git+https://github.com/moonshine-ai/moonshine.git#subdirectory=moonshine-onnx

# Uso basico
import moonshine_onnx
text = moonshine_onnx.transcribe(audio_path, 'moonshine/tiny')
```

**Arquivos a modificar:**
- `jarvis/interface/entrada/stt.py` - adicionar backend Moonshine
- `jarvis/interface/infra/voice_profile.py` - adicionar config JARVIS_STT_BACKEND

**Estimativa de ganho:** p95 pode cair de 2091ms para ~800ms

**Link:** https://github.com/moonshine-ai/moonshine

---

### 2. Implementar Barge-in com Metricas

**Por que:** Permitir usuario interromper resposta do Jarvis.

**Como implementar:**
- VAD continua rodando durante TTS
- Se detectar fala, parar TTS imediatamente
- Medir latencia de interrupcao (~150ms ideal)

**Arquivos a modificar:**
- `jarvis/interface/saida/tts.py` - ja tem `_barge_in_enabled`
- `jarvis/interface/entrada/vad.py` - verificar integracao

**Variaveis:**
```bash
JARVIS_TTS_BARGE_IN=1
JARVIS_TTS_BARGE_IN_STOP_FILE=~/.jarvis/STOP
```

---

### 3. Testar NVIDIA Parakeet (se GPU disponivel)

**Por que:** RTFx >2000, streaming nativo.

**Requisitos:**
- GPU NVIDIA com CUDA
- NeMo toolkit

**Link:** https://docs.nvidia.com/nemo-framework/user-guide/latest/nemotoolkit/asr/intro.html

---

### 4. Validar em Maquina Fraca

**Por que:** Garantir que funciona em hardware limitado.

**Teste sugerido:**
- Raspberry Pi 4 (4GB RAM)
- Laptop antigo (4GB RAM, sem GPU)

**Metricas a coletar:**
- Latencia p50/p95
- Uso de CPU/RAM
- Taxa de sucesso de transcricao

---

### 5. Comparar tiny vs tiny.en vs small

**Por que:** Equilibrar qualidade x latencia.

**Teste:**
```bash
# tiny (atual)
JARVIS_STT_MODEL=tiny python scripts/bench_interface.py stt ...

# tiny.en (ingles apenas, mais rapido)
JARVIS_STT_MODEL=tiny.en python scripts/bench_interface.py stt ...

# small (mais preciso, mais lento)
JARVIS_STT_MODEL=small python scripts/bench_interface.py stt ...
```

---

## TECNOLOGIAS ALTERNATIVAS COMPLETAS

### STT (Speech-to-Text)

| Tecnologia | Tipo | Latencia | Qualidade | Link |
|------------|------|----------|-----------|------|
| **Moonshine** | Local/ONNX | 5-15x mais rapido | Similar Whisper | https://github.com/moonshine-ai/moonshine |
| **NVIDIA Parakeet** | Local/GPU | RTFx >2000 | Excelente | NVIDIA NeMo |
| **WhisperX** | Local | 4x mais rapido | Word-level | https://github.com/m-bain/whisperX |
| **Vosk** | Local | Muito baixa | Boa | https://alphacephei.com/vosk/ |
| **Deepgram Nova-3** | API | Muito baixa | Excelente | https://deepgram.com |
| **AssemblyAI Universal-2** | API | Baixa | Melhor WER | https://assemblyai.com |

### TTS (Text-to-Speech)

| Tecnologia | Tipo | Latencia | Qualidade | Link |
|------------|------|----------|-----------|------|
| **Piper** (atual) | Local/CPU | <100ms | Muito boa | https://github.com/rhasspy/piper |
| **MeloTTS** | Local/CPU | <100ms | Boa | https://github.com/myshell-ai/MeloTTS |
| **Coqui XTTS-v2** | Local/GPU | ~150ms | Excelente | https://github.com/coqui-ai/TTS |
| **Bark** | Local/GPU | >500ms | Expressiva | https://github.com/suno-ai/bark |
| **Edge TTS** | API | Baixa | Muito boa | Microsoft Azure |

### VAD (Voice Activity Detection)

| Tecnologia | Tipo | Latencia | Precisao |
|------------|------|----------|----------|
| **webrtcvad** (atual) | Local | Muito baixa | Boa |
| **Silero VAD** | Local/PyTorch | Baixa | Excelente |
| **pyannote/segmentation** | Local | Media | Excelente |

---

## CRONOGRAMA SUGERIDO

| Semana | Tarefa | Prioridade |
|--------|--------|------------|
| 1 | Testar Moonshine ONNX | Alta |
| 1 | Validar em maquina fraca | Alta |
| 2 | Implementar barge-in com metricas | Media |
| 2 | Comparar tiny vs small | Media |
| 3 | Documentar troubleshooting | Baixa |
| 3 | 3 rodadas de validacao | Media |

---

## COMO TESTAR NOVAS TECNOLOGIAS

### Criar branch de teste:
```bash
git checkout -b feature/moonshine-stt
```

### Implementar backend alternativo:
```python
# Em stt.py, adicionar:
if self._stt_backend == 'moonshine':
    return self._transcribe_moonshine(audio_bytes)
```

### Rodar benchmark comparativo:
```bash
# Whisper (atual)
JARVIS_STT_BACKEND=whisper python scripts/bench_interface.py stt ...

# Moonshine (novo)
JARVIS_STT_BACKEND=moonshine python scripts/bench_interface.py stt ...
```

### Comparar resultados:
- Latencia p50/p95
- WER (Word Error Rate)
- Uso de CPU/RAM

---

## REFERENCIAS

- [Open ASR Leaderboard](https://huggingface.co/spaces/hf-audio/open_asr_leaderboard)
- [Moonshine GitHub](https://github.com/moonshine-ai/moonshine)
- [Piper TTS](https://github.com/rhasspy/piper)
- [faster-whisper](https://github.com/guillaumekln/faster-whisper)
- [Benchmark Article](https://northflank.com/blog/best-open-source-speech-to-text-stt-model-in-2025-benchmarks)
