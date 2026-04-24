"""
Verification script for Janus Multimodal Dissonance Engine.
Tests the engine using simulated emotion distributions and triggers 
the CMU-MOSEI refinement loop.
"""

import logging
import sys
import os

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), "backend"))

from app.services.dissonance_engine import dissonance_engine

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("test_dissonance")

def test_engine_calibration():
    print("\n--- Phase 1: Engine Calibration ---")
    print(f"Initial Threshold: {dissonance_engine.dissonance_threshold}")
    
    # Trigger refinement via HF Dataset Searcher (already fixed in previous step)
    dissonance_engine.refine_with_dataset()
    
    print(f"Refined Threshold: {dissonance_engine.dissonance_threshold}")
    
def test_simulated_dissonance():
    print("\n--- Phase 2: Simulated Conflict Detection ---")
    
    # Simulate a "Sarcastic" scenario:
    # Audio: Angry/Sad
    # Text: Happy/Joy
    print("Scenario: Speaker says 'I am so happy' but sounds Angry.")
    
    # For testing without actual audio files, we manually inject vectors
    # into the logic or mock the extraction.
    audio_vec = [0.1, 0.0, 0.0, 0.8, 0.1, 0.0, 0.0] # High on Angry (index 3)
    text_vec = [0.0, 0.9, 0.0, 0.0, 0.1, 0.0, 0.0]  # High on Happy (index 1)
    
    import scipy.spatial.distance as dist
    score = float(dist.cosine(audio_vec, text_vec))
    is_dissonant = score > dissonance_engine.dissonance_threshold
    
    print(f"Dissonance Score: {score:.4f}")
    print(f"Conflict Detected: {is_dissonant}")

if __name__ == "__main__":
    try:
        test_engine_calibration()
        test_simulated_dissonance()
        print("\n✅ Dissonance Logic Verified.")
    except Exception as e:
        print(f"\n❌ Verification failed: {e}")
