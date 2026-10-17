import type { Job, OutputFormat } from "../lib/api";
import { stageLabel } from "../lib/messages";
import Breakable from "./Breakable";
import ScanPage from "./ScanPage";

interface Props {
  fileName: string;
  job: Job | null;
  output: OutputFormat;
}

export default function Processing({ fileName, job, output }: Props) {
  const progress = Math.round((job?.progress ?? 0) * 100);
  const total = job?.meta.page_total ?? 0;
  const done = job?.meta.page ?? 0;

  return (
    <section className="processing" aria-labelledby="processing-title">
      <ScanPage active />
      <div className="processing-body">
        <p className="eyebrow">Convirtiendo</p>
        <h2 id="processing-title" className="processing-file" title={fileName}>
          <Breakable text={fileName} />
        </h2>
        <p className="processing-stage" aria-live="polite">
          {stageLabel(job, output)}
        </p>
        <div
          className="progress"
          role="progressbar"
          aria-valuemin={0}
          aria-valuemax={100}
          aria-valuenow={progress}
          aria-label="Progreso de la conversión"
        >
          <span style={{ width: `${Math.max(progress, 4)}%` }} />
        </div>
        {total > 1 && (
          <ol className="page-dots" aria-label={`${done} de ${total} páginas leídas`}>
            {Array.from({ length: Math.min(total, 40) }, (_, i) => (
              <li key={i} className={i < done ? "is-done" : i === done ? "is-current" : ""} />
            ))}
          </ol>
        )}
        <p className="processing-note">
          Tu archivo no sale de esta computadora. Una página escaneada tarda unos segundos.
        </p>
      </div>
    </section>
  );
}
