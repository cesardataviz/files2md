"""Ejecución de un job: la única pieza que cambia estados. Igual en cola local y en worker Redis."""
from __future__ import annotations

import logging
import time
import traceback

from app.core.jobs import JobRepository, JobState
from app.core.registry import OPERATIONS, JobContext
from app.core.storage import StorageBackend

log = logging.getLogger("files2md.runner")


def run_job(job_id: str, repo: JobRepository, storage: StorageBackend, settings) -> None:
    job = repo.get(job_id)
    if job is None or job.state != JobState.queued:
        return

    spec = OPERATIONS.get(job.operation)
    if spec is None:
        job.state, job.error = JobState.failed, f"Operación desconocida: {job.operation}"
        repo.update(job)
        return

    job.state = JobState.running
    repo.update(job)
    ctx = JobContext(job=job, storage=storage, repo=repo, settings=settings)
    started = time.perf_counter()
    try:
        spec.fn(ctx)
        job.state, job.progress = JobState.succeeded, 1.0
    except Exception as exc:  # noqa: BLE001 - un job fallido no debe tumbar el worker
        log.error("Job %s falló: %s\n%s", job_id, exc, traceback.format_exc())
        job.state, job.error = JobState.failed, f"{type(exc).__name__}: {exc}"
    finally:
        job.meta["elapsed_s"] = round(time.perf_counter() - started, 3)
        repo.update(job)
