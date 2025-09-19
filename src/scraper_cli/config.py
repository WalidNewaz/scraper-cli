from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
import json
import os
from pathlib import Path

@staticmethod
def load_json_str(s: str) -> "ScraperConfig":
    data = json.loads(s)
    # (same as ScraperConfig.load but from dict)
    lf = data.get("link_filters", {}) or {}
    extracts = [ExtractRule(**e) for e in data.get("extract", [])]
    return ScraperConfig(
        name=data.get("name", "scraper"),
        user_agent=data.get("user_agent", "ScraperCLI/0.1"),
        concurrency=int(data.get("concurrency", 5)),
        delay_ms_min=int(data.get("delay_ms_min", 200)),
        delay_ms_max=int(data.get("delay_ms_max", 600)),
        max_depth=int(data.get("max_depth", 1)),
        follow_same_domain_only=bool(data.get("follow_same_domain_only", True)),
        respect_robots_txt=bool(data.get("respect_robots_txt", True)),
        allowed_domains=list(data.get("allowed_domains", [])),
        seeds=list(data.get("seeds", [])),
        link_filters=LinkFilters(
            allow_regex=lf.get("allow_regex", []) or [],
            deny_regex=lf.get("deny_regex", []) or [],
        ),
        headers=dict(data.get("headers", {})),
        item_selector=data.get("item_selector"),
        extract=extracts,
        etag_cache=bool(data.get("etag_cache", True)),
    )

@dataclass
class ExtractRule:
    name: str
    selector: str
    type: str = "text"  # "text" | "attr"
    attr: Optional[str] = None  # if type == "attr"

@dataclass
class LinkFilters:
    allow_regex: List[str] = field(default_factory=list)
    deny_regex: List[str] = field(default_factory=list)

@dataclass
class ScraperConfig:
    name: str = "scraper"
    user_agent: str = "ScraperCLI/0.1"
    concurrency: int = 5
    delay_ms_min: int = 200
    delay_ms_max: int = 600
    max_depth: int = 1
    follow_same_domain_only: bool = True
    respect_robots_txt: bool = True
    allowed_domains: List[str] = field(default_factory=list)
    seeds: List[str] = field(default_factory=list)
    link_filters: LinkFilters = field(default_factory=LinkFilters)
    headers: Dict[str, str] = field(default_factory=dict)
    item_selector: Optional[str] = None
    extract: List[ExtractRule] = field(default_factory=list)
    etag_cache: bool = True

    @staticmethod
    def load(path: Path) -> "ScraperConfig":
        data = json.loads(Path(path).read_text())
        # Simple dict→dataclass conversion
        lf = data.get("link_filters", {}) or {}
        extracts = [ExtractRule(**e) for e in data.get("extract", [])]
        return ScraperConfig(
            name=data.get("name", "scraper"),
            user_agent=data.get("user_agent", "ScraperCLI/0.1"),
            concurrency=int(data.get("concurrency", 5)),
            delay_ms_min=int(data.get("delay_ms_min", 200)),
            delay_ms_max=int(data.get("delay_ms_max", 600)),
            max_depth=int(data.get("max_depth", 1)),
            follow_same_domain_only=bool(data.get("follow_same_domain_only", True)),
            respect_robots_txt=bool(data.get("respect_robots_txt", True)),
            allowed_domains=list(data.get("allowed_domains", [])),
            seeds=list(data.get("seeds", [])),
            link_filters=LinkFilters(
                allow_regex=lf.get("allow_regex", []) or [],
                deny_regex=lf.get("deny_regex", []) or [],
            ),
            headers=dict(data.get("headers", {})),
            item_selector=data.get("item_selector"),
            extract=extracts,
            etag_cache=bool(data.get("etag_cache", True)),
        )

    def dump(self) -> str:
        def rule_to_dict(r: ExtractRule) -> Dict[str, Any]:
            d = {"name": r.name, "selector": r.selector, "type": r.type}
            if r.attr:
                d["attr"] = r.attr
            return d
        data = {
            "name": self.name,
            "user_agent": self.user_agent,
            "concurrency": self.concurrency,
            "delay_ms_min": self.delay_ms_min,
            "delay_ms_max": self.delay_ms_max,
            "max_depth": self.max_depth,
            "follow_same_domain_only": self.follow_same_domain_only,
            "respect_robots_txt": self.respect_robots_txt,
            "allowed_domains": self.allowed_domains,
            "seeds": self.seeds,
            "link_filters": {
                "allow_regex": self.link_filters.allow_regex,
                "deny_regex": self.link_filters.deny_regex,
            },
            "headers": self.headers,
            "item_selector": self.item_selector,
            "extract": [rule_to_dict(e) for e in self.extract],
            "etag_cache": self.etag_cache,
        }
        return json.dumps(data, indent=2)

def write_default_config(path: Path) -> None:
    if path.exists():
        raise FileExistsError(f"{path} already exists")
    cfg = ScraperConfig(
        seeds=["https://example.com"],
        extract=[
            ExtractRule(name="title", selector="title"),
            ExtractRule(name="h1", selector="h1"),
        ],
    )
    path.write_text(cfg.dump())
