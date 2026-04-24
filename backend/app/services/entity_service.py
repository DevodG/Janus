import re
from typing import Dict, List
from app.schemas.response import ExtractedEntities

class EntityService:
    def __init__(self):
        self.patterns = {
            "phones": [
                r'[\+\d]?\d{10,12}',
                r'\b\d{5}\s\d{5}\b'
            ],
            "upi_ids": r'[a-zA-Z0-9\.\-_]{2,256}@[a-zA-Z]{2,64}',
            "crypto_addresses": r'\b(bc1|[13])[a-zA-HJ-NP-Z0-9]{25,39}\b', # Bitcoin
            "domains": r'(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+(?:com|net|org|xyz|io|top|loan|biz|win|tk|ml|ga)',
            "bank_accounts": r'\b\d{9,18}\b', # Generic Indian bank account range
            "brands": r'\b(Paytm|PhonePe|GPay|Amazon|Flipkart|SBI|HDFC|ICICI|Netflix|Microsoft|Google|Apple|FedEx|BlueDart|IRCTC)\b'
        }

    async def extract(self, text: str) -> ExtractedEntities:
        extracted = {
            "phones": [], "upi_ids": [], "domains": [], "brands": [], "crypto": [], "accounts": []
        }
        
        for key, patterns in self.patterns.items():
            if isinstance(patterns, str):
                patterns = [patterns]
            
            for pattern in patterns:
                matches = re.findall(pattern, text, re.IGNORECASE)
                if key == "phones": extracted["phones"].extend(matches)
                elif key == "upi_ids": extracted["upi_ids"].extend(matches)
                elif key == "domains": extracted["domains"].extend(matches)
                elif key == "brands": extracted["brands"].extend(matches)
                elif key == "crypto_addresses": extracted["crypto"].extend(matches)
                elif key == "bank_accounts": extracted["accounts"].extend(matches)

        # Deduplicate
        return ExtractedEntities(
            phones=list(set(extracted["phones"])),
            domains=list(set(extracted["domains"])),
            upi_ids=list(set(extracted["upi_ids"])),
            brands=list(set(extracted["brands"]))
            # Note: response schema doesn't have crypto/accounts yet, 
            # I should update schemas/response.py for true depth.
        )

entity_service = EntityService()
