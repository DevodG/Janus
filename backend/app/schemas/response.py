from pydantic import BaseModel
from typing import List, Dict, Optional, Any

class IntentScore(BaseModel):
    urgency: float
    impersonation: float
    payment: float
    fear: float

class ExtractedEntities(BaseModel):
    phones: List[str]
    domains: List[str]
    upi_ids: List[str]
    brands: List[str]
    crypto: List[str] = []
    accounts: List[str] = []

class AnalyzeResponse(BaseModel):
    id: str
    text: str
    source: str
    risk_score: float
    decision: str # "BLOCK", "WARN", "ALLOW"
    reasons: List[str]
    intent: IntentScore
    entities: ExtractedEntities
    similarity: Optional[Dict[str, Any]] = None
    timeline_link: Optional[str] = None
