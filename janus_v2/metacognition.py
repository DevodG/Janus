"""metacognition.py — knowing what it knows: calibration tracking.

Every verified attempt logs (predicted confidence, actual outcome). The
calibration report compares them per confidence band; systematic overconfidence
is a measured weakness the self-model must carry, not a vibe.
"""
from __future__ import annotations

import json
import time
from pathlib import Path

_PATH = Path(__file__).parent / "data" / "calibration.jsonl"


def log_attempt(confidence: float, ok: bool, method: str = "") -> None:
    _PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(_PATH, "a") as f:
        f.write(json.dumps({"ts": time.time(), "confidence": confidence,
                            "ok": bool(ok), "method": method}) + "\n")


def report() -> dict:
    if not _PATH.exists():
        return {"n": 0, "calibration_error": None, "bands": {}}
    rows = [json.loads(l) for l in _PATH.read_text().splitlines() if l.strip()]
    bands: dict[str, list] = {}
    for r in rows:
        band = f"{int(r['confidence'] * 10) / 10:.1f}"
        bands.setdefault(band, []).append(r)
    out, err, cnt = {}, 0.0, 0
    for band, rs in sorted(bands.items()):
        acc = sum(r["ok"] for r in rs) / len(rs)
        out[band] = {"n": len(rs), "predicted": float(band), "actual": round(acc, 3)}
        err += abs(float(band) - acc) * len(rs)
        cnt += len(rs)
    return {"n": cnt, "calibration_error": round(err / cnt, 4) if cnt else None, "bands": out}
