"""api.py — Janus V2 service (FastAPI, port 7860 by default).

Endpoints: /health /run /memory /corrections /eval /loop/status.
Run: uvicorn janus_v2.api:app --port 7860   (from repo root)
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from fastapi import FastAPI  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402
from pydantic import BaseModel  # noqa: E402

from janus_v2 import agent, eval as evalmod, loop as loopmod  # noqa: E402
from janus_v2.memory import Memory  # noqa: E402

app = FastAPI(title="Janus V2", version="2.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"],
                   allow_headers=["*"])
_mem = Memory()


class RunIn(BaseModel):
    question: str


class CorrectionIn(BaseModel):
    question: str
    wrong: str = ""
    correct: str


class FactIn(BaseModel):
    subject: str
    predicate: str
    object: str
    source: str = "api"


@app.get("/model")
def model():
    from janus_v2 import model_router
    return {**model_router.MODEL_CARD, "providers_available": model_router.available()}


@app.post("/run/stream")
async def run_stream(body: RunIn):
    """SSE stream, server-paced at ~20 tokens/s; callers need not specify pacing."""
    import asyncio
    import json as _json
    from fastapi.responses import StreamingResponse

    async def gen():
        trace = agent.run(body.question, _mem)
        words = trace["answer"].split(" ")
        for i, w in enumerate(words):
            yield f"data: {_json.dumps({'token': w + (' ' if i < len(words) - 1 else ''), 'done': False})}\n\n"
            await asyncio.sleep(0.05)  # ~20/s pacing, server-side by default
        yield f"data: {_json.dumps({'token': '', 'done': True, 'method': trace['method'], 'confidence': trace['confidence']})}\n\n"

    return StreamingResponse(gen(), media_type="text/event-stream")


@app.get("/live")
def live():
    from janus_v2 import sensors
    return sensors.snapshot()


@app.get("/health")
def health():
    return {"status": "ok", "service": "janus-v2", "enabled": sorted(loopmod._enabled())}


@app.post("/run")
def run(body: RunIn):
    return agent.run(body.question, _mem)


@app.get("/memory")
def memory():
    return {"pinned": _mem.pinned(), "self_model": _mem.self_model(),
            "facts": _mem.facts_now(), "skills": _mem._read("skills.jsonl")}


@app.get("/corrections")
def corrections():
    return {"corrections": _mem._read("corrections.jsonl")}


@app.post("/corrections")
def add_correction(body: CorrectionIn):
    _mem.add_correction(body.question, body.wrong, body.correct)
    return {"stored": True}


@app.post("/facts")
def add_fact(body: FactIn):
    fid = _mem.add_fact(body.subject, body.predicate, body.object, source=body.source)
    return {"stored": bool(fid), "id": fid}


@app.get("/eval")
def eval_scores():
    import tempfile
    mem = Memory(Path(tempfile.mkdtemp(prefix="janus-api-eval-")))
    out = {}
    for name in ("eval", "eval_growth", "eval_general", "eval_transfer"):
        res = evalmod.score(evalmod.load_cases(Path(__file__).parent / f"{name}.jsonl"),
                            mem, verbose=False)
        out[name] = {"SCORE": res["SCORE"], "passed": res["passed"], "n": res["n"]}
    return out


@app.get("/loop/status")
def loop_status():
    log = Path(__file__).parent / "data" / "loop_log.jsonl"
    rows = []
    if log.exists():
        import json
        rows = [json.loads(l) for l in log.read_text().splitlines() if l.strip()][-20:]
    return {"enabled": sorted(loopmod._enabled()), "recent": rows}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", "7860")))
