"""
Lightweight model distillation from Kaggle datasets.
"""

import json
import os
import csv
import logging
from typing import List, Dict, Tuple, Optional
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

class KnowledgeDistiller:
    """Distills datasets into lightweight domain models."""
    
    def __init__(self, data_dir: Optional[str] = None):
        if data_dir is None:
            from app.config import DATA_DIR
            self.data_dir = Path(DATA_DIR)
        else:
            self.data_dir = Path(data_dir)
            
        self.models_dir = self.data_dir / "distilled_models"
        self.models_dir.mkdir(parents=True, exist_ok=True)
    
    def distill_dataset_to_model(
        self,
        dataset_path: str,
        domain: str,
        model_name: str,
        max_size_kb: int = 500
    ) -> Dict:
        """Extract and compress dataset into lightweight domain model."""
        logger.info(f"Distilling {dataset_path} for {domain}...")
        
        # 1. Extract QA pairs
        qa_pairs = self._extract_qa_pairs(dataset_path, domain)
        if not qa_pairs:
            logger.warning(f"No QA pairs extracted from {dataset_path}")
            return {}

        # 2. Rank by relevance
        ranked_qa = self._rank_qa_pairs(qa_pairs, domain)
        
        # 3. Select within size constraint
        compressed_qa = self._compress_to_size_limit(ranked_qa, max_size_kb)
        
        # 4. Create model
        model = {
            "name": model_name,
            "domain": domain,
            "created_at": datetime.now().isoformat(),
            "qa_pairs": compressed_qa,
            "metadata": {
                "total_extracted": len(qa_pairs),
                "selected_pairs": len(compressed_qa),
                "avg_relevance": sum(p.get("relevance", 0) for p in compressed_qa) / len(compressed_qa) if compressed_qa else 0,
                "size_kb": self._estimate_size_kb(compressed_qa),
            }
        }
        
        # 5. Save model
        model_path = self.models_dir / f"{domain}_primary.json"
        with open(model_path, 'w') as f:
            json.dump(model, f, separators=(',', ':'))
        
        logger.info(f"✓ Model saved to {model_path} ({model['metadata']['size_kb']} KB)")
        return model["metadata"]

    def load_model(self, domain: str) -> Optional[Dict]:
        """Load distilled model from disk."""
        model_path = self.models_dir / f"{domain}_primary.json"
        if not model_path.exists():
            return None
        try:
            with open(model_path) as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load model {domain}: {e}")
            return None

    def query_model(self, model: Dict, query: str, top_k: int = 3) -> List[str]:
        """Query a distilled model for relevant insights."""
        qa_pairs = model.get("qa_pairs", [])
        if not qa_pairs:
            return []

        query_words = set(query.lower().split())
        stop_words = {"what", "is", "the", "how", "does", "of", "in", "for", "a", "an", "to", "and", "or", "on", "with", "are", "do", "you", "tell", "me", "about"}
        query_words = query_words - stop_words
        
        if not query_words:
            return []
            
        scored = []
        for pair in qa_pairs:
            q_text = pair.get("question", "").lower()
            q_words = set(q_text.split())
            
            # Simple keyword overlap (excluding stop words from QA as well)
            overlap = len(query_words & (q_words - stop_words))
            
            if overlap > 0:
                # Weight by overlap and relevance
                score = overlap * pair.get("relevance", 0.5)
                scored.append((pair.get("answer"), score))
        
        # Sort and return top unique answers
        scored.sort(key=lambda x: x[1], reverse=True)
        seen = set()
        results = []
        for ans, _ in scored:
            if ans not in seen:
                results.append(ans)
                seen.add(ans)
                if len(results) >= top_k:
                    break
        return results

    def _extract_qa_pairs(self, dataset_path: str, domain: str) -> List[Dict]:
        """Walk through files and extract QA pairs."""
        qa_pairs = []
        for root, _, files in os.walk(dataset_path):
            for file in files:
                file_path = os.path.join(root, file)
                try:
                    if file.endswith('.csv'):
                        qa_pairs.extend(self._extract_from_csv(file_path))
                    elif file.endswith('.json'):
                        qa_pairs.extend(self._extract_from_json(file_path))
                except Exception as e:
                    logger.debug(f"Skipping {file}: {e}")
        return qa_pairs

    def _extract_from_csv(self, path: str) -> List[Dict]:
        pairs = []
        with open(path, encoding='utf-8', errors='ignore') as f:
            reader = csv.DictReader(f)
            # Find columns that look like Q&A or key metrics
            cols = reader.fieldnames or []
            q_col = next((c for c in cols if any(k in c.lower() for k in ['question', 'title', 'name', 'indicator'])), None)
            a_col = next((c for c in cols if any(k in c.lower() for k in ['answer', 'desc', 'value', 'price'])), None)
            
            if q_col and a_col:
                for row in reader:
                    q, a = row.get(q_col), row.get(a_col)
                    if q and a and len(str(q)) > 5:
                        pairs.append({"question": str(q), "answer": str(a)})
        return pairs

    def _extract_from_json(self, path: str) -> List[Dict]:
        pairs = []
        with open(path, encoding='utf-8', errors='ignore') as f:
            data = json.load(f)
            if isinstance(data, list):
                for item in data:
                    if isinstance(item, dict):
                        q = item.get('question') or item.get('q') or item.get('title')
                        a = item.get('answer') or item.get('a') or item.get('content')
                        if q and a:
                            pairs.append({"question": str(q), "answer": str(a)})
        return pairs

    def _rank_qa_pairs(self, pairs: List[Dict], domain: str) -> List[Dict]:
        keywords = {
            "finance": ["stock", "price", "market", "revenue", "earnings", "valuation", "ratio", "dividend"],
            "tech": ["software", "algorithm", "platform", "cloud", "ai", "latency", "architecture"],
            "healthcare": ["drug", "efficacy", "trial", "patient", "disease", "treatment", "medical"],
        }.get(domain, [])

        for p in pairs:
            text = (p['question'] + " " + p['answer']).lower()
            matches = sum(1 for k in keywords if k in text)
            p["relevance"] = min(1.0, 0.2 + (matches * 0.2))
        
        return sorted(pairs, key=lambda x: x["relevance"], reverse=True)

    def _compress_to_size_limit(self, pairs: List[Dict], max_kb: int) -> List[Dict]:
        selected = []
        current_size = 0
        for p in pairs:
            # Estimate size: roughly length of JSON string
            size = len(json.dumps(p)) / 1024
            if current_size + size <= max_kb:
                selected.append(p)
                current_size += size
            else:
                break
        return selected

    def _estimate_size_kb(self, pairs: List[Dict]) -> float:
        return len(json.dumps(pairs).encode('utf-8')) / 1024
