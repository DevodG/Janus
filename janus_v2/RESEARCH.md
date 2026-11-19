# White-paper research → implementation map

| Source | Pattern | Janus implementation |
|---|---|---|
| Anthropic, *Building Effective Agents* (2024/25) | Orchestrator-workers; evaluator-optimizer; routing; "add complexity only when it demonstrably improves" | `reasoners.candidates()` (all workers fire) + `agent.evaluate()` rubric pick; loop gate enforces the "demonstrably improves" clause |
| Anthropic multi-agent research system (Jun 2025, +90.2% internal eval) | Lead agent + parallel subagents, shared context | Kernel orchestrates reasoner workers over one workspace; subagent audits in this repo's history |
| OpenAI Agents SDK (2025) | Input/output guardrails with tripwires, handoffs, span tracing, sessions | `agent.guardrail_in()` tripwire; `verify()` output guardrail; `span:` trace steps; workspace = session state |
| Google DeepMind (Gemini/AlphaEvolve, 2025) | Memory taxonomy (session/semantic/procedural/episodic); evaluator-gated evolution of programs | `memory.py`: workspace=session, facts=semantic, skills=procedural, cases=episodic; `loop.py` = AlphaEvolve-style gated evolution of capabilities |
| Microsoft Research (AutoGen v0.4, Magentic-One, 2025) | Orchestrator with task ledger + progress ledger | `task_ledger` / `progress_ledger` in every trace |
| GEPA (ICLR 2026) + Reflexion/Voyager/Letta lineage | Reflective, feedback-driven candidate evolution; skill library; self-editing memory | `loop.py` feedback-mined candidates + Pareto gate; `skills.jsonl` success-rated skills; pinned-block memory edits with revert |

| Crawl4AI (~80k stars, Apache-2.0) / trafilatura / Scrapy lineage | LLM-ready crawl + extraction tiers | `crawlers.py` tiered extraction (trafilatura live, Crawl4AI when installed, bs4 fallback) |
| Firecrawl (~170k stars) | API-shaped crawl service (AGPL) | not embedded — API-shaped contradicts offline-first; pattern noted only |
| browser-use (~120k) / Stagehand (~26k) / Playwright (~99k) | Observe-act-extract in a real browser | `browser.py`: `roam()` (scroll/read/follow) + `act()` (click/fill/extract) with human pacing, robots, caps |
| DuckDuckGo HTML / Stooq / RSS | Keyless search, quotes, feeds | `crawlers.search_web`, `market_quote`, `crawl_feed` — zero API keys |
| MCP (Anthropic standard, 120k+ servers) | Universal tool protocol | `mcp_client.py`: stdio JSON-RPC, tools discovered into the registry behind write-ring receipts |

Rule inherited from all of them: no capability ships on plausibility — only on
measured improvement against frozen evals, with rollback. That is the pipeline.
