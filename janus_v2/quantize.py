"""quantize.py — compress Janus's brain: per-tensor INT8, audited.

Math: for each weight tensor W, scale s = max|W|/127, stored Wq = round(W/s)
as int8 plus one float scale per tensor. Dequantized W' = Wq*s at inference.
Reports: bytes before/after, held-out accuracy raw vs quantized (fresh seed —
never the training seed). The quantized brain ships only if accuracy holds.
Usage: python -m janus_v2.quantize
"""
from __future__ import annotations

import json
import random
import sys
from pathlib import Path

import torch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from janus_v2 import eval as evalmod, neural  # noqa: E402

OUT = neural.CKPT.parent / "brain_int8.pt"


def quantize_state(state: dict) -> tuple[dict, dict]:
    qstate, scales = {}, {}
    for k, w in state.items():
        if w.dtype.is_floating_point and w.numel() > 16:
            s = (w.abs().max() / 127.0).clamp(min=1e-8)
            qstate[k] = torch.round(w / s).clamp(-127, 127).to(torch.int8)
            scales[k] = float(s)
        else:
            qstate[k] = w
    return qstate, scales


def dequantize_state(qstate: dict, scales: dict) -> dict:
    return {k: (w.float() * scales[k] if k in scales else w) for k, w in qstate.items()}


def heldout_accuracy(use_quantized: bool, n: int = 60, seed: int = 999) -> float:
    blob = torch.load(neural.CKPT, map_location=neural.DEVICE, weights_only=False)
    state = blob["state"]
    if use_quantized:
        qs, sc = quantize_state(state)
        state = dequantize_state(qs, sc)
    model = neural.Brain(len(blob["stoi"]) + 1).to(neural.DEVICE)
    model.load_state_dict(state)
    model.eval()
    stoi, itos = blob["stoi"], blob["itos"]
    cases = neural.gen_examples(random.Random(seed), n)
    passed = 0
    with torch.no_grad():
        for text in cases:
            qpart, apart = text.split(" A: ")
            question = qpart[2:]
            ids = [stoi.get(ch, 0) for ch in f"Q: {question} A:"][:110]
            x = torch.tensor([ids], dtype=torch.long, device=neural.DEVICE)
            out = []
            for _ in range(48):
                nxt = int(model(x)[0, -1].argmax())
                ch = itos.get(nxt, "")
                if ch == "<":
                    break
                out.append(ch)
                x = torch.cat([x, torch.tensor([[nxt]], device=neural.DEVICE)], dim=1)
            expected = apart.replace("<END>", "").strip()
            nums_exp = evalmod.re.findall(r"-?\d[\d,]*(?:\.\d+)?", expected)
            nums_got = evalmod.re.findall(r"-?\d[\d,]*(?:\.\d+)?", "".join(out))
            passed += bool(nums_exp and nums_got and
                           abs(float(nums_got[0].replace(",", "")) - float(nums_exp[0].replace(",", ""))) < 0.51)
    return round(passed / n, 4)


def main() -> int:
    blob = torch.load(neural.CKPT, map_location="cpu", weights_only=False)
    raw_bytes = neural.CKPT.stat().st_size
    qs, sc = quantize_state(blob["state"])
    torch.save({"qstate": qs, "scales": sc, "stoi": blob["stoi"], "itos": blob["itos"],
                "params": blob["params"]}, OUT)
    acc_raw = heldout_accuracy(False)
    acc_q = heldout_accuracy(True)
    report = {"params": blob["params"], "fp_bytes": raw_bytes, "int8_bytes": OUT.stat().st_size,
              "compression_x": round(raw_bytes / OUT.stat().st_size, 2),
              "heldout_acc_fp": acc_raw, "heldout_acc_int8": acc_q,
              "ship_quantized": acc_q >= 0.5 and acc_q >= acc_raw - 0.02,
              "registry_gate": "REJECTED" if acc_q < 0.5 else "candidate"}
    print(json.dumps(report, indent=2))
    with open(neural.CKPT.parent / "quantize_report.json", "w") as f:
        json.dump(report, f, indent=2)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
