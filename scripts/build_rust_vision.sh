#!/usr/bin/env bash
set -euo pipefail

missing=0

for cmd in rustc cargo tesseract; do
  if ! command -v "$cmd" >/dev/null 2>&1; then
    echo "Faltando: $cmd"
    missing=1
  fi
done

if [ "$missing" -ne 0 ]; then
  echo "Instale dependencias do sistema e tente novamente."
  exit 1
fi

if ! command -v gnome-screenshot >/dev/null 2>&1 && ! command -v scrot >/dev/null 2>&1 && ! command -v grim >/dev/null 2>&1; then
  echo "Aviso: nenhum capturador de tela encontrado (gnome-screenshot/scrot/grim)."
fi

if [ ! -d ".venv" ]; then
  python3 -m venv .venv
fi

.venv/bin/pip install -U pip >/dev/null
.venv/bin/pip install -U maturin >/dev/null

FEATURES=""
if [ -n "${JARVIS_RUST_FEATURES:-}" ]; then
  FEATURES="--features ${JARVIS_RUST_FEATURES}"
elif command -v pkg-config >/dev/null 2>&1 && pkg-config --exists tesseract; then
  FEATURES="--features leptess"
  echo "Lib tesseract detectada via pkg-config. Habilitando backend leptess."
fi

( cd rust/jarvis_vision && ../../.venv/bin/maturin develop --release --locked $FEATURES )

echo "Rust vision instalado com sucesso."
