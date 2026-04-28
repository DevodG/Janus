from pydantic import BaseModel, Field
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

class KnowledgeItem(BaseModel):
    """Knowledge item with compressed content."""
    id: Optional[str] = None
    source: str = Field(..., description="Source: 'tavily_search', 'jina_reader', 'newsapi'")
    query: Optional[str] = None
    url: Optional[str] = None
    title: Optional[str] = None
    summary: str = Field(..., description="Compressed summary (2-4KB)")
    published_at: Optional[str] = None
    ingested_at: str
    saved_at: Optional[str] = None
    last_accessed: Optional[str] = None
    trust_score: Optional[float] = Field(default=0.5, ge=0.0, le=1.0)
    freshness_score: Optional[float] = Field(default=1.0, ge=0.0, le=1.0)

class Skill(BaseModel):
    """Distilled skill from execution patterns."""
    id: str
    name: str
    type: str = Field(..., description="Type: 'domain_expertise', 'preferred_source', 'agent_workflow'")
    description: str
    trigger_patterns: List[str] = Field(default_factory=list)
    recommended_agents: List[str] = Field(default_factory=list)
    preferred_sources: List[str] = Field(default_factory=list)
    expected_outcomes: List[str] = Field(default_factory=list)
    frequency: int
    confidence: float = Field(..., ge=0.0, le=1.0)
    created_at: str
    usage_count: int = 0
    success_count: int = 0
    success_rate: float = Field(default=0.0, ge=0.0, le=1.0)

class SourceTrust(BaseModel):
    """Trust score for a source."""
    source: str
    trust_score: float = Field(..., ge=0.0, le=1.0)
    verification_count: int
    success_count: int
    success_rate: float = Field(..., ge=0.0, le=1.0)
    last_updated: str

class PromptVersion(BaseModel):
    """Prompt version with A/B testing metadata."""
    id: str
    prompt_name: str
    version: int
    prompt_text: str
    goal: str
    status: str = Field(..., description="Status: 'testing', 'production', 'archived'")
    created_at: str
    test_count: int = 0
    win_count: int = 0
    win_rate: float = Field(default=0.0, ge=0.0, le=1.0)
    promoted_at: Optional[str] = None
    archived_at: Optional[str] = None

class FreshnessScore(BaseModel):
    """Freshness score for a knowledge item."""
    item_id: str
    freshness_score: float = Field(..., ge=0.0, le=1.0)
    age_days: int
    last_updated: str
