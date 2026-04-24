import sys
from app.services.hf_dataset_searcher import hf_dataset_searcher
print("Streaming datasets sample...")
samples = hf_dataset_searcher.stream_dataset_sample("Open-Orca/OpenOrca", max_samples=3)
if samples:
    print(f"Got {len(samples)} samples:")
    for s in samples:
        print(str(s)[:200])
else:
    print("No samples returned.")
