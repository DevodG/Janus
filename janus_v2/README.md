# Janus V2 — minimal kernel (general being; finance is one domain, not the boundary)

Identity: a domain-agnostic kernel — reasoning, memory, skills, self-model —
with domain packs (finance first) dissolving into one general system. Breadth
is measured, not claimed: [eval_general.jsonl](eval_general.jsonl) (24 cases
across math, logic, science, geography, history, code) gates alongside the
frozen finance set. "All-knowing" is a direction (retrieval + gated learning),
never a shipped claim.

Implements [Janus-V2-Finalised-Architecture.md](/Users/shashwat/Janus-V2-Finalised-Architecture.md)
alongside V1 (nothing deleted; `app` symlink repointed to `backend/app`).

| Module | Role |
|---|---|
| [eval.py](eval.py) | The one gate: `python -m janus_v2.eval` prints SCORE (first-attempt pass rate on frozen [eval.jsonl](eval.jsonl)) |
| [agent.py](agent.py) | Kernel loop: budgeted `build_context` → `llm()` → deterministic verifier → one retry |
| [memory.py](memory.py) | Single writer: SQLite temporal facts, JSONL cases/corrections, pinned USER.md/STATE.md, diff-logged tools |
| [tools.py](tools.py) | `web_search` / `fetch_page` / `market_quote` behind ring checks + receipt log |
| [consolidate.py](consolidate.py) | Offline USER.md compression proposal (dry-run unless `--approve`) |
| [nano_slowloop.py](nano_slowloop.py) | Prompt propose/evaluate/promote — discards anything under the margin |
| [train_lora.py](train_lora.py) | Manual Kaggle/Unsloth compile + mix manifest; never auto-promotes |

Run tests: `python -m pytest janus_v2/tests -q`

Offline default: `llm()` uses a deterministic finance solver (real arithmetic,
no per-case answers) so eval runs with no API key. Set `JANUS_LLM_BASE_URL`
(+ `JANUS_LLM_MODEL`, `JANUS_LLM_API_KEY`) for a real model; SCORE then
measures that model. Deferred per §4 triggers: LoRA promotion, GEPA, Graphiti,
MCP adapter, voice/dissonance behaviour.
