import logging
from typing import AsyncIterator, Optional
import edge_tts

logger = logging.getLogger(__name__)

# Default voice settings
DEFAULT_VOICE = "en-US-AriaNeural"  # High quality female US English
# You can also use "en-IN-NeerjaNeural" for Indian English accent.

class TTSEngine:
    """
    Microsoft Edge TTS engine (free, cloud-based).
    No API key required.
    """

    @property
    def name(self) -> str:
        return "Edge-TTS"

    async def synthesize_stream(self, text: str, voice: Optional[str] = None) -> AsyncIterator[bytes]:
        """Stream synthesized audio from Edge TTS as MP3 bytes."""
        try:
            voice_name = voice or DEFAULT_VOICE
            communicate = edge_tts.Communicate(text, voice_name)
            
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    yield chunk["data"]
        except Exception as e:
            logger.error(f"Edge TTS streaming failed: {e}")
            raise

tts_engine = TTSEngine()
