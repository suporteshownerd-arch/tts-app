"""Testes de integração para fluxo completo do TTS App."""
from unittest.mock import patch, AsyncMock, MagicMock
from tts_utils import generate_audio, generate_audio_long, split_text


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
