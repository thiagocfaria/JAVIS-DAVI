# Voice Profiles — Etapa 4

## Overview

JARVIS Interface provides **3 pre-defined voice profiles** optimized for different hardware and environments. Each profile closes a set of VAD/STT parameters to provide predictable, reproducible performance.

## Profiles

### 1. FAST_CPU
**Optimized for:** Weak CPU (< 2 cores, < 4GB RAM), clean audio (indoor, no background noise)

**Parameters:**
| Parameter | Value | Notes |
|-----------|-------|-------|
| Silence Duration | 400ms | Faster speech detection cutoff |
| Min Speech | 300ms | Shorter minimum command duration |
| VAD Pre-roll | 100ms | Less buffering before speech |
| VAD Post-roll | 100ms | Less buffering after speech |
| VAD Aggressiveness | 3 | Most aggressive (fewer false positives) |
| STT Model | `tiny` | Lightweight, fastest transcription |

**Performance Target:** p95 ~950-1100ms

**Use Case:**
```bash
export JARVIS_VOICE_PROFILE=fast_cpu
# Run on Pop!_OS with < 2 cores, < 4GB RAM
```

---

### 2. BALANCED_CPU (Default)
**Optimized for:** Medium CPU (2-4 cores, 4-8GB RAM), typical office/home environment

**Parameters:**
| Parameter | Value | Notes |
|-----------|-------|-------|
| Silence Duration | 600ms | Balanced speech detection |
| Min Speech | 400ms | Standard minimum command duration |
| VAD Pre-roll | 150ms | Standard buffering before speech |
| VAD Post-roll | 150ms | Standard buffering after speech |
| VAD Aggressiveness | 2 | Medium aggressiveness |
| STT Model | `small` | Balanced quality/speed |

**Performance Target:** p95 ~1050-1150ms (OURO line)

**Use Case:**
```bash
# No need to set anything—this is the default
# Or explicitly:
export JARVIS_VOICE_PROFILE=balanced_cpu
```

---

### 3. NOISY_ROOM
**Optimized for:** Noisy environments (AC, traffic, background music, crowds)

