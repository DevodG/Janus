from dataclasses import dataclass
from typing import Optional

@dataclass
class RuntimeState:
    db_mode: str = "unknown"   # "postgres" | "fallback_json" | "degraded"
    db_ready: bool = False
    reason: Optional[str] = None

runtime_state = RuntimeState()
