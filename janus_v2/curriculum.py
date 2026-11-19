"""curriculum.py — self-learning without any API (Voyager automatic curriculum).

Janus generates its own practice problems with programmatic ground truth,
attempts them through the real kernel, and learns three ways:
  1. successes become self-experience (cases + distillation dataset),
  2. failures become a measured gap list that rewrites its own SELF.md,
  3. gaps feed loop.py candidates — extension still requires the eval gate.
Usage: python -m janus_v2.curriculum [--n 40] [--seed 7]
"""
from __future__ import annotations

import argparse
import json
import random
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from janus_v2 import agent, eval as evalmod  # noqa: E402
from janus_v2.memory import Memory  # noqa: E402

HERE = Path(__file__).parent


def generate(rng: random.Random, n: int) -> list[dict]:
    """Self-generated problems; ground truth computed here, never memorized."""
    out = []
    for i in range(n):
        fam = rng.choice(["percent", "average", "arith-seq", "geom-seq", "factorial",
                          "gcd", "workrate", "temp", "area", "interest"])
        a, b, c = rng.randint(2, 90), rng.randint(2, 60), rng.randint(2, 12)
        if fam == "percent":
            q, exp = f"What is {a} percent of {b * 10}?", a / 100 * b * 10
        elif fam == "average":
            q, exp = f"What is the average of {a}, {b}, and {c * 3}?", (a + b + c * 3) / 3
        elif fam == "arith-seq":
            s = [a + k * c for k in range(5)]
            q, exp = f"What is the next number in the sequence {', '.join(map(str, s))}?", s[-1] + c
        elif fam == "geom-seq":
            s = [a * (2 ** k) for k in range(4)]
            q, exp = f"What is the next number in the sequence {', '.join(map(str, s))}?", s[-1] * 2
        elif fam == "factorial":
            k = rng.randint(3, 8)
            import math
            q, exp = f"What is the factorial of {k}?", math.factorial(k)
        elif fam == "gcd":
            import math
            q, exp = f"What is the greatest common divisor of {a * 2} and {b * 2}?", math.gcd(a * 2, b * 2)
        elif fam == "workrate":
            q = (f"Worker A finishes a job alone in {c} hours and worker B finishes it "
                 f"alone in {c * 2} hours. How long do they take working together in hours?")
            exp = 1 / (1 / c + 1 / (c * 2))
        elif fam == "temp":
            q, exp = f"Convert {a + 40} degrees Fahrenheit to Celsius.", (a + 40 - 32) * 5 / 9
        elif fam == "area":
            q, exp = f"If a rectangle has length {a} and width {b}, what is its area?", a * b
        else:
            q, exp = f"What is the simple interest on ${a * 100} at {c}% per year for 2 years?", a * 100 * c / 100 * 2
        out.append({"id": f"self-{i:03d}", "family": fam, "question": q,
                    "check": {"type": "numeric", "expected": round(exp, 4), "tol": 0.02}})
    return out


def learn(n: int = 40, seed: int = 7, mem: Memory | None = None) -> dict:
    mem = mem or Memory()
    cases = generate(random.Random(seed), n)
    passed, gaps, distill = 0, {}, []
    for case in cases:
        tr = agent.run(case["question"], mem, first_attempt_only=True)
        ok = evalmod.check(case, tr["answer"])
        passed += ok
        if ok:
            distill.append({"instruction": case["question"], "response": tr["answer"],
                            "source": "self-curriculum", "method": tr["method"]})
        else:
            gaps[case["family"]] = gaps.get(case["family"], 0) + 1
    (HERE / "data").mkdir(parents=True, exist_ok=True)
    with open(HERE / "data" / "distill.jsonl", "a") as f:
        for row in distill:
            f.write(json.dumps(row) + "\n")
    weaknesses = [f"self-curriculum family '{fam}' failed {cnt}x (seed {seed})"
                  for fam, cnt in sorted(gaps.items(), key=lambda kv: -kv[1])]
    diff = mem.update_self_model(weaknesses)
    result = {"n": n, "passed": passed, "rate": round(passed / n, 4) if n else 0.0,
              "gaps": gaps, "distill_rows_added": len(distill), "self_model_diff": diff,
              "ts": time.time()}
    with open(HERE / "data" / "curriculum_log.jsonl", "a") as f:
        f.write(json.dumps(result) + "\n")
    return result


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=40)
    ap.add_argument("--seed", type=int, default=7)
    args = ap.parse_args()
    r = learn(args.n, args.seed)
    print(f"self-curriculum: {r['passed']}/{r['n']} passed (rate {r['rate']})")
    print(f"gaps written to SELF.md: {r['gaps'] or 'none'} · distill +{r['distill_rows_added']} rows")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
