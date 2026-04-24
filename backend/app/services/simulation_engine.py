"""
Native Simulation Engine for MiroOrg v2.
Async & Parallel Edition for Stability.
"""

import asyncio
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
    """Native scenario simulation engine (Async Parallel)."""

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
        try:
            with open(path, "w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save simulation {sim_id}: {e}")

    async def run_simulation(self, user_input: str, context: Dict = None) -> Dict:
        """
        Run a full native simulation on a scenario (Async).
        Parallelizes the perspective analysis phase to avoid timeouts.
        """
        sim_id = str(uuid.uuid4())
        t0 = time.perf_counter()
        logger.info(f"[SIMULATION {sim_id[:8]}] Starting: {user_input[:100]}")

        # Step 1: Decompose the scenario (Async, 1 LLM call)
        decomposition = await self._decompose_scenario(user_input, context)
        
        # Step 2: Run multi-perspective analysis (Async Parallel, 4 LLM calls)
        perspectives = await self._run_perspectives(user_input, decomposition, context)

        # Step 3: Synthesize outcomes (Async, 1 LLM call)
        synthesis = await self._synthesize_outcomes(user_input, decomposition, perspectives)

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

    async def _decompose_scenario(self, user_input: str, context: Dict = None) -> Dict:
        """Break down a scenario into its core components (Async)."""
        prompt = """You are a scenario decomposition engine. Break down this "what if" scenario into its core components. Return ONLY valid JSON."""
        messages = [
            {"role": "system", "content": prompt},
            {"role": "user", "content": f"Scenario: {user_input}"},
        ]
        try:
            raw = await asyncio.to_thread(call_model, messages)
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

    async def _run_perspectives(
        self, user_input: str, decomposition: Dict, context: Dict = None
    ) -> List[Dict]:
        """Run analysis from 4 unique perspectives in parallel."""
        perspectives_config = [
            {"name": "optimist", "prompt": "You are an optimistic analyst. Analyze best-case outcomes."},
            {"name": "pessimist", "prompt": "You are a pessimistic analyst. Analyze risks and threats."},
            {"name": "realist", "prompt": "You are a realist analyst. Analyze most likely outcomes."},
            {"name": "contrarian", "prompt": "You are a contrarian analyst. Analyze what everyone is missing."},
        ]

        async def _run_single_perspective(config):
            messages = [
                {"role": "system", "content": config["prompt"]},
                {
                    "role": "user",
                    "content": (
                        f"Scenario: {user_input}\n\n"
                        f"Variables: {json.dumps(decomposition.get('variables', []))}\n"
                        "Provide your analysis as valid JSON with outlook, key_points, probability, confidence."
                    ),
                },
            ]
            try:
                raw = await asyncio.to_thread(call_model, messages)
                result = safe_parse(raw)
                if "error" not in result:
                    result["perspective"] = config["name"]
                    return result
                return {"perspective": config["name"], "outlook": "Parse failed", "probability": 0.5}
            except Exception as e:
                return {"perspective": config["name"], "outlook": f"Failed: {e}", "probability": 0.5}

        # Run all 4 perspectives in parallel
        tasks = [_run_single_perspective(c) for c in perspectives_config]
        return await asyncio.gather(*tasks)

    async def _synthesize_outcomes(
        self, user_input: str, decomposition: Dict, perspectives: List[Dict]
    ) -> Dict:
        """Synthesize all perspectives into coherent scenarios (Async)."""
        perspectives_text = "\n\n".join(
            f"{p.get('perspective', 'unknown').upper()}: {p.get('outlook', '')}\n"
            f"  Prob: {p.get('probability', 0.5)}"
            for p in perspectives
        )

        prompt = """You are a simulation synthesis engine. Combine perspectives into a unified simulation result JSON with 3 scenarios (best, likely, worst)."""
        messages = [
            {"role": "system", "content": prompt},
            {
                "role": "user",
                "content": (
                    f"Scenario: {user_input}\n\n"
                    f"Perspectives:\n{perspectives_text}"
                ),
            },
        ]

        try:
            raw = await asyncio.to_thread(call_model, messages)
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
                    "description": "Simulation synthesis failed, providing default likely outcome.",
                    "probability": 0.5,
                    "impact": "medium",
                }
            ],
            "confidence": 0.3,
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

    async def chat_with_simulation(self, sim_id: str, message: str) -> Dict:
        """Chat with a completed simulation (Async)."""
        simulation = self.get_simulation(sim_id)
        if not simulation:
            return {"error": "Simulation not found"}

        messages = [
            {"role": "system", "content": "Answer questions about this simulation."},
            {
                "role": "user",
                "content": f"Simulation Data: {json.dumps(simulation, default=str)}\n\nQuestion: {message}"
            },
        ]

        try:
            raw = await asyncio.to_thread(call_model, messages)
            return {
                "simulation_id": sim_id,
                "message": message,
                "response": raw,
            }
        except Exception as e:
            return {
                "simulation_id": sim_id,
                "message": message,
                "response": f"Failed: {str(e)}",
            }


# Global instance
simulation_engine = SimulationEngine()
