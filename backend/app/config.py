from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="FILES2MD_", env_file=".env", extra="ignore")

    # Por defecto solo local: no expone el servicio a la red.
    host: str = "127.0.0.1"
    port: int = 8000

    data_dir: Path = Path("./data")
    max_upload_mb: int = 200
    job_ttl_hours: int = 24
    job_timeout_s: int = 600

    # "inprocess" (modo local) | "redis" (modo escalable)
    queue_backend: str = "inprocess"
    queue_workers: int = 2
    redis_url: str = "redis://redis:6379/0"

    # Auth opcional. Vacío = sin auth (solo aceptable en 127.0.0.1).
    api_token: str = ""

    # Ruta del frontend compilado (Vite). Si existe, la API lo sirve.
    frontend_dir: Path = Path("./frontend_dist")

    # OCR (Tesseract). Activo por defecto: si el binario no está instalado, el job falla con
    # un mensaje que dice qué instalar. En Windows suele estar en
    # C:\Program Files\Tesseract-OCR\tesseract.exe y no siempre queda en el PATH.
    enable_ocr: bool = True
    tesseract_cmd: str = ""  # vacío = buscar "tesseract" en el PATH
    ocr_langs: str = "spa+eng"  # idiomas de Tesseract unidos por "+"
    ocr_dpi: int = 300  # resolución al rasterizar PDFs; 300 es el estándar para OCR
    # Preprocesamiento de imagen antes del OCR: "auto" (solo imágenes/fotos), "always" u "off".
    ocr_preprocess: str = "auto"

    # VLM: apagado por defecto (opt-in explícito).
    enable_vlm: bool = False
    vlm_endpoint: str = ""  # p. ej. Ollama local: http://localhost:11434

    @property
    def uploads_dir(self) -> Path:
        return self.data_dir / "uploads"

    @property
    def outputs_dir(self) -> Path:
        return self.data_dir / "outputs"

    @property
    def db_path(self) -> Path:
        return self.data_dir / "jobs.sqlite3"


def get_settings() -> Settings:
    return Settings()
