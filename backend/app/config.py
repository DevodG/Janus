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


# Runtime state directory.
# Override with JANUS_DATA_DIR when you want state on a persistent volume.
DATA_DIR = Path(os.getenv("JANUS_DATA_DIR", str(BASE_DIR / "data"))).expanduser()
MEMORY_DIR = DATA_DIR / "memory"
SIMULATION_DIR = DATA_DIR / "simulations"
SENTINEL_DIR = DATA_DIR / "sentinel"


# Prompt loader
def load_prompt(name: str) -> str:
    """Load a prompt file by name (without .txt extension)."""
    path = PROMPTS_DIR / f"{name}.txt"
    if not path.exists():
        return f"You are the {name} agent in MiroOrg v2. Be helpful and precise."
    return path.read_text(encoding="utf-8").strip()


APP_VERSION = os.getenv("APP_VERSION", "1.0.1")

PRIMARY_PROVIDER = os.getenv("PRIMARY_PROVIDER", "huggingface").lower()
FALLBACK_PROVIDER = os.getenv("FALLBACK_PROVIDER", "openrouter").lower()

# Hugging Face token support - prioritizes HUGGINGFACE_API_KEY then HF_TOKEN (Spaces default)
HUGGINGFACE_API_KEY = os.getenv("HUGGINGFACE_API_KEY", os.getenv("HF_TOKEN", ""))
HUGGINGFACE_MODEL = os.getenv("HUGGINGFACE_MODEL", "openai/gpt-oss-120b")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
CLOUDFLARE_ACCOUNT_ID = os.getenv("CLOUDFLARE_ACCOUNT_ID", "")
CLOUDFLARE_API_TOKEN = os.getenv("CLOUDFLARE_API_TOKEN", "")

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

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
OPENAI_CHAT_MODEL = os.getenv("OPENAI_CHAT_MODEL", "gpt-4o-mini")
OPENAI_REASONER_MODEL = os.getenv("OPENAI_REASONER_MODEL", "gpt-4o")

TAVILY_API_KEY = os.getenv("TAVILY_API_KEY", "")
# News APIs - multiple providers for redundancy
NEWS_API_KEY = os.getenv("NEWS_API_KEY", os.getenv("NEWSAPI_KEY", ""))
NEWSAPI_KEY = NEWS_API_KEY
NEWDATA_API_KEY = os.getenv("NEWDATA_API_KEY", "")
GNEWS_API_KEY = os.getenv("GNEWS_API_KEY", "")
NEWSAPI_ORG_KEY = os.getenv("NEWSAPI_ORG_KEY", "")
ALPHAVANTAGE_API_KEY = os.getenv("ALPHAVANTAGE_API_KEY", "")
JINA_READER_BASE = os.getenv("JINA_READER_BASE", "https://r.jina.ai/http://")

# Financial data APIs
FINNHUB_API_KEY = os.getenv("FINNHUB_API_KEY", "")
FMP_API_KEY = os.getenv("FMP_API_KEY", "")
EODHD_API_KEY = os.getenv("EODHD_API_KEY", "")

MIROFISH_ENABLED = False  # Deprecated — using native simulation engine
MIROFISH_API_BASE = ""
MIROFISH_TIMEOUT_SECONDS = 0

CRAWLER_ENABLED = os.getenv("CRAWLER_ENABLED", "true").lower() == "true"
CRAWLER_TIMEOUT = int(os.getenv("CRAWLER_TIMEOUT", "30"))

SIMULATION_TRIGGER_KEYWORDS = [
    item.strip().lower()
    for item in os.getenv(
        "SIMULATION_TRIGGER_KEYWORDS",
        "simulate,predict,what if,reaction,scenario,public opinion,policy impact,market impact,digital twin",
    ).split(",")
    if item.strip()
]

# Domain pack configuration
FINANCE_DOMAIN_PACK_ENABLED = (
    os.getenv("FINANCE_DOMAIN_PACK_ENABLED", "true").lower() == "true"
)


# Configuration validation
import logging

logger = logging.getLogger(__name__)


