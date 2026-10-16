export type JobState = "queued" | "running" | "succeeded" | "failed" | "cancelled";

export interface Job {
  id: string;
  operation: string;
  state: JobState;
  progress: number;
  outputs: string[];
  meta: Record<string, unknown>;
  error: string | null;
}

export interface OperationInfo {
  name: string;
  description: string;
  accepts: string[];
  min_inputs: number;
  max_inputs: number;
  profile: "lite" | "office" | "full";
}

const headers = (): HeadersInit => {
  const token = localStorage.getItem("files2md_token");
  return token ? { Authorization: `Bearer ${token}` } : {};
};

export async function listOperations(): Promise<OperationInfo[]> {
  const r = await fetch("/api/operations", { headers: headers() });
  if (!r.ok) throw new Error(`Error ${r.status} al listar operaciones`);
  return r.json();
}

export async function createJob(
  operation: string,
  files: File[],
  params: Record<string, unknown> = {},
): Promise<string> {
  const form = new FormData();
  form.append("operation", operation);
  form.append("params", JSON.stringify(params));
  files.forEach((f) => form.append("files", f));
  const r = await fetch("/api/jobs", { method: "POST", body: form, headers: headers() });
  if (!r.ok) throw new Error((await r.json().catch(() => ({}))).detail ?? `Error ${r.status}`);
  return (await r.json()).job_id;
}

export async function waitForJob(id: string, onProgress?: (j: Job) => void): Promise<Job> {
  for (;;) {
    const r = await fetch(`/api/jobs/${id}`, { headers: headers() });
    if (!r.ok) throw new Error(`Error ${r.status} consultando el job`);
    const job: Job = await r.json();
    onProgress?.(job);
    if (job.state === "succeeded" || job.state === "failed") return job;
    await new Promise((res) => setTimeout(res, 500));
  }
}

export const outputUrl = (job: Job, name: string) => `/api/jobs/${job.id}/outputs/${encodeURIComponent(name)}`;
