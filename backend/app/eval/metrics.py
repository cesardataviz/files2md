"""Métricas de calidad de transcripción.

CER (Character Error Rate) = distancia de edición en caracteres / longitud de la referencia.
WER (Word Error Rate)      = distancia de edición en palabras  / número de palabras de la referencia.

La distancia de edición (Levenshtein) cuenta cuántas inserciones, borrados y sustituciones convierten
la hipótesis en la referencia. CER 0.02 = 2 de cada 100 caracteres están mal.

Ambas pueden superar 1.0 si el motor "inventa" mucho texto: es útil, delata alucinaciones.

Antes de comparar se normaliza: la sintaxis Markdown (#, -, *, |) y los espacios no son errores de
transcripción. La estructura (títulos, tablas) se evalúa aparte; mezclarla aquí oculta problemas.
"""
from __future__ import annotations

import re
import unicodedata
from collections.abc import Sequence

_COMMENT = re.compile(r"<!--.*?-->", re.DOTALL)
_HEADING = re.compile(r"^\s{0,3}#{1,6}\s+", re.MULTILINE)
_LIST = re.compile(r"^\s*(?:[-*+•]|\d+[.)])\s+", re.MULTILINE)
_EMPHASIS = re.compile(r"(\*{1,3}|_{1,3})(\S.*?\S|\S)\1")
_TABLE_RULE = re.compile(r"^\s*\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)*\|?\s*$", re.MULTILINE)
_SPACES = re.compile(r"\s+")


def normalize(text: str, strip_markdown: bool = True) -> str:
    text = unicodedata.normalize("NFC", text)
    if strip_markdown:
        text = _COMMENT.sub(" ", text)
        text = _TABLE_RULE.sub(" ", text)
        text = _HEADING.sub("", text)
        text = _LIST.sub("", text)
        text = _EMPHASIS.sub(r"\2", text)
        text = text.replace("|", " ")
    return _SPACES.sub(" ", text).strip()


def _levenshtein(a: Sequence, b: Sequence) -> int:
    try:  # rapidfuzz (C++) es órdenes de magnitud más rápido en documentos largos
        from rapidfuzz.distance import Levenshtein

        return Levenshtein.distance(a, b)
    except ImportError:
        pass
    if len(a) < len(b):
        a, b = b, a
    prev = list(range(len(b) + 1))
    for i, x in enumerate(a, 1):
        cur = [i]
        for j, y in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (x != y)))
        prev = cur
    return prev[-1]


def cer(reference: str, hypothesis: str, strip_markdown: bool = True) -> float:
    ref, hyp = normalize(reference, strip_markdown), normalize(hypothesis, strip_markdown)
    if not ref:
        return 0.0 if not hyp else 1.0
    return _levenshtein(ref, hyp) / len(ref)


def wer(reference: str, hypothesis: str, strip_markdown: bool = True) -> float:
    ref = normalize(reference, strip_markdown).split()
    hyp = normalize(hypothesis, strip_markdown).split()
    if not ref:
        return 0.0 if not hyp else 1.0
    return _levenshtein(ref, hyp) / len(ref)
