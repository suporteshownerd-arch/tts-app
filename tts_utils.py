"""Utilitários mínimos para montar comandos TTS e checar dependências.

Funções:
- build_tts_cmd(voice, rate, text, output_path) -> list: comando para gerar áudio com edge-tts
- build_play_cmd(path) -> list: comando para reproduzir com ffplay
- check_executables() -> dict: mapeamento de executáveis para boolean (se estão no PATH)
"""
from typing import List, Dict
import shutil
import subprocess
import asyncio
import logging
from typing import Optional

logger = logging.getLogger(__name__)

DEFAULT_TMP_FILE = "/tmp/tts_saida.mp3"


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


def build_play_cmd(path: str) -> List[str]:
    """Retorna comando para reproduzir arquivo com ffplay."""
    return ["ffplay", "-nodisp", "-autoexit", path]


def check_executables() -> Dict[str, bool]:
    """Verifica se os executáveis edge-tts e ffplay estão acessíveis no PATH.

    Retorna dicionário com chaves 'edge-tts' e 'ffplay' e valores booleanos.
    """
    return {
        "edge-tts": shutil.which("edge-tts") is not None,
        "ffplay": shutil.which("ffplay") is not None,
    }


def generate_audio(voice: str, rate: int, text: str, output_path: str) -> int:
    """Tenta gerar áudio usando a API edge_tts quando possível.

    - Se a API Python estiver disponível, usa edge_tts.Communicate.save com rate.
    - Caso contrário, cai para o comando CLI (edge-tts).

    Retorna 0 em sucesso, ou código de erro (não zero) em falha.
    """
    if api_available():
        try:
            import edge_tts
            rate_str = f"{rate:+d}%"

            async def _save():
                comm = edge_tts.Communicate(text, voice, rate=rate_str)
                await comm.save(output_path)

            logger.debug("Using edge_tts API to save audio to %s (rate=%s)", output_path, rate_str)
            asyncio.run(_save())
            return 0
        except Exception:
            # fall back to CLI
            pass

    # fallback to CLI
    cmd = build_tts_cmd(voice, rate, text, output_path)
    logger.debug("Falling back to CLI command: %s", cmd)
    proc = subprocess.run(cmd)
    return proc.returncode


def play_audio(path: str) -> int:
    cmd = build_play_cmd(path)
    logger.debug("Playing audio with cmd: %s", cmd)
    proc = subprocess.run(cmd, stderr=subprocess.DEVNULL)
    return proc.returncode