def validate_config():
    """Validate configuration on startup and log warnings/errors."""
    errors = []
    warnings = []

    # Validate primary provider configuration
    primary = PRIMARY_PROVIDER.lower()
    if primary not in ["huggingface", "openrouter", "ollama", "openai"]:
        errors.append(
            f"PRIMARY_PROVIDER '{PRIMARY_PROVIDER}' is not supported. Must be one of: huggingface, openrouter, ollama, openai"
        )

    if primary == "huggingface" and not HUGGINGFACE_API_KEY:
        warnings.append(
            "PRIMARY_PROVIDER is 'huggingface' but HUGGINGFACE_API_KEY is missing - relying on fallback"
        )

    if primary == "openrouter" and not OPENROUTER_API_KEY:
        warnings.append(
            "PRIMARY_PROVIDER is 'openrouter' but OPENROUTER_API_KEY is missing - relying on fallback"
        )

    if primary == "openai" and not OPENAI_API_KEY:
        warnings.append(
            "PRIMARY_PROVIDER is 'openai' but OPENAI_API_KEY is missing - relying on fallback"
        )

    if primary == "ollama" and not OLLAMA_ENABLED:
        warnings.append(
            "PRIMARY_PROVIDER is 'ollama' but OLLAMA_ENABLED is false - relying on fallback"
        )

    # Validate fallback provider configuration
    fallback = FALLBACK_PROVIDER.lower()
    if fallback not in ["huggingface", "openrouter", "ollama", "openai"]:
        errors.append(
            f"FALLBACK_PROVIDER '{FALLBACK_PROVIDER}' is not supported. Must be one of: huggingface, openrouter, ollama, openai"
        )

    if fallback == "huggingface" and not HUGGINGFACE_API_KEY:
        warnings.append(
            "FALLBACK_PROVIDER is 'huggingface' but HUGGINGFACE_API_KEY is missing - fallback will fail"
        )

    if fallback == "openrouter" and not OPENROUTER_API_KEY:
        warnings.append(
            "FALLBACK_PROVIDER is 'openrouter' but OPENROUTER_API_KEY is missing - fallback will fail"
        )

    if fallback == "openai" and not OPENAI_API_KEY:
        warnings.append(
            "FALLBACK_PROVIDER is 'openai' but OPENAI_API_KEY is missing - fallback will fail"
        )

    if fallback == "ollama" and not OLLAMA_ENABLED:
        warnings.append(
            "FALLBACK_PROVIDER is 'ollama' but OLLAMA_ENABLED is false - fallback will fail"
        )

    # Validate optional API keys
    if not TAVILY_API_KEY:
        warnings.append(
            "TAVILY_API_KEY is missing - web search functionality will be limited"
        )

    if not NEWSAPI_KEY:
        warnings.append(
            "NEWS_API_KEY is missing - news research functionality will be limited"
        )

    if not ALPHAVANTAGE_API_KEY:
        warnings.append(
            "ALPHAVANTAGE_API_KEY is missing - financial data functionality will be limited"
        )

    if not FINNHUB_API_KEY:
        warnings.append(
            "FINNHUB_API_KEY is missing - historical data fallback will be limited"
        )

    if not FMP_API_KEY:
        warnings.append(
            "FMP_API_KEY is missing - historical data fallback will be limited"
        )

    if not EODHD_API_KEY:
        warnings.append(
            "EODHD_API_KEY is missing - historical data fallback will be limited"
        )

    # Validate MiroFish configuration
    if MIROFISH_ENABLED and not MIROFISH_API_BASE:
        warnings.append("MIROFISH_ENABLED is true but MIROFISH_API_BASE is missing")

    # Validate data directories
    try:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        MEMORY_DIR.mkdir(parents=True, exist_ok=True)
        SIMULATION_DIR.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        errors.append(f"Failed to create data directories: {e}")

    # Log results — NEVER exit, always allow degraded mode
    if errors:
        logger.error(
            "Configuration validation errors (app will start in degraded mode):"
        )
        for error in errors:
            logger.error(f"  - {error}")

    if warnings:
        logger.warning("Configuration validation completed with warnings:")
        for warning in warnings:
            logger.warning(f"  - {warning}")
    else:
        logger.info("Configuration validation passed")

    return warnings


# ── Data directory initialization ────────────────────────────────────────────

ALL_DATA_DIRS = [
    DATA_DIR,
    MEMORY_DIR,
    SIMULATION_DIR,
    DATA_DIR / "memory",
    DATA_DIR / "simulations",
    DATA_DIR / "knowledge",
    DATA_DIR / "learning",
    DATA_DIR / "cache",
    DATA_DIR / "adaptive",
    DATA_DIR / "sentinel",
    DATA_DIR / "sentinel" / "pending_patches",
    DATA_DIR / "curiosity",
    DATA_DIR / "daemon",
    DATA_DIR / "dreams",
    DATA_DIR / "memory_graph",
    DATA_DIR / "curation",
]


