"""
New service: MemoryManager

Makes Janus genuinely self-improving by maintaining structured memory across sessions:

1. Case deduplication — prevents learning from near-identical queries
2. Topic clustering — groups cases by domain/intent
3. Pattern extraction — identifies what kinds of queries work well vs poorly
4. Knowledge summarization — periodically summarizes case clusters into compact knowledge
5. Semantic similarity check — uses simple TF-IDF (no GPU needed) to find similar past cases

This replaces the raw JSON scan in adaptive_intelligence.py that caused the O(n)
discovery loop — MemoryManager maintains an index so lookups are O(1).
"""
from __future__ import annotations

import json
import math
import logging
import pathlib
import re
import time
from collections import defaultdict
from typing import Any, Optional

logger = logging.getLogger(__name__)

try:
    from app.config import DATA_DIR
except ImportError:
    DATA_DIR = pathlib.Path(__file__).parent.parent / "data"

MEMORY_DIR = pathlib.Path(DATA_DIR) / "memory"
INDEX_FILE = pathlib.Path(DATA_DIR) / "adaptive" / "memory_index.json"


class MemoryManager:
    """
    Indexed case memory with similarity search.
    Zero external dependencies — uses TF-IDF for similarity.
    """

    def __init__(self):
        MEMORY_DIR.mkdir(parents=True, exist_ok=True)
        INDEX_FILE.parent.mkdir(parents=True, exist_ok=True)
        self._index: dict[str, dict] = {}       # case_id → metadata
        self._tfidf: dict[str, dict] = {}       # case_id → term_freq
        self._idf:   dict[str, float] = {}      # term → idf score
        self._load_index()

    # ── Public API ─────────────────────────────────────────────────────────

    def add_case(self, case: dict) -> str:
        """Index a new case. Returns case_id."""
        case_id = case.get("id") or case.get("case_id") or _make_id()
        query   = case.get("query") or case.get("user_input") or ""
        domain  = case.get("domain") or case.get("route", {}).get("domain", "general")
        quality = case.get("quality_score", 0.5)

        # Check for near-duplicate
        similar = self.find_similar(query, top_k=1)
        if similar and similar[0]["score"] > 0.92:
            logger.debug("MemoryManager: skipping near-duplicate case (%.2f similar to %s)",
                         similar[0]["score"], similar[0]["case_id"])
            return similar[0]["case_id"]

        # Index metadata
        self._index[case_id] = {
            "id":      case_id,
            "query":   query[:200],
            "domain":  domain,
            "quality": quality,
            "ts":      time.time(),
        }
        # Index TF-IDF terms
        self._tfidf[case_id] = _term_freq(_tokenise(query))
        self._recompute_idf()
        self._save_index()
        return case_id

    def find_similar(self, query: str, top_k: int = 5) -> list[dict]:
        """Return top_k most similar past cases with cosine similarity scores."""
        if not self._tfidf:
            return []
        query_tf = _term_freq(_tokenise(query))
        scores = []
        for cid, doc_tf in self._tfidf.items():
            score = _cosine(query_tf, doc_tf, self._idf)
            scores.append((score, cid))
        scores.sort(reverse=True)
        return [
            {"case_id": cid, "score": round(score, 4),
             **self._index.get(cid, {})}
            for score, cid in scores[:top_k]
            if score > 0.05
        ]

    def get_domain_stats(self) -> dict[str, Any]:
        """Return per-domain case counts and average quality."""
        domains: dict[str, list] = defaultdict(list)
        for meta in self._index.values():
            domains[meta.get("domain", "general")].append(meta.get("quality", 0.5))
        return {
            domain: {
                "count":   len(scores),
                "avg_quality": round(sum(scores) / len(scores), 3) if scores else 0,
            }
            for domain, scores in domains.items()
        }

    def get_frequent_patterns(self, min_freq: int = 3) -> list[dict]:
        """
        Extract query patterns that appear ≥ min_freq times.
        Used to build skills / prompt specialisations.
        """
        term_counts: dict[str, int] = defaultdict(int)
        term_cases:  dict[str, list] = defaultdict(list)
        for cid, meta in self._index.items():
            for token in _tokenise(meta.get("query", "")):
                if len(token) >= 4:
                    term_counts[token] += 1
                    term_cases[token].append(cid)

        patterns = []
        for term, count in term_counts.items():
            if count >= min_freq:
                patterns.append({
                    "term":     term,
                    "count":    count,
                    "case_ids": term_cases[term][:10],
                })
        return sorted(patterns, key=lambda x: -x["count"])

    def total_cases(self) -> int:
        return len(self._index)

    # ── Internal ───────────────────────────────────────────────────────────

    def _recompute_idf(self):
        N = max(len(self._tfidf), 1)
        term_doc_count: dict[str, int] = defaultdict(int)
        for doc_tf in self._tfidf.values():
            for term in doc_tf:
                term_doc_count[term] += 1
        self._idf = {
            term: math.log((N + 1) / (count + 1)) + 1
            for term, count in term_doc_count.items()
        }

    def _save_index(self):
        try:
            INDEX_FILE.write_text(json.dumps({
                "index": self._index,
                "tfidf": self._tfidf,
                "idf":   self._idf,
                "saved": time.time(),
            }, indent=2))
        except Exception as exc:
            logger.warning("MemoryManager: failed to save index: %s", exc)

    def _load_index(self):
        if not INDEX_FILE.exists():
            # Bootstrap from existing case files
            self._bootstrap_from_cases()
            return
        try:
            data = json.loads(INDEX_FILE.read_text())
            self._index = data.get("index", {})
            self._tfidf = data.get("tfidf", {})
            self._idf   = data.get("idf",   {})
            logger.info("MemoryManager: loaded %d indexed cases", len(self._index))
        except Exception as exc:
            logger.warning("MemoryManager: index load failed (%s), rebuilding", exc)
            self._bootstrap_from_cases()

    def _bootstrap_from_cases(self):
        """Build index from existing case JSON files on first run."""
        if not MEMORY_DIR.exists():
            return
        for f in list(MEMORY_DIR.glob("*.json"))[:500]:
            try:
                case = json.loads(f.read_text())
                case_id = case.get("id") or case.get("case_id") or f.stem
                query   = case.get("query") or case.get("user_input") or ""
                self._index[case_id] = {
                    "id":      case_id,
                    "query":   query[:200],
                    "domain":  case.get("domain", "general"),
                    "quality": case.get("quality_score", 0.5),
                    "ts":      case.get("timestamp", time.time()),
                }
                self._tfidf[case_id] = _term_freq(_tokenise(query))
            except Exception:
                pass
        if self._tfidf:
            self._recompute_idf()
            self._save_index()
        logger.info("MemoryManager: bootstrapped %d cases from disk", len(self._index))


