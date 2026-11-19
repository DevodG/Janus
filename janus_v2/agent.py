"""agent.py — Janus kernel: global workspace + plan/act/verify/synthesize.

One shared workspace object is the system's bottleneck (Global Workspace
pattern): planner, reasoners, memory, and verifier all read/write it, so any
component can answer what Janus currently believes and why. Capabilities live
in reasoners.py (pluggable registry); this file owns only the loop.
Constitution: if it mutates state outside this loop, it does not ship.
"""
from __future__ import annotations

import os
import re

from janus_v2 import reasoners

# v0 context budget (tokens, word-count approximation). Budget is code.
BUDGET = {"system": 800, "user": 500, "corrections": 1500, "episodic": 3000,
          "facts": 1500, "receipts": 3000, "reflection": 500}


def _tok(text: str) -> int:
    return len(text.split())


def build_context(question: str, memory, reflection: str = "") -> list[dict]:
    """Assemble context under BUDGET; overflow raises (never silently truncates)."""
    parts: dict[str, str] = {"system": "You are Janus, a general assistant. "
                                       "Answer with the result first, show your working."}
    pinned = memory.pinned()
    if pinned["user"]:
        parts["system"] += "\nUser model:\n" + pinned["user"]
    parts["system"] += "\nSelf model:\n" + memory.self_model()
    skills = memory.skills_for(question)
    if skills:  # retrieved procedures compound instead of being relearned
        parts["system"] += "\nSkills:\n" + "\n".join(
            f"{s['name']}: {'; '.join(s['steps'])}" for s in skills)
    parts["user"] = question
    corr = memory.corrections_for(question)
    if corr:  # verbatim corrections rank before any general instruction
        parts["corrections"] = "\n".join(
            f"Correction: Q={c['question']} A={c['correct']}" for c in corr)
    epi = memory.episodic_for(question)
    if epi:
        parts["episodic"] = "\n".join(str(e.get("answer", ""))[:300] for e in epi)
    facts = memory.facts_now()
    if facts:
        parts["facts"] = "\n".join(
            f"{f['subject']} {f['predicate']} {f['object']} [{f['source']}]" for f in facts[:10])
    if reflection:
        parts["reflection"] = reflection
    for name, text in parts.items():
        cap = BUDGET.get(name, 500)
        if _tok(text) > cap:
            raise OverflowError(f"context section {name}={_tok(text)}tok exceeds budget {cap}")
    msgs = [{"role": "system", "content": parts["system"]}]
    for name in ("corrections", "facts", "episodic", "reflection"):
        if name in parts:
            msgs.append({"role": "system", "content": f"[{name}] {parts[name]}"})
    msgs.append({"role": "user", "content": parts["user"]})
    return msgs


def plan(question: str) -> list[str]:
    """Decompose into steps. The plan, not a domain, drives the pipeline."""
    q = question.lower()
    steps = ["recall-memory"]
    if any(c.isdigit() for c in q):
        steps += ["parse-quantities", "compute"]
    elif "explain" in q or "what" in q or "who" in q or "how many" in q:
        steps += ["recall-knowledge"]
    else:
        steps += ["reason"]
    steps += ["verify", "synthesize"]
    return steps


def new_workspace(question: str) -> dict:
    """The one shared state object every stage broadcasts through."""
    return {"question": question, "plan": plan(question), "steps": [],
            "claims": [], "sources": [], "tools": [], "method": None,
            "answer": "", "confidence": 0.0, "errors": []}


def llm(messages: list[dict]) -> tuple[str, float]:
    """Model call behind one function — FABLE-5.2 router (strongest healthy brain)."""
    from janus_v2 import model_router
    text, conf, _provider = model_router.route(messages)
    return text, conf


def guardrail_in(question: str) -> list[dict]:
    """Input guardrail (OpenAI pattern): tripwire before any work happens."""
    if not question or not question.strip():
        return [{"check_id": "input-tripwire", "expected": "non-empty question", "got": "",
                 "source_id": ""}]
    if len(question) > 4000:
        return [{"check_id": "input-tripwire", "expected": "<=4000 chars", "got": str(len(question)),
                 "source_id": ""}]
    return []


