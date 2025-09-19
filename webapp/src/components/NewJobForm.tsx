import { useState } from "react";
import { createJob } from "../api";

const defaultConfig = {
  name: "ui-scrape",
  user_agent: "UIScraper/0.1 (+https://example.com/bot)",
  concurrency: 4,
  delay_ms_min: 200,
  delay_ms_max: 500,
  max_depth: 1,
  follow_same_domain_only: true,
  respect_robots_txt: true,
  seeds: ["https://example.com"],
  extract: [
    { name: "title", selector: "title", type: "text" }
  ]
};

export default function NewJobForm({ onCreated }: { onCreated: (jobId: number) => void }) {
  const [configText, setConfigText] = useState(JSON.stringify(defaultConfig, null, 2));
  const [depth, setDepth] = useState<number | "">("");
  const [maxPages, setMaxPages] = useState<number | "">("");

  async function submit() {
    try {
      const config = JSON.parse(configText);
      const payload: any = { config };
      if (depth !== "") payload.depth = Number(depth);
      if (maxPages !== "") payload.max_pages = Number(maxPages);
      const res = await createJob(payload);
      onCreated(res.job_id);
    } catch (e) {
      alert("Invalid config JSON: " + (e as Error).message);
    }
  }

  return (
    <div style={{display:"grid", gap:12}}>
      <h2>New Crawl</h2>
      <label>Config (JSON)</label>
      <textarea value={configText} onChange={e=>setConfigText(e.target.value)} rows={14} style={{fontFamily:"monospace"}} />
      <div style={{display:"flex", gap:12}}>
        <div>
          <label>Depth (override)</label><br/>
          <input value={depth} onChange={e=>setDepth(e.target.value ? Number(e.target.value) : "")} type="number" min={0}/>
        </div>
        <div>
          <label>Max Pages</label><br/>
          <input value={maxPages} onChange={e=>setMaxPages(e.target.value ? Number(e.target.value) : "")} type="number" min={1}/>
        </div>
      </div>
      <button onClick={submit}>Start Job</button>
    </div>
  );
}
