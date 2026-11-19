"""Focused tests for the Janus V2 kernel. Run: python -m pytest janus_v2/tests -q"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from janus_v2 import agent, eval as evalmod, tools  # noqa: E402
from janus_v2.memory import Memory  # noqa: E402


@pytest.fixture()
def mem(tmp_path):
    return Memory(tmp_path)


def test_eval_cases_load_and_score(mem):
    cases = evalmod.load_cases(Path(__file__).parents[1] / "eval.jsonl")
    assert len(cases) == 20
    res = evalmod.score(cases, mem, verbose=False)
    assert res["n"] == 20 and 0.0 <= res["SCORE"] <= 1.0


def test_solver_does_real_arithmetic():
    # unseen numbers (not in eval.jsonl): proves computation, not memorised answers
    ans, conf = agent.llm([{"role": "user", "content":
                            "A stock trades at $240 with EPS of $8. What is its P/E ratio?"}])
    assert "30" in ans and conf >= 0.9
    ans2, _ = agent.llm([{"role": "user", "content":
                          "Operating cash flow is $777 and capital expenditure is $111. "
                          "What is free cash flow?"}])
    assert "666" in ans2


def test_context_budget_overflow_raises(mem):
    mem.memory_append("USER.md", "word " * 900)  # > 800-token system budget
    with pytest.raises(OverflowError):
        agent.build_context("anything", mem)


def test_correction_flips_paraphrase(mem):
    q = "What is the capital of France in this fictional world?"
    before = agent.run(q, mem, first_attempt_only=True)["answer"]
    mem.add_correction(q, before, "The capital is Janus City.")
    hits = mem.corrections_for("capital of France fictional world paraphrase")
    assert hits and "Janus City" in hits[0]["correct"]


def test_temporal_fact_invalidation(mem):
    mem.add_fact("AAPL", "thesis", "bullish", valid_from=1000.0)
    mem.add_fact("AAPL", "thesis", "bearish", valid_from=2000.0)
    now = {f["object"] for f in mem.facts_now("AAPL")}
    then = {f["object"] for f in mem.facts_at(1500.0)}
    assert now == {"bearish"} and then == {"bullish"}


def test_memory_append_and_revert(mem):
    did = mem.memory_append("USER.md", "User prefers brief answers.")
    assert "brief" in mem.pinned()["user"]
    assert mem.revert(did) and "brief" not in mem.pinned()["user"]


def test_verifier_flags_fabricated_citation():
    errs = agent.verify("Answer [S9] with no sources.", sources=[])
    assert any(e["check_id"] == "citation-match" for e in errs)
    assert agent.verify("Plain answer, no citations.", sources=[]) == []


def test_world_tool_requires_preview():
    tools.TOOLS["danger"] = (lambda: {"ok": True}, tools.RING_WORLD)
    try:
        with pytest.raises(PermissionError):
            tools.call_tool("danger")
        assert tools.call_tool("danger", preview_token="approved") == {"ok": True}
    finally:
        del tools.TOOLS["danger"]


def test_loop_promotes_only_through_gate(tmp_path, monkeypatch):
    from janus_v2 import loop
    monkeypatch.setattr(loop, "DATA", tmp_path)
    from janus_v2 import reasoners
    monkeypatch.setattr(reasoners, "_LEARNED", tmp_path / "learned.json")
    hist = loop.run_loop(rounds=12)
    events = [h["event"] for h in hist]
    assert "PROMOTED" in events and "DISCARDED" in events  # gate both ways
    assert all(h["trial"]["frozen"] >= h["incumbent"]["frozen"] for h in hist)


def test_general_transfer_not_finance_only():
    ans, _ = agent.llm([{"role": "user", "content": "What is the average of 12, 18, and 30?"}])
    assert "20" in ans
    ans2, _ = agent.llm([{"role": "user", "content":
                          "What is the next number in the sequence 3, 9, 15, 21, 27?"}])
    assert "33" in ans2  # constant-diff sequence, unseen numbers


def test_skill_library_roundtrip(mem):
    mem.add_skill("pe-ratio", "stock price EPS P/E ratio", ["divide price by EPS", "state both inputs"])
    hits = mem.skills_for("What is the P/E ratio of this stock?")
    assert hits and hits[0]["name"] == "pe-ratio"
    mem.record_skill_outcome("pe-ratio", True)
    assert mem.skills_for("P/E ratio stock")[0]["successes"] == 1
    assert "Janus" in mem.self_model()


def test_transfer_unseen_problem_types():
    from janus_v2 import reasoners
    hit = reasoners.solve("Worker A finishes a job alone in 4 hours and worker B "
                          "finishes it alone in 4 hours. How long working together in hours?")
    assert hit and "2" in hit[0] and hit[2] == "math.workrate"  # unseen numbers
    hit2 = reasoners.solve("What is the factorial of 5?")
    assert hit2 and "120" in hit2[0]


def test_workspace_trace_has_plan_and_method(mem):
    tr = agent.run("What is the average of 10 and 20?", mem, first_attempt_only=True)
    assert tr["plan"] and tr["method"] == "math.average" and tr["steps"]


def test_memory_quality_gate_quarantines_bad_writes(mem):
    assert mem.add_fact("", "is", "x") == ""  # rejected, not stored
    assert mem.facts_now() == []
    mem.add_correction("What is this thing?", "wrong", "right")
    mem.add_correction("What is this thing?", "wrong", "right")  # duplicate -> quarantined
    assert len(mem.corrections_for("What is this thing?")) == 1
    assert mem._read("quarantine.jsonl")  # rejections are logged, auditable


def test_input_guardrail_tripwire(mem):
    tr = agent.run("", mem, first_attempt_only=True)
    assert tr["method"] == "guardrail" and tr["errors"]


def test_api_run_and_corrections():
    from fastapi.testclient import TestClient
    from janus_v2.api import app
    c = TestClient(app)
    assert c.get("/health").json()["status"] == "ok"
    r = c.post("/run", json={"question": "What is 15 percent of 240?"}).json()
    assert "36" in r["answer"] and r["method"]
    assert c.post("/corrections", json={"question": "What is this thing?",
                                         "correct": "It is a test."}).status_code == 200
    assert c.get("/eval").json()["eval"]["SCORE"] >= 0.0


def test_model_router_offline_fallback():
    from janus_v2 import model_router
    text, conf, provider = model_router.route(
        [{"role": "user", "content": "What is the factorial of 5?"}])
    assert "120" in text and provider.startswith("offline")
    assert model_router.MODEL_CARD["name"] == "JANUS FABLE-5.2"


def test_stream_endpoint_paces_and_completes():
    from fastapi.testclient import TestClient
    from janus_v2.api import app
    c = TestClient(app)
    with c.stream("POST", "/run/stream", json={"question": "What is 15 percent of 240?"}) as r:
        body = "".join(r.iter_text())
    assert '"done": true' in body and "36" in body
    assert c.get("/model").json()["name"] == "JANUS FABLE-5.2"


def test_self_curriculum_learns_and_updates_self_model(mem):
    from janus_v2 import curriculum
    r = curriculum.learn(n=20, seed=3, mem=mem)
    assert r["n"] == 20 and 0.0 <= r["rate"] <= 1.0
    assert "Janus self-model" in mem.self_model()  # it rewrote its own model
    assert r["distill_rows_added"] == r["passed"]  # only verified wins distill


def test_offline_first_by_default():
    from janus_v2 import model_router
    assert model_router.available()[0] == "offline"


def test_all_agi_components_public_paths():
    from janus_v2 import goals, metacognition, perception, tools, worldmodel
    # world model predicts before acting
    p = worldmodel.predict("What is the next number in the sequence 5, 10, 20, 40?")
    assert p and p["confidence"] > 0
    # imagination proposes, never asserts
    sims = worldmodel.simulate("Grow savings", [{"object": "steady income"}])
    assert sims and all(s["status"] == "hypothesis-unverified" for s in sims)
    # gaps become goals (intrinsic motivation, bounded)
    made = goals.motivate_from_gaps({"sequences": 2})
    assert made and goals.goals()
    assert goals.set_progress(made[0]["id"], 1.0)
    # metacognition measures calibration
    metacognition.log_attempt(0.9, True, "math.test")
    assert metacognition.report()["n"] >= 1
    # perception is a sensor with evidence, not a truth claim
    r = perception.perceive_text("I am worried and this is urgent, a terrible loss")
    assert r["valence"] < 0 and "deception" not in str(r).lower()
    # action tool computes verifiably
    out = tools.call_tool("code_exec", code="print(6*7)")
    assert "42" in out["stdout"]


def test_mcp_client_against_local_echo_server(tmp_path):
    server_py = tmp_path / "echo_mcp.py"
    server_py.write_text(
        "import sys, json\n"
        "for line in sys.stdin:\n"
        "    m = json.loads(line)\n"
        "    if m.get('method') == 'initialize':\n"
        "        print(json.dumps({'jsonrpc':'2.0','id':m['id'],'result':{'protocolVersion':'2024-11-05'}}), flush=True)\n"
        "    elif m.get('method') == 'tools/list':\n"
        "        print(json.dumps({'jsonrpc':'2.0','id':m['id'],'result':{'tools':[{'name':'echo','description':'echo','inputSchema':{'type':'object'}}]}}), flush=True)\n"
        "    elif m.get('method') == 'tools/call':\n"
        "        print(json.dumps({'jsonrpc':'2.0','id':m['id'],'result':{'content':[{'type':'text','text':'echo:'+str(m['params']['arguments'])}]}}), flush=True)\n")
    from janus_v2.mcp_client import McpServer
    srv = McpServer("echo", ["python3", str(server_py)])
    try:
        tools = srv.list_tools()
        assert tools and tools[0]["name"] == "echo"
        out = srv.call("echo", {"x": 1})
        assert "echo" in str(out)
    finally:
        srv.close()


def test_crawler_tiers_and_feed_parsing():
    from janus_v2 import crawlers
    out = crawlers.crawl_page("https://example.com")
    assert out["tier"] in ("trafilatura", "bs4") and "example" in out["text"].lower()


def test_social_posting_guard_and_draft():
    import pytest
    from janus_v2 import tools
    # world ring: no preview token -> refused before any network call
    with pytest.raises(PermissionError):
        tools.call_tool("social_post", platform="mastodon", text="hello")
    # with preview but no credentials -> draft only, never posted
    out = tools.call_tool("social_post", platform="mastodon", text="hello janus",
                          preview_token="approved-by-user")
    assert out["posted"] is False and out["draft"]["status"] == "draft"


def test_stub_quote_never_fabricates():
    out = tools.market_quote("ZZZZINVALID")
    assert out["price"] is None or out["stub"] is False
