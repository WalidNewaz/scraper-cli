import { useEffect, useRef, useState } from "react";
import { getJob, listItems, openJobWS } from "../api";
import type { ItemRow, Job } from "../types";

type Log = { ts?: string; text: string };

export default function JobDetail({ jobId }: { jobId: number }) {
  const [job, setJob] = useState<Job | null>(null);
  const [logs, setLogs] = useState<Log[]>([]);
  const [items, setItems] = useState<ItemRow[]>([]);
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    (async () => {
      setJob(await getJob(jobId));
      setItems(await listItems(jobId, 100));
    })();
    const ws = openJobWS(jobId);
    wsRef.current = ws;
    ws.onmessage = (ev) => {
      const msg = JSON.parse(ev.data);
      // simple log renderer
      if (msg.type === "page") {
        setLogs(l => [...l, { text: `Fetched ${msg.url} status=${msg.status ?? "?"} depth=${msg.depth}` }]);
      } else if (msg.type === "items") {
        setLogs(l => [...l, { text: `Extracted ${msg.count} items` }]);
        // refresh items opportunistically
        listItems(jobId, 100).then(setItems);
      } else if (msg.type === "done") {
        setLogs(l => [...l, { text: `Job done` }]);
        getJob(jobId).then(setJob);
        listItems(jobId, 100).then(setItems);
      } else if (msg.type === "error") {
        setLogs(l => [...l, { text: `Error: ${msg.message}` }]);
        getJob(jobId).then(setJob);
      }
    };
    ws.onclose = () => { /* noop */ };
    return () => { ws.close(); };
  }, [jobId]);

  return (
    <div style={{display:"grid", gap:12}}>
      <h2>Job #{jobId}</h2>
      <div>Status: <b>{job?.status}</b></div>

      <div style={{display:"grid", gridTemplateColumns:"1fr 1fr", gap:16}}>
        <div>
          <h3>Live Log</h3>
          <div style={{border:"1px solid #ddd", padding:8, height:280, overflow:"auto", fontFamily:"monospace"}}>
            {logs.map((l,i)=><div key={i}>{l.text}</div>)}
          </div>
        </div>
        <div>
          <h3>Items (latest)</h3>
          <div style={{border:"1px solid #ddd", padding:8, height:280, overflow:"auto"}}>
            <table>
              <thead><tr><th>ID</th><th>Data</th><th>Created</th></tr></thead>
              <tbody>
                {items.map(r=>(
                  <tr key={r.id}>
                    <td>{r.id}</td>
                    <td><code style={{fontSize:"12px"}}>{JSON.stringify(r.data_json)}</code></td>
                    <td>{r.created_at}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}
