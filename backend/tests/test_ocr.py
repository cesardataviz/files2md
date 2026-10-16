import io
import json
import time

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.eval.synthetic import SAMPLES, render
from app.main import create_app
from app.modules.parse.engines import tesseract_engine as te
from app.modules.parse.engines.tesseract_engine import (
    TesseractEngine,
    Word,
    parse_tsv,
    words_to_markdown,
)


def w(text, block=1, par=1, line=1, height=30, left=0, width=None, conf=95.0):
    return Word(text, conf, height, left, width if width is not None else 12 * len(text), block, par, line)


def line(words_text, start=100, **kw):
    """Palabras de una línea separadas por un espacio normal (10 px)."""
    out, x = [], start
    for t in words_text.split():
        out.append(w(t, left=x, **kw))
        x += 12 * len(t) + 10
    return out


# ---------------------------------------------------------------- reconstrucción (sin Tesseract)


def test_heading_paragraph_and_hyphenation():
    words = (
        line("Informe Anual", block=1, height=52)
        + line("La operación logística mejoró la informa-", block=2, line=1)
        + line("ción de entregas.", block=2, line=2)
    )
    md, confs = words_to_markdown(words)
    assert md == "# Informe Anual\n\nLa operación logística mejoró la información de entregas."
    assert len(confs) == len(words)


def test_secondary_heading_level():
    # La altura de referencia es la mediana de las líneas de la página: necesita varias líneas de cuerpo.
    # Límite conocido: en páginas casi vacías (p. ej. portadas) la detección de títulos es poco fiable.
    body = [line("Texto normal del cuerpo aquí.", block=2, line=i) for i in (1, 2, 3)]
    words = line("Resultados", block=1, height=40) + [x for b in body for x in b]
    assert words_to_markdown(words)[0].startswith("## Resultados\n\n")


def test_bullets_detected_by_geometry_even_if_misread():
    # Tesseract leyó la viñeta como "e" y "+": un carácter suelto con un hueco grande (40 px).
    words = [
        w("e", par=1, line=1, left=100, width=12), *line("Revisar contratos.", start=152, par=1, line=1),
        w("+", par=2, line=1, left=100, width=12), *line("Medir satisfacción.", start=152, par=2, line=1),
    ]
    assert words_to_markdown(words)[0] == "- Revisar contratos.\n- Medir satisfacción."


def test_short_word_with_normal_space_is_not_a_bullet():
    # "o" es una palabra válida en español: con un espacio normal no debe volverse viñeta.
    md, _ = words_to_markdown(line("o bien se aprueba el presupuesto."))
    assert md == "o bien se aprueba el presupuesto."


def test_parse_tsv_keeps_only_words():
    tsv = (
        "level\tpage_num\tblock_num\tpar_num\tline_num\tword_num\tleft\ttop\twidth\theight\tconf\ttext\n"
        "4\t1\t1\t1\t1\t0\t10\t10\t100\t30\t-1\t\n"
        "5\t1\t1\t1\t1\t1\t10\t10\t40\t30\t96.5\tHola\n"
        "5\t1\t1\t1\t1\t2\t60\t10\t40\t30\t-1\t \n"
    )
    assert parse_tsv(tsv) == [Word("Hola", 96.5, 30, 10, 40, 1, 1, 1)]


# ---------------------------------------------------------------- disponibilidad


def test_unavailable_when_disabled_missing_binary_or_language(monkeypatch):
    engine = TesseractEngine()
    assert "FILES2MD_ENABLE_OCR" in engine.available(Settings(enable_ocr=False))[1]

    monkeypatch.setattr(te, "find_tesseract", lambda s: None)
    assert "FILES2MD_TESSERACT_CMD" in engine.available(Settings())[1]

    monkeypatch.setattr(te, "find_tesseract", lambda s: "/fake/tesseract")
    monkeypatch.setattr(te, "installed_langs", lambda cmd: frozenset({"eng"}))
    ok, reason = engine.available(Settings(ocr_langs="spa+eng"))
    assert not ok and "spa" in reason


# ---------------------------------------------------------------- integración con Tesseract real

ocr_ready = TesseractEngine().available(Settings())
requires_tesseract = pytest.mark.skipif(not ocr_ready[0], reason=f"Tesseract no disponible: {ocr_ready[1]}")


@requires_tesseract
def test_scanned_pdf_end_to_end_through_api(tmp_path):
    doc = SAMPLES[0]
    buf = io.BytesIO()
    render(doc, noise=0.5, seed=1).save(buf, "PDF", resolution=200)

    settings = Settings(data_dir=tmp_path / "data", frontend_dir=tmp_path / "nofront")
    with TestClient(create_app(settings)) as client:
        r = client.post(
            "/api/jobs",
            data={"operation": "parse.to_document", "params": json.dumps({"output": "md"})},
            files=[("files", ("escaneo.pdf", buf.getvalue(), "application/pdf"))],
        )
        job_id = r.json()["job_id"]
        for _ in range(300):
            job = client.get(f"/api/jobs/{job_id}").json()
            if job["state"] in ("succeeded", "failed"):
                break
            time.sleep(0.1)

        assert job["state"] == "succeeded", job["error"]
        assert job["meta"]["input_kind"] == "scanned"
        assert job["meta"]["engine"] == "ocr"
        assert job["meta"]["ocr_mean_conf"] > 80
        md = client.get(f"/api/jobs/{job_id}/outputs/{job['outputs'][0]}").text
        assert md == doc.markdown()
