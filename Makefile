PYTHON=python3
VENV=.venv

.PHONY: help venv install check run test clean install-system uninstall-system

help:
	@echo "Targets: venv install check run test clean install-system uninstall-system"

venv:
	$(PYTHON) -m venv $(VENV)

install: venv
	$(VENV)/bin/python -m pip install -U pip
	$(VENV)/bin/python -m pip install -r requirements.txt
	$(VENV)/bin/python -m pip install -U pytest

install-mic:
	@echo "Instalando dependência de sistema para gravação por microfone..."
	sudo apt-get install -y libportaudio2

check:
	PYTHONPATH='.' $(PYTHON) scripts/check_deps.py

run:
	$(PYTHON) main.py

test: install
	PYTHONPATH='.' $(VENV)/bin/pytest -q

clean:
	-rm -rf $(VENV)

install-system:
	bash install.sh

uninstall-system:
	bash uninstall.sh
