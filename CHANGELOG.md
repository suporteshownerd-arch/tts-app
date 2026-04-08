# Changelog

All notable changes to this project will be documented in this file.

## [0.1.0] - 2026-04-08
### Added
- Initial desktop TTS application using Microsoft Edge TTS (CLI/API fallback).
- GUI with Tkinter: text input, voice selector, speed slider, play and save MP3.
- tts_utils: helpers for building commands, generate_audio (API prefer), play_audio, list_voices.
- Persistent recent-text history and UI to load past entries.
- Open .txt button and Ctrl+O to load files.
- Stop playback control (terminate player process).
- Dynamic light/dark theme toggle and saved preference.
- Packaging placeholders for .deb and AppImage (scripts/package_deb.sh, scripts/package_appimage.sh).
- scripts/check_deps.py to validate edge-tts and ffplay.
- Makefile with install/test/check/run targets.
- GitHub Actions CI: runs tests on Python 3.10-3.12.
- Unit tests for tts_utils (pytest).
- PRD and LICENSE (MIT).

### Fixed
- Safer UI updates from worker threads and proper temporary file handling.
