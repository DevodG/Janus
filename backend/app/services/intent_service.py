import re
from typing import Dict
from app.schemas.response import IntentScore

class IntentService:
    def __init__(self):
        self.keywords = {
            "urgency": ["urgent", "immediately", "today", "seconds", "minute", "deadline", "expire", "limited time", "now"],
            "impersonation": ["bank", "support", "official", "gov", "police", "customs", "delivery", "kyc", "admin", "team", "security"],
            "payment": ["pay", "transfer", "upi", "bank account", "wallet", "cash", "money", "transaction", "fee", "bill"],
            "fear": ["blocked", "suspended", "legal", "arrest", "court", "penalty", "fine", "police", "unauthorized", "locked"]
        }

    async def detect(self, text: str) -> IntentScore:
        text_lower = text.lower()
        scores = {}
        
        for category, kws in self.keywords.items():
            matches = sum(1 for kw in kws if kw in text_lower)
            # Basic normalization: 0.1 per match up to 1.0
            scores[category] = min(matches * 0.15, 1.0)
            
        return IntentScore(
            urgency=scores.get("urgency", 0.0),
            impersonation=scores.get("impersonation", 0.0),
            payment=scores.get("payment", 0.0),
            fear=scores.get("fear", 0.0)
        )

intent_service = IntentService()
