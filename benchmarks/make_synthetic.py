"""Genera documentos escaneados sintéticos con su Markdown correcto.

Uso (desde la raíz del repo, con el backend instalado):
    python benchmarks/make_synthetic.py

Escribe en benchmarks/dataset/synthetic/ y benchmarks/ground_truth/synthetic/ (ignorados por Git:
se regeneran con este script).
"""
from __future__ import annotations

from pathlib import Path

from app.eval.synthetic import write_dataset

ROOT = Path(__file__).resolve().parent

if __name__ == "__main__":
    n = write_dataset(ROOT / "dataset" / "synthetic", ROOT / "ground_truth" / "synthetic")
    print(f"{n} documentos sintéticos generados en {ROOT / 'dataset' / 'synthetic'}")
