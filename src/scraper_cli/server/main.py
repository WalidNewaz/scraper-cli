from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from .models import CreateJobRequest, JobDTO, EventDTO, ItemRow
from ..db import DB
from ..config import ScraperConfig
from .ws import WSManager
from .runner import JobRunner
from pathlib import Path
import asyncio
import json
from typing import List

DB_PATH = Path("scraper.db")

app = FastAPI(title="Scraper Service", version="0.1")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # dev friendly; tighten later
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

ws_manager = WSManager()
db = DB(DB_PATH)
runner = JobRunner(db, ws_manager)

@app.on_event("shutdown")
def _shutdown():
    db.close()

@app.get("/health")
def health():
    return {"ok": True}

@app.post("/jobs")
async def create_job(req: CreateJobRequest):
    cfg_json = json.dumps(req.config)
    job_id = db.create_job(cfg_json, req.depth, req.max_pages)
    # immediately schedule
    asyncio.create_task(runner.run_job(job_id))
    return {"job_id": job_id}

@app.get("/jobs", response_model=List[JobDTO])
def list_jobs():
    rows = db.list_jobs(100)
    out = []
    for r in rows:
        out.append(JobDTO(
            id=r["id"], status=r["status"], created_at=r["created_at"],
            updated_at=r["updated_at"], depth=r["depth"], max_pages=r["max_pages"]
        ))
    return out

@app.get("/jobs/{job_id}", response_model=JobDTO)
def get_job(job_id: int):
    r = db.get_job(job_id)
    if not r:
        return {"detail": "not found"}
    return JobDTO(
        id=r["id"], status=r["status"], created_at=r["created_at"],
        updated_at=r["updated_at"], depth=r["depth"], max_pages=r["max_pages"]
    )

@app.get("/jobs/{job_id}/events", response_model=List[EventDTO])
def get_events(job_id: int, after_id: int = 0, limit: int = 100):
    rows = db.recent_events(job_id, after_id=after_id, limit=limit)
    out = []
    for r in rows:
        out.append(EventDTO(
            id=r["id"], job_id=r["job_id"], type=r["type"],
            payload=json.loads(r["payload"]), ts=r["ts"]
        ))
    return out

@app.get("/items")
def list_items(job_id: int | None = None, limit: int = 100):
    cur = db.conn.cursor()
    if job_id:
        cur.execute("SELECT id, page_id, job_id, data_json, created_at FROM items WHERE job_id=? ORDER BY id DESC LIMIT ?", (job_id, limit))
    else:
        cur.execute("SELECT id, page_id, job_id, data_json, created_at FROM items ORDER BY id DESC LIMIT ?", (limit,))
    rows = cur.fetchall()
    return [
        {
            "id": r["id"], "page_id": r["page_id"], "job_id": r["job_id"],
            "data_json": json.loads(r["data_json"]), "created_at": r["created_at"]
        }
        for r in rows
    ]

@app.websocket("/ws/jobs/{job_id}")
async def ws_job_updates(ws: WebSocket, job_id: int):
    await ws_manager.connect(job_id, ws)
    try:
        while True:
            # keep-alive: we don't require client messages; just receive to detect disconnects
            await ws.receive_text()
    except WebSocketDisconnect:
        await ws_manager.disconnect(job_id, ws)
