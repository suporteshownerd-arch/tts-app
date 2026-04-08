"""Utilitários mínimos para montar comandos TTS e checar dependências."""
from typing import List, Dict, Optional, Tuple
import re
import shutil
import subprocess
import asyncio
import logging
import tempfile
import time
import os
import json

logger = logging.getLogger(__name__)

DEFAULT_TMP_FILE: Optional[str] = None

_RETRY_DELAYS = [1, 3, 7]  # segundos entre tentativas para erro 529

# ── Cache de vozes ────────────────────────────────────────────────────────────
_CONFIG_DIR = os.path.expanduser("~/.config/tts-app")
_VOICES_CACHE_FILE = os.path.join(_CONFIG_DIR, "voices_cache.json")
_VOICES_CACHE_TTL = 86400  # 24h em segundos


def load_voices_cache(locale_filter: Optional[str] = None) -> Optional[List[str]]:
    """Carrega lista de vozes do cache local se válido (TTL 24h).

    Retorna lista de vozes ou None se cache inválido/inexistente.
    """
    try:
        with open(_VOICES_CACHE_FILE, encoding="utf-8") as f:
            data = json.load(f)
        saved_at = data.get("saved_at", 0)
        if time.time() - saved_at > _VOICES_CACHE_TTL:
            return None
        voices = data.get("voices", [])
        if locale_filter:
            voices = [v for v in voices if v.startswith(locale_filter)]
        return voices
    except Exception:
        return None


def save_voices_cache(voices: List[str]) -> None:
    """Salva lista de vozes no cache local com timestamp."""
    try:
        os.makedirs(_CONFIG_DIR, exist_ok=True)
        data = {"saved_at": time.time(), "voices": voices}
        with open(_VOICES_CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
    except Exception:
        logger.warning("Failed to save voices cache")


def api_available() -> bool:
    try:
        import edge_tts
        return hasattr(edge_tts, "Communicate")
    except Exception:
        return False


def build_tts_cmd(voice: str, rate: int, text: str, output_path: str) -> List[str]:
    rate_str = f"{rate:+d}%"
    return ["edge-tts", "--voice", voice, "--rate", rate_str, "--text", text, "--write-media", output_path]


def build_play_cmd(path: str, volume: int = 100) -> List[str]:
    return ["ffplay", "-nodisp", "-autoexit", "-volume", str(volume), path]


def check_executables() -> Dict[str, bool]:
    return {
        "edge-tts": shutil.which("edge-tts") is not None,
        "ffplay": shutil.which("ffplay") is not None,
    }


def generate_audio(voice: str, rate: int, text: str, output_path: Optional[str] = None) -> Tuple[int, str]:
    """Gera áudio usando a API edge_tts com retry automático para erro 529.

    Retorna (returncode, output_path). returncode=0 em sucesso.
    """
    if not output_path:
        fd, tmp = tempfile.mkstemp(suffix=".mp3")
        os.close(fd)
        output_path = tmp

    if api_available():
        import edge_tts
        rate_str = f"{rate:+d}%"

        async def _save():
            comm = edge_tts.Communicate(text, voice, rate=rate_str)
            await comm.save(output_path)

        for attempt, delay in enumerate([0] + _RETRY_DELAYS):
            if delay:
                logger.warning("edge_tts overloaded (529), aguardando %ds antes de tentar novamente (tentativa %d/%d)",
                               delay, attempt + 1, len(_RETRY_DELAYS) + 1)
                time.sleep(delay)
            try:
                logger.debug("Using edge_tts API (attempt %d), rate=%s", attempt + 1, rate_str)
                asyncio.run(_save())
                return 0, output_path
            except Exception as exc:
                err = str(exc)
                if "529" in err or "overloaded" in err.lower():
                    continue  # retry
                logger.exception("edge_tts API failed (non-529)")
                break  # não faz retry em outros erros

    # fallback CLI
    cmd = build_tts_cmd(voice, rate, text, output_path)
    logger.debug("Falling back to CLI: %s", cmd)
    proc = subprocess.run(cmd)
    return proc.returncode, output_path


def play_audio(path: str, volume: int = 100) -> int:
    cmd = build_play_cmd(path, volume=volume)
    logger.debug("Playing: %s", cmd)
    proc = subprocess.run(cmd, stderr=subprocess.DEVNULL)
    return proc.returncode


def list_voices(locale_filter: Optional[str] = None) -> list:
    # Tentar cache primeiro
    cached = load_voices_cache(locale_filter)
    if cached is not None:
        logger.debug("Voices loaded from cache (%d voices)", len(cached))
        return cached

    try:
        import edge_tts
        voices = asyncio.run(edge_tts.list_voices())
        names = sorted([v["ShortName"] for v in voices])
        save_voices_cache(names)  # salva lista completa no cache
        if locale_filter:
            names = [n for n in names if n.startswith(locale_filter)]
        return names
    except Exception:
        logger.exception("Failed to list voices")
        return []


def split_text(text: str, max_chars: int = 4500) -> List[str]:
    """Divide texto longo em chunks no limite de frases.

    Evita cortar no meio de uma frase. Retorna lista com um item se
    o texto couber em max_chars.
    """
    if len(text) <= max_chars:
        return [text]

    sentences = re.split(r'(?<=[.!?])\s+', text)
    chunks: List[str] = []
    current = ""

    for sentence in sentences:
        if len(current) + len(sentence) + 1 <= max_chars:
            current = (current + " " + sentence).strip()
        else:
            if current:
                chunks.append(current)
            if len(sentence) > max_chars:
                for i in range(0, len(sentence), max_chars):
                    chunks.append(sentence[i:i + max_chars])
                current = ""
            else:
                current = sentence

    if current:
        chunks.append(current)

    return chunks


def generate_audio_long(
    voice: str, rate: int, text: str,
    output_path: Optional[str] = None,
    progress_callback=None,
) -> Tuple[int, str]:
    """Gera áudio para textos longos dividindo em chunks e concatenando com ffmpeg.

    progress_callback(current: int, total: int) é chamado antes de cada chunk.
    """
    chunks = split_text(text)
    if len(chunks) == 1:
        return generate_audio(voice, rate, text, output_path)

    tmp_files: List[str] = []
    try:
        for i, chunk in enumerate(chunks, 1):
            if progress_callback:
                try:
                    progress_callback(i, len(chunks))
                except Exception:
                    pass
            rc, tmp = generate_audio(voice, rate, chunk, None)
            if rc != 0:
                return rc, ""
            tmp_files.append(tmp)

        # Concatenar com ffmpeg
        if not output_path:
            fd, output_path = tempfile.mkstemp(suffix=".mp3")
            os.close(fd)

        list_file = tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False)
        for f in tmp_files:
            list_file.write(f"file '{f}'\n")
        list_file.close()

        cmd = ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", list_file.name, "-c", "copy", output_path]
        proc = subprocess.run(cmd, stderr=subprocess.DEVNULL)
        os.unlink(list_file.name)
        return proc.returncode, output_path
    finally:
        for f in tmp_files:
            try:
                os.remove(f)
            except Exception:
                pass
