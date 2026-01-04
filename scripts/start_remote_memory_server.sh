#!/usr/bin/env bash
set -euo pipefail

# Helper to start the lightweight remote memory server.
# Usage: ./scripts/start_remote_memory_server.sh [--host 0.0.0.0] [--port 8000]

if [ -d ".venv" ]; then
  # shellcheck disable=SC1091
  source .venv/bin/activate
fi

exec python -m jarvis.memoria.remote_service "$@"
