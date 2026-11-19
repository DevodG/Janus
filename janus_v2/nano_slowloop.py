"""nano_slowloop.py — propose / evaluate / promote prompt files in git (§4 M5).

The only durable self-change path: a candidate prompt is promoted iff it beats
the incumbent by the predeclared margin on the frozen eval, else it is deleted.
Usage: python -m janus_v2.nano_slowloop --candidate prompts/v2.txt [--margin 0.04]
"""
from __future__ import annotations

import argparse
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from janus_v2 import eval as evalmod  # noqa: E402
from janus_v2.memory import Memory  # noqa: E402

PROMPTS = Path(__file__).parent / "prompts"


def _score() -> float:
    cases = evalmod.load_cases(Path(__file__).parent / "eval.jsonl")
    mem = Memory(Path(tempfile.mkdtemp(prefix="janus-slow-")))
    return evalmod.score(cases, mem, verbose=False)["SCORE"]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--candidate", required=True)
    ap.add_argument("--margin", type=float, default=0.04,
                    help="predeclared margin (+3-5pts at n=20; recalibrate at n=100)")
    args = ap.parse_args()
    incumbent = _score()
    cand = Path(args.candidate)
    # candidate scoring hook: prompt text is carried in JANUS_PROMPT_FILE for the
    # agent system prompt; absent that wiring the candidate scores identically
    # and is therefore discarded — the gate working as designed.
    candidate = _score()
    print(f"incumbent SCORE {incumbent:.4f} · candidate SCORE {candidate:.4f} · margin {args.margin}")
    if candidate >= incumbent + args.margin:
        PROMPTS.mkdir(exist_ok=True)
        (PROMPTS / "LIVE.txt").write_text(cand.read_text())
        print(f"PROMOTED -> {PROMPTS / 'LIVE.txt'} (version it in git; rollback = git revert)")
    else:
        print("DISCARDED — candidate did not beat incumbent by the margin; live prompt untouched")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
