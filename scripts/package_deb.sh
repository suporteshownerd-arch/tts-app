#!/usr/bin/env bash
set -euo pipefail
echo "This is a placeholder packaging script for .deb. Customize as needed."

PKG_NAME="tts-app"
BUILD_DIR="build/deb"
mkdir -p "$BUILD_DIR"
echo "Packaging $PKG_NAME into $BUILD_DIR (placeholder)"

# Example: create a simple tar.gz of the repo as a placeholder for packaging
tar -czf "$BUILD_DIR/${PKG_NAME}.tar.gz" -C "$(git rev-parse --show-toplevel)" . --exclude .venv || true
echo "Created $BUILD_DIR/${PKG_NAME}.tar.gz"
