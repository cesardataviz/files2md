"""Ejecuta los motores sobre el dataset y mide calidad y costo.

Uso (desde la raíz del repo, con el backend instalado: pip install -e "backend[dev,bench]"):
    python benchmarks/run.py                       # todos los motores disponibles
    python benchmarks/run.py --engines ocr         # solo OCR
    python benchmarks/run.py --dataset benchmarks/dataset/private

Para cada archivo de dataset/<categoría>/<nombre>.<ext> busca ground_truth/<categoría>/<nombre>.md.
Escribe un CSV por corrida en benchmarks/results/ e imprime un resumen por motor y categoría.

El benchmark llama a los motores directamente (sin la API) para medir solo el motor.
"""
from __future__ import annotations

import argparse
import csv
import statistics
import sys
import time
from collections import defaultdict
from datetime import datetime
from pathlib import Path

from app.config import Settings
from app.eval.metrics import cer, wer
from app.modules.parse.classify import classify
from app.modules.parse.pipeline import ALL_EXTS, ENGINES

ROOT = Path(__file__).resolve().parent
FIELDS = ["file", "category", "engine", "input_kind", "pages", "seconds", "sec_per_page",
          "cer", "wer", "mean_conf", "status", "detail"]


def find_pairs(dataset: Path, truth: Path) -> list[tuple[Path, Path | None, str]]:
    pairs = []
    for f in sorted(dataset.rglob("*")):
        if f.is_file() and f.suffix.lower().lstrip(".") in ALL_EXTS:
            rel = f.relative_to(dataset)
            gt = truth / rel.with_suffix(".md")
            category = rel.parts[0] if len(rel.parts) > 1 else "general"
            pairs.append((f, gt if gt.is_file() else None, category))
    return pairs


def run_one(engine, doc: Path, gt: Path | None, category: str, settings: Settings) -> dict:
    row = {"file": doc.name, "category": category, "engine": engine.name}
    try:
        cls = classify(doc)
        row.update(input_kind=cls.kind.value, pages=cls.pages or 1)
        if cls.kind not in engine.handles:
            return {**row, "status": "skipped", "detail": f"{engine.name} no procesa '{cls.kind.value}'"}
        start = time.perf_counter()
        result = engine.convert(doc, settings)
        seconds = time.perf_counter() - start
        row.update(seconds=round(seconds, 2), sec_per_page=round(seconds / row["pages"], 2),
                   mean_conf=result.meta.get("ocr_mean_conf", ""), status="ok")
        if gt is None:
            row["detail"] = "sin ground truth: solo se mide tiempo"
        else:
            reference = gt.read_text(encoding="utf-8")
            row.update(cer=round(cer(reference, result.markdown), 4),
                       wer=round(wer(reference, result.markdown), 4))
    except Exception as exc:  # noqa: BLE001 - un documento que falla es un dato, no un motivo para parar
        row.update(status="error", detail=f"{type(exc).__name__}: {exc}"[:200])
    return row


def summarize(rows: list[dict]) -> None:
    groups: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for r in rows:
        if r["status"] != "skipped":
            groups[(r["engine"], r["category"])].append(r)
    if not groups:
        print("Nada que resumir: ningún motor procesó documentos.")
        return
    print(f"\n{'motor':<8} {'categoría':<14} {'docs':>4} {'éxito':>6} {'CER':>7} {'WER':>7} {'s/pág':>6}")
    for (engine, category), rs in sorted(groups.items()):
        ok = [r for r in rs if r["status"] == "ok"]
        scored = [r for r in ok if r.get("cer") != "" and "cer" in r]

        def mean(key, items):
            return f"{statistics.fmean(r[key] for r in items):.3f}" if items else "-"

        print(f"{engine:<8} {category:<14} {len(rs):>4} {len(ok) / len(rs):>6.0%} "
              f"{mean('cer', scored):>7} {mean('wer', scored):>7} {mean('sec_per_page', ok):>6}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--dataset", type=Path, default=ROOT / "dataset")
    parser.add_argument("--truth", type=Path, default=ROOT / "ground_truth")
    parser.add_argument("--engines", default="all", help="lista separada por comas, p. ej. ocr,docling")
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args()

    settings = Settings()
    names = list(ENGINES) if args.engines == "all" else args.engines.split(",")
    engines = []
    for name in names:
        engine = ENGINES.get(name)
        if engine is None:
            print(f"Motor desconocido: {name}", file=sys.stderr)
            return 2
        ok, reason = engine.available(settings)
        if ok:
            engines.append(engine)
        else:
            print(f"[omitido] {name}: {reason}")

    pairs = find_pairs(args.dataset, args.truth)
    if not pairs:
        print(f"No hay documentos en {args.dataset}. Genera sintéticos con: python benchmarks/make_synthetic.py")
        return 1
    if not engines:
        print("Ningún motor disponible.")
        return 1

    rows = []
    for engine in engines:
        for doc, gt, category in pairs:
            row = run_one(engine, doc, gt, category, settings)
            rows.append(row)
            print(f"{engine.name:<8} {category}/{doc.name:<32} {row['status']:<7} "
                  f"CER={row.get('cer', '-')} {row.get('detail', '')}")

    out = args.out or ROOT / "results" / f"{datetime.now():%Y%m%d-%H%M%S}.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=FIELDS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)

    summarize(rows)
    print(f"\nResultados detallados: {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
