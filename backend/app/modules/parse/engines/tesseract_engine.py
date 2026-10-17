"""Motor OCR con Tesseract para PDFs escaneados e imágenes.

Flujo por página:
1. Rasterizar: PDF -> imagen con pypdfium2 (licencia permisiva; evitamos PyMuPDF por AGPL).
2. OCR con posiciones: Tesseract en modo TSV devuelve cada palabra con su caja, su bloque/párrafo/línea
   y una confianza 0-100. No usamos el texto plano porque pierde la estructura.
3. Reconstrucción: agrupamos palabras en líneas y párrafos, unimos palabras cortadas con guion y
   detectamos títulos comparando la altura de la letra con la mediana de la página.

Limitaciones conocidas (medirlas con el benchmark antes de "arreglarlas"):
- No reconstruye tablas: salen como párrafos.
- Varias columnas: Tesseract suele separarlas en bloques; el orden de lectura no está garantizado.
- La detección de títulos es una heurística por tamaño; no distingue negrita del mismo tamaño.
"""
from __future__ import annotations

import csv
import io
import shutil
import statistics
import subprocess
import tempfile
from collections.abc import Iterator
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from PIL import Image, ImageSequence

from app.modules.parse.classify import InputKind
from app.modules.parse.engines.base import Engine, ParseResult, ProgressFn
from app.modules.parse.preprocess import preprocess

HEADING_RATIO = 1.3  # una línea es candidata a título si su letra es >= 1.3x la mediana de la página
H1_RATIO = 1.6  # a partir de aquí, título principal (#). Ej.: 18 pt sobre texto de 11 pt = 1.64
MAX_HEADING_WORDS = 14  # un "título" de 40 palabras casi seguro es un párrafo
HEADING_MIN_CONF = 70.0  # en fotos, manchas grandes (fotos, banners) se leen como "letras grandes"
NOISE_MAX_CHARS = 2  # fragmentos de 1-2 caracteres con baja confianza casi siempre son ruido
LOW_CONFIDENCE = 60.0
SMALL_IMAGE_PX = 1000  # lado corto menor: foto de baja resolución, se avisa al usuario  # páginas con confianza media menor se reportan como dudosas
BULLETS = {"•", "·", "▪", "◦", "-", "–", "*"}
# Tesseract suele leer "•" como "e", "o", "+"... No se puede filtrar por letra ("o" y "e" son palabras
# en español), así que se usa geometría: un carácter suelto seguido de un hueco mucho mayor que un espacio.
BULLET_GAP_RATIO = 0.8  # hueco tras la viñeta >= 0.8x la altura de la letra (un espacio normal ~0.3x)


@dataclass(frozen=True)
class Word:
    text: str
    conf: float
    height: int
    left: int
    width: int
    block: int
    par: int
    line: int


# ---------------------------------------------------------------- Tesseract


def find_tesseract(settings) -> str | None:
    return settings.tesseract_cmd or shutil.which("tesseract")


@lru_cache(maxsize=8)
def installed_langs(cmd: str) -> frozenset[str]:
    proc = subprocess.run([cmd, "--list-langs"], capture_output=True, text=True, timeout=30)
    # La primera línea es un encabezado ("List of available languages ...").
    lines = (proc.stdout or proc.stderr).splitlines()[1:]
    return frozenset(line.strip() for line in lines if line.strip())


def run_tesseract(cmd: str, image: Path, langs: str, timeout: int) -> list[Word]:
    # --psm 3: segmentación automática de página (bloques, párrafos, líneas).
    # tessedit_create_tsv=1 en vez del atajo "tsv": funciona aunque falte la carpeta configs/.
    proc = subprocess.run(
        [cmd, str(image), "stdout", "-l", langs, "--psm", "3", "-c", "tessedit_create_tsv=1"],
        capture_output=True, text=True, encoding="utf-8", timeout=timeout,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"Tesseract falló: {proc.stderr.strip()[:300]}")
    return parse_tsv(proc.stdout)


def parse_tsv(tsv: str) -> list[Word]:
    words: list[Word] = []
    for row in csv.DictReader(io.StringIO(tsv), delimiter="\t", quoting=csv.QUOTE_NONE):
        text = (row.get("text") or "").strip()
        if row.get("level") != "5" or not text:  # nivel 5 = palabra
            continue
        words.append(
            Word(
                text=text,
                conf=float(row["conf"]),
                height=int(row["height"]),
                left=int(row["left"]),
                width=int(row["width"]),
                block=int(row["block_num"]),
                par=int(row["par_num"]),
                line=int(row["line_num"]),
            )
        )
    return words


