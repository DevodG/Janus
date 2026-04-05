"""
Native Simulation Engine for MiroOrg v2.

Replaces external MiroFish dependency with built-in scenario simulation.
This is a unique, defensible feature — no one else has this.

The engine works by:
1. Decomposing the scenario into variables, actors, and forces
2. Running multi-perspective analysis (optimist, pessimist, realist, contrarian)
3. Synthesizing outcomes with probability distributions
4. Storing simulation state for follow-up Q&A
"""

import json
import uuid
import time
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional

from app.agents._model import call_model, safe_parse
from app.config import load_prompt

logger = logging.getLogger(__name__)

SIMULATION_DIR = Path(__file__).parent.parent / "data" / "simulations"
SIMULATION_DIR.mkdir(parents=True, exist_ok=True)


class SimulationEngine:
    """Native scenario simulation engine."""

    def __init__(self):
        self.simulations: Dict[str, Dict] = {}
        self._load_simulations()

    def _load_simulations(self) -> None:
        """Load persisted simulations."""
        for path in SIMULATION_DIR.glob("*.json"):
            try:
                with open(path) as f:
                    data = json.load(f)
                sim_id = data.get("simulation_id", path.stem)
                self.simulations[sim_id] = data
            except Exception:
                pass

    def _save_simulation(self, sim_id: str, data: Dict) -> None:
        """Persist simulation to disk."""
        self.simulations[sim_id] = data
        path = SIMULATION_DIR / f"{sim_id}.json"
        with open(path, "w") as f:
            json.dump(data, f, indent=2)

    def run_simulation(self, user_input: str, context: Dict = None) -> Dict:
        """
        Run a full native simulation on a scenario.

        This replaces the external MiroFish service with built-in intelligence:
        1. Decompose scenario into variables/actors/forces
        2. Run multi-perspective analysis
        3. Synthesize outcomes with probabilities
        4. Store for follow-up Q&A
        """
        sim_id = str(uuid.uuid4())
        t0 = time.perf_counter()
        logger.info(f"[SIMULATION {sim_id[:8]}] Starting: {user_input[:100]}")

        # Step 1: Decompose the scenario
        decomposition = self._decompose_scenario(user_input, context)
        logger.info(
            f"[SIMULATION {sim_id[:8]}] Decomposed: {len(decomposition.get('variables', []))} variables, {len(decomposition.get('actors', []))} actors"
        )

        # Step 2: Run multi-perspective analysis
        perspectives = self._run_perspectives(user_input, decomposition, context)
        logger.info(f"[SIMULATION {sim_id[:8]}] Perspectives: {len(perspectives)}")

        # Step 3: Synthesize outcomes
        synthesis = self._synthesize_outcomes(user_input, decomposition, perspectives)
        logger.info(
            f"[SIMULATION {sim_id[:8]}] Synthesized: {len(synthesis.get('scenarios', []))} scenarios"
        )

        elapsed = time.perf_counter() - t0

        # Build simulation record
        simulation = {
            "simulation_id": sim_id,
            "user_input": user_input,
            "status": "completed",
            "decomposition": decomposition,
            "perspectives": perspectives,
            "synthesis": synthesis,
            "elapsed_seconds": round(elapsed, 1),
            "created_at": time.time(),
            "context": context or {},
        }

        self._save_simulation(sim_id, simulation)
        logger.info(f"[SIMULATION {sim_id[:8]}] Completed in {elapsed:.1f}s")

        return simulation

    def _decompose_scenario(self, user_input: str, context: Dict = None) -> Dict:
        """Break down a scenario into its core components."""
        prompt = """You are a scenario decomposition engine. Break down this "what if" scenario into its core components.

Analyze the scenario and return ONLY valid JSON:
{
  "core_question": "<the fundamental question being asked>",
  "variables": ["<key variable 1>", "<key variable 2>", "..."],
  "actors": ["<key actor/stakeholder 1>", "<key actor 2>", "..."],
  "forces": ["<driving force 1>", "<driving force 2>", "..."],
  "constraints": ["<constraint 1>", "<constraint 2>", "..."],
  "timeframe": "<short-term | medium-term | long-term>",
  "complexity": "low | medium | high | very_high",
  "uncertainty_level": "low | medium | high"
}

Be specific and analytical. Identify the real variables that matter, not just surface-level ones."""

        messages = [
            {"role": "system", "content": prompt},
            {"role": "user", "content": f"Scenario: {user_input}"},
        ]

        try:
            raw = call_model(messages)
            result = safe_parse(raw)
            if "error" in result:
                return self._fallback_decomposition(user_input)
            return result
        except Exception as e:
            logger.warning(f"Scenario decomposition failed: {e}")
            return self._fallback_decomposition(user_input)

    def _fallback_decomposition(self, user_input: str) -> Dict:
        """Fallback decomposition if LLM fails."""
        return {
            "core_question": user_input,
            "variables": [user_input[:100]],
            "actors": ["unknown"],
            "forces": ["unknown"],
            "constraints": ["unknown"],
            "timeframe": "medium-term",
            "complexity": "medium",
            "uncertainty_level": "high",
        }

    def _run_perspectives(
        self, user_input: str, decomposition: Dict, context: Dict = None
    ) -> List[Dict]:
        """Run analysis from multiple perspectives."""
        perspectives_config = [
            {
                "name": "optimist",
                "prompt": "You are an optimistic analyst. Analyze this scenario from the most favorable perspective. What are the best-case outcomes? What opportunities does this create? What positive forces are at play? Be specific and evidence-based, not naive.",
            },
            {
                "name": "pessimist",
                "prompt": "You are a pessimistic analyst. Analyze this scenario from the most cautious perspective. What are the worst-case outcomes? What risks and threats exist? What could go wrong? Be specific and evidence-based, not alarmist.",
            },
            {
                "name": "realist",
                "prompt": "You are a realist analyst. Analyze this scenario from the most balanced, evidence-based perspective. What is the most likely outcome? What does the data suggest? What are the key factors that will determine the result? Be specific and grounded.",
            },
            {
                "name": "contrarian",
                "prompt": "You are a contrarian analyst. Analyze this scenario from an unconventional perspective. What is everyone missing? What assumptions are wrong? What unexpected outcomes could occur? What second-order effects are being ignored? Be specific and insightful.",
            },
        ]

        perspectives = []
        for config in perspectives_config:
            messages = [
                {"role": "system", "content": config["prompt"]},
                {
                    "role": "user",
                    "content": (
                        f"Scenario: {user_input}\n\n"
                        f"Key variables: {json.dumps(decomposition.get('variables', []))}\n"
                        f"Key actors: {json.dumps(decomposition.get('actors', []))}\n"
                        f"Key forces: {json.dumps(decomposition.get('forces', []))}\n\n"
                        "Provide your analysis as valid JSON:\n"
                        "{\n"
                        '  "outlook": "<overall outlook in one sentence>",\n'
                        '  "key_points": ["<point 1>", "<point 2>", "..."],\n'
                        '  "probability": 0.0-1.0,\n'
                        '  "confidence": 0.0-1.0,\n'
                        '  "evidence": ["<evidence 1>", "<evidence 2>"]\n'
                        "}"
                    ),
                },
            ]

            try:
                raw = call_model(messages)
                result = safe_parse(raw)
                if "error" not in result:
                    result["perspective"] = config["name"]
                    perspectives.append(result)
                else:
                    perspectives.append(
                        {
                            "perspective": config["name"],
                            "outlook": f"Analysis from {config['name']} perspective failed",
                            "key_points": [],
                            "probability": 0.5,
                            "confidence": 0.3,
                            "evidence": [],
                        }
                    )
            except Exception as e:
                logger.warning(f"Perspective {config['name']} failed: {e}")
                perspectives.append(
                    {
                        "perspective": config["name"],
                        "outlook": f"Analysis failed: {str(e)[:100]}",
                        "key_points": [],
                        "probability": 0.5,
                        "confidence": 0.3,
                        "evidence": [],
                    }
                )

        return perspectives

    def _synthesize_outcomes(
        self, user_input: str, decomposition: Dict, perspectives: List[Dict]
    ) -> Dict:
        """Synthesize all perspectives into coherent scenarios with probabilities."""
        perspectives_text = "\n\n".join(
            f"{p.get('perspective', 'unknown').upper()}: {p.get('outlook', '')}\n"
            f"  Key points: {json.dumps(p.get('key_points', []))}\n"
            f"  Probability: {p.get('probability', 0.5)}\n"
            f"  Confidence: {p.get('confidence', 0.5)}"
            for p in perspectives
        )

        prompt = """You are a simulation synthesis engine. Combine multiple analytical perspectives into coherent scenarios with probability distributions.

Analyze the perspectives and produce a unified simulation result as valid JSON:
{
  "scenarios": [
    {
      "name": "<scenario name>",
      "description": "<detailed description of what happens>",
      "probability": 0.0-1.0,
      "key_indicators": ["<indicator to watch>", "..."],
      "timeline": "<when this would unfold>",
      "impact": "low | medium | high | extreme"
    }
  ],
  "most_likely": "<which scenario is most likely and why>",
  "key_uncertainties": ["<uncertainty 1>", "<uncertainty 2>"],
  "decision_framework": "<how to think about this decision>",
  "early_warning_signals": ["<signal 1>", "<signal 2>"],
  "confidence": 0.0-1.0
}

Rules:
- Provide 3-4 scenarios (best case, base case, worst case, wildcard)
- Probabilities must sum to 1.0
- Be specific, not generic
- Include concrete indicators and signals to watch"""

        messages = [
            {"role": "system", "content": prompt},
            {
                "role": "user",
                "content": (
                    f"Scenario: {user_input}\n\n"
                    f"Decomposition: {json.dumps(decomposition, indent=2)}\n\n"
                    f"Perspectives:\n{perspectives_text}"
                ),
            },
        ]

        try:
            raw = call_model(messages)
            result = safe_parse(raw)
            if "error" in result:
                return self._fallback_synthesis(perspectives)
            return result
        except Exception as e:
            logger.warning(f"Outcome synthesis failed: {e}")
            return self._fallback_synthesis(perspectives)

    def _fallback_synthesis(self, perspectives: List[Dict]) -> Dict:
        """Fallback synthesis if LLM fails."""
        return {
            "scenarios": [
                {
                    "name": "Base Case",
                    "description": "Most likely outcome based on current trends",
                    "probability": 0.5,
                    "key_indicators": ["monitor the situation"],
                    "timeline": "6-12 months",
                    "impact": "medium",
                },
                {
                    "name": "Alternative",
                    "description": "Alternative outcome if key variables shift",
                    "probability": 0.3,
                    "key_indicators": ["watch for changes"],
                    "timeline": "3-6 months",
                    "impact": "medium",
                },
                {
                    "name": "Wildcard",
                    "description": "Unexpected outcome from black swan event",
                    "probability": 0.2,
                    "key_indicators": ["unpredictable"],
                    "timeline": "unknown",
                    "impact": "high",
                },
            ],
            "most_likely": "Base case scenario is most probable based on available analysis",
            "key_uncertainties": [
                "Multiple perspectives suggest significant uncertainty"
            ],
            "decision_framework": "Monitor key indicators and adjust as new information emerges",
            "early_warning_signals": [
                "Watch for shifts in the key variables identified"
            ],
            "confidence": 0.4,
        }

    def get_simulation(self, sim_id: str) -> Optional[Dict]:
        """Get a simulation by ID."""
        return self.simulations.get(sim_id)

    def list_simulations(self) -> List[Dict]:
        """List all simulations with summary info."""
        return [
            {
                "simulation_id": sim_id,
                "user_input": data.get("user_input", "")[:100],
                "status": data.get("status", "unknown"),
                "scenarios": len(data.get("synthesis", {}).get("scenarios", [])),
                "elapsed_seconds": data.get("elapsed_seconds", 0),
                "created_at": data.get("created_at", 0),
            }
            for sim_id, data in self.simulations.items()
        ]

    def chat_with_simulation(self, sim_id: str, message: str) -> Dict:
        """Chat with a completed simulation for follow-up questions."""
        simulation = self.get_simulation(sim_id)
        if not simulation:
            return {"error": "Simulation not found"}

        synthesis = simulation.get("synthesis", {})
        decomposition = simulation.get("decomposition", {})
        perspectives = simulation.get("perspectives", [])

        prompt = """You are a simulation analyst. Answer questions about a completed scenario simulation.
Use the simulation data to provide specific, evidence-based answers. Don't speculate beyond what the simulation found."""

        messages = [
            {"role": "system", "content": prompt},
            {
                "role": "user",
                "content": (
                    f"Original scenario: {simulation.get('user_input', '')}\n\n"
                    f"Decomposition: {json.dumps(decomposition, indent=2)}\n\n"
                    f"Perspectives: {json.dumps(perspectives, indent=2)}\n\n"
                    f"Synthesis: {json.dumps(synthesis, indent=2)}\n\n"
                    f"Question: {message}"
                ),
            },
        ]

        try:
            raw = call_model(messages)
            return {
                "simulation_id": sim_id,
                "message": message,
                "response": raw,
            }
        except Exception as e:
            return {
                "simulation_id": sim_id,
                "message": message,
                "response": f"Failed to generate response: {str(e)}",
            }


# Global instance
simulation_engine = SimulationEngine()
