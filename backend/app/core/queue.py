"""Cola abstracta. InProcessQueue para modo local; RedisQueue (ARQ) para modo escalable."""
from __future__ import annotations

from abc import ABC, abstractmethod
from concurrent.futures import ThreadPoolExecutor
from typing import Callable


class QueueBackend(ABC):
    @abstractmethod
    def enqueue(self, job_id: str) -> None: ...

    def shutdown(self) -> None:  # pragma: no cover
        pass


class InProcessQueue(QueueBackend):
    """Pool de hilos. Suficiente para uso local; las operaciones pesadas lanzan subprocesos
    (Tesseract) o liberan el GIL (Pillow, modelos)."""

    def __init__(self, runner: Callable[[str], None], workers: int = 2):
        self._runner = runner
        self._pool = ThreadPoolExecutor(max_workers=workers, thread_name_prefix="files2md-worker")

    def enqueue(self, job_id: str) -> None:
        self._pool.submit(self._runner, job_id)

    def shutdown(self) -> None:
        self._pool.shutdown(wait=False, cancel_futures=True)


class RedisQueue(QueueBackend):  # pragma: no cover - se implementa en el perfil "scale"
    """TODO: encolar job_id con ARQ y ejecutar `run_job` en procesos worker separados."""

    def __init__(self, redis_url: str):
        raise NotImplementedError("Perfil 'scale' pendiente: ver docs/ARCHITECTURE.md")

    def enqueue(self, job_id: str) -> None:
        raise NotImplementedError
