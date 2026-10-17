import numpy as np
import pytest

from app.config import Settings
from app.eval.metrics import cer
from app.eval.synthetic import SAMPLES, photo
from app.modules.parse.engines.tesseract_engine import TesseractEngine, Word, words_to_markdown
from app.modules.parse.preprocess import even_light, find_page, preprocess


def test_detects_page_on_table_and_flattens_it():
    img = photo(SAMPLES[0], seed=12, quality=60, width=960)
    corners = find_page(np.array(img.convert("L")))
    assert corners is not None
    out, steps = preprocess(img)
    assert steps[0] == "page" and "light" in steps
    assert out.mode == "L" and max(out.size) >= 2000  # se amplió


def test_no_page_detected_when_photo_is_only_the_sheet():
    gray = np.full((800, 600), 235, np.uint8)
    gray[100:110, 50:550] = 20  # una "línea de texto"
    assert find_page(gray) is None


def test_even_light_flattens_background():
    h, w = 600, 800
    gradient = np.tile(np.linspace(110, 245, w, dtype=np.float32), (h, 1))
    gradient[300:306, 100:700] = 20  # texto oscuro
    out = even_light(gradient.astype(np.uint8))
    background = np.concatenate([out[:250].ravel(), out[350:].ravel()])
    assert background.std() < 8  # el fondo queda parejo...
    assert out[303, 400] < 100  # ...y el texto sigue oscuro


def test_low_confidence_fragments_and_fake_headings_are_filtered():
    words = [
        Word("Ge", 30.0, 80, 0, 40, 1, 1, 1),  # mancha grande de una foto: ruido
        Word("Informe", 95.0, 30, 0, 80, 2, 1, 1),
        Word("anual", 95.0, 30, 90, 60, 2, 1, 1),
        Word("Texto", 95.0, 30, 0, 60, 3, 1, 1),
        Word("normal.", 95.0, 30, 70, 80, 3, 1, 1),
    ]
    md, _ = words_to_markdown(words)
    assert "Ge" not in md and not md.startswith("#")


ready = TesseractEngine().available(Settings())


@pytest.mark.skipif(not ready[0], reason=f"Tesseract no disponible: {ready[1]}")
def test_phone_photo_is_read_correctly(tmp_path):
    doc = SAMPLES[1]
    path = tmp_path / "foto.jpg"
    photo(doc, seed=22, quality=40, width=960).save(path, quality=95)
    result = TesseractEngine().convert(path, Settings())
    assert cer(doc.markdown(), result.markdown) < 0.02
    assert result.meta["image_small"] is True
    assert "light" in result.meta["ocr_preprocess"]

    without = TesseractEngine().convert(path, Settings(ocr_preprocess="off"))
    assert cer(doc.markdown(), without.markdown) > cer(doc.markdown(), result.markdown)
