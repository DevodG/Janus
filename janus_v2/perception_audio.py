"""perception_audio.py — V1 dissonance engine folded in as a perception sensor.

Merged asset (V1 dissonance_engine.py: wav2vec2 + DistilBERT -> VAD
divergence). Imported lazily: heavy ML deps load only when called. Output is
a sensor reading with modality evidence — never a deception verdict.
"""
from __future__ import annotations

import sys
from pathlib import Path

_V1_SERVICES = Path(__file__).resolve().parent.parent / "backend" / "app" / "services"


def perceive_audio(audio_path: str, transcript: str = "") -> dict:
    """Cross-modal dissonance reading, or an honest unavailable report."""
    try:
        if str(_V1_SERVICES) not in sys.path:
            sys.path.insert(0, str(_V1_SERVICES))
        import dissonance_engine as de  # V1 asset, heavy deps (torch/transformers)
        engine = de.DissonanceEngine() if hasattr(de, "DissonanceEngine") else None
        if engine is None:
            return {"available": False, "reason": "V1 engine class not found",
                    "sensor": "dissonance"}
        result = engine.analyze(audio_path, transcript) if hasattr(engine, "analyze") else {}
        return {"available": True, "sensor": "dissonance", "reading": str(result)[:1000],
                "calibration": "uncalibrated — perception only, never a truth claim"}
    except Exception as e:
        return {"available": False, "reason": f"dissonance engine unavailable: {str(e)[:140]}",
                "sensor": "dissonance"}
