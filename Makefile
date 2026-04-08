PYTHON=python3
VENV=.venv

.PHONY: help venv install check run test clean

help:
	@echo "Targets: venv install check run test clean"

venv:
	$(PYTHON) -m venv $(VENV)

install: venv
	$(VENV)/bin/python -m pip install -U pip
	$(VENV)/bin/python -m pip install -r requirements.txt
	$(VENV)/bin/python -m pip install -U pytest

check:
	PYTHONPATH='.' $(PYTHON) scripts/check_deps.py

run:
	$(PYTHON) main.py

test: install
	PYTHONPATH='.' $(VENV)/bin/pytest -q

clean:
	-rm -rf $(VENV)
