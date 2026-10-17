"""Preprocesamiento de imágenes antes del OCR (pensado para fotos de celular).

Diagnóstico que lo motivó (benchmark, categoría "fotos"): con luz desigual Tesseract no "falla al leer",
sino que NO DETECTA zonas enteras de texto (reflejos, sombras). La confianza sigue alta porque lo poco
que lee, lo lee bien. Por eso el paso más importante es igualar la iluminación.

Pasos (cada uno se puede activar por separado para medirlo):
- page:     detectar la hoja (el cuadrilátero más grande) y "aplanarla" corrigiendo la perspectiva.
- upscale:  ampliar imágenes pequeñas; Tesseract necesita letras de ~20-30 px de alto.
- light:    igualar la iluminación: estimar el fondo con un cierre morfológico y dividir por él.
"""
from __future__ import annotations

import cv2
import numpy as np
from PIL import Image

ALL_STEPS = ("page", "upscale", "light")
MIN_LONG_SIDE = 2200  # por debajo de esto se amplía (hasta 3x)


def _order_corners(pts: np.ndarray) -> np.ndarray:
    """Ordena 4 puntos: arriba-izq, arriba-der, abajo-der, abajo-izq."""
    s = pts.sum(axis=1)
    d = np.diff(pts, axis=1).ravel()
    return np.float32([pts[np.argmin(s)], pts[np.argmin(d)], pts[np.argmax(s)], pts[np.argmax(d)]])


def find_page(gray: np.ndarray) -> np.ndarray | None:
    """Esquinas de la hoja si se distingue del fondo; None si la foto ya es solo la hoja."""
    h, w = gray.shape
    scale = 800 / max(h, w)
    small = cv2.resize(gray, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)
    blur = cv2.GaussianBlur(small, (5, 5), 0)
    _, mask = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)  # hoja clara vs. fondo
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones((15, 15), np.uint8))
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return None
    biggest = max(contours, key=cv2.contourArea)
    area_ratio = cv2.contourArea(biggest) / (small.shape[0] * small.shape[1])
    if not 0.25 < area_ratio < 0.97:  # >97%: la hoja ocupa toda la foto, no hay nada que recortar
        return None
    approx = cv2.approxPolyDP(biggest, 0.02 * cv2.arcLength(biggest, True), True)
    if len(approx) != 4:
        return None
    return _order_corners(approx.reshape(4, 2).astype(np.float32) / scale)


def flatten_page(gray: np.ndarray, corners: np.ndarray) -> np.ndarray:
    tl, tr, br, bl = corners
    width = int(max(np.linalg.norm(br - bl), np.linalg.norm(tr - tl)))
    height = int(max(np.linalg.norm(tr - br), np.linalg.norm(tl - bl)))
    dst = np.float32([[0, 0], [width - 1, 0], [width - 1, height - 1], [0, height - 1]])
    matrix = cv2.getPerspectiveTransform(corners, dst)
    return cv2.warpPerspective(gray, matrix, (width, height), flags=cv2.INTER_CUBIC, borderValue=255)


def even_light(gray: np.ndarray) -> np.ndarray:
    """Divide la imagen por una estimación del fondo: el papel queda blanco parejo y el texto se conserva.
    El cierre morfológico con un núcleo mayor que el grosor de las letras "borra" el texto y deja el fondo."""
    k = max(15, (max(gray.shape) // 60) | 1)
    background = cv2.morphologyEx(gray, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k, k)))
    background = cv2.GaussianBlur(background, (0, 0), k / 3)
    return cv2.divide(gray, background, scale=255)


def preprocess(image: Image.Image, steps: tuple[str, ...] = ALL_STEPS) -> tuple[Image.Image, list[str]]:
    """Devuelve la imagen preparada para OCR y la lista de pasos que realmente se aplicaron."""
    gray = np.array(image.convert("L"))
    applied: list[str] = []

    if "page" in steps:
        corners = find_page(gray)
        if corners is not None:
            gray = flatten_page(gray, corners)
            applied.append("page")

    if "upscale" in steps:
        long_side = max(gray.shape)
        if long_side < MIN_LONG_SIDE:
            factor = min(3.0, MIN_LONG_SIDE / long_side)
            gray = cv2.resize(gray, None, fx=factor, fy=factor, interpolation=cv2.INTER_CUBIC)
            applied.append(f"upscale×{factor:.1f}")

    if "light" in steps:
        gray = even_light(gray)
        applied.append("light")

    return Image.fromarray(gray), applied
