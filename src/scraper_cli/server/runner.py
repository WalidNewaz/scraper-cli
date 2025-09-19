import asyncio
import json
from typing import Optional
from ..db import DB
from ..config import ScraperConfig
from ..fetcher import crawl
from .ws import WSManager

class JobRunner:
    def __init__(self, db: DB, ws: WSManager):
        self.db = db
        self.ws = ws

    async def run_job(self, job_id: int):
        job = self.db.get_job(job_id)
        if not job:
            return

        cfg = ScraperConfig.load_from_json(job["config_json"]) if hasattr(ScraperConfig, "load_from_json") else None
        if cfg is None:
            cfg = ScraperConfig.load_json_str(job["config_json"])

        # helper: allow loading from json string (add this to config.py)
        # or reconstruct like:
        # cfg = ScraperConfig(**json.loads(job["config_json"]))

        depth = job["depth"]
        max_pages = job["max_pages"]

        self.db.update_job_status(job_id, "running")
        self.db.add_job_event(job_id, "info", {"message": "job started"})

        def on_event(ev: dict):
            # store event and push via ws
            self.db.add_job_event(job_id, ev.get("type", "info"), ev)
            # fire-and-forget (no await inside sync cb)
            asyncio.create_task(self.ws.broadcast(job_id, {"job_id": job_id, **ev}))

        try:
            await crawl(cfg, self.db, max_pages=max_pages, job_id=job_id, on_event=on_event)
            self.db.update_job_status(job_id, "succeeded")
            self.db.add_job_event(job_id, "done", {"message": "job completed"})
            await self.ws.broadcast(job_id, {"type": "done", "job_id": job_id})
        except Exception as ex:
            self.db.update_job_status(job_id, "failed")
            self.db.add_job_event(job_id, "error", {"message": repr(ex)})
            await self.ws.broadcast(job_id, {"type": "error", "job_id": job_id, "message": repr(ex)})
