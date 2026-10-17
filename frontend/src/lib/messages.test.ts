import { describe, expect, it } from "vitest";
import { ApiError, type Job } from "./api";
import { jobErrorMessage, lowConfidenceNotice, requestErrorMessage, stageLabel } from "./messages";

const job = (meta: Job["meta"], state: Job["state"] = "running"): Job => ({
  id: "1",
  operation: "parse.to_document",
  state,
  progress: 0.5,
  outputs: [],
  meta,
  error: null,
});

describe("stageLabel", () => {
  it("muestra la página actual cuando se conoce", () => {
    expect(stageLabel(job({ stage: "reading", engine: "ocr", page: 2, page_total: 5 }), "md")).toBe(
      "Leyendo el texto · página 2 de 5",
    );
  });

  it("nombra el formato al exportar", () => {
    expect(stageLabel(job({ stage: "exporting" }), "docx")).toBe("Preparando tu archivo Word");
  });

  it("antes de empezar", () => {
    expect(stageLabel(null, "md")).toBe("Preparando la conversión");
  });
});

describe("mensajes de error", () => {
  it("traduce errores HTTP a instrucciones", () => {
    expect(requestErrorMessage(new ApiError("x", 413), 200)).toBe("El archivo supera el máximo de 200 MB.");
    expect(requestErrorMessage(new ApiError("network", 0), 200)).toMatch(/servidor esté encendido/);
  });

  it("explica qué instalar para documentos de Office", () => {
    const backend = "RuntimeError: Ningún motor disponible para esta entrada. docling: Docling no instalado (pip install '.[parse]')";
    expect(jobErrorMessage(backend)).toMatch(/Word, Excel o PowerPoint/);
  });

  it("explica qué instalar cuando falta Tesseract", () => {
    const backend = "RuntimeError: Ningún motor disponible para esta entrada. ocr: Tesseract no está instalado o no está en el PATH";
    expect(jobErrorMessage(backend)).toMatch(/instalar Tesseract/);
  });
});

describe("lowConfidenceNotice", () => {
  it("lista las páginas dudosas", () => {
    expect(lowConfidenceNotice(job({ ocr_low_conf_pages: [3] }))).toMatch(/^Revisa la página 3/);
    expect(lowConfidenceNotice(job({ ocr_low_conf_pages: [1, 4] }))).toMatch(/^Revisa las páginas 1, 4/);
    expect(lowConfidenceNotice(job({}))).toBeNull();
  });
});
