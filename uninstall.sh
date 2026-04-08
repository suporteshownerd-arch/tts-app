#!/usr/bin/env bash
set -e

echo "==> Removendo TTS App..."
sudo rm -rf /opt/tts-app
sudo rm -f /usr/local/bin/tts-app
sudo rm -f /usr/share/applications/tts-app.desktop
sudo update-desktop-database /usr/share/applications 2>/dev/null || true
echo "✅ TTS App removido."
