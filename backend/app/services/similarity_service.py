from typing import List, Dict, Any
import numpy as np

class SimilarityService:
    def __init__(self):
        self.model = None
        self._initialized = False

    def _init_model(self):
        if not self._initialized:
            try:
                from sentence_transformers import SentenceTransformer
                self.model = SentenceTransformer('all-MiniLM-L6-v2')
                self._initialized = True
            except Exception as e:
                print(f"Similarity model init failed: {e}")

    async def get_embedding(self, text: str) -> List[float]:
        self._init_model()
        if not self.model:
            # Fallback mock embedding
            return [0.0] * 384
        
        embedding = self.model.encode(text)
        return embedding.tolist()

    async def find_matches(self, embedding: List[float], threshold: float = 0.8) -> List[Dict[str, Any]]:
        # This will query pgvector in Phase 3
        return []

similarity_service = SimilarityService()
