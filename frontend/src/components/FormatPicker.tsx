import type { Availability, EngineName, OutputFormat } from "../lib/api";

const FORMATS: { id: OutputFormat; title: string; ext: string; description: string }[] = [
  { id: "md", title: "Markdown", ext: ".md", description: "Texto con formato. Ideal para notas, wikis y asistentes de IA." },
  { id: "docx", title: "Word", ext: ".docx", description: "Documento editable para seguir trabajando en Word." },
  { id: "pdf", title: "PDF ordenado", ext: ".pdf", description: "Versión limpia y legible, lista para compartir." },
];

const ENGINES: { id: EngineName; title: string; description: string }[] = [
  { id: "auto", title: "Automático", description: "Elige el mejor método según el documento. Recomendado." },
  { id: "ocr", title: "Reconocimiento de imagen (OCR)", description: "Para escaneos, fotos y PDFs sin texto seleccionable." },
  { id: "docling", title: "Texto digital", description: "Para PDFs y documentos de Office con texto seleccionable." },
];

interface Props {
  outputs: Record<OutputFormat, Availability>;
  engines: Record<string, Availability>;
  output: OutputFormat;
  engine: EngineName;
  onOutput: (o: OutputFormat) => void;
  onEngine: (e: EngineName) => void;
}

export default function FormatPicker({ outputs, engines, output, engine, onOutput, onEngine }: Props) {
  return (
    <>
      <fieldset className="choice-group">
        <legend className="field-label">¿Qué quieres obtener?</legend>
        <div className="format-grid">
          {FORMATS.map((f) => {
            const avail = outputs[f.id] ?? { available: false, reason: "No disponible" };
            return (
              <label key={f.id} className={`format-card${avail.available ? "" : " is-disabled"}`}>
                <input
                  type="radio"
                  name="output"
                  value={f.id}
                  checked={output === f.id}
                  disabled={!avail.available}
                  onChange={() => onOutput(f.id)}
                />
                <span className="format-head">
                  <span className="format-title">{f.title}</span>
                  <span className="format-ext">{f.ext}</span>
                </span>
                <span className="format-desc">
                  {avail.available ? f.description : `No disponible en esta instalación · ${avail.reason}`}
                </span>
              </label>
            );
          })}
        </div>
      </fieldset>

      <details className="advanced">
        <summary>Opciones avanzadas</summary>
        <fieldset className="choice-group">
          <legend className="field-label">Método de lectura</legend>
          {ENGINES.map((e) => {
            const avail = e.id === "auto" ? { available: true, reason: "" } : engines[e.id];
            const enabled = avail?.available ?? false;
            return (
              <label key={e.id} className={`engine-option${enabled ? "" : " is-disabled"}`}>
                <input
                  type="radio"
                  name="engine"
                  value={e.id}
                  checked={engine === e.id}
                  disabled={!enabled}
                  onChange={() => onEngine(e.id)}
                />
                <span>
                  <span className="engine-title">{e.title}</span>
                  <span className="engine-desc">{enabled ? e.description : "No instalado en este equipo."}</span>
                </span>
              </label>
            );
          })}
        </fieldset>
      </details>
    </>
  );
}