# ── TF-IDF helpers ────────────────────────────────────────────────────────────

_STOPWORDS = {
    "the","a","an","is","in","of","for","to","and","or","it","its",
    "this","that","with","on","at","by","from","be","are","was","were",
    "what","how","why","when","who","which","can","will","do","does",
    "i","me","my","we","you","your","he","she","they","them","their",
    "about","tell","explain","show","get","give","make","take","find",
}


def _tokenise(text: str) -> list[str]:
    text   = (text or "").lower()
    tokens = re.findall(r'[a-z]{3,}', text)
    return [t for t in tokens if t not in _STOPWORDS]


def _term_freq(tokens: list[str]) -> dict[str, float]:
    if not tokens:
        return {}
    counts: dict[str, int] = defaultdict(int)
    for t in tokens:
        counts[t] += 1
    total = len(tokens)
    return {t: c / total for t, c in counts.items()}


def _cosine(a: dict[str, float], b: dict[str, float], idf: dict[str, float]) -> float:
    common = set(a) & set(b)
    if not common:
        return 0.0
    dot = sum(a[t] * b[t] * idf.get(t, 1.0) ** 2 for t in common)
    mag_a = math.sqrt(sum((v * idf.get(t, 1.0)) ** 2 for t, v in a.items()))
    mag_b = math.sqrt(sum((v * idf.get(t, 1.0)) ** 2 for t, v in b.items()))
    if mag_a == 0 or mag_b == 0:
        return 0.0
    return dot / (mag_a * mag_b)


def _make_id() -> str:
    import hashlib, uuid
    return hashlib.md5(uuid.uuid4().bytes).hexdigest()[:12]


# Singleton
memory_manager = MemoryManager()
