#!/usr/bin/env bash
set -euo pipefail

if ! command -v python3 >/dev/null 2>&1; then
  echo "python3 nao encontrado"
  exit 1
fi

output="$(python3 -m jarvis.app --text "status" --dry-run 2>&1 || true)"

if echo "$output" | grep -qi "Sistema Jarvis"; then
  echo "OK"
  exit 0
fi

echo "Falha no healthcheck"
echo "$output"
exit 1
