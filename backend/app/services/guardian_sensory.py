"""
ZeroTrust Guardian Sensory Hub — OCR, Link Intelligence, and Document Forensics.
Part of the Janus Scam Journey Guardian Milestone 1.
"""

import os
import re
import logging
from typing import Dict, List, Any, Optional
import sys

# Dynamic site-packages discovery (Janus sensory standard)
py_version = f"python{sys.version_info.major}.{sys.version_info.minor}"
site_pkgs = os.path.join(sys.prefix, "lib", py_version, "site-packages")
if site_pkgs not in sys.path:
    sys.path.append(site_pkgs)

logger = logging.getLogger(__name__)

# Lazy imports for heavy dependencies
reader = None
fitz = None # PyMuPDF
whois = None

class GuardianSensory:
    def __init__(self):
        self._ocr_initialized = False
        self._doc_initialized = False
        
        # Scam pattern triggers
        self.scam_keywords = {
            "urgency": ["urgent", "immediately", "today", "seconds", "minute", "deadline", "expire"],
            "fear": ["blocked", "suspended", "legal", "arrest", "court", "penalty", "fine", "police"],
            "reward": ["winner", "lottery", "cashback", "refund", "gift", "lucky", "claim"],
            "authority": ["bank", "support", "official", "gov", "police", "customs", "delivery", "kyc"]
        }
        
        # Risky TLDs
        self.risky_tlds = [".xyz", ".top", ".top", ".loan", ".win", ".bid", ".gift", ".zip", ".mov"]

    def _init_ocr(self):
        global reader
        if not self._ocr_initialized:
            try:
                import easyocr
                # Initialize reader for English (lean setup)
                reader = easyocr.Reader(['en'], gpu=False)
                self._ocr_initialized = True
                logger.info("[GUARDIAN-SENSORY] OCR Brain initialized.")
            except Exception as e:
                logger.error(f"[GUARDIAN-SENSORY] OCR Init Fail: {e}")

    def _init_doc(self):
        global fitz
        if not self._doc_initialized:
            try:
                import fitz
                self._doc_initialized = True
                logger.info("[GUARDIAN-SENSORY] Document Forensic Brain initialized.")
            except Exception as e:
                logger.error(f"[GUARDIAN-SENSORY] Doc Init Fail: {e}")

    def analyze_screenshot(self, image_path: str) -> Dict[str, Any]:
        """Extract text and detect scam intent from an image."""
        self._init_ocr()
        if not reader:
            return {"error": "OCR Engine unavailable"}

        try:
            results = reader.readtext(image_path)
            full_text = " ".join([res[1] for res in results])
            
            # Analyze intent
            signals = self._detect_signals(full_text)
            entities = self._extract_entities(full_text)
            
            return {
                "text": full_text,
                "signals": signals,
                "entities": entities,
                "risk_score": self._compute_risk(signals)
            }
        except Exception as e:
            logger.error(f"[GUARDIAN-SENSORY] OCR Analysis Fail: {e}")
            return {"error": str(e)}

    def analyze_url(self, url: str) -> Dict[str, Any]:
        """Perform heuristic phishing analysis on a URL."""
        risk_score = 0
        reasons = []
        
        # 1. TLD Check
        tld = "." + url.split(".")[-1].split("/")[0]
        if tld in self.risky_tlds:
            risk_score += 30
            reasons.append(f"Risky TLD detected: {tld}")
            
        # 2. Typosquatting Check (Logic bits)
        brand_spoofs = ["micros0ft", "g00gle", "amzn", "paypa1", "app1e"]
        for spoof in brand_spoofs:
            if spoof in url.lower():
                risk_score += 50
                reasons.append(f"Potential brand spoofing detected: {spoof}")
                
        # 3. Protocol Check
        if url.startswith("http://"):
            risk_score += 20
            reasons.append("Non-secure protocol (HTTP) used for potential scam link")
            
        return {
            "url": url,
            "risk_score": min(risk_score, 100),
            "reasons": reasons,
            "level": "HIGH" if risk_score >= 70 else "MEDIUM" if risk_score >= 30 else "LOW"
        }

    def analyze_document(self, pdf_path: str) -> Dict[str, Any]:
        """Extract scam patterns from a PDF document."""
        self._init_doc()
        if not fitz:
            return {"error": "Doc Engine unavailable"}

        try:
            doc = fitz.open(pdf_path)
            full_text = ""
            for page in doc:
                full_text += page.get_text()
            
            signals = self._detect_signals(full_text)
            return {
                "text_preview": full_text[:500],
                "signals": signals,
                "risk_score": self._compute_risk(signals)
            }
        except Exception as e:
            logger.error(f"[GUARDIAN-SENSORY] Doc Analysis Fail: {e}")
            return {"error": str(e)}

    def _detect_signals(self, text: str) -> Dict[str, int]:
        signals = {}
        text_lower = text.lower()
        for category, keywords in self.scam_keywords.items():
            count = sum(1 for kw in keywords if kw in text_lower)
            if count > 0:
                signals[category] = count
        return signals

    def _extract_entities(self, text: str) -> Dict[str, List[str]]:
        return {
            "phones": re.findall(r'[\+\d]?\d{10,12}', text),
            "upi_ids": re.findall(r'[a-zA-Z0-9\.\-_]{2,256}@[a-zA-Z]{2,64}', text),
            "links": re.findall(r'https?://[^\s<>"]+|www\.[^\s<>"]+', text)
        }

    def _compute_risk(self, signals: Dict[str, int]) -> float:
        # Heuristic: weight signals
        weights = {"urgency": 0.3, "fear": 0.3, "reward": 0.2, "authority": 0.2}
        score = sum(signals.get(cat, 0) * weight for cat, weight in weights.items())
        return min(score * 10, 100.0) # Scale it

guardian_sensory = GuardianSensory()
