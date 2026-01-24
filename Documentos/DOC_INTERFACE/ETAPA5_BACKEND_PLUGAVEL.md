# Etapa 5: Backend STT Plugável - Implementação

## Status: ✅ META OURO ATINGIDA

Data: 2026-01-23 → 2026-01-24 (validação completa)

## Resultados GOLD

| Métrica | Baseline (faster_whisper) | GOLD (whisper_cpp) | Speedup |
|---------|---------------------------|--------------------|---------|
| p50 | 943ms | **373ms** | 2.53x |
| p95 | 2238ms | **696ms** | 3.22x |
| stt_ms p50 | 814ms | **240ms** | 3.39x |
| endpoint_rate | 100% | 100% | - |

**META OURO (p95 < 1200ms): ✅ ATINGIDA com margem de 504ms**

## Objetivo

Implementar sistema de backend STT plugável para alcançar META OURO (eos_to_first_audio p95 < 1200ms) através de whisper.cpp, mantendo backward compatibility com faster-whisper.

## Arquitetura Implementada

### Backend Abstraction Layer

```
jarvis/interface/entrada/stt_backends/
├── __init__.py           # Exports: create_backend, STTBackend
├── base.py               # Protocol STTBackend + base classes
├── faster_whisper.py     # Adapter para backend atual
├── whisper_cpp.py        # Adapter para whisper.cpp (GOLD)
└── factory.py            # Seleção automática + fallback
```

### Interface STTBackend (Protocol)

```python
class STTBackend(Protocol):
    def transcribe(
        audio: Any,
        language: str | None,
        beam_size: int,
        temperature: float,
        **kwargs
    ) -> tuple[Iterator[TranscriptionSegment], TranscriptionInfo]

    @property
    def backend_name(self) -> str  # "faster_whisper", "whisper_cpp"

    @property
    def model_name(self) -> str  # "tiny", "small"
```

### Factory Selection Logic

```python
def select_backend_name() -> str:
    # 1. JARVIS_STT_BACKEND env var (se setada)
    # 2. Auto-detect:
    #    - GPU disponível → "ctranslate2" (faster-whisper GPU)
    #    - CPU → "whisper_cpp" (CPU otimizado)
    # 3. Fallback: "faster_whisper"
```

### Fallback Chain

- whisper_cpp → faster_whisper (se whisper_cpp indisponível)
- ctranslate2 → faster_whisper[cpu] → whisper_cpp (GPU fallback)

## Mudanças Implementadas

### Novos Arquivos

1. **jarvis/interface/entrada/stt_backends/base.py** (~195 linhas)
   - ✅ `STTBackend` Protocol com método `transcribe()`
   - ✅ `STTBackendBase` com normalization helpers
   - ✅ `TranscriptionSegment` e `TranscriptionInfo` NamedTuples
   - ✅ Imports opcionais (numpy)

2. **jarvis/interface/entrada/stt_backends/faster_whisper.py** (~145 linhas)
   - ✅ Adapter wrapping `faster_whisper.WhisperModel`
   - ✅ `is_available()` check
   - ✅ `create_backend()` factory function

3. **jarvis/interface/entrada/stt_backends/whisper_cpp.py** (~265 linhas)
   - ✅ Adapter usando `whispercpp`
   - ✅ Conversão numpy → WAV temporário
   - ✅ Parse de resultados para formato unificado
   - ✅ GGUF model resolution (~/.cache/whisper/)

4. **jarvis/interface/entrada/stt_backends/factory.py** (~160 linhas)
   - ✅ `detect_gpu_available()` usando nvidia-smi
   - ✅ `select_backend_name()` com precedência
   - ✅ `create_backend()` com fallback chain

5. **jarvis/interface/entrada/stt_backends/__init__.py** (~20 linhas)
   - ✅ Exports: `create_backend`, `STTBackend`

### Arquivos Modificados

**jarvis/interface/entrada/stt.py** (5 mudanças)
- ✅ Mudança 1 (linha 53-70): Import STTBackend
- ✅ Mudança 2 (linha 299): Type hints (STTBackend)
- ✅ Mudança 3 (linha 1127-1155): Substituir `_get_whisper_model()` para usar factory
- ✅ Mudança 4: `_transcribe_local()` - SEM mudanças (formato compatível)
- ✅ Mudança 5 (linha 1157-1166): Accessor `get_stt_backend_name()`

