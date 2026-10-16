"""Abstracción de almacenamiento. Local por defecto; S3/R2 implementan la misma interfaz."""
from __future__ import annotations

import re
import shutil
from abc import ABC, abstractmethod
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import BinaryIO

_SAFE = re.compile(r"[^A-Za-z0-9._-]+")


def safe_name(name: str) -> str:
    """Nunca confiar en el nombre que manda el cliente (path traversal, caracteres raros)."""
    base = Path(name).name
    cleaned = _SAFE.sub("_", base).strip("._") or "file"
    return cleaned[:120]


class StorageBackend(ABC):
    @abstractmethod
    def save_upload(self, job_id: str, filename: str, fileobj: BinaryIO, max_bytes: int) -> str: ...

    @abstractmethod
    def upload_path(self, job_id: str, filename: str) -> Path: ...

    @abstractmethod
    def output_dir(self, job_id: str) -> Path: ...

    @abstractmethod
    def output_path(self, job_id: str, filename: str) -> Path: ...

    @abstractmethod
    def delete_job(self, job_id: str) -> None: ...


class LocalStorage(StorageBackend):
    def __init__(self, uploads_dir: Path, outputs_dir: Path):
        self.uploads_dir = uploads_dir
        self.outputs_dir = outputs_dir
        uploads_dir.mkdir(parents=True, exist_ok=True)
        outputs_dir.mkdir(parents=True, exist_ok=True)

    def save_upload(self, job_id: str, filename: str, fileobj: BinaryIO, max_bytes: int) -> str:
        name = safe_name(filename)
        dest_dir = self.uploads_dir / job_id
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest = dest_dir / name
        written = 0
        with dest.open("wb") as out:
            while chunk := fileobj.read(1024 * 1024):
                written += len(chunk)
                if written > max_bytes:
                    out.close()
                    dest.unlink(missing_ok=True)
                    raise ValueError(f"El archivo supera el límite de {max_bytes // (1024 * 1024)} MB")
                out.write(chunk)
        return name

    def upload_path(self, job_id: str, filename: str) -> Path:
        return self.uploads_dir / job_id / safe_name(filename)

    def output_dir(self, job_id: str) -> Path:
        d = self.outputs_dir / job_id
        d.mkdir(parents=True, exist_ok=True)
        return d

    def output_path(self, job_id: str, filename: str) -> Path:
        return self.output_dir(job_id) / safe_name(filename)

    def delete_job(self, job_id: str) -> None:
        shutil.rmtree(self.uploads_dir / job_id, ignore_errors=True)
        shutil.rmtree(self.outputs_dir / job_id, ignore_errors=True)


def ttl_cutoff(hours: int) -> datetime:
    return datetime.now(timezone.utc) - timedelta(hours=hours)
