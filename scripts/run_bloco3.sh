#!/bin/bash
# BLOCO 3 - Executar WER + Latência para todos os modelos (tiny/small/base)

set -e

cd /srv/DocumentosCompartilhados/Jarvis

MODELS=("tiny" "small" "base")
BENCH_DIR="Documentos/DOC_INTERFACE/benchmarks"
AUDIO_DIR="Documentos/DOC_INTERFACE/test_audio"
BENCH_AUDIO="Documentos/DOC_INTERFACE/bench_audio/voice_clean_16k.wav"

echo "=========================================="
echo "BLOCO 3 - WER + Latência (tiny/small/base)"
echo "=========================================="
echo ""

for MODEL in "${MODELS[@]}"; do
    echo "--- Modelo: $MODEL ---"

    # WER benchmark
    echo "  Executando WER benchmark..."
    JARVIS_STT_BACKEND=faster_whisper JARVIS_STT_MODEL="$MODEL" \
    PYTHONPATH=. python scripts/voice_wer_benchmark.py \
      --audio-dir "$AUDIO_DIR" \
      --json-out "$BENCH_DIR/wer_${MODEL}.json" \
      --md-out "$BENCH_DIR/wer_${MODEL}.md"

    # Latência benchmark (10 repetições)
    echo "  Executando latência benchmark (10 reps)..."
    JARVIS_STT_BACKEND=faster_whisper JARVIS_STT_MODEL="$MODEL" \
    PYTHONPATH=. python scripts/bench_interface.py eos_to_first_audio \
      --audio "$BENCH_AUDIO" \
      --text "ola jarvis" \
      --repeat 10 \
      --json "$BENCH_DIR/latency_${MODEL}.json"

    echo "  ✓ $MODEL concluído"
    echo ""
done

echo "=========================================="
echo "Comparando modelos..."
echo "=========================================="
PYTHONPATH=. python scripts/compare_models.py

echo ""
echo "✅ BLOCO 3 concluído!"
