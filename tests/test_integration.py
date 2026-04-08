"""Testes de integração para fluxo completo do TTS App."""
import os
from unittest.mock import patch, AsyncMock, MagicMock
from tts_utils import generate_audio, generate_audio_long, split_text, transcribe_audio


def test_split_text_short():
    assert split_text("Olá mundo.") == ["Olá mundo."]


def test_split_text_long():
    sentence = "Esta é uma frase de teste. " * 200
    chunks = split_text(sentence, max_chars=500)
    assert len(chunks) > 1
    for chunk in chunks:
        assert len(chunk) <= 500


def test_split_text_exact_boundary():
    text = "Primeira frase. Segunda frase. Terceira frase."
    chunks = split_text(text, max_chars=20)
    assert all(len(c) <= 20 for c in chunks)


def test_generate_audio_creates_file():
    mock_communicate = MagicMock()
    mock_communicate.return_value.save = AsyncMock()
    fake_edge_tts = MagicMock()
    fake_edge_tts.Communicate = mock_communicate

    with patch("tts_utils.api_available", return_value=True), \
         patch.dict("sys.modules", {"edge_tts": fake_edge_tts}):
        rc, path = generate_audio("pt-BR-FranciscaNeural", 0, "Olá", None)

    assert rc == 0
    assert path.endswith(".mp3")


def test_generate_audio_long_single_chunk():
    """Texto curto deve usar generate_audio diretamente."""
    mock_communicate = MagicMock()
    mock_communicate.return_value.save = AsyncMock()
    fake_edge_tts = MagicMock()
    fake_edge_tts.Communicate = mock_communicate

    with patch("tts_utils.api_available", return_value=True), \
         patch.dict("sys.modules", {"edge_tts": fake_edge_tts}):
        rc, path = generate_audio_long("pt-BR-FranciscaNeural", 0, "Texto curto.", None)

    assert rc == 0
    assert path.endswith(".mp3")


def test_generate_audio_retries_on_529():
    call_count = 0

    async def flaky_save(_path):
        nonlocal call_count
        call_count += 1
        if call_count < 2:
            raise Exception("429 529 overloaded")

    mock_communicate = MagicMock()
    mock_communicate.return_value.save = flaky_save
    fake_edge_tts = MagicMock()
    fake_edge_tts.Communicate = mock_communicate

    with patch("tts_utils.api_available", return_value=True), \
         patch.dict("sys.modules", {"edge_tts": fake_edge_tts}), \
         patch("tts_utils.time.sleep"):
        rc, path = generate_audio("pt-BR-FranciscaNeural", 0, "Texto", None)

    assert rc == 0
    assert call_count == 2


# ── Transcrição ───────────────────────────────────────────────────────────────

def test_transcribe_audio_calls_whisper(tmp_path):
    """transcribe_audio deve chamar whisper.load_model e transcribe."""
    fake_wav = tmp_path / "test.wav"
    fake_wav.write_bytes(b"\x00" * 100)

    mock_model = MagicMock()
    mock_model.transcribe.return_value = {"text": "  Olá mundo  "}
    mock_whisper = MagicMock()
    mock_whisper.load_model.return_value = mock_model

    with patch.dict("sys.modules", {"whisper": mock_whisper}):
        result = transcribe_audio(str(fake_wav), model_name="base")

    assert result == "Olá mundo"
    mock_whisper.load_model.assert_called_once_with("base")
    mock_model.transcribe.assert_called_once_with(str(fake_wav))


def test_transcribe_audio_with_language(tmp_path):
    """transcribe_audio deve passar language quando especificado."""
    fake_wav = tmp_path / "test.wav"
    fake_wav.write_bytes(b"\x00" * 100)

    mock_model = MagicMock()
    mock_model.transcribe.return_value = {"text": "Hello world"}
    mock_whisper = MagicMock()
    mock_whisper.load_model.return_value = mock_model

    with patch.dict("sys.modules", {"whisper": mock_whisper}):
        result = transcribe_audio(str(fake_wav), model_name="tiny", language="en")

    assert result == "Hello world"
    mock_model.transcribe.assert_called_once_with(str(fake_wav), language="en")


def test_transcribe_audio_strips_whitespace(tmp_path):
    """transcribe_audio deve remover espaços extras do resultado."""
    fake_wav = tmp_path / "test.wav"
    fake_wav.write_bytes(b"\x00" * 100)

    mock_model = MagicMock()
    mock_model.transcribe.return_value = {"text": "\n\n  texto com espaços  \n"}
    mock_whisper = MagicMock()
    mock_whisper.load_model.return_value = mock_model

    with patch.dict("sys.modules", {"whisper": mock_whisper}):
        result = transcribe_audio(str(fake_wav))

    assert result == "texto com espaços"


def test_whisper_available_true():
    mock_whisper = MagicMock()
    with patch.dict("sys.modules", {"whisper": mock_whisper}):
        from tts_utils import whisper_available
        assert whisper_available() is True


def test_whisper_available_false():
    import sys
    original = sys.modules.get("whisper")
    sys.modules["whisper"] = None  # type: ignore[assignment]
    try:
        from tts_utils import whisper_available
        assert whisper_available() is False
    finally:
        if original is not None:
            sys.modules["whisper"] = original
        else:
            del sys.modules["whisper"]


def test_stop_mic_recording_empty_returns_empty_string():
    """stop_mic_recording sem dados gravados deve retornar string vazia."""
    import tts_utils
    tts_utils._rec_data = []
    tts_utils._rec_stream = None
    result = tts_utils.stop_mic_recording()
    assert result == ""
