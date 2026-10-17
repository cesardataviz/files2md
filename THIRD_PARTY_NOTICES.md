# Third-party notices

**Estado: borrador. Verificar cada licencia en su repositorio oficial antes de publicar o distribuir imágenes.**

| Componente | Uso | Licencia (a verificar) | Cómo se usa |
|---|---|---|---|
| FastAPI, Pydantic, Uvicorn | API | MIT / BSD | Dependencia Python |
| pypdf | Clasificación de PDFs | BSD | Dependencia Python |
| Pillow | Imágenes | HPND (permisiva) | Dependencia Python |
| Docling | Parsing digital | MIT | Dependencia opcional (`parse`) |
| mistune | Analizar Markdown para exportar | BSD-3-Clause | Dependencia Python |
| python-docx | Markdown→Word | MIT | Dependencia Python |
| typst (paquete de pip, incluye el compilador y sus fuentes) | Markdown→PDF | Apache-2.0 (fuentes: OFL) | Dependencia Python |
| Tesseract y sus modelos de idioma (tessdata) | OCR | Apache-2.0 | Proceso externo; se instala aparte o en imagen `full` |
| opencv-python-headless, numpy | Preprocesar fotos antes del OCR | Apache-2.0 / BSD-3-Clause | Dependencia Python |
| pypdfium2 (PDFium) | Rasterizar PDFs para OCR | Apache-2.0 / BSD-3-Clause | Dependencia Python |
| rapidfuzz | Distancia de edición en el benchmark | MIT | Dependencia opcional (`bench`) |
| React, Vite | Frontend | MIT | Dependencia frontend |
| marked | Markdown → HTML en la vista previa | MIT | Dependencia frontend |
| fflate | Armar el .zip de varios archivos en el navegador | MIT | Dependencia frontend |
| DOMPurify | Sanitiza el HTML de la vista previa | MPL-2.0 o Apache-2.0 | Dependencia frontend |
| Bricolage Grotesque, Instrument Sans, JetBrains Mono (@fontsource) | Tipografías de la interfaz | OFL-1.1 | Empaquetadas con el frontend |

## Evitados deliberadamente (el repo es MIT)

- **PyMuPDF**: AGPL (o licencia comercial). Incompatible con mantener el proyecto bajo MIT.
- **Marker / Surya**: código y pesos con restricciones para uso comercial.

Regla para añadir dependencias: solo licencias permisivas (MIT, BSD, Apache-2.0, MPL-2.0) enlazadas como librería.
Herramientas GPL/AGPL únicamente como proceso externo y revisando antes. Verificar también la licencia
de los **pesos** de cualquier modelo, que puede diferir de la del código.
