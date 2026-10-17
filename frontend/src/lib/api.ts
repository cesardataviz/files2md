export type JobState = "queued" | "running" | "succeeded" | "failed" | "cancelled";
export type OutputFormat = "md" | "docx" | "pdf";
export type EngineName = "auto" | "docling" | "ocr" | "vlm";

export interface Job {
  id: string;
  operation: string;
  state: JobState;
  progress: number;
  outputs: string[];
  meta: {
    stage?: "analyzing" | "reading" | "exporting" | "done";
    engine?: string;
    input_kind?: string;
    page?: number;
    page_total?: number;
    ocr_mean_conf?: number;
    ocr_low_conf_pages?: number[];
    [key: string]: unknown;
  };
  error: string | null;
}

export interface Availability {
  available: boolean;
  reason: string;
}

export interface Capabilities {
  max_upload_mb: number;
  accepts: string[];
  outputs: Record<OutputFormat, Availability>;
  engines: Record<Exclude<EngineName, "auto">, Availability>;
}

/** Error con el código HTTP, para poder traducirlo a un mensaje útil. */
export class ApiError extends Error {
  constructor(message: string, public status: number) {
    super(message);
  }
}

function headers(): HeadersInit {
  try {
    const token = localStorage.getItem("files2md_token");
    return token ? { Authorization: `Bearer ${token}` } : {};
  } catch {
    return {};
  }
}

async function request(url: string, init?: RequestInit): Promise<Response> {
  let r: Response;
  try {
    r = await fetch(url, { ...init, headers: { ...headers(), ...(init?.headers ?? {}) } });
  } catch {
    throw new ApiError("network", 0);
  }
  if (!r.ok) {
    const detail = (await r.json().catch(() => ({}))).detail;
    throw new ApiError(typeof detail === "string" ? detail : `HTTP ${r.status}`, r.status);
  }
  return r;
}

export async function getCapabilities(): Promise<Capabilities> {
  return (await request("/api/capabilities")).json();
}

export async function createJob(file: File, output: OutputFormat, engine: EngineName): Promise<string> {
  const form = new FormData();
  form.append("operation", "parse.to_document");
  form.append("params", JSON.stringify({ output, engine }));
  form.append("files", file);
  return (await (await request("/api/jobs", { method: "POST", body: form })).json()).job_id;
}

export async function getJob(id: string): Promise<Job> {
  return (await request(`/api/jobs/${id}`)).json();
}

export async function waitForJob(id: string, onUpdate: (job: Job) => void, signal: AbortSignal): Promise<Job> {
  for (;;) {
    if (signal.aborted) throw new DOMException("cancelado", "AbortError");
    const job = await getJob(id);
    onUpdate(job);
    if (job.state === "succeeded" || job.state === "failed") return job;
    await new Promise((res) => setTimeout(res, 600));
  }
}

export const outputUrl = (jobId: string, name: string) =>
  `/api/jobs/${jobId}/outputs/${encodeURIComponent(name)}`;

export async function fetchText(url: string): Promise<string> {
  return (await request(url)).text();
}
