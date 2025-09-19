import { useEffect, useState } from "react";
import { listJobs } from "../api";
import type { Job } from "../types";

export default function JobsTable({ onSelect }: { onSelect: (id: number)=>void }) {
  const [jobs, setJobs] = useState<Job[]>([]);
  useEffect(() => { (async () => setJobs(await listJobs()))(); }, []);
  return (
    <div>
      <h2>Jobs</h2>
      <table>
        <thead><tr><th>ID</th><th>Status</th><th>Created</th><th>Updated</th><th>Depth</th><th>Max Pages</th></tr></thead>
        <tbody>
          {jobs.map(j => (
            <tr key={j.id} onClick={()=>onSelect(j.id)} style={{cursor:"pointer"}}>
              <td>{j.id}</td><td>{j.status}</td><td>{j.created_at}</td><td>{j.updated_at}</td><td>{j.depth ?? ""}</td><td>{j.max_pages ?? ""}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
