const BASE = import.meta.env.VITE_API_BASE ?? "http://localhost:8000";

export async function createJob(payload: any) {
  const r = await fetch(`${BASE}/jobs`, {
    method: "POST", headers: {"Content-Type": "application/json"},
    body: JSON.stringify(payload)
  });
  return r.json();
}

export async function listJobs() {
  const r = await fetch(`${BASE}/jobs`);
  return r.json();
}

export async function getJob(id: number) {
  const r = await fetch(`${BASE}/jobs/${id}`);
  return r.json();
}

export async function listItems(jobId?: number, limit=100) {
  const url = jobId ? `${BASE}/items?job_id=${jobId}&limit=${limit}` : `${BASE}/items?limit=${limit}`;
  const r = await fetch(url);
  return r.json();
}

export function openJobWS(jobId: number): WebSocket {
  return new WebSocket((BASE.replace(/^http/i, "ws")) + `/ws/jobs/${jobId}`);
}
