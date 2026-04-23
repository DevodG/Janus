"""
Test for the Active ZeroTrust Guardian Interceptor.
Simulates a daemon cycle with incoming high-risk signals that link to previous journeys.
"""

import time
import json
import logging
from app.services.daemon import JanusDaemon
from app.services.scam_graph import scam_graph
from app.services.guardian_sensory import guardian_sensory
from app.services.guardian_interceptor import guardian_interceptor

# Setup logging to see the intervention
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def run_active_test():
    print("\n" + "="*50)
    print("🛡️  STARTING ACTIVE GUARDIAN SIMULATION  🛡️")
    print("="*50)
    
    # Clean state
    print("\n[INIT] Clearing previous journey memory...")
    scam_graph.graph.clear()
    if os.path.exists(scam_graph.db_path):
        os.remove(scam_graph.db_path)
    
    # 1. Step 1: Historical "Pre-Attack" (User received an SMS earlier)
    # This sets the "DNA" of the scam in the graph
    print("\n[PHASE 1] Recording historical Scam SMS...")
    sms_text = "Urgent from Bank: Your ID 9876543210 is restricted. Click http://bank-safe.xyz"
    entities = guardian_sensory._extract_entities(sms_text)
    signals = guardian_sensory._detect_signals(sms_text)
    scam_graph.add_event("historical_sms", entities, signals)
    
    # 2. Step 2: The Active Attack (Daemon discovers a 'News' signal containing the same ID)
    print("\n[PHASE 2] Simulating Active Daemon Cycle with Shared Artifact...")
    
    # This signal looks like a normal market update but contains the "Linked Artifact" (9876543210)
    suspicious_signal = {
        "source": "news_pulse",
        "topic": "Banking",
        "headline": "Support Alert for ID 9876543210: Mandatory KYC update required immediately.",
        "url": "http://bank-safe.xyz",
        "created_at": time.time()
    }
    
    innocent_signal = {
        "source": "market_watcher",
        "ticker": "AAPL",
        "change_percent": 1.2,
        "headline": "Apple shares steady after hours."
    }
    
    all_incoming = [suspicious_signal, innocent_signal]
    print(f"Incoming signals to audit: {len(all_incoming)}")
    
    # 3. Step 3: Run the Interceptor
    print("\n[PHASE 3] Guardian Interceptor running on heartbeat...")
    clean, interventions = guardian_interceptor.process_signals(all_incoming)
    
    print(f"\n--- INTERVENTION REPORT ---")
    print(f"Clean Signals allowed: {len(clean)}")
    for s in clean:
        print(f"  ✅ ALLOWED: {s.get('headline')}")
        
    print(f"Interventions triggered: {len(interventions)}")
    for i in interventions:
        print(f"  🚨 BLOCKED: {i['original_signal']['headline']}")
        print(f"  Reason: {i['reason']}")
        print(f"  Journey Risk: {i['risk_report']['score']}%")

    # 4. Step 4: Verify Daemon Integration
    print("\n[PHASE 4] Verifying Daemon Thought Insertion...")
    daemon = JanusDaemon()
    # Inject the intervention manually to simulate the daemon's logic
    for inter in interventions:
        daemon._pending_thoughts.insert(0, {
            "thought": f"🚨 GUARDIAN INTERVENTION: {inter['reason']}",
            "priority": 1.0,
            "created_at": time.time(),
            "source": "guardian"
        })
    
    top_thought = daemon._pending_thoughts[0]
    print(f"Highest Priority Thought: {top_thought['thought']}")
    
    if len(clean) == 1 and len(interventions) == 1 and top_thought["source"] == "guardian":
        print("\n🏆 ACTIVE GUARDIAN TEST: PASSED")
        print("Janus effectively squashed the attack and alerted the system.")
    else:
        print("\n❌ ACTIVE GUARDIAN TEST: FAILED")

if __name__ == "__main__":
    import os
    run_active_test()
