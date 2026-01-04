#!/usr/bin/env bash
set -euo pipefail

DATA_DIR="${JARVIS_DATA_DIR:-$HOME/.jarvis}"
LOG_FILE="$DATA_DIR/events.jsonl"
MAX_MB="${JARVIS_LOG_MAX_MB:-50}"

if [ ! -f "$LOG_FILE" ]; then
  exit 0
fi

size_bytes="$(stat -c%s "$LOG_FILE")"
limit_bytes="$((MAX_MB * 1024 * 1024))"

if [ "$size_bytes" -lt "$limit_bytes" ]; then
  exit 0
fi

ts="$(date +%Y%m%d_%H%M%S)"
rotated="$LOG_FILE.$ts"

mv "$LOG_FILE" "$rotated"
gzip -f "$rotated"
