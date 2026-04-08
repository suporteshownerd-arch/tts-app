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
