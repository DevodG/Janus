"""
Dream processor for Janus — runs during off-hours to consolidate knowledge.

FIXES vs previous version:
  - Dream cycles were running in 0.0 seconds (no LLM calls were being made)
  - Root cause: the processor was checking for memory/case data that doesn't exist
    on HF Spaces (ephemeral filesystem wipes on restart), short-circuiting early
  - Fix: each dream cycle now always runs at least one LLM reflection, even with
    no historical cases. Uses the curiosity engine's discoveries as input instead.
  - Added proper logging so failures are visible in Space logs
  - Added timeout guard so stuck LLM calls don't block the daemon
"""

import time
import json
import logging
from pathlib import Path
from typing import Optional
from datetime import datetime

logger = logging.getLogger(__name__)

try:
    from app.config import DATA_DIR
except ImportError:
    DATA_DIR = Path(__file__).parent.parent / "data"

DREAMS_DIR = Path(DATA_DIR) / "dreams"
MAX_DREAMS_STORED = 50   # rolling window
LLM_TIMEOUT = 120        # seconds per dream cycle LLM call


def _call_with_timeout(fn, timeout: float):
    """Run fn() with a timeout. Returns (result, error)."""
    import threading
    result = [None]
    error  = [None]

    def target():
        try:
            result[0] = fn()
        except Exception as e:
            error[0] = e

    t = threading.Thread(target=target, daemon=True)
    t.start()
    t.join(timeout)
    if t.is_alive():
        return None, TimeoutError(f"LLM call timed out after {timeout}s")
    return result[0], error[0]


