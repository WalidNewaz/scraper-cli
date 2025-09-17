from __future__ import annotations
from urllib.parse import urlparse, urljoin
from typing import Iterable, List, Tuple, Optional
import hashlib
import re

def domain_of(url: str) -> str:
    return urlparse(url).netloc.lower()

def absolutize(base_url: str, href: str) -> str:
    return urljoin(base_url, href)

def hash_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8", "ignore")).hexdigest()

def compile_patterns(patterns: Iterable[str]) -> List[re.Pattern]:
    return [re.compile(p) for p in patterns or []]

def any_match(patterns: List[re.Pattern], text: str) -> bool:
    return any(p.search(text) for p in patterns)
