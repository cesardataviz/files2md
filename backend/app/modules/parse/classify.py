"""Clasificador de entrada: decide la rama del pipeline.

Heurística barata y determinista: caracteres extraíbles por página. Un PDF "digital" tiene capa
de texto; uno escaneado devuelve ~0 caracteres y requiere OCR/VLM.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from pypdf import PdfReader

MIN_CHARS_PER_PAGE = 40  # umbral inicial; calibrar con el benchmark


class InputKind(str, Enum):
    digital = "digital"
    scanned = "scanned"
    mixed = "mixed"
    image = "image"
    office = "office"
    other = "other"


@dataclass
class Classification:
    kind: InputKind
    pages: int = 0
    pages_without_text: int = 0


IMAGE_EXTS = {"jpg", "jpeg", "png", "webp", "bmp", "tiff", "gif"}
OFFICE_EXTS = {"doc", "docx", "odt", "rtf", "xls", "xlsx", "ods", "ppt", "pptx", "odp"}


def classify(path: Path) -> Classification:
    ext = path.suffix.lower().lstrip(".")
    if ext in IMAGE_EXTS:
        return Classification(InputKind.image)
    if ext in OFFICE_EXTS:
        return Classification(InputKind.office)
    if ext != "pdf":
        return Classification(InputKind.other)

    reader = PdfReader(path)
    total = len(reader.pages)
    empty = sum(
        1 for p in reader.pages if len((p.extract_text() or "").strip()) < MIN_CHARS_PER_PAGE
    )
    if empty == 0:
        kind = InputKind.digital
    elif empty == total:
        kind = InputKind.scanned
    else:
        kind = InputKind.mixed
    return Classification(kind, pages=total, pages_without_text=empty)
