"""Utilitários mínimos para montar comandos TTS e checar dependências.

Funções:
- build_tts_cmd(voice, rate, text, output_path) -> list: comando para gerar áudio com edge-tts
- build_play_cmd(path) -> list: comando para reproduzir com ffplay
- check_executables() -> dict: mapeamento de executáveis para boolean (se estão no PATH)
"""
from typing import List, Dict, Optional, Tuple
import shutil
import subprocess
import asyncio
import logging
import tempfile
import os

logger = logging.getLogger(__name__)

# When None, generate_audio will create a unique temporary file
DEFAULT_TMP_FILE: Optional[str] = None


def api_available() -> bool:
    """Retorna True se o módulo edge_tts estiver disponível e fornece Communicate."""
    try:
        import edge_tts
        return hasattr(edge_tts, "Communicate")
    except Exception:
        return False


def build_tts_cmd(voice: str, rate: int, text: str, output_path: str) -> List[str]:
    """Retorna a lista de argumentos para chamar edge-tts.

    rate deve ser inteiro representando porcentagem (ex: -10, 0, 25). A função
    formata como "+25%" ou "-10%" requerido pelo CLI.
    """
    rate_str = f"{rate:+d}%"
    return [
        "edge-tts",
        "--voice",
        voice,
        "--rate",
        rate_str,
        "--text",
        text,
        "--write-media",
        output_path,
    ]


def build_play_cmd(path: str, volume: int = 100) -> List[str]:
    """Retorna comando para reproduzir arquivo com ffplay."""
    return ["ffplay", "-nodisp", "-autoexit", "-volume", str(volume), path]


def check_executables() -> Dict[str, bool]:
    """Verifica se os executáveis edge-tts e ffplay estão acessíveis no PATH.

    Retorna dicionário com chaves 'edge-tts' e 'ffplay' e valores booleanos.
    """
    return {
        "edge-tts": shutil.which("edge-tts") is not None,
        "ffplay": shutil.which("ffplay") is not None,
    }


def generate_audio(voice: str, rate: int, text: str, output_path: Optional[str] = None) -> Tuple[int, str]:
    """Gera áudio usando a API edge_tts quando possível; retorna (rc, path).

    - Se output_path for None, cria um arquivo temporário único e retorna seu caminho.
    - Prefere a API Python quando disponível; caso contrário usa o CLI.
    - Retorna (returncode, output_path)
    """
    temp_created = False
    if not output_path:
        fd, tmp = tempfile.mkstemp(suffix=".mp3")
        os.close(fd)
        output_path = tmp
        temp_created = True

    # prefer API when available
    if api_available():
        try:
            import edge_tts
            rate_str = f"{rate:+d}%"

            async def _save():
                rate_str = f"{rate:+d}%"
                # Call Communicate with rate when available
                comm = edge_tts.Communicate(text, voice, rate=rate_str)
                await comm.save(output_path)

            logger.debug("Using edge_tts API to save audio to %s (rate=%s)", output_path, rate_str)
            asyncio.run(_save())
            return 0, output_path
        except Exception:
            logger.exception("edge_tts API path failed, falling back to CLI")

    # fallback to CLI
    cmd = build_tts_cmd(voice, rate, text, output_path)
    logger.debug("Falling back to CLI command: %s", cmd)
    proc = subprocess.run(cmd)
    return proc.returncode, output_path


def play_audio(path: str) -> int:
    cmd = build_play_cmd(path)
    logger.debug("Playing audio with cmd: %s", cmd)
    proc = subprocess.run(cmd, stderr=subprocess.DEVNULL)
    return proc.returncode


def list_voices(locale_filter: Optional[str] = None) -> list:
    """Lista vozes disponíveis via API edge_tts.

    Se locale_filter for informado (ex: 'pt-BR'), retorna apenas vozes desse locale.
    Retorna lista de ShortNames ordenada, ou lista vazia em caso de erro.
    """
    try:
        import edge_tts

        voices = asyncio.run(edge_tts.list_voices())
        names = [v["ShortName"] for v in voices]
        if locale_filter:
            names = [n for n in names if n.startswith(locale_filter)]
        return sorted(names)
    except Exception:
        logger.exception("Failed to list voices")
        return []
