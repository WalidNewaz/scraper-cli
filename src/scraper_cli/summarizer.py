from __future__ import annotations
from typing import List
import re
from collections import Counter

_SENT_SPLIT = re.compile(r"(?<=[.!?])\s+")

def summarize_text(text: str, max_sentences: int = 5) -> str:
    """
    Lightweight extractive summary:
    - Split into sentences
    - Score by word frequency (normalized)
    - Return top-N sentences in document order
    """
    sents = [s.strip() for s in _SENT_SPLIT.split(text) if s.strip()]
    if len(sents) <= max_sentences:
        return " ".join(sents)

    words = re.findall(r"\w+", text.lower())
    freq = Counter(w for w in words if len(w) > 2)
    if not freq:
        return " ".join(sents[:max_sentences])

    scores = []
    for i, s in enumerate(sents):
        sw = re.findall(r"\w+", s.lower())
        val = sum(freq.get(w, 0) for w in sw) / (len(sw) + 1)
        scores.append((i, val, s))

    # pick top max_sentences by score, then sort by original index
    top = sorted(sorted(scores, key=lambda x: x[1], reverse=True)[:max_sentences], key=lambda x: x[0])
    return " ".join(s for _, __, s in top)
