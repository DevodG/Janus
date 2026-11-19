"""
Learning subsystem for autonomous knowledge evolution.

This module provides the infrastructure for the system to improve itself
over time without local model training. It includes:
- Knowledge ingestion from external sources
- Experience learning from case execution
- Prompt evolution through A/B testing
- Skill distillation from repeated patterns
- Trust and freshness management
"""

from .knowledge_ingestor import KnowledgeIngestor
from .knowledge_store import KnowledgeStore
from .learning_engine import LearningEngine
from .prompt_optimizer import PromptOptimizer
from .skill_distiller import SkillDistiller
from .trust_manager import TrustManager
from .scheduler import LearningScheduler

__all__ = [
    "KnowledgeIngestor",
    "KnowledgeStore",
    "LearningEngine",
    "PromptOptimizer",
    "SkillDistiller",
    "TrustManager",
    "LearningScheduler",
]
