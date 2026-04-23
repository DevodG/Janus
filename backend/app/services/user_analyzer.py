"""
Janus User Tone Analyzer.
Analyzes user queries to adapt the agent's cognitive style.
"""
import logging
from typing import Dict, Any
from textblob import TextBlob # Lightweight sentiment fallback

logger = logging.getLogger(__name__)

class UserAnalyzer:
    """
    Analyzes user interaction tone and injects cognitive context.
    """
    
    def analyze_query(self, query: str) -> Dict[str, Any]:
        """
        Analyze the sentiment and cognitive state of the user query.
        """
        try:
            analysis = TextBlob(query)
            sentiment = analysis.sentiment.polarity # -1 to 1
            subjectivity = analysis.sentiment.subjectivity # 0 to 1
            
            # Map to Janus Cognitive States
            tone = "neutral"
            if sentiment > 0.3: tone = "optimistic"
            elif sentiment < -0.3: tone = "skeptical/urgent"
            
            cognitive_focus = "analytical"
            if subjectivity > 0.6: cognitive_focus = "intuitive/personal"
            
            logger.info(f"[USER-ANALYZER] Detected User Tone: {tone} | Focus: {cognitive_focus}")
            
            return {
                "user_tone": tone,
                "user_sentiment": round(sentiment, 2),
                "cognitive_focus": cognitive_focus,
                "context_injection": self._get_context_prompt(tone, cognitive_focus)
            }
        except Exception as e:
            logger.warning(f"[USER-ANALYZER] Analysis failed: {e}")
            return {"user_tone": "neutral", "user_sentiment": 0.0, "cognitive_focus": "analytical", "context_injection": ""}

    def _get_context_prompt(self, tone: str, focus: str) -> str:
        """
        Generates a hidden system instruction based on user state.
        """
        if tone == "skeptical/urgent":
            return "NOTICE: The user is currently skeptical or urgent. Prioritize deep-dive forensic verification and risk-mitigation data."
        elif tone == "optimistic":
            return "NOTICE: The user is optimistic. Balance your analysis with growth-scaling opportunities, but remain objectively grounded."
        return ""

# Singleton
user_analyzer = UserAnalyzer()
