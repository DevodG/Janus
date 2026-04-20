"""
Metadata store for API discovery results.
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

try:
    from app.config import DATA_DIR
except ImportError:
    DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"

METADATA_DIR = Path(DATA_DIR) / "api_metadata"
METADATA_DIR.mkdir(parents=True, exist_ok=True)


def save_api_metadata(api_name: str, metadata: Dict[str, Any]) -> None:
    """Save API metadata to local storage."""
    safe_name = api_name.replace("/", "_").replace(" ", "_")
    path = METADATA_DIR / f"{safe_name}.json"
    
    data = {
        **metadata,
        "saved_at": datetime.utcnow().isoformat(),
    }
    
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    
    logger.info(f"Saved metadata for API: {api_name}")


def get_api_metadata(api_name: str) -> Optional[Dict[str, Any]]:
    """Get API metadata from local storage."""
    safe_name = api_name.replace("/", "_").replace(" ", "_")
    path = METADATA_DIR / f"{safe_name}.json"
    
    if not path.exists():
        return None
    
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def list_saved_apis() -> List[str]:
    """List all APIs with saved metadata."""
    return [p.stem for p in METADATA_DIR.glob("*.json")]


def delete_api_metadata(api_name: str) -> bool:
    """Delete API metadata."""
    safe_name = api_name.replace("/", "_").replace(" ", "_")
    path = METADATA_DIR / f"{safe_name}.json"
    
    if not path.exists():
        return False
    
    path.unlink()
    logger.info(f"Deleted metadata for API: {api_name}")
    return True
