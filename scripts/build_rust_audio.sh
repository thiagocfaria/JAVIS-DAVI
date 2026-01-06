#!/usr/bin/env bash
set -euo pipefail

missing=0

for cmd in rustc cargo; do
  if ! command -v "$cmd" >/dev/null 2>&1; then
    echo "Faltando: $cmd"
    missing=1
  fi
done

if [ "$missing" -ne 0 ]; then
  echo "Instale as dependencias do sistema e tente novamente."
  exit 1
fi

if [ ! -d ".venv" ]; then
  python3 -m venv .venv
fi

.venv/bin/pip install -U pip >/dev/null
.venv/bin/pip install -U maturin >/dev/null

( cd rust/jarvis_audio && ../../.venv/bin/maturin develop --release --locked )

echo "jarvis_audio instalado com sucesso."
echo "Teste rapido: PYTHONPATH=. .venv/bin/python - <<'PY'\nimport jarvis_audio\nprint('import ok', jarvis_audio)\nPY"
