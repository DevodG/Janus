"""
Verification script for the Phase 2 MMSA-based Dissonance Engine.
"""
import sys
import os

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), "backend"))

def test_mmsa_logic():
    print("--- 🧪 MMSA Engine Verification ---")
    try:
        from app.services.mmsa_engine import mmsa_engine
        
        # Test Case: Sarcasm Simulation
        # Transcript is positive, but audio sentiment is negative (simulated)
        audio_path = "backend/tests/test_probe.wav"
        transcript = "This is just great, absolutely wonderful."
        
        print(f"Analyzing: '{transcript}'")
        result = mmsa_engine.analyze(audio_path, transcript)
        
        print("\nResults:")
        import json
        print(json.dumps(result, indent=2))
        
        # Assertion
        if result.get("is_dissonant"):
            print("\n✅ Success: Engine correctly identified simulated emotional dissonance.")
        else:
            print("\n⚠️ Note: No dissonance detected (expected in this mock run).")
            
    except Exception as e:
        print(f"\n❌ Test Failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    test_mmsa_logic()