def ensure_data_dirs():
    """Idempotent: create all runtime data dirs. Call once at startup."""
    for d in ALL_DATA_DIRS:
        try:
            d.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            logger.warning(f"Failed to create data dir {d}: {e}")


# ── Feature Flags ────────────────────────────────────────────────────────────

FEATURES = {
    "daemon": os.getenv("FEATURE_DAEMON", "true").lower() == "true",
    "learning": os.getenv("FEATURE_LEARNING", "false").lower() == "true",
    "sentinel": os.getenv("SENTINEL_ENABLED", os.getenv("FEATURE_SENTINEL", "true")).lower() == "true",
    "simulation": os.getenv("SIMULATION_ENABLED", "true").lower() == "true",
    "adaptive": os.getenv("FEATURE_ADAPTIVE", "false").lower() == "true",
    "self_training": os.getenv("FEATURE_SELF_TRAINING", "false").lower() == "true",
    "experimental": os.getenv("FEATURE_EXPERIMENTAL", "false").lower() == "true",
    "user_patterns": os.getenv("FEATURE_USER_PATTERNS", "false").lower() == "true",
    "lora": os.getenv("FEATURE_LORA", "false").lower() == "true",
}


def get_feature_status():
    """Return current feature flag status."""
    return {
        name: {"enabled": enabled, "env_var": f"FEATURE_{name.upper()}"}
        for name, enabled in FEATURES.items()
    }


# ── Learning layer configuration ─────────────────────────────────────────────

LEARNING_ENABLED = os.getenv("LEARNING_ENABLED", "false").lower() == "true"
KNOWLEDGE_MAX_SIZE_MB = int(os.getenv("KNOWLEDGE_MAX_SIZE_MB", "200"))
LEARNING_SCHEDULE_INTERVAL = int(os.getenv("LEARNING_SCHEDULE_INTERVAL", "6"))  # hours
LEARNING_BATCH_SIZE = int(os.getenv("LEARNING_BATCH_SIZE", "10"))
LEARNING_TOPICS = [
    item.strip()
    for item in os.getenv(
        "LEARNING_TOPICS",
        "finance,markets,global equities,top companies,central banks,semiconductors,energy,technology,policy,india markets,china economy",
    ).split(",")
    if item.strip()
]


def get_config():
    """Get configuration object for dependency injection."""

    class Config:
        app_version = APP_VERSION
        primary_provider = PRIMARY_PROVIDER
        fallback_provider = FALLBACK_PROVIDER

        huggingface_api_key = HUGGINGFACE_API_KEY
        huggingface_model = HUGGINGFACE_MODEL

        gemini_api_key = GEMINI_API_KEY
        groq_api_key = GROQ_API_KEY
        cloudflare_account_id = CLOUDFLARE_ACCOUNT_ID
        cloudflare_api_token = CLOUDFLARE_API_TOKEN

        openrouter_api_key = OPENROUTER_API_KEY
        openrouter_base_url = OPENROUTER_BASE_URL
        openrouter_chat_model = OPENROUTER_CHAT_MODEL
        openrouter_reasoner_model = OPENROUTER_REASONER_MODEL

        ollama_enabled = OLLAMA_ENABLED
        ollama_base_url = OLLAMA_BASE_URL
        ollama_chat_model = OLLAMA_CHAT_MODEL
        ollama_reasoner_model = OLLAMA_REASONER_MODEL

        openai_api_key = OPENAI_API_KEY
        openai_base_url = OPENAI_BASE_URL
        openai_chat_model = OPENAI_CHAT_MODEL
        openai_reasoner_model = OPENAI_REASONER_MODEL

        tavily_api_key = TAVILY_API_KEY
        newsapi_key = NEWSAPI_KEY
        alphavantage_api_key = ALPHAVANTAGE_API_KEY

        mirofish_enabled = MIROFISH_ENABLED
        mirofish_api_base = MIROFISH_API_BASE

        crawler_enabled = CRAWLER_ENABLED
        crawler_timeout = CRAWLER_TIMEOUT

        data_dir = str(DATA_DIR)
        memory_dir = str(MEMORY_DIR)
        simulation_dir = str(SIMULATION_DIR)
        prompts_dir = str(PROMPTS_DIR)

        learning_enabled = LEARNING_ENABLED
        knowledge_max_size_mb = KNOWLEDGE_MAX_SIZE_MB
        learning_schedule_interval = LEARNING_SCHEDULE_INTERVAL
        learning_batch_size = LEARNING_BATCH_SIZE
        learning_topics = LEARNING_TOPICS

    return Config()
