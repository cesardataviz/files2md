# Pendientes de files2md

Leyenda: 🔴 crítica · 🟠 alta · 🟡 media · 🟢 baja · ✅ resuelto

---

## ✅ Resuelto (16-oct-2026)

| Pendiente | Solución |
|---|---|
| Word y PDF pedían Pandoc y Typst | Ahora se generan con librerías de Python (`python-docx` y `typst` de pip). No hay que instalar nada aparte. |
| Solo se podía subir un archivo | Hasta 20 archivos por vez, un job por archivo, lista con el estado de cada uno y "Descargar todo (.zip)". |
| El OCR fallaba mucho con fotos de celular | Preprocesamiento: corregir perspectiva + ampliar + igualar la luz. Fotos sintéticas: CER 24,8 % → 0,0 %. Foto real de libro: palabras impresas recuperadas 90 % → 98 %, sin títulos falsos. |
| No se avisaba de fotos de baja calidad | Aviso en el resultado cuando la foto tiene poca resolución, con consejos para tomarla mejor. |

Detalle de la medición en [benchmarks/README.md](../benchmarks/README.md).

---

## 1. 🟠 Dataset real con ground truth

Los resultados actuales vienen de documentos **sintéticos**, que son más fáciles que los reales. Falta:
- 10 fotos reales de celular (`benchmarks/dataset/fotos_reales/`) y 10 escaneos reales, con su texto correcto.
- Medir el preprocesamiento con ellos y ajustar umbrales (`MIN_LONG_SIDE`, `HEADING_MIN_CONF`, etc.).

*(≈3-4 h, sobre todo escribir el texto correcto)*. Los documentos personales no se suben al repo (`.gitignore`).

## 2. 🟡 Páginas curvadas (lomo del libro)

La corrección de perspectiva aplana una hoja **plana** fotografiada en ángulo. Una página **curvada** cerca del
lomo necesita "dewarping" (modelar la curva de las líneas). Evaluar después de tener el dataset real. *(≈6-10 h)*

## 3. 🟡 Comparar con otro motor

PaddleOCR (Apache-2.0) suele rendir mejor con fotos; un VLM local, con páginas de diseño complejo (columnas,
recuadros). Decidir con el benchmark, no por intuición. *(≈6-10 h)*

## 4. 🟢 Selector de idioma

Hoy el OCR usa `spa+eng`. Permitir elegir idioma (o detectarlo) en "Opciones avanzadas". *(≈1-2 h)*

## 5. 🟢 "Texto digital" (Docling) sigue siendo opcional

**No es un error:** es el lector para PDFs con texto seleccionable y documentos de Office. Pesa varios GB
(PyTorch y modelos), por eso es opcional.

- Sin Docling: los PDF digitales se leen con OCR (funciona, más lento, sin tablas) y Word/Excel/PowerPoint no
  se pueden convertir.
- Para activarlo: `pip install -e ".[parse]"` en `backend/` con el entorno virtual activo.

## Fuera de alcance de Tesseract

Texto manuscrito (respuestas a mano, notas). Si se necesita, va por el camino del VLM (punto 3).
