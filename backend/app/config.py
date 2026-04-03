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

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
OPENAI_CHAT_MODEL = os.getenv("OPENAI_CHAT_MODEL", "gpt-4o-mini")
OPENAI_REASONER_MODEL = os.getenv("OPENAI_REASONER_MODEL", "gpt-4o")

TAVILY_API_KEY = os.getenv("TAVILY_API_KEY", "")
NEWSAPI_KEY = os.getenv("NEWSAPI_KEY", "")
ALPHAVANTAGE_API_KEY = os.getenv("ALPHAVANTAGE_API_KEY", "")
JINA_READER_BASE = os.getenv("JINA_READER_BASE", "https://r.jina.ai/http://")

MIROFISH_ENABLED = os.getenv("MIROFISH_ENABLED", "false").lower() == "true"
MIROFISH_API_BASE = os.getenv("MIROFISH_API_BASE", "http://127.0.0.1:5001")
MIROFISH_TIMEOUT_SECONDS = int(os.getenv("MIROFISH_TIMEOUT_SECONDS", "120"))

SIMULATION_TRIGGER_KEYWORDS = [
    item.strip().lower()
    for item in os.getenv(
        "SIMULATION_TRIGGER_KEYWORDS",
        "simulate,predict,what if,reaction,scenario,public opinion,policy impact,market impact,digital twin",
    ).split(",")
    if item.strip()
]

# Domain pack configuration
FINANCE_DOMAIN_PACK_ENABLED = os.getenv("FINANCE_DOMAIN_PACK_ENABLED", "true").lower() == "true"


# Configuration validation
import logging
import sys

logger = logging.getLogger(__name__)


def validate_config():
    """Validate configuration on startup and log warnings/errors."""
    errors = []
    warnings = []
    
    # Validate primary provider configuration
    primary = PRIMARY_PROVIDER.lower()
    if primary not in ["openrouter", "ollama", "openai"]:
        errors.append(f"PRIMARY_PROVIDER '{PRIMARY_PROVIDER}' is not supported. Must be one of: openrouter, ollama, openai")
    
    if primary == "openrouter" and not OPENROUTER_API_KEY:
        errors.append("PRIMARY_PROVIDER is 'openrouter' but OPENROUTER_API_KEY is missing")
    
    if primary == "openai" and not OPENAI_API_KEY:
        errors.append("PRIMARY_PROVIDER is 'openai' but OPENAI_API_KEY is missing")
    
    if primary == "ollama" and not OLLAMA_ENABLED:
        errors.append("PRIMARY_PROVIDER is 'ollama' but OLLAMA_ENABLED is false")
    
    # Validate fallback provider configuration
    fallback = FALLBACK_PROVIDER.lower()
    if fallback not in ["openrouter", "ollama", "openai"]:
        errors.append(f"FALLBACK_PROVIDER '{FALLBACK_PROVIDER}' is not supported. Must be one of: openrouter, ollama, openai")
    
    if fallback == "openrouter" and not OPENROUTER_API_KEY:
        warnings.append("FALLBACK_PROVIDER is 'openrouter' but OPENROUTER_API_KEY is missing - fallback will fail")
    
    if fallback == "openai" and not OPENAI_API_KEY:
        warnings.append("FALLBACK_PROVIDER is 'openai' but OPENAI_API_KEY is missing - fallback will fail")
    
    if fallback == "ollama" and not OLLAMA_ENABLED:
        warnings.append("FALLBACK_PROVIDER is 'ollama' but OLLAMA_ENABLED is false - fallback will fail")
    
    # Validate optional API keys
    if not TAVILY_API_KEY:
        warnings.append("TAVILY_API_KEY is missing - web search functionality will be limited")
    
    if not NEWSAPI_KEY:
        warnings.append("NEWSAPI_KEY is missing - news research functionality will be limited")
    
    if not ALPHAVANTAGE_API_KEY:
        warnings.append("ALPHAVANTAGE_API_KEY is missing - financial data functionality will be limited")
    
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
    
    # Log results
    if errors:
        logger.error("Configuration validation failed with errors:")
        for error in errors:
            logger.error(f"  - {error}")
        sys.exit(1)
    
    if warnings:
        logger.warning("Configuration validation completed with warnings:")
        for warning in warnings:
            logger.warning(f"  - {warning}")
    else:
        logger.info("Configuration validation passed")


# Run validation on import (startup)
validate_config()


# Learning layer configuration
LEARNING_ENABLED = os.getenv("LEARNING_ENABLED", "true").lower() == "true"
KNOWLEDGE_MAX_SIZE_MB = int(os.getenv("KNOWLEDGE_MAX_SIZE_MB", "200"))
LEARNING_SCHEDULE_INTERVAL = int(os.getenv("LEARNING_SCHEDULE_INTERVAL", "6"))  # hours
LEARNING_BATCH_SIZE = int(os.getenv("LEARNING_BATCH_SIZE", "10"))
LEARNING_TOPICS = [
    item.strip()
    for item in os.getenv(
        "LEARNING_TOPICS",
        "finance,markets,technology,policy",
    ).split(",")
    if item.strip()
]


def get_config():
    """Get configuration object for dependency injection."""
    class Config:
        app_version = APP_VERSION
        primary_provider = PRIMARY_PROVIDER
        fallback_provider = FALLBACK_PROVIDER
        
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
