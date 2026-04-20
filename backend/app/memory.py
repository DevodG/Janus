import json
from datetime import datetime
from pathlib import Path
import glob
import logging
import time
import uuid

from app.config import MEMORY_DIR, DATA_DIR

logger = logging.getLogger(__name__)

Path(MEMORY_DIR).mkdir(parents=True, exist_ok=True)

KNOWLEDGE_DIR = DATA_DIR / "knowledge"
KNOWLEDGE_DIR.mkdir(parents=True, exist_ok=True)
KNOWLEDGE_QUERY_LOG = DATA_DIR / "adaptive" / "knowledge_query_log.json"


def save_case(case_id: str, payload: dict) -> str:
    path = Path(MEMORY_DIR) / f"{case_id}.json"
    payload["saved_at"] = datetime.utcnow().isoformat()
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
    return str(path)


class KnowledgeStore:
    """
    Simple keyword match over knowledge JSON files.
    Each file is expected to be a dict or list of dicts with a 'text' field.
    Upgrade to embedding-based retrieval when ready.
    """

    def _load_query_log(self) -> list[dict]:
        if not KNOWLEDGE_QUERY_LOG.exists():
            return []
        try:
            return json.loads(KNOWLEDGE_QUERY_LOG.read_text(encoding="utf-8"))
        except Exception:
            return []

    def _save_query_log(self, entries: list[dict]) -> None:
        try:
            KNOWLEDGE_QUERY_LOG.parent.mkdir(parents=True, exist_ok=True)
            KNOWLEDGE_QUERY_LOG.write_text(
                json.dumps(entries[-100:], indent=2), encoding="utf-8"
            )
        except Exception as exc:
            logger.debug("KnowledgeStore query log save failed: %s", exc)

    def _record_query(self, query: str, domain: str, result_count: int) -> None:
        log = self._load_query_log()
        log.append(
            {
                "query": query,
                "domain": domain,
                "result_count": result_count,
                "timestamp": time.time(),
            }
        )
        self._save_query_log(log)

    def _iter_items(self) -> list[dict]:
        items: list[dict] = []
        pattern = str(KNOWLEDGE_DIR / "*.json")
        for path in glob.glob(pattern):
            try:
                data = json.loads(Path(path).read_text(encoding="utf-8"))
                if isinstance(data, list):
                    items.extend(item for item in data if isinstance(item, dict))
                elif isinstance(data, dict):
                    items.append(data)
            except Exception:
                continue
        return items

    def save_knowledge(self, item: dict) -> str:
        item_id = item.get("id") or str(uuid.uuid4())
        payload = dict(item)
        payload["id"] = item_id
        payload.setdefault("saved_at", datetime.utcnow().isoformat())
        path = KNOWLEDGE_DIR / f"{item_id}.json"
        path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        return item_id

    def list_all(self, limit: int | None = None) -> list[dict]:
        items = self._iter_items()

        def _sort_key(item: dict) -> float:
            marker = item.get("saved_at") or item.get("timestamp")
            if isinstance(marker, (int, float)):
                return float(marker)
            if isinstance(marker, str) and marker:
                try:
                    return datetime.fromisoformat(marker.replace("Z", "+00:00")).timestamp()
                except ValueError:
                    return 0.0
            return 0.0

        items.sort(
            key=_sort_key,
            reverse=True,
        )
        return items[:limit] if limit else items

    def search(
        self,
        query: str,
        domain: str = "general",
        top_k: int = 5,
        limit: int | None = None,
    ) -> list[dict]:
        results = []
        query_lower = query.lower()
        requested = limit or top_k
        for item in self._iter_items():
            item_domain = item.get("domain") or item.get("topic") or "general"
            if domain not in ("", "general") and domain not in str(item_domain).lower():
                continue
            text = " ".join(
                [
                    str(item.get("text", "")),
                    str(item.get("content", "")),
                    str(item.get("summary", "")),
                    str(item.get("title", "")),
                    str(item.get("topic", "")),
                ]
            ).lower()
            if any(word for word in query_lower.split() if word in text):
                results.append(item)
                if len(results) >= requested:
                    break

        self._record_query(query, domain, len(results))
        return results

    def get_recent_queries(self, limit: int = 20) -> list[dict]:
        return list(reversed(self._load_query_log()))[:limit]

    def get_stats(self) -> dict:
        items = self._iter_items()
        domain_counts: dict[str, int] = {}
        for item in items:
            domain = str(item.get("domain") or item.get("topic") or "general")
            domain_counts[domain] = domain_counts.get(domain, 0) + 1

        return {
            "total_queries": len(self._load_query_log()),
            "total_entities": 0,
            "total_links": 0,
            "domain_counts": domain_counts,
            "knowledge_items": len(items),
        }


knowledge_store = KnowledgeStore()
