from __future__ import annotations
import asyncio
import random
from typing import Dict, List, Optional, Set, Tuple
from urllib.parse import urlparse
import httpx
from bs4 import BeautifulSoup
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, TimeElapsedColumn
import urllib.robotparser as robotparser
from .utils import domain_of, absolutize, compile_patterns, any_match, hash_text
from .db import DB
from .config import ScraperConfig

class RobotsCache:
    def __init__(self):
        self._cache: Dict[str, robotparser.RobotFileParser] = {}

    async def allowed(self, client: httpx.AsyncClient, url: str, user_agent: str) -> bool:
        netloc = domain_of(url)
        if netloc not in self._cache:
            rp = robotparser.RobotFileParser()
            robots_url = f"{urlparse(url).scheme}://{netloc}/robots.txt"
            try:
                r = await client.get(robots_url, timeout=10.0)
                rp.parse(r.text.splitlines())
            except Exception:
                # If robots cannot be fetched, be conservative and allow only if config disables respect_robots
                rp.parse([])
            self._cache[netloc] = rp
        return self._cache[netloc].can_fetch(user_agent, url)

async def fetch_one(
    client: httpx.AsyncClient,
    db: DB,
    cfg: ScraperConfig,
    url: str,
    depth: int,
    robots: RobotsCache,
) -> Tuple[str, Optional[str], Optional[int], Optional[str], Optional[str], Optional[str]]:
    # Returns (url, html, status, etag, last_modified, error)
    headers = {"User-Agent": cfg.user_agent, **(cfg.headers or {})}
    # ETag / Last-Modified caching
    etag = None
    last_modified = None
    prior = db.get_page(url)
    req_headers = dict(headers)
    if cfg.etag_cache and prior:
        if prior["etag"]:
            req_headers["If-None-Match"] = prior["etag"]
        if prior["last_modified"]:
            req_headers["If-Modified-Since"] = prior["last_modified"]

    # robots
    if cfg.respect_robots_txt:
        allowed = await robots.allowed(client, url, cfg.user_agent)
        if not allowed:
            return (url, None, 999, None, None, "Blocked by robots.txt")

    try:
        r = await client.get(url, headers=req_headers, timeout=httpx.Timeout(10.0, read=20.0), follow_redirects=True)
        status = r.status_code
        etag = r.headers.get("ETag")
        last_modified = r.headers.get("Last-Modified")
        html = None
        if status == 304 and prior and prior["html"]:
            html = prior["html"]
        elif 200 <= status < 300:
            # basic content-type check
            ct = r.headers.get("Content-Type", "")
            if "text/html" in ct or "application/xhtml+xml" in ct or ct == "":
                html = r.text
        return (url, html, status, etag, last_modified, None)
    except Exception as ex:
        return (url, None, None, None, None, repr(ex))

def extract_links(base_url: str, html: str) -> List[str]:
    # soup = BeautifulSoup(html, "lxml") if "lxml" in BeautifulSoup.builder_registry.builders else BeautifulSoup(html, "html.parser")
    soup = BeautifulSoup(html, 'html.parser')
    out = []
    for a in soup.find_all("a", href=True):
        out.append(absolutize(base_url, a["href"]))

    return out

def extract_domain_filtered(
    urls: List[str],
    base_domain: str,
    same_domain_only: bool,
    allowed_domains: List[str],
    allow_patterns, deny_patterns
) -> List[str]:
    filtered = []
    for u in urls:
        d = domain_of(u)
        if same_domain_only and d != base_domain:
            continue
        if allowed_domains and d not in allowed_domains:
            continue
        if deny_patterns and any_match(deny_patterns, u):
            continue
        if allow_patterns and not any_match(allow_patterns, u):
            continue
        filtered.append(u)
    return filtered

async def crawl(cfg: ScraperConfig, db: DB, max_pages: Optional[int] = None):
    visited: Set[str] = set()
    to_visit: List[Tuple[str, int]] = [(s, 0) for s in cfg.seeds]
    robots = RobotsCache()
    allow_pat = compile_patterns(cfg.link_filters.allow_regex)
    deny_pat = compile_patterns(cfg.link_filters.deny_regex)

    limits = httpx.Limits(max_keepalive_connections=cfg.concurrency, max_connections=cfg.concurrency)
    async with httpx.AsyncClient(limits=limits, http2=True) as client:
        with Progress(
            SpinnerColumn(),
            TextColumn("[bold]Crawling[/bold]"),
            BarColumn(),
            TextColumn("{task.completed}/{task.total} pages"),
            TimeElapsedColumn(),
            expand = True,
        ) as progress:
            all_links = {item[0] for item in to_visit}
            task = progress.add_task("crawl", total=len(all_links))
            sem = asyncio.Semaphore(cfg.concurrency)

            async def worker(url: str, depth: int):
                nonlocal visited
                nonlocal all_links
                if max_pages and progress.tasks[0].completed >= max_pages:
                    return
                if url in visited:
                    return
                visited.add(url)
                base_domain = domain_of(url)
                await asyncio.sleep(random.uniform(cfg.delay_ms_min, cfg.delay_ms_max) / 1000.0)
                async with sem:
                    (u, html, status, etag, last_modified, error) = await fetch_one(
                        client, db, cfg, url, depth, robots
                    )
                content_hash = None
                page_id = db.upsert_page(
                    url=u, domain=base_domain, status=status, html=html,
                    etag=etag, last_modified=last_modified, error=error,
                    depth=depth, content_hash=content_hash
                )
                progress.update(task, advance=1)
                # Extract links and queue
                if html and depth < cfg.max_depth:
                    links = extract_links(u, html)
                    links = extract_domain_filtered(
                        links, base_domain, cfg.follow_same_domain_only,
                        cfg.allowed_domains, allow_pat, deny_pat
                    )
                    db.insert_links(page_id, links)
                    for ln in links:
                        if (not max_pages) or (progress.tasks[0].completed + len(to_visit) < max_pages):
                            to_visit.append((ln, depth + 1))

                    all_links.update(links)
                    progress.update(task, total=len(all_links))  # Update the total number of items in progress

                # Extract items per config now (page-time parsing)
                if html and cfg.extract:
                    from .parser import extract_items
                    items = extract_items(html, cfg)
                    if items:
                        db.insert_items(page_id, items)

            while to_visit and (not max_pages or progress.tasks[0].completed < max_pages):
                url, depth = to_visit.pop(0)
                try:
                    await worker(url, depth)
                except Exception as ex:
                    # best-effort continuity
                    db.upsert_page(url=url, domain=domain_of(url), error=repr(ex), depth=depth)

