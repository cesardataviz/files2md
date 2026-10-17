from __future__ import annotations

import asyncio
import contextlib
import logging
from contextlib import asynccontextmanager
from functools import partial

from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi
from fastapi.staticfiles import StaticFiles

from app import modules  # noqa: F401  # registra las operaciones (efecto lateral intencional)
from app.api.routes import router
from app.config import Settings, get_settings
from app.core.jobs import JobRepository
from app.core.queue import InProcessQueue, QueueBackend, RedisQueue
from app.core.runner import run_job
from app.core.storage import LocalStorage, ttl_cutoff

log = logging.getLogger("files2md")


def build_queue(settings: Settings, runner) -> QueueBackend:
    if settings.queue_backend == "redis":
        return RedisQueue(settings.redis_url)
    return InProcessQueue(runner, workers=settings.queue_workers)


async def _purge_loop(app: FastAPI) -> None:
    """Borrado por TTL: privacidad por defecto, los archivos no se quedan para siempre."""
    s: Settings = app.state.settings
    while True:
        try:
            for job_id in app.state.repo.expired_ids(ttl_cutoff(s.job_ttl_hours)):
                app.state.storage.delete_job(job_id)
                app.state.repo.delete(job_id)
        except Exception:  # noqa: BLE001
            log.exception("Fallo en purga por TTL")
        await asyncio.sleep(600)


def _fix_file_inputs(schema: dict) -> None:
    """FastAPI documenta los archivos como `contentMediaType` (OpenAPI 3.1), pero la página /docs
    (Swagger UI) solo muestra el selector de archivos con `format: binary`. Se añade ese campo."""
    if isinstance(schema, dict):
        if schema.get("type") == "string" and "contentMediaType" in schema:
            schema.setdefault("format", "binary")
        for value in schema.values():
            _fix_file_inputs(value)
    elif isinstance(schema, list):
        for item in schema:
            _fix_file_inputs(item)


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        task = asyncio.create_task(_purge_loop(app))
        yield
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task
        app.state.queue.shutdown()

    app = FastAPI(title="files2md", version="0.1.0", lifespan=lifespan)
    storage = LocalStorage(settings.uploads_dir, settings.outputs_dir)
    repo = JobRepository(settings.db_path)

    app.state.settings = settings
    app.state.storage = storage
    app.state.repo = repo
    app.state.queue = build_queue(settings, partial(run_job, repo=repo, storage=storage, settings=settings))

    app.include_router(router)

    def custom_openapi() -> dict:
        if app.openapi_schema is None:
            schema = get_openapi(title=app.title, version=app.version, routes=app.routes)
            _fix_file_inputs(schema)
            app.openapi_schema = schema
        return app.openapi_schema

    app.openapi = custom_openapi
    if settings.frontend_dir.is_dir():
        app.mount("/", StaticFiles(directory=settings.frontend_dir, html=True), name="frontend")
    return app


app = create_app()