def evaluate(candidates: list[tuple], sources: list[str]) -> tuple | None:
    """Evaluator (evaluator-optimizer): rubric-score worker outputs, pick best.

    Rubric: deterministic verification errors cost most, then confidence.
    Returns (answer, confidence, method) of the winner or None.
    """
    best, best_score = None, -1e9
    for ans, conf, method in candidates:
        score = conf - 0.5 * len(verify(ans, sources))
        if score > best_score:
            best, best_score = (ans, conf, method), score
    return best


def verify(answer: str, sources: list[str]) -> list[dict]:
    """Deterministic verifier — structured error tuples, never prose control flow."""
    errors = []
    if not answer or len(answer.strip()) < 3:
        errors.append({"check_id": "nonempty", "expected": "non-empty answer", "got": answer[:40],
                       "source_id": ""})
    for marker in re.findall(r"\[S(\d+)\]", answer):
        if int(marker) > len(sources):
            errors.append({"check_id": "citation-match", "expected": f"source S{marker} exists",
                           "got": f"{len(sources)} sources", "source_id": f"S{marker}"})
    return errors


def run(question: str, memory, first_attempt_only: bool = False) -> dict:
    """Kernel loop: guardrail -> orchestrate workers -> evaluate -> verify -> synthesize.

    Patterns: orchestrator-workers + evaluator-optimizer (Anthropic), input/output
    guardrails + span tracing (OpenAI), task/progress ledgers (Microsoft Magentic-One).
    first_attempt_only = SCORE gate path (no retry).
    """
    ws = new_workspace(question)
    ws["task_ledger"] = [{"step": s, "status": "pending"} for s in ws["plan"]]
    ws["progress_ledger"] = []
    trip = guardrail_in(question)
    if trip:
        ws["errors"] = trip
        ws["answer"] = "Request blocked by input guardrail."
        ws["progress_ledger"].append("guardrail:tripped")
        trace = {k: ws[k] for k in ("question", "answer", "confidence", "errors", "plan")}
        trace.update({"attempts": 0, "tools": [], "sources": [], "steps": ws["steps"],
                      "method": "guardrail", "claims": [],
                      "task_ledger": ws["task_ledger"], "progress_ledger": ws["progress_ledger"]})
        return trace
    reflection = ""
    attempt = 1
    for attempt in (1, 2):
        msgs = build_context(question, memory, reflection)
        ws["steps"].append(f"span:context(attempt={attempt},msgs={len(msgs)})")
        ws["progress_ledger"].append(f"attempt {attempt}: context built")
        # thinking engine: predict-first + verifier-guided search (incl. neural worker)
        from janus_v2 import thinking
        thought = thinking.think(question, ws["sources"])
        ws["branches"] = thought["branches"]
        winner = (thought["answer"], thought["confidence"], thought["method"]) \
            if thought["answer"] is not None else None
        if winner is None:  # no branch fired -> routed model (FABLE-5.2)
            ans, conf = llm(msgs)
            winner = (ans, conf, "model-router")
        ws["answer"], ws["confidence"], ws["method"] = winner
        ws["claims"] = [ws["answer"]] if ws["answer"] else []
        ws["errors"] = verify(ws["answer"], ws["sources"])
        ws["steps"].append(f"span:act({ws['method']})->verify({len(ws['errors'])} errors)")
        ws["progress_ledger"].append(f"attempt {attempt}: {ws['method']} conf={ws['confidence']}")
        for entry in ws["task_ledger"]:
            entry["status"] = "done"
        if not ws["errors"] or first_attempt_only or attempt == 2:
            break
        reflection = "Previous attempt failed checks: " + "; ".join(
            f"{e['check_id']}: expected {e['expected']}, got {e['got']}" for e in ws["errors"])
    trace = {"question": question, "answer": ws["answer"], "confidence": ws["confidence"],
             "attempts": attempt, "errors": ws["errors"], "tools": ws["tools"],
             "sources": ws["sources"], "plan": ws["plan"], "steps": ws["steps"],
             "method": ws["method"], "claims": ws["claims"],
             "branches": ws.get("branches", []),
             "task_ledger": ws["task_ledger"], "progress_ledger": ws["progress_ledger"]}
    if not first_attempt_only:
        memory.log_case(trace)
    return trace