# ---------------------------------------------------------------- Reconstrucción


def _join_lines(lines: list[str]) -> str:
    """Une líneas de un párrafo reparando palabras cortadas: 'informa-' + 'ción' -> 'información'."""
    out = ""
    for line in lines:
        if out.endswith("-") and line[:1].islower():
            out = out[:-1] + line
        else:
            out = f"{out} {line}" if out else line
    return out


def _is_bullet_line(ws: list[Word], height: float) -> bool:
    if len(ws) < 2 or len(ws[0].text) != 1:
        return False
    if ws[0].text in BULLETS:
        return True
    gap = ws[1].left - (ws[0].left + ws[0].width)
    return gap >= BULLET_GAP_RATIO * height


def words_to_markdown(words: list[Word]) -> tuple[str, list[float]]:
    """Convierte las palabras de UNA página en Markdown. Devuelve (markdown, confianzas)."""
    if not words:
        return "", []

    # Agrupar en líneas y párrafos respetando el orden de Tesseract.
    lines: dict[tuple[int, int, int], list[Word]] = {}
    for w in words:
        lines.setdefault((w.block, w.par, w.line), []).append(w)

    line_height = {k: statistics.median(w.height for w in ws) for k, ws in lines.items()}
    page_median = statistics.median(line_height.values()) or 1

    paragraphs: dict[tuple[int, int], list[tuple[int, int, int]]] = {}
    for key in lines:
        paragraphs.setdefault(key[:2], []).append(key)

    blocks: list[str] = []
    for line_keys in paragraphs.values():
        texts = [" ".join(w.text for w in lines[k]) for k in line_keys]
        n_words = sum(len(lines[k]) for k in line_keys)
        ratio = min(line_height[k] for k in line_keys) / page_median
        par_words = [w for k in line_keys for w in lines[k]]
        par_conf = statistics.fmean(w.conf for w in par_words) if par_words else 0.0
        letters = sum(ch.isalpha() for t in texts for ch in t)
        alnum = sum(ch.isalnum() for t in texts for ch in t)

        if alnum <= NOISE_MAX_CHARS and par_conf < LOW_CONFIDENCE:
            continue  # ruido: bordes de fotos, manchas, restos de dibujos

        is_heading = (
            ratio >= HEADING_RATIO
            and len(line_keys) <= 2
            and n_words <= MAX_HEADING_WORDS
            and par_conf >= HEADING_MIN_CONF
            and letters >= 3
        )
        if is_heading:
            prefix = "#" if ratio >= H1_RATIO else "##"
            blocks.append(f"{prefix} {' '.join(texts)}")
            continue

        # Viñetas: cada línea que empieza con viñeta abre un ítem nuevo; las demás continúan el ítem.
        bullet_flags = [_is_bullet_line(lines[k], line_height[k]) for k in line_keys]
        if any(bullet_flags):
            items: list[list[str]] = []
            for k, is_bullet in zip(line_keys, bullet_flags):
                ws = lines[k]
                if is_bullet:
                    items.append([" ".join(w.text for w in ws[1:])])
                elif items:
                    items[-1].append(" ".join(w.text for w in ws))
                else:
                    items.append([" ".join(w.text for w in ws)])
            list_md = "\n".join(f"- {_join_lines(i)}" for i in items)
            # Tesseract a veces pone cada viñeta en su propio párrafo: se unen en una sola lista.
            if blocks and blocks[-1].startswith("- "):
                blocks[-1] += "\n" + list_md
            else:
                blocks.append(list_md)
            continue

        blocks.append(_join_lines(texts))

    return "\n\n".join(blocks), [w.conf for w in words if w.conf >= 0]


# ---------------------------------------------------------------- Imágenes de entrada


def _flatten(img: Image.Image) -> Image.Image:
    if img.mode in ("RGBA", "LA", "P"):
        rgba = img.convert("RGBA")
        base = Image.new("RGB", rgba.size, "white")
        base.paste(rgba, mask=rgba.getchannel("A"))
        return base
    return img.convert("RGB") if img.mode not in ("RGB", "L") else img


