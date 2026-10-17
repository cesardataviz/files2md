"""Motor determinista (rama digital): sin alucinaciones, rápido, offline. Requiere extra `parse`."""
from __future__ import annotations

import importlib.util
from pathlib import Path

from app.modules.parse.classify import InputKind
from app.modules.parse.engines.base import Engine, ParseResult, ProgressFn


class DoclingEngine(Engine):
    name = "docling"
    handles = {InputKind.digital, InputKind.office}

    def available(self, settings) -> tuple[bool, str]:
        if importlib.util.find_spec("docling") is None:
            return False, "Docling no instalado (pip install '.[parse]')"
        return True, ""

    def convert(self, path: Path, settings, progress: ProgressFn | None = None) -> ParseResult:
        # Docling no expone progreso por página: la interfaz muestra la etapa sin contador.
        from docling.document_converter import DocumentConverter  # import perezoso: es pesado

        result = DocumentConverter().convert(str(path))
        return ParseResult(markdown=result.document.export_to_markdown(), engine=self.name)
