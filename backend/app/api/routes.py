"""API HTTP. Contrato: POST /api/jobs -> job_id; GET /api/jobs/{id} (polling); descarga de outputs."""
from __future__ import annotations

import json
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse

from app.core.jobs import Job
from app.core.registry import OPERATIONS
from app.core.storage import safe_name

router = APIRouter(prefix="/api")


def require_token(request: Request) -> None:
    token = request.app.state.settings.api_token
    if not token:
        return
    supplied = request.headers.get("authorization", "").removeprefix("Bearer ").strip()
    if supplied != token:
        raise HTTPException(status_code=401, detail="Token inválido")


Auth = Depends(require_token)


@router.get("/health")
def health():
    return {"status": "ok"}


@router.get("/operations", dependencies=[Auth])
def list_operations():
    return [
        {
            "name": s.name,
            "description": s.description,
            "accepts": s.accepts,
            "min_inputs": s.min_inputs,
            "max_inputs": s.max_inputs,
            "profile": s.profile,
        }
        for s in OPERATIONS.values()
    ]


@router.post("/jobs", status_code=202, dependencies=[Auth])
async def create_job(
    request: Request,
    operation: Annotated[str, Form()],
    files: Annotated[list[UploadFile], File()],
    params: Annotated[str, Form()] = "{}",
):
    app = request.app
    settings, storage, repo, queue = (
        app.state.settings, app.state.storage, app.state.repo, app.state.queue,
    )

    spec = OPERATIONS.get(operation)
    if spec is None:
        raise HTTPException(404, f"Operación desconocida: {operation}")
    if not (spec.min_inputs <= len(files) <= spec.max_inputs):
        raise HTTPException(
            422, f"{operation} requiere entre {spec.min_inputs} y {spec.max_inputs} archivos"
        )
    try:
        parsed_params = json.loads(params)
        if not isinstance(parsed_params, dict):
            raise ValueError
    except ValueError:
        raise HTTPException(422, "params debe ser un objeto JSON") from None

    job = Job(operation=operation, params=parsed_params)
    max_bytes = settings.max_upload_mb * 1024 * 1024
    try:
        for f in files:
            ext = safe_name(f.filename or "").rsplit(".", 1)[-1].lower()
            if spec.accepts and ext not in spec.accepts:
                raise HTTPException(415, f"Extensión .{ext} no admitida para {operation}")
            job.input_files.append(storage.save_upload(job.id, f.filename or "file", f.file, max_bytes))
    except ValueError as exc:
        storage.delete_job(job.id)
        raise HTTPException(413, str(exc)) from None
    except HTTPException:
        storage.delete_job(job.id)
        raise

    repo.create(job)
    queue.enqueue(job.id)
    return {"job_id": job.id, "state": job.state}


@router.get("/jobs/{job_id}", dependencies=[Auth])
def get_job(job_id: str, request: Request):
    job = request.app.state.repo.get(job_id)
    if job is None:
        raise HTTPException(404, "Job no encontrado (¿expiró por TTL?)")
    return job


@router.get("/jobs/{job_id}/outputs/{name}", dependencies=[Auth])
def download_output(job_id: str, name: str, request: Request):
    job = request.app.state.repo.get(job_id)
    if job is None or name not in job.outputs:
        raise HTTPException(404, "Output no encontrado")
    path = request.app.state.storage.output_path(job_id, name)
    if not path.is_file():
        raise HTTPException(404, "Archivo eliminado")
    return FileResponse(path, filename=name)


@router.delete("/jobs/{job_id}", status_code=204, dependencies=[Auth])
def delete_job(job_id: str, request: Request):
    request.app.state.storage.delete_job(job_id)
    request.app.state.repo.delete(job_id)
