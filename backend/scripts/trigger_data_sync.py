
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Add backend to path
sys.path.append(str(Path.cwd() / "backend"))

# Load environment
load_dotenv(Path.cwd() / "backend" / ".env")

from app.services.curation.persistence_manager import PersistenceManager

def trigger_sync():
    print("=== TRIGGERING PERSISTENCE SYNC ===")
    pm = PersistenceManager()
    if not pm.repo_id or not pm.token:
        print("Error: HF_STORE_REPO or HF_TOKEN/HUGGINGFACE_API_KEY not set in environment.")
        return
    
    print(f"Syncing to repo: {pm.repo_id}")
    pm.upload_all()
    print("Sync complete.")

if __name__ == "__main__":
    trigger_sync()
