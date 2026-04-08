# TTS App
Aplicativo de Text to Speech para Linux

## Como rodar
```bash
python3 main.py
```

## Dependências
```bash
pipx install edge-tts
sudo apt install python3-tk ffmpeg
```

## Checagem automática
Há um script simples para checar dependências:

```bash
python3 scripts/check_deps.py
```

## Testes
Este repositório inclui testes pytest para utilitários. Execute:

```bash
python3 -m pip install -U pytest
pytest -q
```

Com Makefile:

```bash
make install   # cria .venv e instala dependências e pytest
make test      # roda os testes no .venv
```

Observação: o alvo install cria um virtualenv em .venv. Se preferir não usar .venv,
pode criar um ambiente separado e ajustar os comandos.
