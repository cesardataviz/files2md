"""Motores para escaneados/imágenes. Esqueleto: se implementan al elegir OCR tras el benchmark.

Candidatos a comparar (verificar licencias vigentes antes de adoptar): Tesseract, PaddleOCR,
Surya/Marker (licencia con restricciones comerciales), VLM local vía Ollama.
"""
from __future__ import annotations

from pathlib import Path

from app.modules.parse.classify import InputKind
from app.modules.parse.engines.base import Engine, ParseResult


class OcrEngine(Engine):
    name = "ocr"
    handles = {InputKind.scanned, InputKind.mixed, InputKind.image}

    def available(self, settings) -> tuple[bool, str]:
        if not settings.enable_ocr:
            return False, "OCR deshabilitado (FILES2MD_ENABLE_OCR=true y perfil Docker 'full')"
        return False, "Motor OCR aún no implementado"

    def convert(self, path: Path, settings) -> ParseResult:
        raise NotImplementedError("TODO: layout analysis + OCR -> Markdown")


class VlmEngine(Engine):
    name = "vlm"
    handles = {InputKind.scanned, InputKind.mixed, InputKind.image}

    def available(self, settings) -> tuple[bool, str]:
        if not (settings.enable_vlm and settings.vlm_endpoint):
            return False, "VLM deshabilitado (FILES2MD_ENABLE_VLM y FILES2MD_VLM_ENDPOINT)"
        return False, "Motor VLM aún no implementado"

    def convert(self, path: Path, settings) -> ParseResult:
        raise NotImplementedError("TODO: render de página -> VLM -> Markdown, con verificación")
