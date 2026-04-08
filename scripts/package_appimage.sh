#!/usr/bin/env bash
set -euo pipefail
echo "Placeholder script to create AppImage. Customize for your app."
mkdir -p build/appimage
echo "AppImage build placeholder - creating repo tarball"
tar -czf build/appimage/tts-app.tar.gz -C "$(git rev-parse --show-toplevel)" . --exclude .venv || true
echo "Created build/appimage/tts-app.tar.gz"

# If appimagetool is available, create a simple AppImage placeholder (requires AppDir structure)
if command -v appimagetool >/dev/null 2>&1; then
  echo "appimagetool found: creating AppImage (placeholder)"
  mkdir -p build/appdir/usr/bin
  cp -r . build/appdir/usr/bin/ || true
  appimagetool build/appdir || true
else
  echo "appimagetool not found: skipping AppImage build"
fi
