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
    logger.info("--- JANUS LITE VERIFICATION START ---")
    
    try:
        from app.graph import get_compiled_graph
        from app.config import HUGGINGFACE_API_KEY, HUGGINGFACE_MODEL, PRIMARY_PROVIDER
        
        logger.info(f"Configuration: Primary={PRIMARY_PROVIDER}")
        
        graph = get_compiled_graph()
        
        # Simple Lite Query
        user_input = "Hello, introduce yourself briefly."
        
        initial_state = {
            "user_input": user_input,
            "complexity": "low",
            "replan_count": 0,
            "context": {}
        }
        
        logger.info("Executing Graph (Lite Mode)...")
        final_state = await graph.ainvoke(initial_state)
        
        logger.info("Graph Execution COMPLETE.")
        
        # Validation
        result = final_state.get("final", {})
        response = result.get("response", "")
        
        print("\n" + "="*50)
        print("LITE VERIFICATION RESULTS")
        print("="*50)
        
        if "<think>" in response:
            print("[PASS] Reasoning Transparency detected.")
        else:
            print("[FAIL] Reasoning Transparency MISSING.")
            
        if "I " in response or "Me " in response or "My " in response:
            print("[PASS] Unified Persona detected.")
        else:
            print("[FAIL] Unified Persona MISSING.")
            
        print("-" * 30)
        print("RESPONSE:")
        print(response)
        print("-" * 30)
        
    except Exception as e:
        logger.error(f"Verification FAILED: {e}")

if __name__ == "__main__":
    asyncio.run(verify())
