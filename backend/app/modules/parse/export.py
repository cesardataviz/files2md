"""Exportadores: Markdown -> md | docx | pdf (vía Pandoc).

Pandoc se invoca como proceso externo (no contamina la licencia del proyecto).
docx admite plantilla de estilos con --reference-doc. pdf usa Typst (ligero, sin LaTeX).
"""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

PANDOC_FORMATS = {"docx", "pdf"}


def export(markdown: str, stem: str, fmt: str, out_dir: Path, *, reference_doc: Path | None = None,
           timeout: int = 300) -> Path:
    md_path = out_dir / f"{stem}.md"
    md_path.write_text(markdown, encoding="utf-8")
    if fmt == "md":
        return md_path
    if fmt not in PANDOC_FORMATS:
        raise ValueError(f"Formato de salida no soportado: {fmt}")

    pandoc = shutil.which("pandoc")
    if not pandoc:
        raise RuntimeError("Pandoc no está instalado (necesario para docx/pdf). Usa el perfil 'office'.")

    out = out_dir / f"{stem}.{fmt}"
    cmd = [pandoc, str(md_path), "-f", "markdown", "-o", str(out)]
    if fmt == "docx" and reference_doc is not None:
        cmd += ["--reference-doc", str(reference_doc)]
    if fmt == "pdf":
        cmd += ["--pdf-engine=typst"]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    if proc.returncode != 0:
        raise RuntimeError(f"Pandoc falló: {proc.stderr.strip()[:500]}")
    return out
