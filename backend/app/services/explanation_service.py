from typing import List, Dict

class ExplanationService:
    def get_explanation(self, decision: str, reasons: List[str], risk_score: float) -> str:
        if decision == "BLOCK":
            base = f"This message was BLOCKED (Risk: {risk_score}%). "
        elif decision == "WARN":
            base = f"Janus issues a WARNING for this intake (Risk: {risk_score}%). "
        else:
            base = f"This intake appears safe (Risk: {risk_score}%). "

        if not reasons:
            return base + "No significant scam patterns were identified."

        reason_text = " ".join(reasons)
        return f"{base}We detected the following indicators: {reason_text}. Please exercise caution."

explanation_service = ExplanationService()
