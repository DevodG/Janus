import logging
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from app.services.tts_engine import tts_engine

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/voice", tags=["voice"])

class SynthesizeRequest(BaseModel):
    text: str
    voice: str = None

@router.post("/synthesize")
async def synthesize_speech(request: SynthesizeRequest):
    """
    Synthesize text into speech using Edge TTS.
    Returns an MP3 audio stream.
    """
    if not request.text.strip():
        raise HTTPException(status_code=400, detail="Text cannot be empty")

    try:
        # Stream the audio chunks back to the client as they are generated
        return StreamingResponse(
            tts_engine.synthesize_stream(request.text, request.voice),
            media_type="audio/mpeg"
        )
    except Exception as e:
        logger.error(f"TTS synthesis failed: {e}")
        raise HTTPException(status_code=500, detail="Speech synthesis failed")
