// Traduce estados y errores técnicos a lenguaje para la persona que usa la app.
import { ApiError, type Job, type OutputFormat } from "./api";

export const FORMAT_LABEL: Record<OutputFormat, string> = {
  md: "Markdown",
  docx: "Word",
  pdf: "PDF",
};

export function stageLabel(job: Job | null, output: OutputFormat): string {
  if (!job || job.state === "queued") return "Preparando la conversión";
  const { stage, page, page_total } = job.meta;
  switch (stage) {
    case "analyzing":
      return "Analizando el documento";
    case "reading":
      if (page && page_total) return `Leyendo el texto · página ${page} de ${page_total}`;
      return job.meta.engine === "ocr" ? "Leyendo el texto" : "Extrayendo el texto";
    case "exporting":
      return `Preparando tu archivo ${FORMAT_LABEL[output]}`;
    case "done":
      return "Listo";
    default:
      return "Procesando";
  }
}

export function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

export function extensionOf(name: string): string {
  const dot = name.lastIndexOf(".");
  return dot >= 0 ? name.slice(dot + 1).toLowerCase() : "";
}

/** Mensaje para errores al subir o consultar (errores HTTP o de red). */
export function requestErrorMessage(err: unknown, maxMb: number): string {
  if (err instanceof ApiError) {
    if (err.status === 0) return "No se pudo conectar con files2md. Comprueba que el servidor esté encendido.";
    if (err.status === 413) return `El archivo supera el máximo de ${maxMb} MB.`;
    if (err.status === 415) return "Este tipo de archivo no es compatible. Usa PDF, una imagen o un documento Word.";
    if (err.status === 401) return "Esta instalación pide un token de acceso.";
    return `No se pudo completar la solicitud: ${err.message}`;
  }
  return "Ocurrió un error inesperado. Vuelve a intentarlo.";
}

/** Mensaje para un job que terminó en error (el texto viene del backend). */
export function jobErrorMessage(error: string | null): string {
  const e = error ?? "";
  if (/Tesseract no está instalado/i.test(e))
    return "Para leer escaneos e imágenes hay que instalar Tesseract. La guía de instalación está en el README.";
  if (/Faltan idiomas de Tesseract/i.test(e))
    return "A Tesseract le falta el idioma español. Agrega el paquete «spa» y vuelve a intentarlo.";
  // Los PDF digitales caen a OCR si falta Docling; este error solo aparece con Word, Excel o PowerPoint.
  if (/Docling no instalado/i.test(e))
    return "Para convertir documentos de Word, Excel o PowerPoint hay que instalar el módulo de texto digital (Docling).";
  if (/Pandoc/i.test(e)) return "Para generar Word o PDF hay que instalar Pandoc. Mientras tanto, elige Markdown.";
  if (/Ningún motor disponible/i.test(e))
    return "Esta instalación no tiene un lector para este tipo de documento.";
  if (/Tipo de entrada no soportado/i.test(e)) return "Este tipo de archivo no se puede convertir.";
  return "La conversión falló. Prueba con otro archivo o revisa el registro del servidor.";
}

export function lowConfidenceNotice(job: Job): string | null {
  const pages = job.meta.ocr_low_conf_pages ?? [];
  if (pages.length === 0) return null;
  const list = pages.length === 1 ? `la página ${pages[0]}` : `las páginas ${pages.join(", ")}`;
  return `Revisa ${list}: la imagen no era muy clara y el texto podría tener errores.`;
}
