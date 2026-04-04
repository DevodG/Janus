import json
from datetime import datetime
from pathlib import Path
import glob
import logging

from app.config import MEMORY_DIR, DATA_DIR

logger = logging.getLogger(__name__)

Path(MEMORY_DIR).mkdir(parents=True, exist_ok=True)

KNOWLEDGE_DIR = DATA_DIR / "knowledge"


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

    def search(self, query: str, domain: str = "general", top_k: int = 5) -> list[dict]:
        results = []
        query_lower = query.lower()
        pattern = str(KNOWLEDGE_DIR / "*.json")
        for path in glob.glob(pattern):
            try:
                data = json.loads(Path(path).read_text())
                items = data if isinstance(data, list) else [data]
                for item in items:
                    text = str(item.get("text", item.get("content", "")))
                    if any(w in text.lower() for w in query_lower.split()):
                        results.append(item)
                        if len(results) >= top_k:
                            return results
            except Exception:
                continue
        return results


knowledge_store = KnowledgeStore()