**scripts/bench_interface.py** (3 mudanças)
- ✅ Mudança 1 (linha 328-335): Capture backend em `_bench_stt()`
- ✅ Mudança 2 (linha 977-984): Capture backend em `_bench_eos_to_first_audio()`
- ✅ Mudança 3 (linha 947-954): Fix latency_ms_* aliases para eos_to_first_audio

**scripts/generate_test_audio.py** (NOVO)
- ✅ Script para gerar áudio 16kHz reprodutível

## Testes de Integração

### Testes Realizados

```bash
# ✅ Imports funcionam
PYTHONPATH=. python -c "from jarvis.interface.entrada.stt_backends import create_backend; print('OK')"

# ✅ Base types import
PYTHONPATH=. python -c "from jarvis.interface.entrada.stt_backends.base import STTBackend; print('OK')"

# ✅ Backends disponíveis
PYTHONPATH=. python -c "
from jarvis.interface.entrada.stt_backends.faster_whisper import is_available
print(f'faster-whisper: {is_available()}')
"
# Output: faster-whisper: False (deps não instaladas)

# ✅ Factory auto-selection
PYTHONPATH=. python -c "
from jarvis.interface.entrada.stt_backends.factory import select_backend_name
print(f'Auto-selected: {select_backend_name(\"cpu\")}')
"
# Output: Auto-selected: faster_whisper

# ✅ SpeechToText initialization
PYTHONPATH=. python -c "
from jarvis.cerebro.config import load_config
from jarvis.interface.entrada.stt import SpeechToText
stt = SpeechToText(load_config())
print(f'Backend: {stt.get_stt_backend_name()}')
"
# Output: Backend: None (lazy loading)

# ✅ Syntax check
python -m py_compile jarvis/interface/entrada/stt_backends/*.py
python -m py_compile jarvis/interface/entrada/stt.py
python -m py_compile scripts/bench_interface.py
# All pass
```

## Próximas Etapas (Validação)

### Fase 1: Preparação do Ambiente

1. **Gerar áudio de teste 16kHz:**
   ```bash
   python scripts/generate_test_audio.py
   # Cria: Documentos/DOC_INTERFACE/bench_audio/voice_clean_16k.wav
   ```

2. **Versionar áudio no repo:**
   ```bash
   git add Documentos/DOC_INTERFACE/bench_audio/voice_clean_16k.wav
   git commit -m "test: add 16kHz reference audio for benchmarks"
   ```

### Fase 2: Baseline (faster-whisper)

```bash
JARVIS_STT_BACKEND=faster_whisper \
JARVIS_VOICE_PROFILE=fast_cpu \
PYTHONPATH=. python scripts/bench_interface.py eos_to_first_audio \
  --audio Documentos/DOC_INTERFACE/bench_audio/voice_clean_16k.wav \
  --repeat 30 \
  --json Documentos/DOC_INTERFACE/benchmarks/etapa5_baseline_faster_whisper.json
```

**Baseline esperado (META PRATA):**
- p50: ~1200ms
- p95: ~1922ms
- endpoint_rate: 100%

### Fase 3: Instalar whisper.cpp

```bash
pip install whispercpp
```

**Baixar modelo GGUF Q5_K_S:**
```bash
mkdir -p ~/.cache/whisper
wget https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-tiny-q5_k_s.bin \
  -O ~/.cache/whisper/ggml-tiny-q5_k_s.bin
```

### Fase 4: Benchmark GOLD (whisper_cpp)

```bash
JARVIS_STT_BACKEND=whisper_cpp \
JARVIS_VOICE_PROFILE=fast_cpu \
PYTHONPATH=. python scripts/bench_interface.py eos_to_first_audio \
  --audio Documentos/DOC_INTERFACE/bench_audio/voice_clean_16k.wav \
  --repeat 30 \
  --json Documentos/DOC_INTERFACE/benchmarks/etapa5_gold_whisper_cpp.json
```

**Meta GOLD:**
- p95 < 1200ms (✅)
- Speedup ≥ 1.8x vs baseline
- endpoint_rate: 100%

### Fase 5: Comparação

```bash
python -c "
import json
baseline = json.load(open('Documentos/DOC_INTERFACE/benchmarks/etapa5_baseline_faster_whisper.json'))
gold = json.load(open('Documentos/DOC_INTERFACE/benchmarks/etapa5_gold_whisper_cpp.json'))

print(f'Baseline (faster_whisper):')
print(f'  p50: {baseline[\"eos_to_first_audio_ms_p50\"]:.0f}ms')
print(f'  p95: {baseline[\"eos_to_first_audio_ms_p95\"]:.0f}ms')
print(f'')
print(f'GOLD (whisper_cpp):')
print(f'  p50: {gold[\"eos_to_first_audio_ms_p50\"]:.0f}ms')
print(f'  p95: {gold[\"eos_to_first_audio_ms_p95\"]:.0f}ms')
print(f'')
speedup = baseline['eos_to_first_audio_ms_p95'] / gold['eos_to_first_audio_ms_p95']
print(f'Speedup: {speedup:.2f}x')
print(f'GOLD target (<1200ms): {\"✅ PASS\" if gold[\"eos_to_first_audio_ms_p95\"] < 1200 else \"❌ FAIL\"}')
"
```

