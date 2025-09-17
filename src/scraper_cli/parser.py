from __future__ import annotations
from typing import Any, Dict, List
from bs4 import BeautifulSoup
from .config import ScraperConfig

def _get_text(el) -> str:
    return (el.get_text(" ", strip=True) if el else "").strip()

def _get_attr(el, attr: str) -> str:
    if not el:
        return ""
    return (el.get(attr) or "").strip()

def extract_items(html: str, cfg: ScraperConfig) -> List[Dict[str, Any]]:
    # If item_selector provided → multi-item page; else single item/page
    soup = BeautifulSoup(html, "lxml") if "lxml" in BeautifulSoup.builder_registry.builders else BeautifulSoup(html, "html.parser")

    if cfg.item_selector:
        items = []
        for node in soup.select(cfg.item_selector):
            row: Dict[str, Any] = {}
            for rule in cfg.extract:
                target = node.select_one(rule.selector)
                if rule.type == "text":
                    row[rule.name] = _get_text(target)
                elif rule.type == "attr" and rule.attr:
                    row[rule.name] = _get_attr(target, rule.attr)
                else:
                    row[rule.name] = ""
            items.append(row)
        return items

    # single page item
    row: Dict[str, Any] = {}
    for rule in cfg.extract:
        target = soup.select_one(rule.selector)
        if rule.type == "text":
            row[rule.name] = _get_text(target)
        elif rule.type == "attr" and rule.attr:
            row[rule.name] = _get_attr(target, rule.attr)
        else:
            row[rule.name] = ""
    return [row] if row else []
