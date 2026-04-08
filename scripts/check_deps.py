#!/usr/bin/env python3
"""Script simples para checar dependências do TTS App.

Uso: python3 scripts/check_deps.py
Retorna código 0 se tudo ok, 1 se alguma dependência está faltando.
"""
import sys
from tts_utils import check_executables


def main():
    ex = check_executables()
    ok = True
    if ex["edge-tts"]:
        print("edge-tts: found")
    else:
        print("edge-tts: NOT FOUND")
        ok = False
    if ex["ffplay"]:
        print("ffplay: found")
    else:
        print("ffplay: NOT FOUND")
        ok = False
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
