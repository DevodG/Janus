import asyncio
import json
import logging
import os
import sys

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s — %(message)s")
logger = logging.getLogger("VERIFY")

sys.path.append(os.path.join(os.getcwd(), "backend"))
sys.path.append(os.path.join(os.getcwd(), "backend", "app"))

async def verify():
    logger.info("--- JANUS COGNITIVE EVOLUTION VERIFICATION START ---")
    
    try:
        from app.graph import get_compiled_graph
        from app.services.adaptive_intelligence import adaptive_intelligence
        
        # Set "High Parameters" internally
        adaptive_intelligence.system_personality["cognitive_breadth"] = 0.9
        adaptive_intelligence.system_personality["analytical_depth"] = 0.9
        adaptive_intelligence.system_personality["socratic_depth"] = 0.8
        
        graph = get_compiled_graph()
        
        # High Complexity Query to trigger Scratchpad and Verifier loops
        user_input = "Analyze the ethical implications of using 70B parameter models in autonomous medical triage, specifically focusing on data privacy vs. speed of care."
        
        initial_state = {
            "user_input": user_input,
            "complexity": "high",
            "replan_count": 0,
            "context": {"adaptive_intelligence": adaptive_intelligence.get_context_for_query(user_input, "ethics")}
        }
        
        logger.info("Executing Graph (High Complexity/Evolution Mode)...")
        final_state = await graph.ainvoke(initial_state)
        
        logger.info("--- ARCHITECTURAL TRACE ---")
        if "scratchpad" in final_state:
            print("[PASS] Mental Scratchpad triggered and deliberation recorded.")
            print("-" * 30)
            print("SCRATCHPAD STRATEGY PREVIEW:")
            print(final_state["scratchpad"].get("strategy", "")[:500] + "...")
            print("-" * 30)
        else:
            print("[FAIL] Mental Scratchpad was NOT triggered.")

        result = final_state.get("final", {})
        response = result.get("response", "")
        
        print("\n" + "="*50)
        print("EVOLUTION RESULTS")
        print("="*50)
        
        if "<think>" in response:
            print("[PASS] Evolutionary Reasoning (Think Block) detected.")
        
        if "PRIVACY" in response.upper() or "ETHICS" in response.upper():
            print("[PASS] Complex Synthesis successful.")

        print("-" * 30)
        print("FINAL RESPONSE SAMPLE:")
        print(response[:800] + "...")
        print("-" * 30)
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        logger.error(f"Verification FAILED: {e}")

if __name__ == "__main__":
    asyncio.run(verify())
