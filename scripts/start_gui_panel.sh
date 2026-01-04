#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_PATH="$ROOT_DIR/.venv"

cd "$ROOT_DIR"

if [ ! -d "$VENV_PATH" ]; then
  python3 -m venv "$VENV_PATH"
  "$VENV_PATH/bin/pip" install -r requirements.txt
else
  "$VENV_PATH/bin/pip" --version >/dev/null 2>&1
fi

# Activate the env in this shell
# shellcheck source=/dev/null
. "$VENV_PATH/bin/activate"

# Defaults para testes rápidos: sem aprovação e sem efeitos colaterais
export JARVIS_REQUIRE_APPROVAL="${JARVIS_REQUIRE_APPROVAL:-false}"
export JARVIS_DRY_RUN="${JARVIS_DRY_RUN:-false}"

PYTHONPATH="$ROOT_DIR" python3 -m jarvis.app --gui-panel
