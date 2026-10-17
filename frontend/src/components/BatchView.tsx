import { zipSync } from "fflate";
import { useState } from "react";
import { fetchBlob, outputUrl, type Job, type OutputFormat } from "../lib/api";
import { FORMAT_LABEL, formatBytes, jobErrorMessage, stageLabel } from "../lib/messages";

export interface BatchItem {
  file: File;
  job: Job | null;
  error: string | null; // error al subir (red, tamaño, tipo)
}

interface Props {
  items: BatchItem[];
  output: OutputFormat;
  onOpen: (index: number) => void;
  onReset: () => void;
}

function status(item: BatchItem, output: OutputFormat): { label: string; tone: "busy" | "ok" | "error" } {
  if (item.error) return { label: item.error, tone: "error" };
  if (!item.job) return { label: "En espera", tone: "busy" };
  if (item.job.state === "succeeded") return { label: "Listo", tone: "ok" };
  if (item.job.state === "failed") return { label: jobErrorMessage(item.job.error), tone: "error" };
  return { label: stageLabel(item.job, output), tone: "busy" };
}

/** Nombre único dentro del zip: dos archivos con el mismo nombre no se pisan. */
function uniqueName(name: string, used: Set<string>): string {
  let candidate = name;
  let i = 2;
  while (used.has(candidate)) {
    const dot = name.lastIndexOf(".");
    candidate = dot > 0 ? `${name.slice(0, dot)} (${i})${name.slice(dot)}` : `${name} (${i})`;
    i++;
  }
  used.add(candidate);
  return candidate;
}

export default function BatchView({ items, output, onOpen, onReset }: Props) {
  const [zipping, setZipping] = useState(false);
  const [zipError, setZipError] = useState<string | null>(null);
  const done = items.filter((i) => i.job?.state === "succeeded");
  const finished = items.filter((i) => i.error || i.job?.state === "succeeded" || i.job?.state === "failed");
  const allFinished = finished.length === items.length;

  async function downloadZip() {
    setZipping(true);
    setZipError(null);
    try {
      const entries: Record<string, Uint8Array> = {};
      const used = new Set<string>();
      for (const item of done) {
        const name = item.job!.outputs[0];
        const blob = await fetchBlob(outputUrl(item.job!.id, name));
        entries[uniqueName(name, used)] = new Uint8Array(await blob.arrayBuffer());
      }
      const zip = zipSync(entries, { level: 6 });
      const url = URL.createObjectURL(new Blob([zip], { type: "application/zip" }));
      Object.assign(document.createElement("a"), { href: url, download: `files2md-${FORMAT_LABEL[output]}.zip` }).click();
      setTimeout(() => URL.revokeObjectURL(url), 2000);
    } catch {
      setZipError("No se pudo armar el .zip. Descarga los archivos uno por uno.");
    } finally {
      setZipping(false);
    }
  }

  return (
    <section className="batch" aria-labelledby="batch-title">
      <div className="result-head">
        <div>
          <p className="eyebrow">{allFinished ? "Conversión terminada" : "Convirtiendo"}</p>
          <h2 id="batch-title" className="result-title">
            {done.length} de {items.length} documentos listos
          </h2>
        </div>
        <div className="result-actions">
          <button
            type="button"
            className="button button-primary"
            onClick={downloadZip}
            disabled={done.length === 0 || zipping}
          >
            {zipping ? "Preparando .zip…" : `Descargar todo (.zip)`}
          </button>
        </div>
      </div>

      {zipError && <p className="notice notice-error" role="alert">{zipError}</p>}

      <ul className="batch-list" aria-live="polite">
        {items.map((item, i) => {
          const s = status(item, output);
          const progress = Math.round((item.job?.progress ?? 0) * 100);
          return (
            <li key={`${item.file.name}-${i}`} className={`batch-row is-${s.tone}`}>
              <span className="batch-dot" aria-hidden="true" />
              <div className="batch-info">
                <p className="file-name" title={item.file.name}>{item.file.name}</p>
                <p className="batch-status">
                  {formatBytes(item.file.size)} · {s.label}
                </p>
                {s.tone === "busy" && (
                  <div className="progress progress-thin" aria-hidden="true">
                    <span style={{ width: `${Math.max(progress, 4)}%` }} />
                  </div>
                )}
              </div>
              {s.tone === "ok" && (
                <div className="batch-actions">
                  <button type="button" className="button button-ghost" onClick={() => onOpen(i)}>
                    Ver
                  </button>
                  <a
                    className="button button-secondary"
                    href={outputUrl(item.job!.id, item.job!.outputs[0])}
                    download={item.job!.outputs[0]}
                  >
                    Descargar
                  </a>
                </div>
              )}
            </li>
          );
        })}
      </ul>

      <div className="result-foot">
        <button type="button" className="button button-ghost" onClick={onReset}>
          Convertir otros documentos
        </button>
      </div>
    </section>
  );
}
