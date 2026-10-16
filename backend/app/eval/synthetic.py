"""Generador de documentos "escaneados" sintéticos con su Markdown correcto (ground truth).

Sirve para probar el pipeline y el benchmark sin depender de documentos reales.
No sustituye a documentos reales: el ruido sintético es más amable que un escáner de verdad.
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

# A4 a 200 dpi: resolución típica de un escaneo de oficina.
PAGE_SIZE = (1654, 2339)
MARGIN = 150

_FONT_CANDIDATES = [
    "DejaVuSans.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "arial.ttf",  # Windows
    "C:/Windows/Fonts/arial.ttf",
    "/System/Library/Fonts/Supplemental/Arial.ttf",  # macOS
    "/Library/Fonts/Arial.ttf",
]


def load_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for name in _FONT_CANDIDATES:
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default(size=size)  # Pillow >= 10.1


@dataclass
class SyntheticDoc:
    title: str
    paragraphs: list[str]
    bullets: list[str] = field(default_factory=list)

    def markdown(self) -> str:
        parts = [f"# {self.title}", *self.paragraphs]
        if self.bullets:
            parts.append("\n".join(f"- {b}" for b in self.bullets))
        return "\n\n".join(parts) + "\n"


def _wrap(draw: ImageDraw.ImageDraw, text: str, font, width: int) -> list[str]:
    lines, current = [], ""
    for word in text.split():
        candidate = f"{current} {word}".strip()
        if draw.textlength(candidate, font=font) <= width:
            current = candidate
        else:
            lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def render(doc: SyntheticDoc, noise: float = 0.0, seed: int = 0) -> Image.Image:
    """Dibuja el documento. noise 0 = limpio; 0.3-0.6 = escaneo mediocre (inclinación, blur, grano)."""
    rng = random.Random(seed)
    img = Image.new("L", PAGE_SIZE, 255)
    draw = ImageDraw.Draw(img)
    body, title = load_font(38), load_font(66)
    width = PAGE_SIZE[0] - 2 * MARGIN
    y = MARGIN

    draw.text((MARGIN, y), doc.title, font=title, fill=0)
    y += 130
    for paragraph in doc.paragraphs:
        for line in _wrap(draw, paragraph, body, width):
            draw.text((MARGIN, y), line, font=body, fill=0)
            y += 56
        y += 40
    for bullet in doc.bullets:
        for i, line in enumerate(_wrap(draw, bullet, body, width - 60)):
            if i == 0:
                draw.text((MARGIN, y), "•", font=body, fill=0)
            draw.text((MARGIN + 60, y), line, font=body, fill=0)
            y += 56
        y += 10

    if noise > 0:
        img = img.rotate(rng.uniform(-1.5, 1.5) * noise, fillcolor=255, resample=Image.BICUBIC)
        img = img.filter(ImageFilter.GaussianBlur(radius=0.4 + noise))
        grain = Image.effect_noise(PAGE_SIZE, 40 * noise)
        img = Image.blend(img, grain, alpha=0.12 * noise)
    return img


SAMPLES: list[SyntheticDoc] = [
    SyntheticDoc(
        "Informe de Gestión Trimestral",
        [
            "Durante el tercer trimestre la operación logística redujo el tiempo promedio de entrega "
            "de 4,2 a 3,1 días, principalmente por la reorganización de rutas en la zona norte.",
            "El costo por envío aumentó un 6,5% debido al alza del combustible. Se recomienda "
            "renegociar las tarifas con los dos proveedores principales antes de diciembre.",
        ],
        ["Revisar contratos de transporte.", "Medir la satisfacción del cliente en enero."],
    ),
    SyntheticDoc(
        "Acta de Reunión del Comité",
        [
            "Siendo las diez de la mañana se dio inicio a la sesión con la presencia de cinco "
            "miembros. Se aprobó por unanimidad el acta anterior sin observaciones.",
            "La gerencia presentó la propuesta de capacitación en análisis de datos para el área "
            "comercial, con una duración de ocho semanas y una inversión estimada de S/ 12 400.",
        ],
    ),
    SyntheticDoc(
        "Política de Uso de Información",
        [
            "Toda información clasificada como confidencial deberá almacenarse en repositorios "
            "con acceso restringido. El incumplimiento será evaluado por el comité de ética.",
            "Los colaboradores recibirán una inducción obligatoria sobre protección de datos "
            "personales durante su primer mes, incluyendo ejemplos prácticos y una evaluación final.",
        ],
        ["No compartir contraseñas.", "Reportar incidentes en menos de 24 horas."],
    ),
]


def write_dataset(dataset_dir: Path, truth_dir: Path, noise_levels: tuple[float, ...] = (0.0, 0.5)) -> int:
    """Escribe PDFs de solo imagen (sin capa de texto) y su ground truth. Devuelve cuántos generó."""
    dataset_dir.mkdir(parents=True, exist_ok=True)
    truth_dir.mkdir(parents=True, exist_ok=True)
    count = 0
    for i, doc in enumerate(SAMPLES, 1):
        for noise in noise_levels:
            stem = f"doc{i:02d}_ruido{int(noise * 100):02d}"
            render(doc, noise=noise, seed=i).save(dataset_dir / f"{stem}.pdf", "PDF", resolution=200)
            (truth_dir / f"{stem}.md").write_text(doc.markdown(), encoding="utf-8")
            count += 1
    return count
