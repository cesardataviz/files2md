# Benchmark de motores (módulo P2)

Objetivo: decidir con datos qué motor usar por tipo de entrada, y publicar los resultados.

## Estructura prevista

```
benchmarks/
  dataset/            # documentos propios o sin derechos de autor (NO commitear material con copyright)
    digital/  scanned/  tables/  multicolumn/  forms/
  ground_truth/       # Markdown esperado, corregido a mano (30-50 documentos)
  run.py              # ejecuta cada motor sobre cada documento, guarda resultados + tiempos
  metrics.py          # edit distance normalizada (texto), TEDS (tablas), orden de lectura
  results/            # CSV/JSON por corrida (versionar resúmenes, no los modelos)
```

## Métricas

| Dimensión | Métrica |
|---|---|
| Texto | Distancia de edición normalizada (CER/WER) |
| Tablas | TEDS (verificar implementación de referencia) |
| Estructura | Orden de lectura, jerarquía de encabezados |
| Costo | Segundos/página y RAM/VRAM pico en CPU y GPU |
| Robustez | % de documentos que terminan sin error |

## Comparación mínima

`docling` (determinista) vs `ocr` vs `vlm`, separando por categoría de documento. El resultado esperado
es una tabla de decisión: qué motor para qué tipo de entrada, con su costo.

Estado: sin dataset ni scripts todavía.
