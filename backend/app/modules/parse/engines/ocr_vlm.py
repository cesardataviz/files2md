"""Motor VLM (modelo de visión + lenguaje) para escaneados complejos. Esqueleto, opt-in.

El OCR con Tesseract vive en tesseract_engine.py. Otros candidatos a comparar en el benchmark
(verificar licencias vigentes de código Y pesos antes de adoptar): PaddleOCR, VLM local vía Ollama.
Marker/Surya quedan fuera por restricciones comerciales.
"""
from __future__ import annotations

from pathlib import Path

from app.modules.parse.classify import InputKind
from app.modules.parse.engines.base import Engine, ParseResult, ProgressFn


class VlmEngine(Engine):
    name = "vlm"
    handles = {InputKind.scanned, InputKind.mixed, InputKind.image}

    def available(self, settings) -> tuple[bool, str]:
        if not (settings.enable_vlm and settings.vlm_endpoint):
            return False, "VLM deshabilitado (FILES2MD_ENABLE_VLM y FILES2MD_VLM_ENDPOINT)"
        return False, "Motor VLM aún no implementado"

    def convert(self, path: Path, settings, progress: ProgressFn | None = None) -> ParseResult:
        raise NotImplementedError("TODO: render de página -> VLM -> Markdown, con verificación")
