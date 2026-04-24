from typing import List, Dict, Any
import numpy as np
import logging
from sqlalchemy import select
from app.db.session import AsyncSessionLocal
from app.db.models import ScamEvent

logger = logging.getLogger(__name__)

class SimilarityService:
    def __init__(self):
        self.model = None
        self._initialized = False

    def _init_model(self):
        if not self._initialized:
            try:
                from sentence_transformers import SentenceTransformer
                # Using all-MiniLM-L6-v2: Fast, locally executable, 384 dimensions
                self.model = SentenceTransformer('all-MiniLM-L6-v2')
                self._initialized = True
                logger.info("Similarity model (all-MiniLM-L6-v2) loaded successfully.")
            except Exception as e:
                logger.error(f"Similarity model init failed: {e}")
                self._initialized = True # Prevent repeated retries if it fails

    async def get_embedding(self, text: str) -> List[float]:
        """Convert text to a 384-dimensional vector."""
        self._init_model()
        if not self.model:
            # Fallback mock embedding (all zeros) if model fails to load
            return [0.0] * 384
        
        try:
            # Synchronous encode wrapped in thread if needed, but usually fast enough for local
            embedding = self.model.encode(text)
            return embedding.tolist()
        except Exception as e:
            logger.error(f"Embedding generation failed: {e}")
            return [0.0] * 384

    async def find_matches(self, embedding: List[float], limit: int = 5, threshold: float = 0.3) -> List[Dict[str, Any]]:
        """
        Find nearest historical scams using pgvector cosine distance.
        Note: pgvector cosine_distance = 1 - cosine_similarity.
        So distance 0.3 means 0.7 similarity.
        """
        async with AsyncSessionLocal() as session:
            try:
                # pgvector's cosine_distance operator (<=>)
                distance_col = ScamEvent.embedding.cosine_distance(embedding)
                stmt = (
                    select(ScamEvent, distance_col)
                    .order_by(distance_col)
                    .limit(limit)
                )
                
                result = await session.execute(stmt)
                rows = result.all()
                
                matches = []
                for event, distance in rows:
                    if distance is not None and (1 - distance) < threshold:
                        continue
                        
                    matches.append({
                        "event_id": str(event.id),
                        "text": event.text[:200] + "..." if len(event.text) > 200 else event.text,
                        "source": event.source,
                        "risk_score": event.risk_score,
                        "ts": event.created_at.isoformat(),
                        "similarity": round((1 - (distance or 0)) * 100, 1)
                    })
                
                return matches
            except Exception as e:
                logger.error(f"Database vector search failed: {e}")
                return []

similarity_service = SimilarityService()
