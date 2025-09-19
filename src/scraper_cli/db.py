from __future__ import annotations
import sqlite3
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple
import json
from contextlib import contextmanager
from datetime import datetime

def _now_iso() -> str:
    return datetime.utcnow().isoformat(timespec="seconds") + "Z"

SCHEMA = """
PRAGMA journal_mode = WAL;
CREATE TABLE IF NOT EXISTS pages (
  id INTEGER PRIMARY KEY,
  url TEXT UNIQUE,
  domain TEXT,
  status INTEGER,
  etag TEXT,
  last_modified TEXT,
  content_hash TEXT,
  html TEXT,
  error TEXT,
  fetched_at TEXT,
  depth INTEGER
);
CREATE TABLE IF NOT EXISTS links (
  from_page_id INTEGER,
  to_url TEXT
);
CREATE TABLE IF NOT EXISTS items (
  id INTEGER PRIMARY KEY,
  page_id INTEGER,
  job_id INTEGER,
  data_json TEXT,
  created_at TEXT
);
CREATE TABLE IF NOT EXISTS summaries (
  id INTEGER PRIMARY KEY,
  scope TEXT,
  key TEXT,
  text TEXT,
  created_at TEXT
);
-- NEW: jobs table
CREATE TABLE IF NOT EXISTS jobs (
  id INTEGER PRIMARY KEY,
  status TEXT,                    -- queued|running|succeeded|failed|canceled
  created_at TEXT,
  updated_at TEXT,
  config_json TEXT,
  max_pages INTEGER,
  depth INTEGER
);
-- NEW: job events (append-only)
CREATE TABLE IF NOT EXISTS job_events (
  id INTEGER PRIMARY KEY,
  job_id INTEGER,
  type TEXT,                      -- info|progress|error|done
  payload TEXT,
  ts TEXT
);
"""

