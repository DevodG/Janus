"""thinking.py — thinking that gets checked by reality while it thinks.

Beyond chain-of-thought (generate words, hope). Three modes run together:
  SEARCH   — every worker proposes; the verifier rubric is the compass that
             picks the branch (verifier-guided beam, width = all candidates).
  PROGRAM  — multi-step problems are composed as operations and executed,
             not recalled (reasoners.reason_program).
  PREDICT  — the world model forecasts first; the answer must state its
             assumption, so a wrong assumption is visible, not hidden.
The thought trace (branches tried, scores, winner) is returned, inspectable.
"""
from __future__ import annotations

from janus_v2 import agent, reasoners, worldmodel


def think(question: str, sources: list[str] | None = None) -> dict:
    sources = sources or []
    branches = []
    # PREDICT first: forecast + assumption enters the trace before any answer
    forecast = worldmodel.predict(question)
    if forecast:
        branches.append({"mode": "predict", "forecast": str(forecast["forecast"])[:80],
                         "assumption": forecast["assumption"]})
    # SEARCH: all workers fire; evaluator rubric scores every branch
    scored = []
    for ans, conf, method in reasoners.candidates(question):
        errs = agent.verify(ans, sources)
        score = conf - 0.5 * len(errs)
        scored.append((score, ans, conf, method))
        branches.append({"mode": "search", "method": method, "score": round(score, 3)})
    # neural worker joins the search when its brain exists (it must win on score)
    try:
        from janus_v2 import neural
        hit = neural.neural_answer(question)
        if hit:
            errs = agent.verify(hit[0], sources)
            scored.append((hit[1] - 0.5 * len(errs), hit[0], hit[1], hit[2]))
            branches.append({"mode": "search", "method": hit[2], "score": round(hit[1], 3)})
    except Exception:
        pass
    if not scored:
        return {"answer": None, "confidence": 0.0, "method": "none", "branches": branches}
    scored.sort(key=lambda t: -t[0])
    _, ans, conf, method = scored[0]
    return {"answer": ans, "confidence": conf, "method": method, "branches": branches}
