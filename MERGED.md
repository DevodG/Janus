# Merge manifest — V1 → V2 (executed)

Primary system: [janus_v2](/Users/shashwat/Janus/janus_v2) kernel + API + console (/v2).
V1 backend is legacy: salvaged assets folded in, mutators archived, data migrated.

| Action | Detail |
|---|---|
| Data migrated | V1 knowledge + memory_graph.db → V2 single-writer temporal facts (see `janus_v2/data/facts.db`, source `v1-*`) |
| Asset folded | V1 `dissonance_engine.py` → `janus_v2/perception_audio.py` (lazy, perception only) |
| Archived (17) | `archive_v1/services/`: daemon, dream_processor, curiosity_engine, autonomous_learner, continuous_training, self_training, self_reflection, model_training_scheduler, memory_graph, memory_service, persistent_store, fallback_store, simulation_store, sentinel/, learning/, curation/, api_discovery/ |
| Kept legacy | Remaining V1 services + frontend (V2 console lives at frontend /v2) |
| Gate | All janus_v2 evals + tests must pass post-merge; V1 backend imports of archived modules will fail by design |

Rollback: `git status` shows every move; restore with `git checkout -- backend` +
remove `archive_v1/` (nothing was deleted, only relocated).
