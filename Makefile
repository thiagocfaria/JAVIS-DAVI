PYTHON ?= python3
VENV ?= .venv
PIP := $(VENV)/bin/pip

.PHONY: setup test preflight run smoke build-rust test-rust

setup:
	@[ -d $(VENV) ] || $(PYTHON) -m venv $(VENV)
	@$(PIP) install -r requirements.txt

# Compila a extensão Rust (jarvis_audio) e instala no ambiente Python ativo.
# Requer: cargo + maturin  →  pip install maturin
build-rust:
	cd rust/jarvis_audio && maturin develop --release

# Verifica compilação Rust sem precisar de Python ativo.
test-rust:
	cd rust/jarvis_audio && cargo check

test:
	$(PYTHON) -m pytest -q

preflight:
	JARVIS_STT_MODE=none $(PYTHON) -m jarvis.app --preflight --preflight-strict

run:
	@echo "Iniciando loop (Ctrl+C para sair)"
	$(PYTHON) -m jarvis.app --loop

smoke:
	$(PYTHON) scripts/run_smoke.py
