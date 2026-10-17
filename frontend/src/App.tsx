import { useEffect, useRef, useState } from "react";
import DropZone from "./components/DropZone";
import FileCard from "./components/FileCard";
import FormatPicker from "./components/FormatPicker";
import Header from "./components/Header";
import Processing from "./components/Processing";
import Result from "./components/Result";
import {
  createJob,
  getCapabilities,
  waitForJob,
  type Capabilities,
  type EngineName,
  type Job,
  type OutputFormat,
} from "./lib/api";
import { extensionOf, jobErrorMessage, requestErrorMessage } from "./lib/messages";

type Phase = "pick" | "processing" | "result" | "failed";

const STEPS = ["Sube tu documento", "Elige el formato", "Descarga el resultado"];

export default function App() {
  const [caps, setCaps] = useState<Capabilities | null>(null);
  const [capsError, setCapsError] = useState<string | null>(null);
  const [phase, setPhase] = useState<Phase>("pick");
  const [file, setFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState("");
  const [output, setOutput] = useState<OutputFormat>("md");
  const [engine, setEngine] = useState<EngineName>("auto");
  const [job, setJob] = useState<Job | null>(null);
  const [error, setError] = useState<string | null>(null);
  const abort = useRef<AbortController | null>(null);

  useEffect(() => {
    getCapabilities()
      .then(setCaps)
      .catch((e) => setCapsError(requestErrorMessage(e, 0)));
  }, []);

  // La vista previa del original se genera en el navegador: no hace falta volver a pedirlo al servidor.
  useEffect(() => {
    if (!file) return;
    const url = URL.createObjectURL(file);
    setPreviewUrl(url);
    return () => URL.revokeObjectURL(url);
  }, [file]);

  const maxMb = caps?.max_upload_mb ?? 200;

  function chooseFile(f: File) {
    setError(null);
    if (caps && !caps.accepts.includes(extensionOf(f.name))) {
      setError("Este tipo de archivo no es compatible. Usa PDF, una imagen o un documento Word.");
      return;
    }
    if (f.size > maxMb * 1024 * 1024) {
      setError(`El archivo supera el máximo de ${maxMb} MB.`);
      return;
    }
    setFile(f);
  }

  async function convert() {
    if (!file) return;
    setError(null);
    setJob(null);
    setPhase("processing");
    abort.current?.abort();
    abort.current = new AbortController();
    try {
      const id = await createJob(file, output, engine);
      const finished = await waitForJob(id, setJob, abort.current.signal);
      setJob(finished);
      if (finished.state === "succeeded") {
        setPhase("result");
      } else {
        setError(jobErrorMessage(finished.error));
        setPhase("failed");
      }
    } catch (e) {
      if (e instanceof DOMException && e.name === "AbortError") return;
      setError(requestErrorMessage(e, maxMb));
      setPhase("failed");
    }
  }

  function reset() {
    abort.current?.abort();
    setFile(null);
    setJob(null);
    setError(null);
    setPhase("pick");
  }

  const step = phase === "result" ? 2 : file ? 1 : 0;

  return (
    <div className="app">
      <Header />
      <main className="main">
        {phase === "pick" && (
          <div className="intro">
            <div className="intro-copy">
              <h1 className="headline">
                De escaneo a <em>texto editable</em>, sin salir de tu computadora.
              </h1>
              <p className="lede">
                Sube un PDF, una foto o un documento escaneado y recíbelo como Markdown, Word o un PDF ordenado.
              </p>
              <ol className="steps">
                {STEPS.map((s, i) => (
                  <li key={s} className={i === step ? "is-current" : i < step ? "is-done" : ""}>
                    <span className="step-num">{i + 1}</span>
                    {s}
                  </li>
                ))}
              </ol>
            </div>

            <div className="panel">
              {capsError && <p className="notice notice-error" role="alert">{capsError}</p>}
              {!file ? (
                <DropZone accepts={caps?.accepts ?? []} maxMb={maxMb} onFile={chooseFile} />
              ) : (
                <div className="setup">
                  <FileCard file={file} onChange={() => setFile(null)} />
                  {caps && (
                    <FormatPicker
                      outputs={caps.outputs}
                      engines={caps.engines}
                      output={output}
                      engine={engine}
                      onOutput={setOutput}
                      onEngine={setEngine}
                    />
                  )}
                  <button type="button" className="button button-primary button-wide" onClick={convert}>
                    Convertir documento
                  </button>
                </div>
              )}
              {error && <p className="notice notice-error" role="alert">{error}</p>}
            </div>
          </div>
        )}

        {phase === "processing" && file && <Processing fileName={file.name} job={job} output={output} />}

        {phase === "result" && file && job && (
          <Result file={file} previewUrl={previewUrl} job={job} output={output} onReset={reset} />
        )}

        {phase === "failed" && (
          <section className="failure" aria-labelledby="failure-title">
            <p className="eyebrow eyebrow-error">No se pudo convertir</p>
            <h2 id="failure-title" className="failure-title">
              {error}
            </h2>
            {file && <FileCard file={file} />}
            <div className="failure-actions">
              <button type="button" className="button button-primary" onClick={() => setPhase("pick")}>
                Cambiar opciones
              </button>
              <button type="button" className="button button-ghost" onClick={reset}>
                Elegir otro archivo
              </button>
            </div>
          </section>
        )}
      </main>
      <footer className="footer">
        <span>files2md · código abierto con licencia MIT</span>
        <a href="/docs">API para desarrolladores</a>
      </footer>
    </div>
  );
}
