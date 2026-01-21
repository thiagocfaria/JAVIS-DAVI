#!/usr/bin/env bash
set -euo pipefail

# Reproduz todos os WAVs de teste no alto-falante com pequena pausa entre eles.
# Útil para o teste acústico (alto-falante -> microfone) enquanto o Jarvis está ouvindo.

AUDIO_DIR="${1:-Documentos/DOC_INTERFACE/test_audio}"
GAP_SECONDS="${GAP_SECONDS:-2}"

if [ ! -d "$AUDIO_DIR" ]; then
  echo "Pasta não encontrada: $AUDIO_DIR" >&2
  exit 1
fi

for f in "$AUDIO_DIR"/*.wav; do
  [ -e "$f" ] || continue
  echo ">> $(basename "$f")"
  aplay "$f"
  sleep "$GAP_SECONDS"
done
