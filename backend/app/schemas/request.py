from pydantic import BaseModel, HttpUrl
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
