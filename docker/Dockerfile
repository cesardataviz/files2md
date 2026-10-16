# syntax=docker/dockerfile:1
# Capas: lite -> export -> full. Los pesos de modelos NO van en la imagen (volumen + descarga en primer uso).

# ---- build del frontend ----
FROM node:22-slim AS frontend
WORKDIR /fe
COPY frontend/package*.json ./
RUN npm install
COPY frontend/ ./
RUN npm run build

# ---- lite: API + Docling (PDF digital / Office -> Markdown) ----
FROM python:3.12-slim AS lite
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY backend/pyproject.toml ./pyproject.toml
COPY backend/app ./app
RUN pip install --no-cache-dir ".[parse]"
COPY --from=frontend /fe/dist ./frontend_dist
RUN useradd -m appuser && mkdir -p /data && chown appuser /data
USER appuser
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

# ---- export: + Pandoc (docx) ----
FROM lite AS export
USER root
RUN apt-get update && apt-get install -y --no-install-recommends pandoc \
    && rm -rf /var/lib/apt/lists/*
# TODO: instalar Typst (binario oficial, versión y checksum fijados) para exportar a PDF.
USER appuser

# ---- full: + OCR (dependencias definitivas tras el benchmark) ----
FROM export AS full
USER root
RUN apt-get update && apt-get install -y --no-install-recommends tesseract-ocr tesseract-ocr-spa tesseract-ocr-eng \
    && rm -rf /var/lib/apt/lists/*
USER appuser
