"""train_lora.py — manual Kaggle compile (M4). LoRA-never-base; data is the asset.

Emits an Unsloth training script + a versioned mix manifest (curated corrections
+ 20% replay). It never trains locally and never auto-promotes: run the script
on Kaggle, then gate the adapter with eval.py before any manifest flip.
Usage: python -m janus_v2.train_lora --out /tmp/janus-train
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from janus_v2.memory import Memory  # noqa: E402

SCRIPT = '''# Kaggle kernel — Janus LoRA compile (Unsloth). Manual run only.
# Mix: mix.jsonl (corrections + 20% replay). Adapter -> Hub repo as CANDIDATE.
from unsloth import FastLanguageModel
from trl import SFTTrainer
from datasets import load_dataset
model, tok = FastLanguageModel.from_pretrained("unsloth/Qwen2.5-7B-Instruct", load_in_4bit=True)
model = FastLanguageModel.get_peft_model(model, r=16, lora_alpha=32)
ds = load_dataset("json", data_files="mix.jsonl", split="train")
trainer = SFTTrainer(model=model, tokenizer=tok, train_dataset=ds, max_seq_length=2048)
trainer.train()
model.push_to_hub("{hub_repo}", token=None)  # candidate only — gate with eval.py first
'''


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="/tmp/janus-train")
    ap.add_argument("--hub-repo", default="DevodG/janus-adapters")
    args = ap.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    mem = Memory()
    corr = mem._read("corrections.jsonl")
    cases = mem._read("cases.jsonl")
    replay = cases[: max(1, len(corr) // 4)] if corr else []  # ~20% replay share
    mix = [{"instruction": c["question"], "response": c["correct"], "source": "correction"}
           for c in corr]
    mix += [{"instruction": c.get("question", ""), "response": c.get("answer", ""), "source": "replay"}
            for c in replay]
    (out / "mix.jsonl").write_text("\n".join(json.dumps(m) for m in mix) + ("\n" if mix else ""))
    (out / "train.py").write_text(SCRIPT.format(hub_repo=args.hub_repo))
    manifest = {"rows": len(mix), "corrections": len(corr), "replay": len(replay),
                "gate": "promote iff candidate SCORE >= live + margin on frozen eval, else delete"}
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2))
    print(f"wrote {out}/train.py + mix.jsonl ({len(mix)} rows) + manifest.json")
    print("next: run train.py on Kaggle, then gate the adapter with: python -m janus_v2.eval")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
