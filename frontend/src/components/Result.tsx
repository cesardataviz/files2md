import { useEffect, useMemo, useState } from "react";
import { fetchText, outputUrl, type Job, type OutputFormat } from "../lib/api";
import { renderMarkdown } from "../lib/markdown";
import { extensionOf, FORMAT_LABEL, lowConfidenceNotice, photoTipNotice } from "../lib/messages";
import Breakable from "./Breakable";

interface Props {
  file: File;
  job: Job;
  output: OutputFormat;
  onReset: () => void;
  resetLabel?: string;
}

type Tab = "preview" | "source";

export default function Result({ file, job, output, onReset, resetLabel = "Convertir otro documento" }: Props) {
  // La vista previa del original se genera en el navegador: no hace falta volver a pedirlo al servidor.
  const [previewUrl, setPreviewUrl] = useState("");
  useEffect(() => {
    const url = URL.createObjectURL(file);
    setPreviewUrl(url);
    return () => URL.revokeObjectURL(url);
  }, [file]);
  const [markdown, setMarkdown] = useState<string | null>(null);
  const [loadError, setLoadError] = useState(false);
  const [tab, setTab] = useState<Tab>("preview");
  const [copied, setCopied] = useState(false);

  const mainName = job.outputs[0];
  const mdName = job.outputs.find((o) => o.endsWith(".md"));

  useEffect(() => {
    if (!mdName) return;
    fetchText(outputUrl(job.id, mdName))
      .then(setMarkdown)
      .catch(() => setLoadError(true));
  }, [job.id, mdName]);

  const html = useMemo(() => (markdown ? renderMarkdown(markdown) : ""), [markdown]);
  const notices = [lowConfidenceNotice(job), photoTipNotice(job)].filter((n): n is string => n !== null);
  const ext = extensionOf(file.name);
  const isPdf = ext === "pdf";
  const isImage = ["jpg", "jpeg", "png", "webp", "bmp", "gif"].includes(ext);

  async function copy() {
    if (!markdown) return;
    try {
      await navigator.clipboard.writeText(markdown);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      setTab("source"); // sin permiso de portapapeles: mostrar el texto para copiarlo a mano
    }
  }

  return (
    <section className="result" aria-labelledby="result-title">
      <div className="result-head">
        <div>
          <p className="eyebrow eyebrow-success">
            <svg viewBox="0 0 16 16" aria-hidden="true">
              <path d="m3.5 8.5 3 3 6-7" />
            </svg>
            Conversión lista
          </p>
          <h2 id="result-title" className="result-title" title={mainName}>
            <Breakable text={mainName} />
          </h2>
        </div>
        <div className="result-actions">
          <a className="button button-primary" href={outputUrl(job.id, mainName)} download={mainName}>
            Descargar {FORMAT_LABEL[output]}
          </a>
          {output !== "md" && mdName && (
            <a className="button button-secondary" href={outputUrl(job.id, mdName)} download={mdName}>
              Descargar Markdown
            </a>
          )}
          <button type="button" className="button button-secondary" onClick={copy} disabled={!markdown}>
            {copied ? "Texto copiado" : "Copiar texto"}
          </button>
        </div>
      </div>

      <p className="visually-hidden" aria-live="polite">
        {copied ? "Texto copiado al portapapeles" : ""}
      </p>

      {notices.map((n) => (
        <p key={n} className="notice notice-warn" role="status">
          <svg viewBox="0 0 20 20" aria-hidden="true">
            <path d="M10 3 2 17h16zM10 8v4M10 14.5v.01" />
          </svg>
          {n}
        </p>
      ))}

      <div className="compare">
        <figure className="pane">
          <figcaption className="pane-head">
            <span className="pane-title">Original</span>
            <span className="pane-meta">{file.name}</span>
          </figcaption>
          <div className="pane-body pane-original">
            {isPdf && previewUrl && <iframe src={previewUrl} title={`Documento original: ${file.name}`} />}
            {isImage && previewUrl && <img src={previewUrl} alt={`Documento original: ${file.name}`} />}
            {!isPdf && !isImage && <p className="pane-empty">La vista previa no está disponible para este tipo de archivo.</p>}
          </div>
        </figure>

        <figure className="pane">
          <figcaption className="pane-head">
            <span className="pane-title">Resultado</span>
            <span className="tabs" role="tablist" aria-label="Forma de ver el resultado">
              <button type="button" role="tab" aria-selected={tab === "preview"} onClick={() => setTab("preview")}>
                Vista
              </button>
              <button type="button" role="tab" aria-selected={tab === "source"} onClick={() => setTab("source")}>
                Markdown
              </button>
            </span>
          </figcaption>
          <div className="pane-body" role="tabpanel">
            {loadError && <p className="pane-empty">No se pudo cargar la vista previa. El archivo sí está listo para descargar.</p>}
            {!loadError && markdown === null && <p className="pane-empty">Cargando vista previa…</p>}
            {markdown !== null && tab === "preview" && (
              <article className="prose" dangerouslySetInnerHTML={{ __html: html }} />
            )}
            {markdown !== null && tab === "source" && <pre className="source">{markdown}</pre>}
          </div>
        </figure>
      </div>

      <div className="result-foot">
        <button type="button" className="button button-ghost" onClick={onReset}>
          {resetLabel}
        </button>
      </div>
    </section>
  );
}
