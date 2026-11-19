"""swarm.py — massive-mode workers: parallel reasoning swarms at scale.

Lead agent decomposes; workers run in parallel threads over the same workspace;
results Fuse with provenance. Pattern: Anthropic multi-agent research (+90.2%
on their internal eval over single-agent). Workers are Janus's own reasoners —
no external calls, threads only.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

from janus_v2 import agent, reasoners, thinking


def decompose(question: str) -> list[tuple[str, str]]:
    """Split one question into worker subtasks (scale-free, domain-free)."""
    q = question.lower()
    subs = [("compute", question)]
    if any(k in q for k in ("and", "also", "plus", "then")):
        parts = q.replace(" and then ", " || ").replace(" and also ", " || ").split(" || ")
        subs = [("compute", p.strip()) for p in parts if p.strip()] or subs
    subs.append(("forecast", question))
    subs.append(("verify", question))
    return subs


def _worker(task: tuple[str, str]) -> dict:
    kind, q = task
    if kind == "compute":
        hit = reasoners.solve(q)
        return {"worker": "compute", "answer": hit[0] if hit else None,
                "method": hit[2] if hit else "none"}
    if kind == "forecast":
        from janus_v2 import worldmodel
        f = worldmodel.predict(q)
        return {"worker": "forecast", "answer": str(f["forecast"]) if f else None,
                "method": "worldmodel"}
    thought = thinking.think(q, [])
    return {"worker": "verify", "answer": thought["answer"], "method": thought["method"]}


def run_swarm(question: str, workers: int = 6) -> dict:
    """Parallel swarm: decompose, fan out, fuse best-verified result."""
    tasks = decompose(question)
    outputs = []
    with ThreadPoolExecutor(max_workers=workers) as ex:
        for out in ex.map(_worker, tasks):
            outputs.append(out)
    fused = [o for o in outputs if o["answer"]]
    best = None
    if fused:
        scored = [(o["answer"], 0.7 - 0.1 * i, o["method"]) for i, o in enumerate(fused)]
        winner = agent.evaluate(scored, [])
        best = {"answer": winner[0], "method": winner[2]}
    return {"workers": outputs, "fused": best,
            "provenance": {"fan_out": len(tasks), "workers_used": workers}}
