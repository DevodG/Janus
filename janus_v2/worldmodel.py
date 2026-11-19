"""worldmodel.py — predict before acting + imagination (scenario hypotheses).

predict(): for dynamics Janus understands (growth, sequences, rates), forecast
an outcome with a confidence and the assumption used. simulate(): generate
plausible scenarios from goals/facts as hypotheses — they propose, the eval
gate disposes; scenarios NEVER write to memory or prompts directly.
"""
from __future__ import annotations

from janus_v2 import reasoners


def predict(question: str) -> dict | None:
    """Forecast via the same verified dynamics the reasoners compute with."""
    q = question.lower()
    n = reasoners._nums(question)
    if "compound" in q or "grow" in q and "year" in q:
        if len(n) >= 3:
            fv = n[0] * (1 + n[1] / 100) ** n[2]
            return {"forecast": fv, "unit": "future value",
                    "assumption": f"constant {n[1]:g}% rate for {n[2]:g} periods",
                    "confidence": 0.8}
    if "sequence" in q:
        hit = reasoners.solve(question)
        if hit:
            return {"forecast": hit[0], "unit": "next term",
                    "assumption": f"pattern via {hit[2]}", "confidence": hit[1]}
    if "together" in q and "hours" in q:
        hit = reasoners.solve(question)
        if hit:
            return {"forecast": hit[0], "unit": "joint completion time",
                    "assumption": "constant individual rates, no interference",
                    "confidence": hit[1]}
    return None


def simulate(goal: str, facts: list[dict], k: int = 3) -> list[dict]:
    """Imagination: k scenario hypotheses ranked by plausibility. Pure proposal."""
    base = [f.get("object", "") for f in facts[:3]] or ["current state"]
    scenarios = []
    for i, variant in enumerate(["best case", "expected case", "adverse case"][:k]):
        scenarios.append({
            "goal": goal, "scenario": variant,
            "hypothesis": f"If {goal} proceeds under {variant} conditions given {', '.join(base)}, "
                          f"outcome shifts accordingly — verify before acting.",
            "plausibility": round(0.7 - 0.2 * i, 2), "status": "hypothesis-unverified"})
    return scenarios
