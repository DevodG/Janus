"""
Verification script for the ZeroTrust Scam Journey Guardian.
Simulates a multi-channel scan journey and verifies graph escalation and action guidance.
"""

from app.services.mmsa_engine import MMSADissonanceEngine
from app.services.scam_graph import scam_graph
from app.services.guardian_sensory import guardian_sensory
import os

def test_scam_journey_escalation():
    print("--- 🛡️ VERIFYING ZERO TRUST GUARDIAN ---")
    
    # 1. Step 1: User receives a suspicious SMS
    sms_text = "Urgent: Your bank account is blocked. Call 9876543210 now or click http://bank-secure-login.xyz to verify KYC."
    print("\n[STEP 1] Ingesting Suspicious SMS...")
    
    # Extract entities and signals
    signals = guardian_sensory._detect_signals(sms_text)
    entities = guardian_sensory._extract_entities(sms_text)
    print(f"Detected Signals: {signals}")
    print(f"Extracted Entities: {entities}")
    
    # Add to graph
    scam_graph.add_event("sms", entities, signals)
    
    # 2. Step 2: Check URL Risk
    url = entities["links"][0]
    url_report = guardian_sensory.analyze_url(url)
    print(f"\n[STEP 2] Link Intelligence: {url_report}")
    
    # 3. Step 3: Simulate a follow-up call transcript
    # This should trigger a Journey Escalation because it shares entities
    call_transcript = "This is official bank support. You must use the link sent to 9876543210 immediately to avoid arrest."
    print("\n[STEP 3] Ingesting Follow-up Call (Multi-channel escalation)...")
    
    engine = MMSADissonanceEngine()
    # Mocking paths since we won't actually run heavy MMSA in this test
    # We just want to check the Guardian Fusion logic
    result = engine.analyze(audio_path="/tmp/fake.wav", transcript=call_transcript)
    
    print(f"\n[RESULT] Guardian Score: {result.get('guardian_score')}")
    print(f"Safe Action: {result.get('safe_action')}")
    print(f"Scam Journey: {result.get('scam_journey')}")
    
    # Verification
    if result['guardian_score'] >= 70:
        print("\n✅ SUCCESS: Scam Journey properly escalated to BLOCK level.")
    else:
        print("\n❌ FAILURE: Scam Journey did not reach expected threshold.")

if __name__ == "__main__":
    # Mock MMSA analyze for verification (so we don't need real model weights for this test)
    from unittest.mock import MagicMock
    import app.services.mmsa_engine as mmsa
    
    mmsa.MMSADissonanceEngine._lazy_load = MagicMock()
    mmsa.MMSADissonanceEngine._extract_acoustic_features = MagicMock(return_value={})
    mmsa.MMSADissonanceEngine._get_text_embeddings = MagicMock(return_value={})
    mmsa.MMSADissonanceEngine._update_cognitive_memory = MagicMock()
    
    test_scam_journey_escalation()
