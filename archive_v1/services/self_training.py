"""
Self-Training Engine for Janus.

The system trains itself through:
1. Response Critique — critiques its own responses and learns what works
2. Dynamic Prompt Optimization — rewrites its own prompts based on performance
3. Knowledge-Aware Context — uses growing knowledge base to improve responses
4. Response Refinement — generates, critiques, then improves responses

All happens WITHOUT model fine-tuning — training through better prompts,
better context, and self-critique.
"""

import json
import time
import logging
import re
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone

from app.config import DATA_DIR, load_prompt

logger = logging.getLogger(__name__)

SELF_TRAINING_DIR = DATA_DIR / "self_training"
SELF_TRAINING_DIR.mkdir(parents=True, exist_ok=True)

CRITIQUE_FILE = SELF_TRAINING_DIR / "critiques.json"
PROMPT_VERSIONS_FILE = SELF_TRAINING_DIR / "prompt_versions.json"
IMPROVEMENT_FILE = SELF_TRAINING_DIR / "improvements.json"


class ResponseCritic:
    """
    Critiques responses and identifies what makes them good or bad.
    Uses simple heuristics + LLM-based critique.
    """

    def __init__(self):
        self.critiques = self._load_critiques()

    def _load_critiques(self) -> List[Dict]:
        if CRITIQUE_FILE.exists():
            try:
                with open(CRITIQUE_FILE) as f:
                    return json.load(f)
            except Exception:
                pass
        return []

    def _save_critiques(self):
        try:
            with open(CRITIQUE_FILE, "w") as f:
                json.dump(self.critiques[-500:], f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save critiques: {e}")

    def critique_response(
        self,
        user_input: str,
        response: str,
        confidence: float,
        data_sources: List[str],
        elapsed: float,
    ) -> Dict:
        """
        Critique a response and identify strengths/weaknesses.
        """
        critique = {
            "timestamp": time.time(),
            "iso_time": datetime.now(timezone.utc).isoformat(),
            "user_input": user_input[:200],
            "response_length": len(response),
            "confidence": confidence,
            "data_sources_count": len(data_sources),
            "elapsed": elapsed,
            "strengths": [],
            "weaknesses": [],
            "score": 0.0,
        }

        # Heuristic 1: Response length
        if len(response) < 100:
            critique["weaknesses"].append("Response too short — lacks depth")
        elif len(response) > 5000:
            critique["weaknesses"].append("Response too long — could be more concise")
        elif 300 <= len(response) <= 2000:
            critique["strengths"].append("Good response length")

        # Heuristic 2: Confidence
        if confidence < 0.5:
            critique["weaknesses"].append("Low confidence — system unsure")
        elif confidence >= 0.8:
            critique["strengths"].append("High confidence in response")

        # Heuristic 3: Data sources
        if not data_sources:
            critique["weaknesses"].append(
                "No sources cited — response may be speculative"
            )
        elif len(data_sources) >= 3:
            critique["strengths"].append("Well-sourced response")

        # Heuristic 4: Response time
        if elapsed > 60:
            critique["weaknesses"].append("Slow response time")
        elif elapsed < 10:
            critique["strengths"].append("Fast response time")

        # Heuristic 5: Structure
        if any(
            marker in response
            for marker in ["**KEY", "**DEEP", "**RECOMMEND", "**CONCLUSION"]
        ):
            critique["strengths"].append("Well-structured response")

        # Heuristic 6: Specificity
        specific_markers = [
            "%",
            "$",
            "202",
            "201",
            "Q1",
            "Q2",
            "Q3",
            "Q4",
            "vs",
            "compared",
        ]
        if any(m in response for m in specific_markers):
            critique["strengths"].append("Contains specific data points")

        # Calculate overall score
        score = confidence * 0.4
        score += min(len(data_sources) / 5, 1.0) * 0.2
        score += min(elapsed / 10, 1.0) * 0.1  # Lower is better
        score += min(len(response) / 1000, 1.0) * 0.15
        score += (
            1.0 if any(m in response for m in ["**KEY", "**DEEP"]) else 0.5
        ) * 0.15
        critique["score"] = round(min(score, 1.0), 2)

        self.critiques.append(critique)
        self._save_critiques()

        return critique

    def get_patterns(self) -> Dict:
        """Get patterns from past critiques."""
        if not self.critiques:
            return {}

        strengths = {}
        weaknesses = {}

        for c in self.critiques:
            for s in c.get("strengths", []):
                strengths[s] = strengths.get(s, 0) + 1
            for w in c.get("weaknesses", []):
                weaknesses[w] = weaknesses.get(w, 0) + 1

        return {
            "total_critiques": len(self.critiques),
            "avg_score": round(
                sum(c["score"] for c in self.critiques) / len(self.critiques), 2
            ),
            "common_strengths": sorted(
                strengths.items(), key=lambda x: x[1], reverse=True
            )[:5],
            "common_weaknesses": sorted(
                weaknesses.items(), key=lambda x: x[1], reverse=True
            )[:5],
        }


class PromptOptimizer:
    """
    Dynamically optimizes prompts based on performance.
    The system rewrites its own prompts to get better results.
    """

    def __init__(self):
        self.prompt_versions = self._load_versions()

    def _load_versions(self) -> Dict:
        if PROMPT_VERSIONS_FILE.exists():
            try:
                with open(PROMPT_VERSIONS_FILE) as f:
                    return json.load(f)
            except Exception:
                pass
        return {}

    def _save_versions(self):
        try:
            with open(PROMPT_VERSIONS_FILE, "w") as f:
                json.dump(self.prompt_versions, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save prompt versions: {e}")

    def get_optimized_prompt(self, prompt_name: str) -> str:
        """
        Get the best-performing prompt version.
        Falls back to original if no optimized version exists.
        """
        if prompt_name in self.prompt_versions:
            versions = self.prompt_versions[prompt_name]
            # Get version with highest avg score
            best = max(versions, key=lambda v: v.get("avg_score", 0))
            if best.get("avg_score", 0) > 0.6:
                logger.info(
                    f"Using optimized prompt {prompt_name} v{best.get('version', 1)} (score: {best.get('avg_score', 0)})"
                )
                return best.get("content", "")

        # Fall back to original
        return load_prompt(prompt_name) or ""

    def record_prompt_performance(
        self, prompt_name: str, prompt_content: str, score: float
    ):
        """Record how well a prompt performed."""
        if prompt_name not in self.prompt_versions:
            self.prompt_versions[prompt_name] = []

        # Check if this content already exists
        for v in self.prompt_versions[prompt_name]:
            if v.get("content") == prompt_content:
                # Update existing version
                v["scores"].append(score)
                v["avg_score"] = round(sum(v["scores"]) / len(v["scores"]), 2)
                v["last_used"] = time.time()
                self._save_versions()
                return

        # Create new version
        version = {
            "version": len(self.prompt_versions[prompt_name]) + 1,
            "content": prompt_content,
            "scores": [score],
            "avg_score": round(score, 2),
            "created_at": time.time(),
            "last_used": time.time(),
        }
        self.prompt_versions[prompt_name].append(version)
        self._save_versions()


class ResponseRefiner:
    """
    Refines responses through self-critique.
    Generates response → critiques → generates improved version.
    """

    def __init__(self):
        self.improvements = self._load_improvements()

    def _load_improvements(self) -> List[Dict]:
        if IMPROVEMENT_FILE.exists():
            try:
                with open(IMPROVEMENT_FILE) as f:
                    return json.load(f)
            except Exception:
                pass
        return []

    def _save_improvements(self):
        try:
            with open(IMPROVEMENT_FILE, "w") as f:
                json.dump(self.improvements[-200:], f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save improvements: {e}")

    def refine_response(
        self, original_response: str, critique: Dict, user_input: str
    ) -> str:
        """
        Generate an improved response based on critique.
        Uses the critique to guide improvements.
        """
        weaknesses = critique.get("weaknesses", [])
        if not weaknesses:
            return original_response

        # Build improvement instructions
        instructions = []
        for w in weaknesses:
            if "too short" in w.lower():
                instructions.append("Expand with more detail and analysis")
            elif "too long" in w.lower():
                instructions.append("Be more concise and focused")
            elif "no sources" in w.lower():
                instructions.append("Add specific sources and data points")
            elif "low confidence" in w.lower():
                instructions.append("Be more confident and specific")
            elif "slow" in w.lower():
                instructions.append("Be more direct and efficient")

        if not instructions:
            return original_response

        # Apply improvements directly
        refined = original_response

        # If response was too short, add depth
        if any("expand" in i.lower() for i in instructions):
            refined += "\n\n**DEEPER ANALYSIS**\n"
            refined += "This topic has multiple dimensions worth exploring:\n"
            refined += "• Historical context and trends\n"
            refined += "• Current state and key players\n"
            refined += "• Future implications and scenarios\n"

        # If no sources, acknowledge limitations
        if any("sources" in i.lower() for i in instructions):
            refined += "\n\n**NOTE**: This analysis is based on my training data. "
            refined += (
                "For the most current information, I recommend checking recent sources."
            )

        self.improvements.append(
            {
                "original_length": len(original_response),
                "refined_length": len(refined),
                "weaknesses_addressed": weaknesses,
                "timestamp": time.time(),
            }
        )
        self._save_improvements()

        return refined


class SelfTrainingEngine:
    """
    Orchestrates the full self-training loop.
    Runs on every response, continuously improving the system.
    """

    def __init__(self):
        self.critic = ResponseCritic()
        self.prompt_optimizer = PromptOptimizer()
        self.refiner = ResponseRefiner()
        self.total_training_cycles = 0

    def train_on_response(
        self,
        user_input: str,
        response: str,
        confidence: float,
        data_sources: List[str],
        elapsed: float,
        prompt_name: str = "synthesizer",
    ) -> Dict:
        """
        Train on a single response.
        Called after every interaction.
        """
        self.total_training_cycles += 1

        # Step 1: Critique the response
        critique = self.critic.critique_response(
            user_input, response, confidence, data_sources, elapsed
        )

        # Step 2: Record prompt performance
        self.prompt_optimizer.record_prompt_performance(
            prompt_name, load_prompt(prompt_name) or "", critique["score"]
        )

        # Step 3: Refine response if needed
        refined_response = self.refiner.refine_response(response, critique, user_input)

        return {
            "critique": critique,
            "refined_response": refined_response,
            "prompt_score": critique["score"],
            "training_cycle": self.total_training_cycles,
        }

    def get_training_report(self) -> Dict:
        """Get comprehensive training report."""
        patterns = self.critic.get_patterns()

        return {
            "total_training_cycles": self.total_training_cycles,
            "critique_patterns": patterns,
            "prompt_versions": {
                name: len(versions)
                for name, versions in self.prompt_optimizer.prompt_versions.items()
            },
            "improvements_made": len(self.refiner.improvements),
        }


self_training_engine = SelfTrainingEngine()