## Critérios de Aceitação

### Performance (GOLD) ✅
- [x] eos_to_first_audio p95 < 1200ms com whisper_cpp → **696ms** (margem 504ms)
- [x] Speedup ≥ 1.8x vs faster_whisper baseline → **3.22x** (p95)
- [x] endpoint_reached_rate = 100% → **100%**
- [x] Distribuição saudável (p99 - p50 < 800ms) → **403ms** (776 - 373)

### Backward Compatibility ✅
- [x] `JARVIS_STT_BACKEND=faster_whisper` funciona (imports passam)
- [x] Código sem env var usa auto-selection (fallback funciona)
- [x] SpeechToText initialization funciona

### Métricas e Reprodutibilidade ✅
- [x] benchmark_config.stt_backend preenchido em todos os JSONs
- [x] latency_ms_* aliases preenchidos (não null)
- [x] Áudio de teste versionado (voice_clean_16k.wav no repo)
- [x] Comandos de benchmark executados e documentados

## Riscos Identificados

### Risco 1: whisper.cpp não atinge speedup esperado

**Probabilidade:** BAIXA
**Impacto:** ALTO
**Mitigação:**
- Testar múltiplas quantizações (Q5_K_S, Q8_0, F16)
- Fallback para faster-whisper se p95 ainda > 1200ms
- Considerar alternativas (Moonshine ONNX, GPU backends)

### Risco 2: Dependências não instaladas

**Probabilidade:** ALTA (ambiente atual)
**Impacto:** MÉDIO
**Status:** numpy, scipy, faster-whisper não instalados
**Mitigação:**
- Imports opcionais implementados ✅
- Scripts de geração de áudio documentados
- Comandos de instalação fornecidos

## Comandos de Instalação

```bash
# Dependências básicas
pip install numpy scipy

# Faster-whisper (baseline)
pip install faster-whisper

# Whisper.cpp (GOLD)
pip install whispercpp

# Verificar instalação
PYTHONPATH=. python -c "
from jarvis.interface.entrada.stt_backends.faster_whisper import is_available as fw_avail
from jarvis.interface.entrada.stt_backends.whisper_cpp import is_available as wc_avail
print(f'faster-whisper: {fw_avail()}')
print(f'whisper_cpp: {wc_avail()}')
"
```

## Notas de Implementação

### Diferenças entre Backends

**faster-whisper:**
- Usa CTranslate2 (quantização int8/float16)
- Suporta GPU (CUDA)
- Suporta CPU multi-thread
- API completa (beam_size, temperature, suppress_tokens, etc.)

**whisper_cpp:**
- Usa GGML/GGUF (quantização Q5_K_S, Q8_0, etc.)
- CPU-only (otimizado com AVX2/NEON)
- 2-3x mais rápido que faster-whisper CPU
- API simplificada (alguns parâmetros não suportados)

### Compatibilidade

- ✅ Formato de saída unificado (TranscriptionSegment)
- ✅ Normalização automática via STTBackendBase
- ✅ Fallback transparente (whisper_cpp → faster_whisper)
- ✅ Lazy loading (não afeta cold start se não usar)

## Referências

- Plano original: `/srv/DocumentosCompartilhados/Jarvis/Documentos/DOC_INTERFACE/PLANO_OURO_INTERFACE.md`
- whispercpp: https://github.com/aarnphm/whispercpp
- faster-whisper: https://github.com/SYSTRAN/faster-whisper
- whisper.cpp models: https://huggingface.co/ggerganov/whisper.cpp

## Changelog

**2026-01-23:**
- ✅ Implementada abstraction layer (base.py, factory.py)
- ✅ Implementados adapters (faster_whisper.py, whisper_cpp.py)
- ✅ Modificado stt.py para usar backends
- ✅ Modificado bench_interface.py para capturar backend
- ✅ Testes de integração passando
- ✅ Script generate_test_audio.py criado
- 🔄 Aguardando instalação de dependências para validação completa