def page_count(path: Path) -> int:
    if path.suffix.lower() == ".pdf":
        import pypdfium2 as pdfium

        pdf = pdfium.PdfDocument(str(path))
        try:
            return len(pdf)
        finally:
            pdf.close()
    with Image.open(path) as img:
        return getattr(img, "n_frames", 1)


def iter_page_images(path: Path, dpi: int) -> Iterator[Image.Image]:
    """Una imagen por página, generada de a una para no cargar todo el documento en memoria."""
    if path.suffix.lower() == ".pdf":
        import pypdfium2 as pdfium  # import perezoso: solo hace falta para PDFs

        pdf = pdfium.PdfDocument(str(path))
        try:
            for i in range(len(pdf)):
                page = pdf[i]
                try:
                    yield page.render(scale=dpi / 72, grayscale=True).to_pil()
                finally:
                    page.close()
        finally:
            pdf.close()
    else:
        with Image.open(path) as img:
            for frame in ImageSequence.Iterator(img):  # TIFF multipágina
                yield _flatten(frame.copy())


# ---------------------------------------------------------------- Motor


class TesseractEngine(Engine):
    name = "ocr"
    handles = {InputKind.scanned, InputKind.mixed, InputKind.image}

    def available(self, settings) -> tuple[bool, str]:
        if not settings.enable_ocr:
            return False, "OCR deshabilitado (FILES2MD_ENABLE_OCR=false)"
        cmd = find_tesseract(settings)
        if not cmd:
            return False, (
                "Tesseract no está instalado o no está en el PATH. Instálalo con los idiomas "
                f"{settings.ocr_langs} o define FILES2MD_TESSERACT_CMD con la ruta al ejecutable"
            )
        try:
            missing = set(settings.ocr_langs.split("+")) - installed_langs(cmd)
        except (OSError, subprocess.SubprocessError) as exc:
            return False, f"No se pudo ejecutar Tesseract ({cmd}): {exc}"
        if missing:
            return False, f"Faltan idiomas de Tesseract: {', '.join(sorted(missing))}"
        return True, ""

    def convert(self, path: Path, settings, progress: ProgressFn | None = None) -> ParseResult:
        cmd = find_tesseract(settings)
        total = page_count(path)
        timeout = getattr(settings, "job_timeout_s", 600)
        pages_md: list[str] = []
        page_conf: list[float] = []
        all_conf: list[float] = []

        is_pdf = path.suffix.lower() == ".pdf"
        mode = getattr(settings, "ocr_preprocess", "auto")
        # auto: solo imágenes (fotos de celular). Los PDF escaneados ya vienen planos y bien iluminados.
        use_preprocess = mode == "always" or (mode == "auto" and not is_pdf)
        applied: list[str] = []
        small_image = False

        with tempfile.TemporaryDirectory(prefix="files2md-ocr-") as tmp:
            for n, img in enumerate(iter_page_images(path, settings.ocr_dpi), start=1):
                if not is_pdf and n == 1:
                    small_image = min(img.size) < SMALL_IMAGE_PX
                if use_preprocess:
                    img, steps = preprocess(img)
                    if n == 1:
                        applied = steps
                png = Path(tmp) / f"page-{n}.png"
                img.save(png)
                img.close()
                md, confs = words_to_markdown(run_tesseract(cmd, png, settings.ocr_langs, timeout))
                png.unlink(missing_ok=True)
                pages_md.append(md)
                page_conf.append(round(statistics.fmean(confs), 1) if confs else 0.0)
                all_conf.extend(confs)
                if progress:
                    progress(n, total)

        if len(pages_md) > 1:
            # Comentario HTML: invisible al renderizar, pero permite rastrear de qué página vino cada texto.
            markdown = "\n\n".join(f"<!-- página {i} -->\n\n{md}" for i, md in enumerate(pages_md, 1))
        else:
            markdown = pages_md[0] if pages_md else ""

        return ParseResult(
            markdown=markdown.strip() + "\n",
            engine=self.name,
            meta={
                "ocr_langs": settings.ocr_langs,
                "ocr_dpi": settings.ocr_dpi,
                "ocr_preprocess": applied,
                "image_small": small_image,
                "ocr_mean_conf": round(statistics.fmean(all_conf), 1) if all_conf else 0.0,
                "ocr_page_conf": page_conf,
                "ocr_low_conf_pages": [i for i, c in enumerate(page_conf, 1) if c < LOW_CONFIDENCE],
            },
        )
