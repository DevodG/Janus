
import os
import sys
from pathlib import Path

# Add backend to path
sys.path.append(str(Path.cwd() / "backend"))

def check_local_env():
    print("=== Local Environment Flag Check ===")
    from app.config import FEATURES, LEARNING_ENABLED
    
    # Check FEATURES dictionary
    all_passed = True
    for name, val in FEATURES.items():
        status = "✅ TRUE" if val else "❌ FALSE"
        print(f"FEATURE_{name.upper():17}: {status}")
        # Simulation and Daemon are usually true, others we just enabled
        if not val and name != "user_patterns" and name != "lora":
             # user_patterns and lora were not in my previous turn's "enable" list
             pass
            
    print(f"{'LEARNING_ENABLED':25}: {'✅ TRUE' if LEARNING_ENABLED else '❌ FALSE'}")
    
    # MiroFish should be False
    from app.config import MIROFISH_ENABLED
    print(f"{'MIROFISH_ENABLED':25}: {'❌ FALSE (Correct)' if not MIROFISH_ENABLED else '⚠️ TRUE (Expected False)'}")
    
    # Specific check for the ones we enabled
    expected_true = ["daemon", "learning", "sentinel", "simulation", "adaptive", "self_training", "experimental"]
    for feat in expected_true:
        if not FEATURES.get(feat):
            print(f"⚠️ ERROR: {feat} is still FALSE but should be TRUE")
            all_passed = False

    if all_passed:
        print("\n🏆 Local Configuration Check: PASSED")
    else:
        print("\n⚠️ Local Configuration Check: FAILED")

if __name__ == "__main__":
    check_local_env()
