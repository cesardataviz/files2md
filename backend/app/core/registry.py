"""Registro de operaciones. Cada módulo (tools, parse) registra sus funciones con @operation."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from app.core.jobs import Job, JobRepository
from app.core.storage import StorageBackend


@dataclass
class JobContext:
    job: Job
    storage: StorageBackend
    repo: JobRepository
    settings: object

    def input_paths(self) -> list[Path]:
        return [self.storage.upload_path(self.job.id, n) for n in self.job.input_files]

    def output_path(self, filename: str) -> Path:
        return self.storage.output_path(self.job.id, filename)

    def add_output(self, path: Path) -> None:
        self.job.outputs.append(path.name)

    def progress(self, value: float) -> None:
        self.job.progress = max(0.0, min(1.0, value))
        self.repo.update(self.job)


@dataclass
class OperationSpec:
    name: str
    fn: Callable[[JobContext], None]
    description: str = ""
    accepts: list[str] = field(default_factory=list)  # extensiones de entrada admitidas
    min_inputs: int = 1
    max_inputs: int = 1
    # Qué perfil de imagen Docker trae sus dependencias: lite | office | full
    profile: str = "lite"


OPERATIONS: dict[str, OperationSpec] = {}


def operation(
    name: str,
    *,
    description: str = "",
    accepts: list[str] | None = None,
    min_inputs: int = 1,
    max_inputs: int = 1,
    profile: str = "lite",
):
    def deco(fn: Callable[[JobContext], None]):
        OPERATIONS[name] = OperationSpec(
            name=name,
            fn=fn,
            description=description,
            accepts=[a.lower().lstrip(".") for a in (accepts or [])],
            min_inputs=min_inputs,
            max_inputs=max_inputs,
            profile=profile,
        )
        return fn

    return deco
