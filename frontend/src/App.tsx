import { useState } from "react";
import { createJob, outputUrl, waitForJob, type Job } from "./lib/api";

const ENGINES = ["auto", "docling", "ocr", "vlm"] as const;
const OUTPUTS = ["md", "docx", "pdf"] as const;

// Esqueleto funcional. Pendiente: vista previa lado a lado (original vs Markdown) y diff.
export default function App() {
  const [file, setFile] = useState<File | null>(null);
  const [engine, setEngine] = useState<string>("auto");
  const [output, setOutput] = useState<string>("md");
  const [job, setJob] = useState<Job | null>(null);
  const [error, setError] = useState<string | null>(null);
  const busy = job?.state === "queued" || job?.state === "running";

  async function run() {
    if (!file) return;
    setError(null);
    setJob(null);
    try {
      const id = await createJob("parse.to_document", [file], { engine, output });
      setJob(await waitForJob(id, setJob));
    } catch (e) {
      setError(String(e));
    }
  }

  return (
    <main style={{ maxWidth: 760, margin: "2rem auto", fontFamily: "system-ui", padding: "0 1rem" }}>
      <h1>files2md</h1>
      <p>PDF, imagen o documento Office → Markdown, Word o PDF ordenado. Todo se procesa en tu máquina.</p>

      <input type="file" onChange={(e) => setFile(e.target.files?.[0] ?? null)} />
      <p>
        <label>Motor{" "}
          <select value={engine} onChange={(e) => setEngine(e.target.value)}>
            {ENGINES.map((x) => <option key={x}>{x}</option>)}
          </select>
        </label>{" "}
        <label>Salida{" "}
          <select value={output} onChange={(e) => setOutput(e.target.value)}>
            {OUTPUTS.map((x) => <option key={x}>{x}</option>)}
          </select>
        </label>
      </p>
      <button onClick={run} disabled={!file || busy}>Convertir</button>

      {error && <p style={{ color: "crimson" }}>{error}</p>}
      {job && (
        <section>
          <p>
            Estado: <b>{job.state}</b> ({Math.round(job.progress * 100)}%)
            {job.error && <span style={{ color: "crimson" }}> — {job.error}</span>}
          </p>
          {job.outputs.map((o) => (
            <p key={o}><a href={outputUrl(job, o)}>Descargar {o}</a></p>
          ))}
          {Object.keys(job.meta).length > 0 && (
            <pre style={{ background: "#f4f4f4", padding: 8 }}>{JSON.stringify(job.meta, null, 2)}</pre>
          )}
        </section>
      )}
    </main>
  );
}
