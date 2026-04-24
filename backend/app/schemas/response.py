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

class EvidenceItem(BaseModel):
    source: str
    signal: str
    value: Optional[Any] = None
    severity: str
    explanation: str

class OfficialVerify(BaseModel):
    brand: Optional[str] = None
    instruction: str
    official_site: Optional[str] = None

class AnalyzeResponse(BaseModel):
    id: str
    text: str
    source: str
    risk_score: float
    decision: str # "BLOCK", "WARN", "ALLOW"
    reasons: List[str]
    intent: IntentScore
    entities: ExtractedEntities
    evidence: List[EvidenceItem] = []
    claimed_brand: Optional[str] = None
    official_verify: Optional[OfficialVerify] = None
    next_steps: List[str] = []
    similarity: Optional[Dict[str, Any]] = None
    timeline_link: Optional[str] = None
    breadcrumbs: List[str] = []
    verdict_synthesis: Optional[str] = None

class LearningStatusResponse(BaseModel):
    enabled: bool
    storage: Dict[str, Any]
    last_run: Dict[str, str]

class LearningInsightsResponse(BaseModel):
    recent_knowledge: List[Dict[str, Any]]
    storage_stats: Dict[str, Any]
