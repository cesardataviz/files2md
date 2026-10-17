# Pendientes de files2md

Detectados en la primera prueba real (15-oct-2026). Ordenados por prioridad.
Leyenda: 🔴 crítica · 🟠 alta · 🟡 media · 🟢 baja

---

## 1. 🟠 Mejorar el OCR de fotos tomadas con el celular

**Caso que falló:** foto de una página de libro de inglés (`SPSA.jpg`, 960×1280, 16 KB). El Markdown salió con
muchos errores.

**Causas probables** (por orden de impacto estimado; confirmar midiendo):

| Causa | Por qué afecta a Tesseract |
|---|---|
| Resolución y compresión muy bajas (16 KB) | Tesseract necesita letras de ~20-30 px de alto (equivalente a 300 dpi). Aquí el texto mide ~10 px y la compresión JPG deja artefactos alrededor de cada letra. |
| Página curvada y en ángulo | Tesseract asume líneas rectas y horizontales. Cerca del lomo del libro las líneas se curvan y se cortan. |
| Iluminación desigual (reflejo de sol, sombras) | La binarización (pasar a blanco y negro) usa un umbral global: lo muy iluminado se "lava" y lo sombreado se vuelve manchas. |
| Diseño complejo | Dos columnas, recuadros de color, fotos, un banner rosado y títulos grandes. El orden de lectura se mezcla y el fondo de color reduce el contraste. |
| Escritura a mano (respuestas y garabatos) | Tesseract no lee manuscrito: genera basura y además tapa el texto impreso. |
| Idioma | El documento está en inglés y el OCR usa `spa+eng`. Influye poco, pero conviene poder elegirlo. |

**Plan de mejora** (medir cada paso con el benchmark antes de seguir):

1. 🟠 **Dataset de fotos reales:** crear la categoría `benchmarks/dataset/fotos_celular/` con 10 fotos y su
   texto correcto. Sin esto no sabremos si cada cambio mejora o empeora. *(≈3 h)*
2. 🟠 **Preprocesamiento de imagen** con OpenCV (licencia Apache-2.0): ampliar las imágenes pequeñas (×2-3),
   normalizar la iluminación, umbral adaptativo y enderezar la inclinación. *(≈4-6 h)*
3. 🟡 **Corrección de perspectiva:** detectar los bordes de la página y "aplanarla". La curvatura del lomo
   (dewarping) es más difícil; evaluar después. *(≈4-8 h)*
4. 🟡 **Comparar con otro motor:** PaddleOCR (Apache-2.0) suele rendir mejor con fotos, y un VLM local para
   páginas complejas. Decidir con el benchmark. *(≈6-10 h)*
5. 🟢 **Avisos en la interfaz:** si la imagen es pequeña o la confianza sale baja, sugerir cómo mejorar la foto
   ("tómala de frente, sin reflejos y con buena luz"). *(≈1-2 h)*
6. 🟢 **Selector de idioma** (o detección automática). *(≈1-2 h)*

**Fuera de alcance de Tesseract:** el texto manuscrito. Si se necesita, va por el camino del VLM.

---

## 2. 🟡 Convertir varios archivos a la vez

**Hoy:** un archivo por conversión (`max_inputs=1` en `parse.to_document`). El límite es de **200 MB por
archivo** (`FILES2MD_MAX_UPLOAD_MB`). No hay límite de páginas; cada página escaneada tarda unos segundos.

**Propuesta:** que la interfaz acepte varios archivos y cree **un job por archivo** (el backend ya procesa 2 en
paralelo con `FILES2MD_QUEUE_WORKERS`). Mostrar una lista con el estado de cada uno y un botón
"Descargar todo (.zip)". No hace falta cambiar el modelo de jobs. *(≈4-6 h)*

---

## 3. 🟡 Habilitar Word y PDF como salida

**Hoy:** requieren dos programas externos que no se instalan con `pip`:
- **Word (.docx):** Pandoc.
- **PDF:** Pandoc + Typst.

**Opciones:**
- **A. Instalar en Windows** (rápido, sin código): `winget install --id JohnMacFarlane.Pandoc` y
  `winget install --id Typst.Typst` *(verificar los identificadores con `winget search` antes)*. Reiniciar el
  backend para que `/api/capabilities` los detecte. *(≈15 min)*
- **B. Generar el .docx con Python** (`python-docx`, licencia MIT): quita la dependencia de Pandoc para Word y
  hace la instalación más simple para quien descargue el repo. *(≈3-4 h)*

Recomendación: A para probar ya; B antes de publicar una versión para otras personas.
Pendiente técnico relacionado: instalar Typst en la imagen Docker (`docker/Dockerfile`, perfil `export`).

---

## 4. 🟢 "Texto digital" aparece como no instalado

**No es un error:** es Docling, el lector para PDFs con texto seleccionable y documentos de Office. Es opcional
porque pesa varios GB (incluye PyTorch y modelos).

**Sin Docling:** los PDF digitales se leen con OCR (funciona, pero es más lento y pierde tablas) y los archivos
de Word, Excel y PowerPoint no se pueden convertir.

**Para activarlo:** `pip install -e ".[parse]"` en `backend/` con el entorno virtual activado. La primera
conversión descarga los modelos. *(≈30 min, sobre todo descarga)*

Después de instalarlo: probar con 3 PDFs digitales y 1 Word, y compararlo con OCR en el benchmark.

---

## Orden sugerido

1. Instalar Pandoc y Typst (opción 3A). Es el arreglo más rápido y desbloquea Word y PDF.
2. Dataset de fotos (1.1) y preprocesamiento (1.2): es donde está el mayor problema de calidad.
3. Varios archivos a la vez (2).
4. Docling (4) cuando haga falta convertir documentos de Office.