**Parameters:**
| Parameter | Value | Notes |
|-----------|-------|-------|
| Silence Duration | 800ms | Longer speech detection window (fewer false breaks) |
| Min Speech | 500ms | Longer minimum command to avoid noise triggers |
| VAD Pre-roll | 200ms | More buffering before speech (catch quiet starts) |
| VAD Post-roll | 200ms | More buffering after speech (don't cut off tail) |
| VAD Aggressiveness | 1 | Least aggressive (more sensitive to low-level speech) |
| STT Model | `small` | Better accuracy in noisy conditions |

**Performance Target:** p95 ~1100-1200ms (still < PRATA 1500ms)

**Use Case:**
```bash
export JARVIS_VOICE_PROFILE=noisy_room
# Run in open office, café, or outdoor environment
```

---

## Selection

### Via Environment Variable
```bash
# Option 1: FAST_CPU
export JARVIS_VOICE_PROFILE=fast_cpu

# Option 2: BALANCED_CPU (default if not set)
export JARVIS_VOICE_PROFILE=balanced_cpu

# Option 3: NOISY_ROOM
export JARVIS_VOICE_PROFILE=noisy_room
```

### Via Benchmark Script
```bash
# Benchmark with fast_cpu profile
PYTHONPATH=. JARVIS_VOICE_PROFILE=fast_cpu \
  python scripts/bench_interface.py eos_to_first_audio \
  --audio Documentos/DOC_INTERFACE/bench_audio/voice_clean.wav \
  --repeat 20 --resample --json fast_cpu_bench.json

# Or use --profile flag
PYTHONPATH=. python scripts/bench_interface.py eos_to_first_audio \
  --audio Documentos/DOC_INTERFACE/bench_audio/voice_clean.wav \
  --repeat 20 --resample --profile fast_cpu \
  --json fast_cpu_bench.json
```

### Precedence
When selecting a profile, JARVIS respects this priority:

1. **Explicit environment variable** → `JARVIS_VOICE_PROFILE=fast_cpu` (highest priority)
2. **Benchmark --profile flag** → `--profile balanced_cpu`
3. **Default** → `balanced_cpu` (if nothing is set)

Individual parameters can ALWAYS override a profile:
```bash
# Use balanced_cpu profile BUT override STT model
export JARVIS_VOICE_PROFILE=balanced_cpu
export JARVIS_STT_MODEL=base  # This wins over profile's "small"
```

---

## Python API

### Load a Profile
```python
from jarvis.interface.infra.profiles import load_profile, apply_profile

# Load by name
profile = load_profile("fast_cpu")
print(profile)
# {
#   'name': 'fast_cpu',
#   'silence_ms': 400,
#   'min_speech_ms': 300,
#   ...
# }

# Load from env var (or default)
profile = load_profile()  # Uses JARVIS_VOICE_PROFILE or "balanced_cpu"
```

### Apply a Profile
```python
from jarvis.interface.infra.profiles import load_profile, apply_profile

profile = load_profile("noisy_room")
apply_profile(profile)

# This sets env vars (but doesn't override already-set vars):
# JARVIS_VAD_SILENCE_MS=800
# JARVIS_MIN_AUDIO_SECONDS=0.5
# JARVIS_VAD_PRE_ROLL_MS=200
# JARVIS_VAD_POST_ROLL_MS=200
# JARVIS_VAD_AGGRESSIVENESS=1
# JARVIS_STT_MODEL=small
```

### List Available Profiles
```python
from jarvis.interface.infra.profiles import PROFILES

for name, profile in PROFILES.items():
    print(f"{name}: VAD agg={profile['vad_aggressiveness']}, STT={profile['stt_model']}")
```

---

## Benchmarking

### Test All Profiles

```bash
#!/bin/bash
# Run eos_to_first_audio benchmark with each profile

AUDIO="Documentos/DOC_INTERFACE/bench_audio/voice_clean.wav"
REPEAT=20

# Baseline (unset profile, should default to balanced_cpu)
unset JARVIS_VOICE_PROFILE
PYTHONPATH=. python scripts/bench_interface.py eos_to_first_audio \
  --audio "$AUDIO" --repeat $REPEAT --resample \
  --json baseline_bench.json

# FAST_CPU
PYTHONPATH=. JARVIS_VOICE_PROFILE=fast_cpu \
  python scripts/bench_interface.py eos_to_first_audio \
  --audio "$AUDIO" --repeat $REPEAT --resample \
  --json fast_cpu_bench.json

# BALANCED_CPU
PYTHONPATH=. JARVIS_VOICE_PROFILE=balanced_cpu \
  python scripts/bench_interface.py eos_to_first_audio \
  --audio "$AUDIO" --repeat $REPEAT --resample \
  --json balanced_cpu_bench.json

# NOISY_ROOM
PYTHONPATH=. JARVIS_VOICE_PROFILE=noisy_room \
  python scripts/bench_interface.py eos_to_first_audio \
  --audio "$AUDIO" --repeat $REPEAT --resample \
  --json noisy_room_bench.json
```

### Compare Results

```bash
# Compare all 3 profiles
jq -s '{
  baseline: {p50: .[0].latency_ms_p50, p95: .[0].latency_ms_p95, p99: .[0].latency_ms_p99},
  fast_cpu: {p50: .[1].latency_ms_p50, p95: .[1].latency_ms_p95, p99: .[1].latency_ms_p99},
  balanced: {p50: .[2].latency_ms_p50, p95: .[2].latency_ms_p95, p99: .[2].latency_ms_p99},
  noisy: {p50: .[3].latency_ms_p50, p95: .[3].latency_ms_p95, p99: .[3].latency_ms_p99}
}' baseline_bench.json fast_cpu_bench.json balanced_cpu_bench.json noisy_room_bench.json
```

Expected Output:
```json
{
  "baseline": {
    "p50": 1050,
    "p95": 1077,
    "p99": 1120
  },
  "fast_cpu": {
    "p50": 920,
    "p95": 1020,
    "p99": 1080
  },
  "balanced": {
    "p50": 1050,
    "p95": 1077,
    "p99": 1120
  },
  "noisy": {
    "p50": 1100,
    "p95": 1180,
    "p99": 1240
  }
}
```

---

## Backward Compatibility

Existing code continues to work. If `JARVIS_VOICE_PROFILE` is NOT set:
- VAD uses default aggressiveness 2
- STT uses default model selection (tiny on fast_profile, small otherwise)
- All other VAD/STT parameters use their respective env var defaults

Profiles only activate when:
1. `JARVIS_VOICE_PROFILE` env var is set, OR
2. `apply_profile()` is called explicitly, OR
3. `--profile` flag is used in benchmark script

---

## Architecture

### Module Structure
```
jarvis/interface/infra/profiles.py
├── VoiceProfile (TypedDict)
├── PROFILES (dict of 3 profiles)
├── load_profile(name: str | None) -> VoiceProfile
└── apply_profile(profile: VoiceProfile) -> None

jarvis/interface/entrada/vad.py
└── resolve_vad_aggressiveness() — checks profile if env var not set

jarvis/interface/entrada/stt.py
└── _init_ — checks profile if JARVIS_STT_MODEL not set

jarvis/interface/infra/voice_profile.py
└── auto_configure_voice_profile() — applies profile if JARVIS_VOICE_PROFILE set

scripts/bench_interface.py
└── --profile flag — applies profile before benchmark
```

### Flow
```
User sets JARVIS_VOICE_PROFILE=fast_cpu
    ↓
auto_configure_voice_profile() sees it
    ↓
load_profile("fast_cpu")
    ↓
apply_profile({silence_ms: 400, ...})
    ↓
Sets env vars (if not already set)
    ↓
VAD/STT read env vars at startup
    ↓
Profile parameters take effect
```

---

## Troubleshooting

### Profile Not Applying
```bash
# Check if JARVIS_VOICE_PROFILE is set
echo $JARVIS_VOICE_PROFILE

# Verify env vars were set
echo $JARVIS_VAD_AGGRESSIVENESS
echo $JARVIS_STT_MODEL
```

### Custom Parameter Wins Profile
```bash
# This works as intended:
export JARVIS_VOICE_PROFILE=balanced_cpu
export JARVIS_VAD_AGGRESSIVENESS=0  # Overrides profile's 2

# If you want profile to take effect, unset the override:
unset JARVIS_VAD_AGGRESSIVENESS
```

### Unknown Profile Error
```bash
# Available profiles: fast_cpu, balanced_cpu, noisy_room
# This fails:
export JARVIS_VOICE_PROFILE=ultra_fast  # ❌ Unknown

# This works:
export JARVIS_VOICE_PROFILE=fast_cpu  # ✅ Valid
```

---

## See Also

- [PLANO_OURO_INTERFACE.md](./PLANO_OURO_INTERFACE.md) — Full Etapa 4 specification
- [benchmark_interface.md](./benchmark_interface.md) — Benchmarking guide
- [jarvis/interface/infra/profiles.py](../../jarvis/interface/infra/profiles.py) — Source code
