# AGI component stack — Janus audit

| # | Component | Status | Where |
|---|---|---|---|
| 1 | Perception (text affect; audio/vision later) | built (text) | `perception.py` |
| 2 | Reasoning (pluggable workers) | built | `reasoners.py` |
| 3 | Planning (decompose → steps → ledger) | built | `agent.plan`, task_ledger |
| 4 | Working memory (global workspace) | built | `agent.new_workspace` |
| 5 | Episodic memory (cases + traces) | built | `memory.py` cases.jsonl |
| 6 | Semantic memory (temporal facts) | built | `memory.py` SQLite facts |
| 7 | Procedural memory (skills, success-rated) | built | `memory.py` skills.jsonl |
| 8 | World model (predict before acting) | built | `worldmodel.py` |
| 9 | Imagination (scenario hypotheses, never direct writes) | built | `worldmodel.simulate` |
| 10 | Goals + intrinsic motivation (gaps → goals) | built | `goals.py` |
| 11 | Metacognition (calibration: predicted vs actual) | built | `metacognition.py` |
| 12 | Self-model (readable, self-rewriting) | built | SELF.md |
| 13 | Learning (curriculum, distillation, gated evolution) | built | `curriculum.py`, `loop.py` |
| 14 | Consolidation / sleep (offline propose, approve) | built | `consolidate.py` |
| 15 | Action (tools + rings; sandboxed code exec) | built | `tools.py` |
| 16 | Communication (API, streaming, console) | built | `api.py`, frontend /v2 |
| 17 | Verification / guardrails | built | `agent.verify`, `guardrail_in` |
| 18 | User model (inspectable, correctable) | built | USER.md pinned block |
| 19 | Emotion-as-claim / deception detection | **refused** | uncalibrated in V1; perception only |
| 20 | Embodiment / robotics | out of scope | software system |

Rule: a component counts as built only with a test through its public path.
