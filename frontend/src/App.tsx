import { useEffect, useRef, useState } from "react";
import BatchView, { type BatchItem } from "./components/BatchView";
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

type Phase = "pick" | "processing" | "result" | "failed" | "batch";

const STEPS = ["Sube tus documentos", "Elige el formato", "Descarga el resultado"];
// Cada archivo es una conversión independiente; el servidor procesa 2 a la vez y el resto espera en cola.
const MAX_FILES = 20;

export default function App() {
  const [caps, setCaps] = useState<Capabilities | null>(null);
  const [capsError, setCapsError] = useState<string | null>(null);
  const [phase, setPhase] = useState<Phase>("pick");
  const [files, setFiles] = useState<File[]>([]);
  const [output, setOutput] = useState<OutputFormat>("md");
  const [engine, setEngine] = useState<EngineName>("auto");
  const [job, setJob] = useState<Job | null>(null);
  const [batch, setBatch] = useState<BatchItem[]>([]);
  const [openIndex, setOpenIndex] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const abort = useRef<AbortController | null>(null);
  const addMore = useRef<HTMLInputElement>(null);

  useEffect(() => {
    getCapabilities()
      .then(setCaps)
      .catch((e) => setCapsError(requestErrorMessage(e, 0)));
  }, []);

  const maxMb = caps?.max_upload_mb ?? 200;

  function addFiles(incoming: File[]) {
    setError(null);
    const rejected: string[] = [];
    const valid = incoming.filter((f) => {
      const ok = (!caps || caps.accepts.includes(extensionOf(f.name))) && f.size <= maxMb * 1024 * 1024;
      if (!ok) rejected.push(f.name);
      return ok;
    });
    const next = [...files, ...valid];
    if (next.length > MAX_FILES) {
      setError(`Puedes convertir hasta ${MAX_FILES} archivos a la vez. Se agregaron los primeros ${MAX_FILES}.`);
    } else if (rejected.length) {
      setError(`No se agregaron (tipo no compatible o más de ${maxMb} MB): ${rejected.join(", ")}`);
    }
    setFiles(next.slice(0, MAX_FILES));
  }

  function removeFile(index: number) {
    setFiles((prev) => prev.filter((_, i) => i !== index));
  }

  async function convertOne(file: File) {
    setJob(null);
    setPhase("processing");
    const signal = (abort.current = new AbortController()).signal;
    try {
      const id = await createJob(file, output, engine);
      const finished = await waitForJob(id, setJob, signal);
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

  async function convertMany(list: File[]) {
    const signal = (abort.current = new AbortController()).signal;
    setBatch(list.map((file) => ({ file, job: null, error: null })));
    setOpenIndex(null);
    setPhase("batch");
    const update = (i: number, patch: Partial<BatchItem>) =>
      setBatch((prev) => prev.map((item, j) => (j === i ? { ...item, ...patch } : item)));

    await Promise.all(
      list.map(async (file, i) => {
        try {
          const id = await createJob(file, output, engine);
          await waitForJob(id, (j) => update(i, { job: j }), signal);
        } catch (e) {
          if (e instanceof DOMException && e.name === "AbortError") return;
          update(i, { error: requestErrorMessage(e, maxMb) });
        }
      }),
    );
  }

  function convert() {
    if (files.length === 0) return;
    setError(null);
    abort.current?.abort();
    if (files.length === 1) void convertOne(files[0]);
    else void convertMany(files);
  }

  function reset() {
    abort.current?.abort();
    setFiles([]);
    setJob(null);
    setBatch([]);
    setOpenIndex(null);
    setError(null);
    setPhase("pick");
  }

  const step = phase === "result" || phase === "batch" ? 2 : files.length ? 1 : 0;
  const opened = openIndex !== null ? batch[openIndex] : null;

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
                Sube PDFs, fotos o documentos escaneados y recíbelos como Markdown, Word o un PDF ordenado.
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
              {files.length === 0 ? (
                <DropZone accepts={caps?.accepts ?? []} maxMb={maxMb} maxFiles={MAX_FILES} onFiles={addFiles} />
              ) : (
                <div className="setup">
                  <div className="file-list">
                    {files.map((f, i) => (
                      <FileCard
                        key={`${f.name}-${i}`}
                        file={f}
                        onChange={() => removeFile(i)}
                        changeLabel={files.length > 1 ? "Quitar" : "Cambiar"}
                      />
                    ))}
                    {files.length < MAX_FILES && (
                      <button type="button" className="button button-ghost add-more" onClick={() => addMore.current?.click()}>
                        + Agregar más archivos
                      </button>
                    )}
                    <input
                      ref={addMore}
                      type="file"
                      multiple
                      hidden
                      accept={(caps?.accepts ?? []).map((e) => `.${e}`).join(",")}
                      onChange={(e) => {
                        addFiles(Array.from(e.target.files ?? []));
                        e.target.value = "";
                      }}
                    />
                  </div>
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
                    {files.length === 1 ? "Convertir documento" : `Convertir ${files.length} documentos`}
                  </button>
                </div>
              )}
              {error && <p className="notice notice-error" role="alert">{error}</p>}
            </div>
          </div>
        )}

        {phase === "processing" && files[0] && <Processing fileName={files[0].name} job={job} output={output} />}

        {phase === "result" && files[0] && job && (
          <Result file={files[0]} job={job} output={output} onReset={reset} />
        )}

        {phase === "batch" && !opened && (
          <BatchView items={batch} output={output} onOpen={setOpenIndex} onReset={reset} />
        )}

        {phase === "batch" && opened?.job && (
          <Result
            file={opened.file}
            job={opened.job}
            output={output}
            onReset={() => setOpenIndex(null)}
            resetLabel="← Volver a la lista"
          />
        )}

        {phase === "failed" && (
          <section className="failure" aria-labelledby="failure-title">
            <p className="eyebrow eyebrow-error">No se pudo convertir</p>
            <h2 id="failure-title" className="failure-title">
              {error}
            </h2>
            {files[0] && <FileCard file={files[0]} />}
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
        <span>files2md · un producto de Softcom · código abierto con licencia MIT</span>
        <a href="/docs">API para desarrolladores</a>
      </footer>
    </div>
  );
}
