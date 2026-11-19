"""model_router.py — model layer: route to the strongest available brain.

Providers (first healthy wins, order via JANUS_PROVIDER_ORDER):
  openai-compat  JANUS_LLM_BASE_URL (+ JANUS_LLM_MODEL/API_KEY) — incl. Ollama
                 at http://localhost:11434/v1
  anthropic      ANTHROPIC_API_KEY (+ JANUS_ANTHROPIC_MODEL)
  offline        built-in reasoner registry — never hard-fails, honest confidence
AGI features ride on top in agent.py (workspace, workers, evaluator, memory,
skills, self-model, guardrails); the router only decides whose weights think.
"""
from __future__ import annotations

import os

from janus_v2 import reasoners

MODEL_NAME = "JANUS"
MODEL_CARD = {
    "name": MODEL_NAME,
    "kind": "flagship agentic system (routed models + gated self-improvement)",
    "capabilities": ["general reasoning (math/logic/finance/language/code/science)",
                     "orchestrator-workers with evaluator gate", "single-writer temporal memory",
                     "success-rated skill library", "verbatim corrections retrieved first",
                     "input/output guardrails", "eval-gated capability evolution (loop)"],
    "limits": ["not a from-scratch frontier model — weights come from routed providers",
               "offline mode answers only what reasoners can compute or recall",
               "no AGI claim: breadth is proven per-eval, not asserted"],
}


def _openai_compat(messages):
    import httpx
    base = os.environ["JANUS_LLM_BASE_URL"]
    r = httpx.post(f"{base}/chat/completions",
                   json={"model": os.environ.get("JANUS_LLM_MODEL", "janus-chat"),
                         "messages": messages},
                   headers={"Authorization": f"Bearer {os.environ.get('JANUS_LLM_API_KEY', '')}"},
                   timeout=60)
    return r.json()["choices"][0]["message"]["content"], 0.85, "openai-compat"


def _anthropic(messages):
    import httpx
    system = "\n".join(m["content"] for m in messages if m["role"] == "system")
    convo = [m for m in messages if m["role"] != "system"]
    r = httpx.post("https://api.anthropic.com/v1/messages",
                   json={"model": os.environ.get("JANUS_ANTHROPIC_MODEL", "claude-sonnet-5"),
                         "max_tokens": 1024, "system": system, "messages": convo},
                   headers={"x-api-key": os.environ["ANTHROPIC_API_KEY"],
                            "anthropic-version": "2023-06-01"}, timeout=60)
    text = "".join(b.get("text", "") for b in r.json()["content"])
    return text, 0.85, "anthropic"


def _offline(messages):
    hit = reasoners.solve(messages[-1]["content"])
    if hit:
        return hit[0], hit[1], f"offline:{hit[2]}"
    return ("I do not have a verified answer for that yet; "
            "no source was available to check against."), 0.2, "offline:none"


_PROVIDERS = {"openai-compat": _openai_compat, "anthropic": _anthropic, "offline": _offline}


def available() -> list[str]:
    """Offline-first by design: Janus learns and reasons on its own.

    External APIs are opt-in enhancement only — set JANUS_PROVIDER_ORDER
    (e.g. "anthropic,offline") to let a hosted model think first.
    """
    out = ["offline"]
    if os.environ.get("JANUS_LLM_BASE_URL"):
        out.append("openai-compat")
    if os.environ.get("ANTHROPIC_API_KEY"):
        out.append("anthropic")
    return out


def route(messages) -> tuple[str, float, str]:
    """First healthy provider wins; failures fall through, never hard-fail."""
    order = [p.strip() for p in os.environ.get(
        "JANUS_PROVIDER_ORDER", ",".join(available())).split(",") if p.strip()]
    for name in order:
        fn = _PROVIDERS.get(name)
        if fn is None:
            continue
        try:
            return fn(messages)
        except Exception:
            continue
    return _offline(messages)
