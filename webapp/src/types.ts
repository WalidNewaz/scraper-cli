export type Job = {
  id: number; status: string; created_at: string; updated_at: string;
  depth?: number | null; max_pages?: number | null;
};

export type Event = {
  id: number; job_id: number; type: string;
  payload: Record<string, unknown>; ts: string;
};

export type ItemRow = {
  id: number; page_id: number; job_id?: number | null;
  data_json: Record<string, unknown>; created_at: string;
};
