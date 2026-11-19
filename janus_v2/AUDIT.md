# V1 → V2 audit (subagent sweep, read-only)

Source verdicts: [Janus-V2-Finalised-Architecture.md](/Users/shashwat/Janus-V2-Finalised-Architecture.md) §1/§4. V1 code untouched by this audit.

## Services: 66 entries, ~17,974 LOC → target 1,200–1,500 LOC

- **FOLD/KEEP 8** (concept survives, file deleted): `adaptive_pipeline`/`context_engine`/`query_classifier` → `agent.py`; `case_store`/`memory_manager` → `memory.py`; `crawler`/`external_sources` → `tools.py`; `metrics_collector`/`observation` → `eval.py` + trace.
- **CUT 48**: all autonomous mutators first — `daemon.py` (wires dream/curiosity/learner/training via `main.py`), `dream_processor`, `curiosity_engine`, `autonomous_learner`, `continuous_training`, `self_training`, `self_reflection`, `learning/*` (prompt-evolution, skill-library, freshness-decay), `sentinel/*`, `model_training_scheduler`; plus scam/simulation verticals, duplicate caches, LangGraph `workflow_engine`/`agent_registry`, `reflex_layer`.
- **DEFER 10** (delete now, rebuild on §4 triggers): `dissonance_engine`/`mmsa_engine` (logged sensor only, if calibrated), `fine_tuning_builder`/`module_training` (manual M4), `domain_classifier`, `input_processor`/`tts_engine`/`user_analyzer` (voice after text SCORE stable).

## Memory: 8 physical backends → one writer

Fully absorbed by `janus_v2/memory.py`: case/knowledge JSON (#1/#6), fallback JSON, simulation JSON → `cases.jsonl`; SQLite graph, Postgres entities, scam-graph entities → temporal `facts`. Partial: TF-IDF/pgvector retrieval → word-overlap (FTS5 first, embeddings only if recall fails). **No equivalent (dropped or stays outside)**: HF durability/sync, prompt files, graph traversal, LRU/TTL eviction, feedback table. Two colliding `KnowledgeStore` writers on the same directory resolve to the single writer.

## Frontend: V2 console does not exist yet

All routes (`/`, `/intel`, `/markets`, `/guardian/*`, `/cases`, `/simulation`, `/prompts`, `/config`…) call the V1 API; zero references to `janus_v2`. Transcript/trace, memory browser, eval SCORE, adapter version, and correction surface each need a **new route**, not a remap (closest existing: `/config` aggregates, `/prompts` static V1 prompts).

## Dissonance: keep the sensor, strip the lie detector

Reusable: `dissonance_engine.py` (wav2vec2 + DistilBERT → VAD divergence + librosa prosody) and `guardian_sensory.py` heuristics, as calibrated perception. Overclaim to remove: hand-tuned `EMOTION_TO_VAD`/thresholds with no held-out ROC, `_detect_deception()` turning valence gaps into `deception_probability` + BLOCK/WARN, placeholder video channel ("tri-modal" is bi-modal). The gap-map SVG's `conflict → deception` leap is the part to retire.
