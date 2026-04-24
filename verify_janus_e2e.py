import asyncio
import json
import logging
import os
import sys

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s — %(message)s")
logger = logging.getLogger("VERIFY")

# Add backend and app to path
sys.path.append(os.path.join(os.getcwd(), "backend"))
sys.path.append(os.path.join(os.getcwd(), "backend", "app"))

async def verify():
    logger.info("--- JANUS E2E VERIFICATION START ---")
    
    try:
        from app.graph import get_compiled_graph
        from app.config import HUGGINGFACE_API_KEY, HUGGINGFACE_MODEL, PRIMARY_PROVIDER
        
        logger.info(f"Configuration: Primary={PRIMARY_PROVIDER}, Model={HUGGINGFACE_MODEL}")
        logger.info(f"HF Token present: {bool(HUGGINGFACE_API_KEY)}")
        
        graph = get_compiled_graph()
        
        # Test Query
        user_input = "Provide a deep analysis of the current AI chip market competition, incorporating your formed opinions on energy efficiency."
        
        initial_state = {
            "user_input": user_input,
            "complexity": "high",
            "replan_count": 0,
            "context": {
                "self_reflection": {
                    "opinions": [
                        {"topic": "energy efficiency", "statement": "Energy efficiency is no longer just a perk; it is the primary bottleneck for massive-scale AI inference, favoring custom silicon like TPUs and LPUs over generic GPUs."}
                    ]
                }
            }
        }
        
        logger.info("Executing Graph (this may take a minute surring HF)...")
        final_state = await graph.ainvoke(initial_state)
        
        logger.info("Graph Execution COMPLETE.")
        
        # Validation
        result = final_state.get("final", {})
        response = result.get("response", "")
        
        print("\n" + "="*50)
        print("VERIFICATION RESULTS")
        print("="*50)
        
        if "<think>" in response:
            print("[PASS] Reasoning Transparency (<think> block) detected.")
        else:
            print("[FAIL] Reasoning Transparency (<think> block) MISSING.")
            
        if "I " in response or "My " in response or "me " in response.lower():
            print("[PASS] Unified Persona (First-person pronouns) detected.")
        else:
            print("[FAIL] Unified Persona (First-person pronouns) MISSING.")
            
        research = final_state.get("research", {})
        if research:
            print(f"[PASS] Research node contributed findings (Sources: {len(research.get('sources', []))}).")
        else:
            print("[FAIL] Research node seems empty.")
            
        print("-" * 30)
        print("SAMPLE RESPONSE PREVIEW:")
        if response:
            print(response[:800] + "...")
        else:
            print("EMPTY RESPONSE!")
        print("-" * 30)
        
    except Exception as e:
        logger.error(f"Verification FAILED with error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(verify())
