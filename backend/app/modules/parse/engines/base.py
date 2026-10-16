"""Contrato común de motores. Todos devuelven Markdown + metadatos para poder compararlos en el benchmark."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path

from app.modules.parse.classify import InputKind


@dataclass
class ParseResult:
    markdown: str
    engine: str
    meta: dict = field(default_factory=dict)  # páginas, warnings, tiempos internos, costo estimado


class Engine(ABC):
    name: str
    handles: set[InputKind]

    @abstractmethod
    def available(self, settings) -> tuple[bool, str]:
        """(disponible, motivo si no). Permite degradar con un mensaje claro en vez de explotar."""

    @abstractmethod
    def convert(self, path: Path, settings) -> ParseResult: ...
