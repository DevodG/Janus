"""Janus V2 — minimal kernel per Janus-V2-Finalised-Architecture.md.

agent.py (kernel loop) · memory.py (single writer) · tools.py (3 read tools +
receipts) · eval.py (the one gate: SCORE). Sidecars run offline only:
consolidate.py, nano_slowloop.py, train_lora.py. V1 code is untouched.
"""
