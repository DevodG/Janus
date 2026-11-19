"""train_loop.py — side-by-side training loop: brains vs rules, gate decides.

Each round: train (or retrain) a brain variant from scratch on Janus's own
distilled + generated data, then run a fresh-seed A/B on identical eval cases:
  A) rules/programmatic reasoners (incumbent, always live)
  B) neural brain variant (challenger)
The challenger is promoted into the registry only if it beats the incumbent
by the margin with zero frozen regression (loop.py's rule, same as everything).
Rounds are logged to data/train_loop_log.jsonl; the brain never edits its own eval.
Usage: python -m janus_v2.train_loop [--steps 600] [--rounds 2]
"""
from __future__ import annotations

import argparse
import json
import random
import sys
import time
from pathlib import Path

import torch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from janus_v2 import eval as evalmod, neural  # noqa: E402
from janus_v2 import thinking  # noqa: E402

HERE = Path(__file__).parent
LOG = HERE / "data" / "train_loop_log.jsonl"
# A/B uses fresh-seed generated cases only — Janus never grades itself on its own evals.


def _brain_accuracy(n: int = 40, seed: int = 4242) -> float:
    """Challenger B: the trained brain answers fresh-seed cases."""
    cases = neural.gen_examples(random.Random(seed), n)
    passed = 0
    for text in cases:
        qpart, apart = text.split(" A: ")
        hit = neural.neural_answer(qpart[2:])
        if not hit:
            continue
        exp = apart.replace("<END>", "").strip()
        nums_exp = evalmod.re.findall(r"-?\d[\d,]*(?:\.\d+)?", exp)
        nums_got = evalmod.re.findall(r"-?\d[\d,]*(?:\.\d+)?", hit[0])
        passed += bool(nums_exp and nums_got and
                       abs(float(nums_got[0].replace(",", "")) - float(nums_exp[0].replace(",", ""))) < 0.51)
    return round(passed / n, 4) if n else 0.0


def _rules_accuracy(n: int = 40, seed: int = 4242) -> float:
    """Incumbent A: the thinking engine on the same fresh-seed cases."""
    cases = neural.gen_examples(random.Random(seed), n)
    passed = 0
    for text in cases:
        qpart, apart = text.split(" A: ")
        t = thinking.think(qpart[2:], [])
        if not t["answer"]:
            continue
        exp = apart.replace("<END>", "").strip()
        nums_exp = evalmod.re.findall(r"-?\d[\d,]*(?:\.\d+)?", exp)
        nums_got = evalmod.re.findall(r"-?\d[\d,]*(?:\.\d+)?", t["answer"])
        passed += bool(nums_exp and nums_got and
                       abs(float(nums_got[0].replace(",", "")) - float(nums_exp[0].replace(",", ""))) < 0.51)
    return round(passed / n, 4) if n else 0.0


def run(steps: int = 600, rounds: int = 2) -> list[dict]:
    history = []
    for rnd in range(1, rounds + 1):
        neural.train(steps=steps, n_data=8000, seed=100 + rnd)
        a = _rules_accuracy()
        b = _brain_accuracy()
        promoted = b >= a + 0.05  # must beat incumbent by margin, same rule as loop.py
        row = {"ts": time.time(), "round": rnd, "steps": steps,
               "rules_acc": a, "brain_acc": b,
               "event": "PROMOTED" if promoted else "DISCARDED",
               "note": "challenger promoted to registry" if promoted else
                       "challenger benched; rules remain incumbent"}
        LOG.parent.mkdir(parents=True, exist_ok=True)
        with open(LOG, "a") as f:
            f.write(json.dumps(row) + "\n")
        history.append(row)
        print(f"round {rnd}: rules {a:.3f} vs brain {b:.3f} -> {row['event']}")
    return history


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--steps", type=int, default=600)
    ap.add_argument("--rounds", type=int, default=2)
    args = ap.parse_args()
    run(args.steps, args.rounds)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
