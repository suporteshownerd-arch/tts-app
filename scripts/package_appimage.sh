#!/usr/bin/env bash
set -euo pipefail
echo "Placeholder script to create AppImage. Customize for your app."
mkdir -p build/appimage
echo "AppImage build placeholder - creating repo tarball"
tar -czf build/appimage/tts-app.tar.gz -C "$(git rev-parse --show-toplevel)" . --exclude .venv || true
echo "Created build/appimage/tts-app.tar.gz"
