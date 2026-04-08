import json
import time
import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from tts_utils import build_tts_cmd, build_play_cmd, check_executables, generate_audio


def test_build_tts_cmd_basic():
    cmd = build_tts_cmd("pt-BR-FranciscaNeural", 0, "Olá", "/tmp/out.mp3")
    assert "edge-tts" in cmd[0]
    assert "--voice" in cmd
    assert "pt-BR-FranciscaNeural" in cmd
    assert "--write-media" in cmd
    assert "/tmp/out.mp3" in cmd


def test_build_tts_cmd_rate_sign():
    cmd = build_tts_cmd("v", 25, "t", "o")
    assert "+25%" in cmd
    cmd2 = build_tts_cmd("v", -10, "t", "o")
    assert "-10%" in cmd2


def test_build_play_cmd():
    cmd = build_play_cmd("/tmp/out.mp3")
    assert cmd[0] == "ffplay"
    assert "/tmp/out.mp3" in cmd


def test_check_executables_keys():
    ex = check_executables()
    assert set(ex.keys()) == {"edge-tts", "ffplay"}


def test_generate_audio_uses_api_with_rate():
    mock_communicate = MagicMock()
    mock_communicate.return_value.save = AsyncMock()

    fake_edge_tts = MagicMock()
    fake_edge_tts.Communicate = mock_communicate

    with patch("tts_utils.api_available", return_value=True), \
         patch.dict("sys.modules", {"edge_tts": fake_edge_tts}):
        rc, path = generate_audio("pt-BR-FranciscaNeural", 25, "Olá", "/tmp/out.mp3")

    assert rc == 0
    mock_communicate.assert_called_once_with("Olá", "pt-BR-FranciscaNeural", rate="+25%")


def test_generate_audio_api_rate_zero():
    mock_communicate = MagicMock()
    mock_communicate.return_value.save = AsyncMock()

    fake_edge_tts = MagicMock()
    fake_edge_tts.Communicate = mock_communicate

    with patch("tts_utils.api_available", return_value=True), \
         patch.dict("sys.modules", {"edge_tts": fake_edge_tts}):
        rc, path = generate_audio("pt-BR-FranciscaNeural", 0, "Olá", "/tmp/out.mp3")

    assert rc == 0
    mock_communicate.assert_called_once_with("Olá", "pt-BR-FranciscaNeural", rate="+0%")


# ── Voice cache tests ─────────────────────────────────────────────────────────

def test_load_voices_cache_returns_none_when_missing(tmp_path, monkeypatch):
    monkeypatch.setattr("tts_utils._VOICES_CACHE_FILE", str(tmp_path / "voices.json"))
    import tts_utils
    assert tts_utils.load_voices_cache() is None


def test_save_and_load_voices_cache(tmp_path, monkeypatch):
    monkeypatch.setattr("tts_utils._VOICES_CACHE_FILE", str(tmp_path / "voices.json"))
    monkeypatch.setattr("tts_utils._CONFIG_DIR", str(tmp_path))
    import tts_utils
    voices = ["pt-BR-FranciscaNeural", "en-US-JennyNeural"]
    tts_utils.save_voices_cache(voices)
    result = tts_utils.load_voices_cache()
    assert result == voices


def test_load_voices_cache_with_locale_filter(tmp_path, monkeypatch):
    monkeypatch.setattr("tts_utils._VOICES_CACHE_FILE", str(tmp_path / "voices.json"))
    monkeypatch.setattr("tts_utils._CONFIG_DIR", str(tmp_path))
    import tts_utils
    voices = ["pt-BR-FranciscaNeural", "en-US-JennyNeural", "pt-PT-DuarteNeural"]
    tts_utils.save_voices_cache(voices)
    result = tts_utils.load_voices_cache("pt")
    assert len(result) == 2
    assert all(v.startswith("pt") for v in result)


def test_load_voices_cache_expired(tmp_path, monkeypatch):
    cache_file = str(tmp_path / "voices.json")
    monkeypatch.setattr("tts_utils._VOICES_CACHE_FILE", cache_file)
    data = {"saved_at": time.time() - 90000, "voices": ["pt-BR-FranciscaNeural"]}
    with open(cache_file, "w") as f:
        json.dump(data, f)
    import tts_utils
    assert tts_utils.load_voices_cache() is None
