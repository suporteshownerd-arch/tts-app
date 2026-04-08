#!/usr/bin/env bash
set -e

APP_DIR="/opt/tts-app"
DESKTOP_DIR="/usr/share/applications"
BIN_DIR="/usr/local/bin"

echo "==> Instalando TTS App..."

# Dependências do sistema
echo "==> Verificando dependências do sistema..."
if ! command -v python3 &>/dev/null; then
    echo "ERRO: python3 não encontrado."
    exit 1
fi
if ! python3 -c "import tkinter" &>/dev/null; then
    echo "==> Instalando python3-tk..."
    sudo apt-get install -y python3-tk
fi
if ! command -v ffplay &>/dev/null; then
    echo "==> Instalando ffmpeg..."
    sudo apt-get install -y ffmpeg
fi
if ! command -v pipx &>/dev/null; then
    echo "==> Instalando pipx..."
    sudo apt-get install -y pipx
    pipx ensurepath
fi
if ! command -v edge-tts &>/dev/null; then
    echo "==> Instalando edge-tts..."
    pipx install edge-tts
fi

# Copiar arquivos para /opt/tts-app
echo "==> Copiando arquivos para $APP_DIR..."
sudo mkdir -p "$APP_DIR"
sudo cp main.py tts_utils.py requirements.txt "$APP_DIR/"
sudo cp -r assets "$APP_DIR/"
sudo cp -r scripts "$APP_DIR/"

# Criar virtualenv e instalar dependências Python
echo "==> Criando ambiente virtual..."
sudo python3 -m venv "$APP_DIR/.venv"
sudo "$APP_DIR/.venv/bin/pip" install -q -U pip
sudo "$APP_DIR/.venv/bin/pip" install -q -r "$APP_DIR/requirements.txt"

# Script de execução
echo "==> Criando script de execução..."
sudo tee "$APP_DIR/run.sh" > /dev/null <<'EOF'
#!/usr/bin/env bash
PYTHONPATH=/opt/tts-app /opt/tts-app/.venv/bin/python /opt/tts-app/main.py "$@"
EOF
sudo chmod +x "$APP_DIR/run.sh"

# Symlink no PATH
echo "==> Criando comando 'tts-app'..."
sudo ln -sf "$APP_DIR/run.sh" "$BIN_DIR/tts-app"

# Entrada no GNOME launcher
echo "==> Instalando atalho no launcher..."
sudo cp tts-app.desktop "$DESKTOP_DIR/tts-app.desktop"
sudo update-desktop-database "$DESKTOP_DIR" 2>/dev/null || true

echo ""
echo "✅ TTS App instalado com sucesso!"
echo "   • Launcher: procure 'TTS App' no GNOME Activities"
echo "   • Terminal:  tts-app"
