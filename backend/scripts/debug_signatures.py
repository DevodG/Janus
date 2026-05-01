
import sys
import inspect
from pathlib import Path

# Add backend to path
sys.path.append(str(Path.cwd() / "backend"))

def debug_signatures():
    print("=== DEBUG SIGNATURES ===")
    
    # Check KnowledgeStore
    try:
        from app.memory import knowledge_store
        print(f"knowledge_store instance: {knowledge_store}")
        print(f"knowledge_store class: {knowledge_store.__class__}")
        print(f"Defined in: {inspect.getfile(knowledge_store.__class__)}")
        
        search_sig = inspect.signature(knowledge_store.search)
        print(f"knowledge_store.search signature: {search_sig}")
    except Exception as e:
        print(f"Error inspecting knowledge_store: {e}")

    print("-" * 20)
    
    # Check AutonomousLearner
    try:
        from app.services.autonomous_learner import autonomous_learner
        print(f"autonomous_learner instance: {autonomous_learner}")
        print(f"Defined in: {inspect.getfile(autonomous_learner.__class__)}")
        
        run_sig = inspect.signature(autonomous_learner.run_learning_cycle)
        print(f"autonomous_learner.run_learning_cycle signature: {run_sig}")
    except Exception as e:
        print(f"Error inspecting autonomous_learner: {e}")

if __name__ == "__main__":
    debug_signatures()
