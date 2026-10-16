import io
import time

from fastapi.testclient import TestClient
from PIL import Image

from app.config import Settings
from app.main import create_app
from app.modules.parse import pipeline
from app.modules.parse.classify import InputKind, classify
from app.modules.parse.engines.base import ParseResult


def text_pdf(text: str) -> bytes:
    """PDF digital mínimo con capa de texto (Helvetica), construido a mano para no depender de nada."""
    content = f"BT /F1 12 Tf 72 720 Td ({text}) Tj ET".encode()
    objs = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R "
        b"/Resources << /Font << /F1 5 0 R >> >> >>",
        b"<< /Length %d >>\nstream\n" % len(content) + content + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    out, offsets = io.BytesIO(), []
    out.write(b"%PDF-1.4\n")
    for i, body in enumerate(objs, 1):
        offsets.append(out.tell())
        out.write(b"%d 0 obj\n" % i + body + b"\nendobj\n")
    xref = out.tell()
    out.write(b"xref\n0 %d\n0000000000 65535 f \n" % (len(objs) + 1))
    for off in offsets:
        out.write(b"%010d 00000 n \n" % off)
    out.write(b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (len(objs) + 1, xref))
    return out.getvalue()


def image_pdf() -> bytes:
    """PDF 'escaneado': solo una imagen, sin capa de texto."""
    buf = io.BytesIO()
    Image.new("RGB", (200, 100), "white").save(buf, "PDF")
    return buf.getvalue()


def make_client(tmp_path, **overrides) -> TestClient:
    settings = Settings(data_dir=tmp_path / "data", frontend_dir=tmp_path / "nofront", **overrides)
    return TestClient(create_app(settings))


def wait(client: TestClient, job_id: str, timeout: float = 10.0) -> dict:
    deadline = time.time() + timeout
    while time.time() < deadline:
        job = client.get(f"/api/jobs/{job_id}").json()
        if job["state"] in ("succeeded", "failed"):
            return job
        time.sleep(0.05)
    raise AssertionError("El job no terminó a tiempo")


def submit(client, name, data, **params):
    import json

    r = client.post(
        "/api/jobs",
        data={"operation": "parse.to_document", "params": json.dumps(params)},
        files=[("files", (name, data, "application/octet-stream"))],
    )
    assert r.status_code == 202, r.text
    return wait(client, r.json()["job_id"])


LONG_TEXT = "Informe trimestral de ventas por region con detalle de cada categoria"


def test_classify_digital_vs_scanned(tmp_path):
    digital = tmp_path / "d.pdf"
    digital.write_bytes(text_pdf(LONG_TEXT))
    scanned = tmp_path / "s.pdf"
    scanned.write_bytes(image_pdf())
    assert classify(digital).kind == InputKind.digital
    assert classify(scanned).kind == InputKind.scanned


def test_health_and_operations(tmp_path):
    with make_client(tmp_path) as client:
        assert client.get("/api/health").json() == {"status": "ok"}
        names = {o["name"] for o in client.get("/api/operations").json()}
        assert names == {"parse.to_document"}


def test_pipeline_end_to_end_with_stub_engine(tmp_path, monkeypatch):
    """Prueba el flujo completo (clasificar -> motor -> export md) sin instalar Docling."""
    engine = pipeline.ENGINES["docling"]
    monkeypatch.setattr(engine, "available", lambda settings: (True, ""))
    monkeypatch.setattr(
        engine, "convert", lambda path, settings: ParseResult("# Informe\n\nTexto.", "docling")
    )
    with make_client(tmp_path) as client:
        job = submit(client, "informe.pdf", text_pdf(LONG_TEXT), output="md")
        assert job["state"] == "succeeded", job["error"]
        assert job["meta"]["input_kind"] == "digital"
        assert job["meta"]["engine"] == "docling"
        md = client.get(f"/api/jobs/{job['id']}/outputs/{job['outputs'][0]}").text
        assert md.startswith("# Informe")


def test_scanned_without_ocr_fails_with_actionable_message(tmp_path):
    with make_client(tmp_path, enable_ocr=False) as client:
        job = submit(client, "escaneo.pdf", image_pdf())
        assert job["state"] == "failed"
        assert job["meta"]["input_kind"] == "scanned"
        assert "FILES2MD_ENABLE_OCR" in job["error"]


def test_rejects_unsupported_extension_and_oversize(tmp_path):
    with make_client(tmp_path) as client:
        r = client.post(
            "/api/jobs",
            data={"operation": "parse.to_document"},
            files=[("files", ("x.exe", b"MZ", "application/octet-stream"))],
        )
        assert r.status_code == 415
    with make_client(tmp_path, max_upload_mb=0) as client:
        r = client.post(
            "/api/jobs",
            data={"operation": "parse.to_document"},
            files=[("files", ("../../a.pdf", text_pdf(LONG_TEXT), "application/pdf"))],
        )
        assert r.status_code == 413


def test_token_required_when_configured(tmp_path):
    with make_client(tmp_path, api_token="secreto") as client:
        assert client.get("/api/operations").status_code == 401
        ok = client.get("/api/operations", headers={"Authorization": "Bearer secreto"})
        assert ok.status_code == 200
