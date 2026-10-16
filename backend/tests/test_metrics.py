import pytest

from app.eval.metrics import cer, normalize, wer


def test_identical_text_has_zero_error():
    assert cer("Hola mundo", "Hola mundo") == 0.0
    assert wer("Hola mundo", "Hola mundo") == 0.0


def test_markdown_syntax_and_spacing_are_not_errors():
    ref = "# Título\n\n- uno\n- **dos**\n\n<!-- página 2 -->\n\nfin"
    hyp = "Título  uno dos\nfin"
    assert normalize(ref) == normalize(hyp) == "Título uno dos fin"
    assert cer(ref, hyp) == 0.0


def test_single_substitution():
    # "casa" -> "cosa": 1 error en 4 caracteres; 1 palabra mal de 1.
    assert cer("casa", "cosa") == pytest.approx(0.25)
    assert wer("casa", "cosa") == pytest.approx(1.0)


def test_word_error_rate_counts_words():
    assert wer("el informe fue aprobado", "el informe aprobado") == pytest.approx(0.25)


def test_hallucinated_text_can_exceed_one():
    assert cer("ok", "texto inventado larguísimo") > 1.0


def test_accents_matter_and_unicode_is_normalized():
    assert cer("acción", "accion") > 0  # perder la tilde es un error real
    assert cer("acción", "acción") == 0.0  # mismo texto en dos codificaciones Unicode


def test_empty_reference():
    assert cer("", "") == 0.0
    assert cer("", "algo") == 1.0
