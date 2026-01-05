PYTHON ?= python3
VENV ?= .venv
PIP := $(VENV)/bin/pip

.PHONY: setup test preflight run smoke

setup:
	@[ -d $(VENV) ] || $(PYTHON) -m venv $(VENV)
	@$(PIP) install -r requirements.txt

test:
	$(PYTHON) -m pytest -q

preflight:
	JARVIS_STT_MODE=none $(PYTHON) -m jarvis.app --preflight --preflight-strict

run:
	@echo "Iniciando loop (Ctrl+C para sair)"
	$(PYTHON) -m jarvis.app --loop

smoke:
	$(PYTHON) scripts/run_smoke.py
