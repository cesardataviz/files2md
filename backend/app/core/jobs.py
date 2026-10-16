"""Modelo de job + repositorio SQLite.

El job es el contrato central: API, cola y workers solo se hablan a través de él.
"""
from __future__ import annotations

import sqlite3
import threading
import uuid
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path

from pydantic import BaseModel, Field


def _now() -> datetime:
    return datetime.now(timezone.utc)


class JobState(str, Enum):
    queued = "queued"
    running = "running"
    succeeded = "succeeded"
    failed = "failed"
    cancelled = "cancelled"


class Job(BaseModel):
    id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    operation: str  # p. ej. "tool.image_to_pdf", "parse.to_markdown"
    state: JobState = JobState.queued
    progress: float = 0.0  # 0..1
    input_files: list[str] = Field(default_factory=list)  # nombres dentro del dir de uploads del job
    params: dict = Field(default_factory=dict)
    outputs: list[str] = Field(default_factory=list)  # nombres dentro del dir de outputs del job
    meta: dict = Field(default_factory=dict)  # métricas: motor usado, páginas, tiempos
    error: str | None = None
    created_at: datetime = Field(default_factory=_now)
    updated_at: datetime = Field(default_factory=_now)


class JobRepository:
    """Persistencia mínima. Un blob JSON por job: suficiente para modo local."""

    def __init__(self, db_path: Path):
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.execute(
            "CREATE TABLE IF NOT EXISTS jobs ("
            "id TEXT PRIMARY KEY, data TEXT NOT NULL, created_at TEXT NOT NULL)"
        )
        self._conn.commit()

    def create(self, job: Job) -> Job:
        with self._lock:
            self._conn.execute(
                "INSERT INTO jobs (id, data, created_at) VALUES (?, ?, ?)",
                (job.id, job.model_dump_json(), job.created_at.isoformat()),
            )
            self._conn.commit()
        return job

    def get(self, job_id: str) -> Job | None:
        with self._lock:
            row = self._conn.execute("SELECT data FROM jobs WHERE id = ?", (job_id,)).fetchone()
        return Job.model_validate_json(row[0]) if row else None

    def update(self, job: Job) -> Job:
        job.updated_at = _now()
        with self._lock:
            self._conn.execute("UPDATE jobs SET data = ? WHERE id = ?", (job.model_dump_json(), job.id))
            self._conn.commit()
        return job

    def expired_ids(self, before: datetime) -> list[str]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT id FROM jobs WHERE created_at < ?", (before.isoformat(),)
            ).fetchall()
        return [r[0] for r in rows]

    def delete(self, job_id: str) -> None:
        with self._lock:
            self._conn.execute("DELETE FROM jobs WHERE id = ?", (job_id,))
            self._conn.commit()
