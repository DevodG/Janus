"""perception.py — affect perception sensor (calibrated language, never truth).

Text affect via a transparent lexicon -> valence/arousal estimate with the
contributing words shown. Output is a probability-style sensor reading that
may modulate brevity/clarification. It is NOT a deception detector; V1's
deception_probability path is refused here by design (see COMPONENTS.md #19).
"""
from __future__ import annotations

_POS = {"good", "great", "happy", "love", "excellent", "calm", "thanks", "hope", "win", "glad"}
_NEG = {"bad", "sad", "angry", "hate", "terrible", "stress", "worried", "loss", "fail", "pain"}
_HIGH = {"urgent", "now", "critical", "emergency", "immediately", "panic", "furious"}


def perceive_text(text: str) -> dict:
    words = {w.strip(".,!?;:").lower() for w in text.split()}
    pos, neg, high = len(words & _POS), len(words & _NEG), len(words & _HIGH)
    total = max(pos + neg, 1)
    valence = (pos - neg) / total  # -1..1
    arousal = min(1.0, 0.3 + 0.25 * high + 0.1 * (pos + neg))
    return {"valence": round(valence, 3), "arousal": round(arousal, 3),
            "evidence": {"positive": sorted(words & _POS), "negative": sorted(words & _NEG),
                         "urgency": sorted(words & _HIGH)},
            "calibration": "uncalibrated lexicon sensor — modulates style only, never a truth claim",
            "suggested_style": ("brief, slow, clarify first" if valence < -0.3
                                else "urgent, short, action first" if arousal > 0.7
                                else "normal")}
