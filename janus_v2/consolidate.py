"""consolidate.py — offline sleep consolidation (never in-request).

Proposes a compressed USER.md from the day's cases; writes nothing until the
user approves the diff (--approve). Dreams propose, the gate disposes.
Usage: python -m janus_v2.consolidate [--approve]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from janus_v2.memory import Memory  # noqa: E402


def propose(mem: Memory) -> str:
    cases = mem._read("cases.jsonl")
    corr = mem._read("corrections.jsonl")
    lines = [f"# USER.md (proposed)\nCases logged: {len(cases)} · Corrections: {len(corr)}"]
    for c in corr[-10:]:
        lines.append(f"- Corrected: {c['question'][:80]} -> {c['correct'][:120]}")
    return "\n".join(lines) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--approve", action="store_true", help="write the proposal to USER.md")
    args = ap.parse_args()
    mem = Memory()
    text = propose(mem)
    print(text)
    if args.approve:
        diff_id = mem.memory_append("USER.md", text)
        print(f"applied (diff {diff_id}; revert via Memory.revert)")
    else:
        print("[dry-run] re-run with --approve to apply")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
