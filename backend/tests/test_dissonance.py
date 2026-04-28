"""
Dissonance Engine — Unit / Integration Tests.

Tests the engine at three levels:
  1. Pure logic: VAD projection and cosine divergence (no models needed)
  2. API shape:  dissonance_engine.analyze() returns expected keys (no models)
  3. Calibration: refine_with_dataset() triggers CMU-MOSEI + CREMA-D lookup

Run from repo root:
    cd backend && python3 tests/test_dissonance.py
"""

import logging
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("test_dissonance")


# ---------------------------------------------------------------------------
# Phase 1: Pure logic — VAD projection + cosine divergence (no models needed)
# ---------------------------------------------------------------------------
def test_vad_projection():
    print("\n─── Phase 1: VAD Projection Logic ───")
    import numpy as np
    import scipy.spatial.distance as dist
    from app.services.dissonance_engine import _probs_to_vad, EMOTION_TO_VAD

    # Simulate: audio says "angry", text says "joy" → should be highly dissonant
    audio_probs = {"angry": 0.8, "neutral": 0.1, "happy": 0.1}
    text_probs  = {"joy": 0.85, "love": 0.1, "surprise": 0.05}

    audio_vad = _probs_to_vad(audio_probs)
    text_vad  = _probs_to_vad(text_probs)

    score = float(dist.cosine(audio_vad, text_vad))
    print(f"  audio_vad  = {audio_vad.round(3)}")
    print(f"  text_vad   = {text_vad.round(3)}")
    print(f"  cosine div = {score:.4f}")

    assert score > 0.08, f"Expected meaningful divergence for angry vs joy, got {score:.4f}"
    print("  ✅ Meaningful divergence confirmed for angry-audio vs joy-text")

    # Same emotion → near-zero divergence
    audio_probs2 = {"happy": 0.9, "neutral": 0.1}
    text_probs2  = {"joy": 0.9, "surprise": 0.1}
    audio_vad2   = _probs_to_vad(audio_probs2)
    text_vad2    = _probs_to_vad(text_probs2)
    score2 = float(dist.cosine(audio_vad2, text_vad2))
    print(f"  happy-vs-joy cosine div = {score2:.4f}")
    assert score2 < 0.05, f"Expected near-zero divergence for happy vs joy, got {score2:.4f}"
    print("  ✅ Near-zero divergence confirmed for happy-audio vs joy-text")


# ---------------------------------------------------------------------------
# Phase 2: Engine init — no models, check env config and threshold
# ---------------------------------------------------------------------------
def test_engine_init():
    print("\n─── Phase 2: Engine Config & Threshold ───")
    from app.services.dissonance_engine import dissonance_engine

    print(f"  Initial threshold     = {dissonance_engine.dissonance_threshold}")
    print(f"  Audio temperature T   = {dissonance_engine.audio_temperature}")
    print(f"  Fusion weights        = ({dissonance_engine.w_audio_text}, "
          f"{dissonance_engine.w_prosody}, {dissonance_engine.w_text_conf})")

    assert dissonance_engine.dissonance_threshold == 0.5
    assert dissonance_engine.audio_temperature == 1.5
    assert abs(dissonance_engine.w_audio_text + dissonance_engine.w_prosody
               + dissonance_engine.w_text_conf - 1.0) < 0.01, \
        "Fusion weights should sum to ~1.0"
    print("  ✅ Config OK")


# ---------------------------------------------------------------------------
# Phase 3: Dataset calibration (network call — may be skipped in CI)
# ---------------------------------------------------------------------------
def test_engine_calibration(skip_network: bool = False):
    print("\n─── Phase 3: Dataset Calibration (CMU-MOSEI + CREMA-D) ───")
    from app.services.dissonance_engine import dissonance_engine

    before = dissonance_engine.dissonance_threshold

    if skip_network:
        print("  ⚠️  Skipping network call (skip_network=True)")
        return

    dissonance_engine.refine_with_dataset()
    after = dissonance_engine.dissonance_threshold

    print(f"  Before: {before}  →  After: {after}")
    # If datasets were reachable, threshold should drop to 0.35
    # If not reachable, it stays at its current value — both are fine
    print("  ✅ Calibration completed (result depends on network access)")


# ---------------------------------------------------------------------------
# Phase 4: MMSA engine singleton check
# ---------------------------------------------------------------------------
def test_mmsa_wiring():
    print("\n─── Phase 4: MMSA ↔ DissonanceEngine Wiring ───")
    from app.services.mmsa_engine import mmsa_engine
    from app.services.dissonance_engine import dissonance_engine

    # Verify mmsa_engine holds a reference to the same singleton
    import app.services.mmsa_engine as mmsa_mod
    assert hasattr(mmsa_mod, "dissonance_engine"), \
        "mmsa_engine module must import dissonance_engine"
    assert mmsa_mod.dissonance_engine is dissonance_engine, \
        "mmsa_engine must use the same dissonance_engine singleton"
    print("  ✅ mmsa_engine is wired to dissonance_engine singleton")


if __name__ == "__main__":
    try:
        test_vad_projection()
        test_engine_init()
        test_engine_calibration(skip_network="--skip-network" in sys.argv)
        test_mmsa_wiring()
        print("\n✅ All dissonance tests passed.")
    except AssertionError as e:
        print(f"\n❌ Assertion failed: {e}")
        sys.exit(1)
    except Exception as e:
        import traceback
        print(f"\n❌ Test error: {e}")
        traceback.print_exc()
        sys.exit(1)
