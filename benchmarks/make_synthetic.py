"""Genera documentos escaneados sintéticos con su Markdown correcto.

Uso (desde la raíz del repo, con el backend instalado):
    python benchmarks/make_synthetic.py

Escribe en benchmarks/dataset/{escaneos,fotos}/ y benchmarks/ground_truth/{escaneos,fotos}/ (ignorados por Git:
se regeneran con este script).
"""
from __future__ import annotations

from pathlib import Path

from app.eval.synthetic import write_dataset, write_photo_dataset

ROOT = Path(__file__).resolve().parent

if __name__ == "__main__":
    n = write_dataset(ROOT / "dataset" / "escaneos", ROOT / "ground_truth" / "escaneos")
    f = write_photo_dataset(ROOT / "dataset" / "fotos", ROOT / "ground_truth" / "fotos")
    print(f"{n} escaneos y {f} fotos de celular sintéticos en {ROOT / 'dataset'}")