class DreamCycleProcessor:
    """
    Runs during the night/background phase.
    Performs reflection, pattern recognition, hypothesis generation.
    """

    def __init__(self):
        DREAMS_DIR.mkdir(parents=True, exist_ok=True)
        self._dream_history: list = []
        self._total_dreams = 0
        self._total_insights = 0
        self._total_hypotheses = 0
        self._load_history()

    def _load_history(self):
        try:
            files = sorted(DREAMS_DIR.glob("dream_*.json"), reverse=True)[:MAX_DREAMS_STORED]
            self._dream_history = []
            for f in files:
                try:
                    self._dream_history.append(json.loads(f.read_text()))
                except Exception:
                    pass
            self._total_dreams     = len(self._dream_history)
            self._total_insights   = sum(len(d.get("insights", [])) for d in self._dream_history)
            self._total_hypotheses = sum(len(d.get("hypotheses", [])) for d in self._dream_history)
        except Exception as e:
            logger.warning(f"DreamProcessor: failed to load history: {e}")

    def _get_recent_cases(self, limit: int = 10) -> list:
        """Load recent cases from memory dir."""
        memory_dir = Path(DATA_DIR) / "memory"
        cases = []
        if memory_dir.exists():
            for f in sorted(memory_dir.glob("*.json"), reverse=True)[:limit]:
                try:
                    cases.append(json.loads(f.read_text()))
                except Exception:
                    pass
        return cases

    def _get_recent_discoveries(self, limit: int = 5) -> list:
        """Load recent curiosity discoveries."""
        curiosity_dir = Path(DATA_DIR) / "curiosity"
        discoveries = []
        if curiosity_dir.exists():
            for f in sorted(curiosity_dir.glob("*.json"), reverse=True)[:limit]:
                try:
                    d = json.loads(f.read_text())
                    discoveries.append(d)
                except Exception:
                    pass
        return discoveries

    def run_dream_cycle(self, memory_graph=None, adaptive_intelligence=None, force: bool = False) -> dict:
        """
        Run one complete dream cycle.
        FIXED: always attempts LLM calls regardless of whether local data exists.
        """
        t0 = time.time()
        logger.info("DreamProcessor: starting dream cycle")

        report = {
            "timestamp": datetime.utcnow().isoformat(),
            "cycles": [],
            "insights": [],
            "self_corrections": [],
            "hypotheses": [],
            "duration_seconds": 0.0,
        }

        try:
            from app.agents._model import call_model

            # Gather context — works even if empty (HF ephemeral FS)
            recent_cases      = self._get_recent_cases(10)
            recent_discoveries = self._get_recent_discoveries(5)
            past_insights     = [i for d in self._dream_history[-5:] for i in d.get("insights", [])]

            # ── Cycle 1: Pattern recognition ─────────────────────────────────
            cycle1_report = self._run_pattern_recognition(
                call_model, recent_cases, recent_discoveries, past_insights
            )
            report["cycles"].append({"name": "pattern_recognition", "report": cycle1_report})
            report["insights"].extend(cycle1_report.get("insights", []))

            # ── Cycle 2: Hypothesis generation ────────────────────────────────
            cycle2_report = self._run_hypothesis_generation(
                call_model, recent_cases, report["insights"]
            )
            report["cycles"].append({"name": "hypothesis_generation", "report": cycle2_report})
            report["hypotheses"].extend(cycle2_report.get("hypotheses", []))

            # ── Cycle 3: Self-improvement ─────────────────────────────────────
            cycle3_report = self._run_self_improvement(call_model, recent_cases)
            report["cycles"].append({"name": "self_improvement", "report": cycle3_report})
            report["self_corrections"].extend(cycle3_report.get("corrections", []))

            # ── Cycle 4: Knowledge consolidation ─────────────────────────────
            cycle4_report = self._run_knowledge_consolidation(
                call_model, report["insights"], report["hypotheses"]
            )
            report["cycles"].append({"name": "knowledge_consolidation", "report": cycle4_report})

        except Exception as e:
            logger.error(f"DreamProcessor: dream cycle error: {e}")
            report["error"] = str(e)

        report["duration_seconds"] = round(time.time() - t0, 2)

        # Update stats
        self._total_dreams     += 1
        self._total_insights   += len(report["insights"])
        self._total_hypotheses += len(report["hypotheses"])

        # Save dream
        self._dream_history.insert(0, report)
        self._dream_history = self._dream_history[:MAX_DREAMS_STORED]
        self._save_dream(report)

        logger.info(
            f"DreamProcessor: cycle complete in {report['duration_seconds']:.1f}s — "
            f"{len(report['insights'])} insights, {len(report['hypotheses'])} hypotheses"
        )
        return report

    def _run_pattern_recognition(self, call_model, cases, discoveries, past_insights) -> dict:
        """Identify patterns in recent activity."""
        context_parts = []
        if cases:
            topics = [c.get("user_input", c.get("query", ""))[:100] for c in cases[:5]]
            context_parts.append(f"Recent queries:\n" + "\n".join(f"- {t}" for t in topics if t))
        if discoveries:
            context_parts.append(
                "Recent discoveries:\n" + "\n".join(
                    f"- {d.get('topic', '')}: {d.get('insight', '')[:100]}"
                    for d in discoveries[:3]
                )
            )
        if not context_parts:
            context_parts.append("No recent activity yet — reflect on general knowledge patterns in finance and AI.")

        prompt = (
            "You are Janus in dream mode — doing deep background reflection. "
            "Identify 2-3 meaningful patterns or connections in the following activity. "
            "Be specific and insightful, not generic.\n\n"
            + "\n\n".join(context_parts)
            + "\n\nRespond with a JSON object: "
            '{"insights": ["insight1", "insight2"], "patterns_found": 2}'
        )

        result, err = _call_with_timeout(
            lambda: call_model([{"role": "user", "content": prompt}]),
            LLM_TIMEOUT
        )
        if err or not result:
            logger.warning(f"DreamProcessor pattern_recognition failed: {err}")
            return {"insights": [], "patterns_found": 0, "error": str(err)}

        try:
            from app.agents.smart_router import safe_parse
            data = safe_parse(result)
            insights = data.get("insights", [])
            if isinstance(insights, list):
                return {"insights": insights, "patterns_found": len(insights)}
        except Exception:
            pass
        if len(result) > 50:
            return {"insights": [result[:500]], "patterns_found": 1}
        return {"insights": [], "patterns_found": 0}

    def _run_hypothesis_generation(self, call_model, cases, insights) -> dict:
        """Generate testable hypotheses from patterns."""
        context = ""
        if insights:
            context = "Based on these insights:\n" + "\n".join(f"- {i}" for i in insights[:3])
        else:
            context = "Generate a hypothesis about a financial or technological trend worth investigating."

        prompt = (
            "You are Janus in hypothesis generation mode. "
            "Generate 1-2 specific, testable hypotheses based on the following.\n\n"
            + context
            + "\n\nRespond with JSON: "
            '{"hypotheses": ["if X then Y because Z", ...], "hypotheses_generated": 1}'
        )

        result, err = _call_with_timeout(
            lambda: call_model([{"role": "user", "content": prompt}]),
            LLM_TIMEOUT
        )
        if err or not result:
            logger.warning(f"DreamProcessor hypothesis_generation failed: {err}")
            return {"hypotheses": [], "hypotheses_generated": 0}

        try:
            from app.agents.smart_router import safe_parse
            data = safe_parse(result)
            hyps = data.get("hypotheses", [])
            return {"hypotheses": hyps, "hypotheses_generated": len(hyps)}
        except Exception:
            if len(result) > 30:
                return {"hypotheses": [result[:300]], "hypotheses_generated": 1}
        return {"hypotheses": [], "hypotheses_generated": 0}

    def _run_self_improvement(self, call_model, cases) -> dict:
        """Identify areas for self-improvement."""
        if cases:
            errors = [
                c for c in cases
                if c.get("final", {}).get("confidence", 1.0) < 0.5
                or "error" in str(c.get("final", {})).lower()
            ]
            context = f"Found {len(errors)} low-confidence responses out of {len(cases)} recent cases."
        else:
            context = "No recent cases to analyze. Identify a general capability gap to improve."

        prompt = (
            "You are Janus in self-improvement mode. Identify 1-2 specific improvements. "
            f"\n\n{context}\n\n"
            'Respond with JSON: {"corrections": ["improvement1"], "improvements_identified": 1}'
        )

        result, err = _call_with_timeout(
            lambda: call_model([{"role": "user", "content": prompt}]),
            LLM_TIMEOUT
        )
        if err or not result:
            return {"corrections": [], "improvements_identified": 0}

        try:
            from app.agents.smart_router import safe_parse
            data = safe_parse(result)
            corrections = data.get("corrections", [])
            return {"corrections": corrections, "improvements_identified": len(corrections)}
        except Exception:
            return {"corrections": [], "improvements_identified": 0}

    def _run_knowledge_consolidation(self, call_model, insights, hypotheses) -> dict:
        """Consolidate insights into actionable knowledge."""
        if not insights and not hypotheses:
            return {"actions": [], "actions_taken": 0}

        content = ""
        if insights:
            content += "Insights:\n" + "\n".join(f"- {i}" for i in insights[:3])
        if hypotheses:
            content += "\nHypotheses:\n" + "\n".join(f"- {h}" for h in hypotheses[:2])

        prompt = (
            "You are Janus consolidating knowledge. Given the following insights and hypotheses, "
            "identify 1-2 concrete actions or knowledge updates.\n\n"
            + content
            + '\n\nJSON: {"actions": ["action1"], "actions_taken": 1}'
        )

        result, err = _call_with_timeout(
            lambda: call_model([{"role": "user", "content": prompt}]),
            LLM_TIMEOUT
        )
        if err or not result:
            return {"actions": [], "actions_taken": 0}

        try:
            from app.agents.smart_router import safe_parse
            data = safe_parse(result)
            actions = data.get("actions", [])
            return {"actions": actions, "actions_taken": len(actions)}
        except Exception:
            return {"actions": [], "actions_taken": 0}

    def _save_dream(self, report: dict):
        try:
            ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            path = DREAMS_DIR / f"dream_{ts}.json"
            path.write_text(json.dumps(report, indent=2, default=str))
            # Clean old dreams
            all_files = sorted(DREAMS_DIR.glob("dream_*.json"))
            for old in all_files[:-MAX_DREAMS_STORED]:
                try:
                    old.unlink()
                except Exception:
                    pass
        except Exception as e:
            logger.warning(f"DreamProcessor: save failed: {e}")

    def get_dream_history(self, limit: int = 10) -> list:
        return self._dream_history[:limit]

    def get_status(self) -> dict:
        return {
            "total_dreams":     self._total_dreams,
            "total_insights":   self._total_insights,
            "total_hypotheses": self._total_hypotheses,
            "latest_dream":     self._dream_history[0] if self._dream_history else None,
        }
