import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

try:
    from dotenv import load_dotenv
    # Load .env from the backend directory
    env_path = BASE_DIR.parent / ".env"
    load_dotenv(env_path)
except ImportError:
    pass
PROMPTS_DIR = BASE_DIR / "prompts"
DATA_DIR = BASE_DIR / "data"
MEMORY_DIR = DATA_DIR / "memory"
SIMULATION_DIR = DATA_DIR / "simulations"

APP_VERSION = os.getenv("APP_VERSION", "0.3.0")

PRIMARY_PROVIDER = os.getenv("PRIMARY_PROVIDER", "openrouter").lower()
FALLBACK_PROVIDER = os.getenv("FALLBACK_PROVIDER", "ollama").lower()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_BASE_URL = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
OPENROUTER_CHAT_MODEL = os.getenv("OPENROUTER_CHAT_MODEL", "openrouter/free")
OPENROUTER_REASONER_MODEL = os.getenv("OPENROUTER_REASONER_MODEL", "openrouter/free")
OPENROUTER_SITE_URL = os.getenv("OPENROUTER_SITE_URL", "")
OPENROUTER_APP_NAME = os.getenv("OPENROUTER_APP_NAME", "MiroOrg Basic")

OLLAMA_ENABLED = os.getenv("OLLAMA_ENABLED", "true").lower() == "true"
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434/api")
OLLAMA_CHAT_MODEL = os.getenv("OLLAMA_CHAT_MODEL", "qwen2.5:3b-instruct")
OLLAMA_REASONER_MODEL = os.getenv("OLLAMA_REASONER_MODEL", "qwen2.5:3b-instruct")

TAVILY_API_KEY = os.getenv("TAVILY_API_KEY", "")
NEWSAPI_KEY = os.getenv("NEWSAPI_KEY", "")
ALPHAVANTAGE_API_KEY = os.getenv("ALPHAVANTAGE_API_KEY", "")
JINA_READER_BASE = os.getenv("JINA_READER_BASE", "https://r.jina.ai/http://")

MIROFISH_ENABLED = os.getenv("MIROFISH_ENABLED", "false").lower() == "true"
MIROFISH_API_BASE = os.getenv("MIROFISH_API_BASE", "http://127.0.0.1:5001")
MIROFISH_TIMEOUT_SECONDS = int(os.getenv("MIROFISH_TIMEOUT_SECONDS", "120"))
MIROFISH_HEALTH_PATH = os.getenv("MIROFISH_HEALTH_PATH", "/health")
MIROFISH_RUN_PATH = os.getenv("MIROFISH_RUN_PATH", "/simulation/run")
MIROFISH_STATUS_PATH = os.getenv("MIROFISH_STATUS_PATH", "/simulation/{id}")
MIROFISH_REPORT_PATH = os.getenv("MIROFISH_REPORT_PATH", "/simulation/{id}/report")
MIROFISH_CHAT_PATH = os.getenv("MIROFISH_CHAT_PATH", "/simulation/{id}/chat")

SIMULATION_TRIGGER_KEYWORDS = [
    item.strip().lower()
    for item in os.getenv(
        "SIMULATION_TRIGGER_KEYWORDS",
        "simulate,predict,what if,reaction,scenario,public opinion,policy impact,market impact,digital twin",
    ).split(",")
    if item.strip()
]
