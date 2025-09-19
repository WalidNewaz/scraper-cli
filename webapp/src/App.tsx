import { useState } from "react";
import NewJobForm from "./components/NewJobForm";
import JobsTable from "./components/JobsTable";
import JobDetail from "./components/JobDetail";

export default function App() {
  const [selectedJob, setSelectedJob] = useState<number | null>(null);
  return (
    <div style={{maxWidth:1200, margin:"0 auto", padding:16, display:"grid", gap:24}}>
      <h1>Scraper Control Panel</h1>
      <NewJobForm onCreated={setSelectedJob} />
      <JobsTable onSelect={setSelectedJob} />
      {selectedJob && <JobDetail jobId={selectedJob} />}
    </div>
  );
}
