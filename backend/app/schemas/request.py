from pydantic import BaseModel, HttpUrl, Field
from typing import Optional, List

class AnalyzeRequest(BaseModel):
    text: Optional[str] = None
    url: Optional[str] = None
    image_base64: Optional[str] = None
    source: Optional[str] = "unknown" # e.g., "sms", "whatsapp", "email"

class FeedbackRequest(BaseModel):
    analyze_id: str
    is_scam: bool
    correct_category: Optional[str] = None
    notes: Optional[str] = None

class KnowledgeIngestionRequest(BaseModel):
    """Request to ingest knowledge."""
    topics: List[str] = Field(..., description="Topics to ingest knowledge about")

class SkillDistillRequest(BaseModel):
    """Request to distill skills."""
    min_frequency: int = Field(default=3, description="Minimum pattern frequency")
