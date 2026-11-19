"""eval.py — the single gate (Finalised Architecture §5).

SCORE = first-attempt (no retry, no user correction) mean pass on the frozen
eval.jsonl, from `python -m janus_v2.eval`, at the fixed context budget.
Diagnostics (Net Rescue, Repeat-Mistake, citation rate) are logged, never gates.
Usage: python -m janus_v2.eval [--eval-file PATH] [--data-dir PATH]
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from janus_v2 import agent  # noqa: E402
from janus_v2.memory import Memory  # noqa: E402

HERE = Path(__file__).parent


def check(case: dict, answer: str) -> bool:
    c = case["check"]
    if c["type"] == "contains":
        a = answer.lower()
        return all(t.lower() in a for t in c["terms"])
    if c["type"] == "numeric":
        found = re.findall(r"-?\d[\d,]*(?:\.\d+)?", answer.replace("$", ""))
        vals = [float(x.replace(",", "")) for x in found]
        exp, tol = c["expected"], c.get("tol", 0.01)
        return any(abs(v - exp) <= max(abs(exp) * tol, 1e-9) for v in vals)
    raise ValueError(f"unknown check type {c['type']}")


def load_cases(path: Path) -> list[dict]:
    return [json.loads(l) for l in path.read_text().splitlines() if l.strip()]


def score(cases: list[dict], memory: Memory, verbose: bool = True) -> dict:
    passed, rows = 0, []
    for case in cases:
        tr = agent.run(case["question"], memory, first_attempt_only=True)
        ok = check(case, tr["answer"])
        passed += ok
        rows.append({"id": case["id"], "pass": ok, "answer": tr["answer"][:160]})
        if verbose:
            print(f"{'PASS' if ok else 'FAIL'} {case['id']}: {tr['answer'][:90]}")
    result = {"n": len(cases), "passed": passed,
              "SCORE": round(passed / len(cases), 4) if cases else 0.0, "rows": rows}
    return result


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--eval-file", default=str(HERE / "eval.jsonl"))
    ap.add_argument("--data-dir", default=None, help="memory dir (default: temp-isolated)")
    args = ap.parse_args()
    import tempfile
    root = Path(args.data_dir) if args.data_dir else Path(tempfile.mkdtemp(prefix="janus-eval-"))
    res = score(load_cases(Path(args.eval_file)), Memory(root))
    print(f"SCORE {res['SCORE']:.4f}  ({res['passed']}/{res['n']} first-attempt passes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
