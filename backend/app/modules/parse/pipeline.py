"""P2 - pipeline documento -> Markdown / Word / PDF.

Flujo: clasificar -> elegir motor -> convertir -> (opcional) post-proceso -> exportar.
El motor elegido y los motivos quedan en job.meta para poder auditar y alimentar el benchmark.
"""
from __future__ import annotations

from app.core.registry import JobContext, operation
from app.modules.parse.classify import InputKind, classify
from app.modules.parse.engines.base import Engine
from app.modules.parse.engines.docling_engine import DoclingEngine
from app.modules.parse.engines.ocr_vlm import VlmEngine
from app.modules.parse.engines.tesseract_engine import TesseractEngine
from app.modules.parse.export import export

ENGINES: dict[str, Engine] = {e.name: e for e in (DoclingEngine(), TesseractEngine(), VlmEngine())}

# Orden de preferencia por tipo de entrada (el determinista siempre primero cuando aplica).
PREFERENCE: dict[InputKind, list[str]] = {
    # Si Docling no está instalado (pesa varios GB), un PDF digital también se puede leer con OCR:
    # más lento y menos fiel, pero funciona. La nota de fallback queda en job.meta.
    InputKind.digital: ["docling", "ocr"],
    InputKind.office: ["docling"],
    InputKind.scanned: ["ocr", "vlm"],
    InputKind.mixed: ["ocr", "vlm", "docling"],
    InputKind.image: ["ocr", "vlm"],
}

ALL_EXTS = ["pdf", "docx", "pptx", "xlsx", "jpg", "jpeg", "png", "webp", "tiff", "bmp"]


def select_engine(kind: InputKind, requested: str, settings) -> tuple[Engine, list[str]]:
    """Devuelve (motor, notas). Si el pedido no está disponible, falla con un motivo claro."""
    notes: list[str] = []
    candidates = [requested] if requested != "auto" else PREFERENCE.get(kind, [])
    if not candidates:
        raise ValueError(f"Tipo de entrada no soportado: {kind.value}")
    for name in candidates:
        engine = ENGINES.get(name)
        if engine is None:
            raise ValueError(f"Motor desconocido: {name}")
        ok, reason = engine.available(settings)
        if ok:
            return engine, notes
        notes.append(f"{name}: {reason}")
    raise RuntimeError("Ningún motor disponible para esta entrada. " + " | ".join(notes))


@operation(
    "parse.to_document",
    description=(
        "Convierte un archivo a Markdown y lo exporta. "
        "params: {engine: auto|docling|ocr|vlm, output: md|docx|pdf}"
    ),
    accepts=ALL_EXTS,
    profile="full",
)
def to_document(ctx: JobContext) -> None:
    src = ctx.input_paths()[0]
    requested = str(ctx.job.params.get("engine", "auto"))
    fmt = str(ctx.job.params.get("output", "md")).lower()

    ctx.job.meta["stage"] = "analyzing"  # la interfaz traduce la etapa a lenguaje humano
    ctx.progress(0.05)
    cls = classify(src)
    ctx.job.meta["input_kind"] = cls.kind.value
    ctx.job.meta["pages"] = cls.pages

    engine, notes = select_engine(cls.kind, requested, ctx.settings)
    ctx.job.meta["engine"] = engine.name
    if notes:
        ctx.job.meta["engine_fallback_notes"] = notes
    ctx.job.meta["stage"] = "reading"
    ctx.progress(0.1)

    def on_page(page: int, total: int) -> None:
        ctx.job.meta.update(page=page, page_total=total)
        ctx.progress(0.1 + 0.8 * page / max(total, 1))  # leer es ~80% del trabajo

    result = engine.convert(src, ctx.settings, progress=on_page)
    ctx.job.meta.update(result.meta)
    ctx.job.meta["stage"] = "exporting"
    ctx.progress(0.92)

    out = export(
        result.markdown, src.stem, fmt, ctx.storage.output_dir(ctx.job.id),
        timeout=getattr(ctx.settings, "job_timeout_s", 600),
    )
    ctx.add_output(out)
    if fmt != "md":
        # El .md siempre se entrega también: la interfaz lo usa para la vista previa.
        ctx.add_output(out.with_suffix(".md"))
    ctx.job.meta["stage"] = "done"
