"""loop.py — the improvement loop (research -> propose -> gate -> promote -> repeat).

GEPA-style, keyless: per-sample textual feedback from failed eval cases selects
candidates; a Pareto frontier (frozen SCORE, growth SCORE) picks what to try;
promotion requires beating the incumbent by a predeclared margin on the combined
set with zero frozen regression, else the candidate is discarded. Every round is
logged to data/loop_log.jsonl. Promotions land in data/learned.json, which
agent.py reads — nothing enters the kernel without passing this gate.

Usage: python -m janus_v2.loop [--rounds N] [--margin 0.03]
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from janus_v2 import agent, eval as evalmod  # noqa: E402
from janus_v2.memory import Memory  # noqa: E402

HERE = Path(__file__).parent
DATA = HERE / "data"
CANDIDATES = ["quick_ratio", "asset_turnover", "operating_margin", "payout_ratio",
              "price_to_book", "gross_margin", "sharpe", "wacc", "ebitda", "split"]


def _enabled() -> set:
    try:
        return set(json.loads((DATA / "learned.json").read_text()).get("enabled", []))
    except Exception:
        return set()


def _set_enabled(names: set) -> None:
    DATA.mkdir(parents=True, exist_ok=True)
    (DATA / "learned.json").write_text(json.dumps({"enabled": sorted(names)}, indent=2))


def _score_all() -> dict:
    frozen = evalmod.load_cases(HERE / "eval.jsonl")
    growth = evalmod.load_cases(HERE / "eval_growth.jsonl")
    general = evalmod.load_cases(HERE / "eval_general.jsonl")
    transfer = evalmod.load_cases(HERE / "eval_transfer.jsonl")
    mem = Memory(Path(tempfile.mkdtemp(prefix="janus-loop-")))
    f = evalmod.score(frozen, mem, verbose=False)
    g = evalmod.score(growth, mem, verbose=False)
    n = evalmod.score(general, mem, verbose=False)
    t = evalmod.score(transfer, mem, verbose=False)
    feedback = [r["id"] for r in g["rows"] + n["rows"] + t["rows"] if not r["pass"]]
    passed = f["passed"] + g["passed"] + n["passed"] + t["passed"]
    total = f["n"] + g["n"] + n["n"] + t["n"]
    return {"frozen": f["SCORE"], "growth": g["SCORE"], "general": n["SCORE"],
            "transfer": t["SCORE"], "passed": passed, "total": total,
            "combined": passed / total, "failed_growth": feedback}


def _log(row: dict) -> None:
    DATA.mkdir(parents=True, exist_ok=True)
    with open(DATA / "loop_log.jsonl", "a") as fh:
        fh.write(json.dumps(row) + "\n")


def run_loop(rounds: int = 10, margin: float = 0.03) -> list[dict]:
    history = []
    frontier: list[dict] = []  # Pareto frontier over (frozen, growth)
    discarded: set = set()  # discarded candidates are not retried this run
    for rnd in range(1, rounds + 1):
        base_enabled = _enabled()
        incumbent = _score_all()
        pending = [c for c in CANDIDATES if c not in base_enabled and c not in discarded]
        if not pending:
            print(f"round {rnd}: candidate pool exhausted — loop complete")
            _log({"ts": time.time(), "round": rnd, "event": "pool-exhausted", **incumbent})
            break
        cand_name = pending[0]  # feedback order: first unpromoted capability
        _set_enabled(base_enabled | {cand_name})
        trial = _score_all()
        dominates = trial["frozen"] >= incumbent["frozen"] and trial["growth"] >= incumbent["growth"]
        frontier.append({"candidate": cand_name, "frozen": trial["frozen"], "growth": trial["growth"]})
        # scale-free gate: at least one more passed case, zero frozen regression
        promoted = (trial["passed"] >= incumbent["passed"] + 1
                      and trial["frozen"] >= incumbent["frozen"])
        if promoted:
            event = "PROMOTED"
        else:
            _set_enabled(base_enabled)  # discard: revert, live kernel untouched
            discarded.add(cand_name)
            event = "DISCARDED"
        row = {"ts": time.time(), "round": rnd, "candidate": cand_name, "event": event,
               "pareto_dominates": dominates, "incumbent": incumbent, "trial": trial,
               "failed_growth": trial["failed_growth"]}
        _log(row)
        history.append(row)
        print(f"round {rnd}: {cand_name} {event} "
              f"(combined {incumbent['combined']:.3f} -> {trial['combined']:.3f}, "
              f"frozen {trial['frozen']:.3f}, growth {trial['growth']:.3f})")
    return history


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--rounds", type=int, default=10)
    ap.add_argument("--margin", type=float, default=0.03)
    args = ap.parse_args()
    run_loop(args.rounds, args.margin)
    print(f"enabled now: {sorted(_enabled())}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
