import pytest
from tts_utils import build_tts_cmd, build_play_cmd, check_executables


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