class DB:
    def __init__(self, path: Path):
        self.path = path
        self.conn = sqlite3.connect(path)
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(SCHEMA)
        self.conn.commit()

    def close(self):
        self.conn.close()

    def upsert_page(
        self,
        url: str,
        domain: str,
        status: Optional[int] = None,
        html: Optional[str] = None,
        etag: Optional[str] = None,
        last_modified: Optional[str] = None,
        error: Optional[str] = None,
        depth: Optional[int] = None,
        content_hash: Optional[str] = None,
    ) -> int:
        cur = self.conn.cursor()
        cur.execute("SELECT id FROM pages WHERE url = ?", (url,))
        row = cur.fetchone()
        if row:
            page_id = row["id"]
            cur.execute(
                """UPDATE pages SET domain = COALESCE(?, domain),
                    status = COALESCE(?, status),
                    etag = COALESCE(?, etag),
                    last_modified = COALESCE(?, last_modified),
                    content_hash = COALESCE(?, content_hash),
                    html = COALESCE(?, html),
                    error = COALESCE(?, error),
                    fetched_at = ?, depth = COALESCE(?, depth)
                    WHERE id = ?""",
                (
                    domain, status, etag, last_modified, content_hash, html, error,
                    _now_iso(), depth, page_id
                ),
            )
        else:
            cur.execute(
                """INSERT INTO pages(url, domain, status, etag, last_modified, content_hash,
                   html, error, fetched_at, depth)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (url, domain, status, etag, last_modified, content_hash,
                 html, error, _now_iso(), depth),
            )
            page_id = cur.lastrowid
        self.conn.commit()
        return page_id

    def get_page(self, url: str) -> Optional[sqlite3.Row]:
        cur = self.conn.cursor()
        cur.execute("SELECT * FROM pages WHERE url = ?", (url,))
        return cur.fetchone()

    def insert_links(self, from_page_id: int, to_urls: Iterable[str]) -> None:
        cur = self.conn.cursor()
        cur.executemany(
            "INSERT INTO links(from_page_id, to_url) VALUES (?, ?)",
            [(from_page_id, u) for u in to_urls]
        )
        self.conn.commit()

    # def insert_items(self, page_id: int, items: List[Dict[str, Any]]) -> None:
    #     cur = self.conn.cursor()
    #     rows = [(page_id, json.dumps(it), _now_iso()) for it in items]
    #     cur.executemany(
    #         "INSERT INTO items(page_id, data_json, created_at) VALUES (?, ?, ?)",
    #         rows
    #     )
    #     self.conn.commit()

    def insert_summary(self, scope: str, key: str, text: str) -> None:
        cur = self.conn.cursor()
        cur.execute(
            "INSERT INTO summaries(scope, key, text, created_at) VALUES (?, ?, ?, ?)",
            (scope, key, text, _now_iso())
        )
        self.conn.commit()

    def stats(self) -> Dict[str, int]:
        cur = self.conn.cursor()
        cur.execute("SELECT COUNT(*) AS c FROM pages")
        pages = cur.fetchone()["c"]
        cur.execute("SELECT COUNT(*) AS c FROM items")
        items = cur.fetchone()["c"]
        cur.execute("SELECT COUNT(*) AS c FROM summaries")
        sums = cur.fetchone()["c"]
        return {"pages": pages, "items": items, "summaries": sums}

    # --- jobs ---
    def create_job(self, config_json: str, depth: Optional[int], max_pages: Optional[int]) -> int:
        cur = self.conn.cursor()
        cur.execute(
            """INSERT INTO jobs(status, created_at, updated_at, config_json, max_pages, depth)
               VALUES (?, ?, ?, ?, ?, ?)""",
            ("queued", _now_iso(), _now_iso(), config_json, max_pages, depth)
        )
        self.conn.commit()
        return cur.lastrowid

    def update_job_status(self, job_id: int, status: str):
        cur = self.conn.cursor()
        cur.execute(
            "UPDATE jobs SET status=?, updated_at=? WHERE id=?",
            (status, _now_iso(), job_id)
        )
        self.conn.commit()

    def get_job(self, job_id: int) -> Optional[sqlite3.Row]:
        cur = self.conn.cursor()
        cur.execute("SELECT * FROM jobs WHERE id=?", (job_id,))
        return cur.fetchone()

    def list_jobs(self, limit: int = 50) -> List[sqlite3.Row]:
        cur = self.conn.cursor()
        cur.execute("SELECT * FROM jobs ORDER BY id DESC LIMIT ?", (limit,))
        return cur.fetchall()

    # --- job events ---
    def add_job_event(self, job_id: int, ev_type: str, payload: Dict[str, Any]):
        cur = self.conn.cursor()
        cur.execute(
            "INSERT INTO job_events(job_id, type, payload, ts) VALUES (?, ?, ?, ?)",
            (job_id, ev_type, json.dumps(payload), _now_iso())
        )
        self.conn.commit()

    def recent_events(self, job_id: int, after_id: Optional[int] = None, limit: int = 100):
        cur = self.conn.cursor()
        if after_id:
            cur.execute(
                "SELECT * FROM job_events WHERE job_id=? AND id>? ORDER BY id ASC LIMIT ?",
                (job_id, after_id, limit)
            )
        else:
            cur.execute(
                "SELECT * FROM job_events WHERE job_id=? ORDER BY id ASC LIMIT ?",
                (job_id, limit)
            )
        return cur.fetchall()

    # override insert_items to accept job_id
    def insert_items(self, page_id: int, items: List[Dict[str, Any]], job_id: Optional[int] = None) -> None:
        cur = self.conn.cursor()
        rows = [(page_id, job_id, json.dumps(it), _now_iso()) for it in items]
        cur.executemany(
            "INSERT INTO items(page_id, job_id, data_json, created_at) VALUES (?, ?, ?, ?)",
            rows
        )
        self.conn.commit()

