# 🎙 TTS App

Aplicativo desktop **Text-to-Speech para Linux** usando as vozes neurais do Microsoft Edge TTS.
Interface gráfica moderna com tema claro/escuro, histórico, fila de exportação e tray icon.
Não requer conta nem API key — apenas conexão com a internet.

---

## Funcionalidades

| #    | Recurso                                                          |
| ---- | ---------------------------------------------------------------- |
| ▶    | Reprodução direta com botão **Falar** / **■ Parar**              |
| ⏸    | **Pausar / Retomar** durante a reprodução                        |
| 🔁   | **Repetir** o último áudio gerado                                |
| 💾   | Exportar como **MP3**                                            |
| 📂   | Abrir arquivo `.txt` (botão ou `Ctrl+O`)                         |
| 📋   | Colar do clipboard                                               |
| 🗂   | **Drag & drop** de arquivos `.txt` na área de texto              |
| 🕘   | **Histórico** dos últimos 20 textos                              |
| 📤   | **Fila de exportação** em lote                                   |
| 🌐   | **Filtro de vozes** com abas por idioma (PT EN ES FR DE JA ZH)   |
| 🔍   | Detecção automática de idioma ao digitar                         |
| ☀️🌙 | **Tema claro/escuro** com preferência persistente                |
| 🇧🇷🇺🇸 | Interface em **Português / English**                             |
| 🔔   | Notificação desktop ao concluir                                  |
| 🖥   | **Tray icon** — minimiza para a bandeja do sistema               |
| ♾    | Textos longos divididos em chunks e concatenados automaticamente |
| 🔄   | Retry automático (até 4x) para erro 529 do serviço               |
| 🖥   | Escala **HiDPI** automática                                      |

---

## Instalação rápida

### Dependências do sistema

```bash
sudo apt install python3-tk ffmpeg python3-pip
```

### Via Makefile (recomendado)

```bash
git clone https://github.com/suporteshownerd-arch/tts-app
cd tts-app
make install   # cria .venv e instala todas as dependências Python
make run       # inicia o app
```

### Instalação no sistema (launcher GNOME)

```bash
make install-system   # instala em /opt/tts-app + ícone no launcher
tts-app               # executar de qualquer lugar
```

Para desinstalar:

```bash
make uninstall-system
```

---

## Execução manual

```bash
# Ativar virtualenv
source .venv/bin/activate

# Rodar
python main.py
```

---

## Dependências Python

| Pacote        | Função                             |
| ------------- | ---------------------------------- |
| `edge-tts`    | Engine TTS — gera o áudio          |
| `pystray`     | Tray icon no sistema               |
| `Pillow`      | Imagem do tray icon                |
| `langdetect`  | Detecção automática de idioma      |
| `tkinterdnd2` | Drag & drop de arquivos (opcional) |

Instaladas automaticamente via `make install` ou:

```bash
pip install -r requirements.txt
```

---

## Atalhos de teclado

| Atalho            | Ação               |
| ----------------- | ------------------ |
| `Ctrl+Enter`      | Falar              |
| `Ctrl+S`          | Salvar MP3         |
| `Ctrl+O`          | Abrir arquivo .txt |
| `Esc`             | Parar reprodução   |
| `Ctrl+Z / Ctrl+Y` | Desfazer / Refazer |

---

## Testes

```bash
make test        # roda pytest no .venv
```

ou diretamente:

```bash
pytest -q
```

O CI roda os testes automaticamente em cada push via **GitHub Actions**.

---

## Verificar dependências

```bash
python3 scripts/check_deps.py
```

---

## Estrutura do projeto

```
tts-app/
├── main.py                # Interface gráfica (Tkinter)
├── tts_utils.py           # Lógica TTS: API, CLI, split, retry, cache
├── requirements.txt       # Dependências Python
├── Makefile               # install, run, test, install-system
├── install.sh             # Instalação em /opt/tts-app
├── uninstall.sh           # Desinstalação
├── tts-app.desktop        # Entrada no launcher GNOME
├── assets/tts-app.svg     # Ícone do app
├── scripts/
│   ├── check_deps.py      # Verificação de dependências
│   ├── package_deb.sh     # Empacotamento .deb (experimental)
│   └── package_appimage.sh
├── tests/
│   ├── test_tts_utils.py
│   └── test_integration.py
└── .github/workflows/ci.yml
```

---

## Requisitos

- Linux (Ubuntu 22.04+ / Pop!\_OS / Debian e derivados)
- Python 3.10+
- Conexão com a internet (vozes neurais online)
