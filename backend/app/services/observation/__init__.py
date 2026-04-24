from app.services.observation.scorer import TraceScorer
from app.services.observation.tracer import TraceLogger
import logging

logger = logging.getLogger(__name__)

scorer = TraceScorer()
_tracer_instance = None  # Lazy init — will be created on first use


def get_tracer():
    """Lazy tracer initialization to avoid import-time failures."""
    global _tracer_instance
    if _tracer_instance is None:
        try:
            logger.info("Initializing tracer...")
            _tracer_instance = TraceLogger()
            logger.info("Tracer initialized successfully")
        except Exception as e:
            import traceback

            logger.error(f"Failed to init tracer: {e}")
            logger.error(traceback.format_exc())
            _tracer_instance = None  # Keep as None if init fails
    return _tracer_instance


__all__ = ["scorer", "get_tracer", "TraceScorer", "TraceLogger"]
