import base64
import os
import tempfile
from typing import Dict, Any, Optional
from app.services.guardian_sensory import guardian_sensory

from app.services.mmsa_engine import mmsa_engine

class InputProcessor:
    async def process(self, request: Any) -> Dict[str, Any]:
        """
        Normalize input from text, URL, or Image.
        Returns a dictionary with 'text', 'source_type', and 'metadata'.
        """
        normalized = {
            "text": "",
            "source": request.source,
            "metadata": {}
        }

        if request.url:
            # Depth: Heuristic logic from Guardian + Multi-modal Dissonance from MMSA
            url_analysis = guardian_sensory.analyze_url(request.url)
            normalized["text"] = f"URL: {request.url}"
            normalized["metadata"]["url_analysis"] = url_analysis
            
            # Deep Scan: If it's a video URL, run MMSA
            if "youtube.com" in request.url or "youtu.be" in request.url:
                # We need a transcript for MMSA, if not provided we use a placeholder or 
                # in a real app we'd fetch it.
                mmsa_report = mmsa_engine.analyze_url(request.url, request.text or "Analyzing video signals.")
                normalized["metadata"]["mmsa"] = mmsa_report
                if "error" not in mmsa_report:
                    normalized["text"] += f"\nVideo Analysis: {mmsa_report.get('analysis_tags', [])}"
            
        if request.image_base64:
            text_from_image = await self._process_image(request.image_base64)
            normalized["text"] = text_from_image
            normalized["metadata"]["is_ocr"] = True

        if request.text:
            # Combine or prefer explicit text
            if normalized["text"]:
                normalized["text"] += f"\nMeta-Text: {request.text}"
            else:
                normalized["text"] = request.text

        return normalized

    async def _process_image(self, base64_str: str) -> str:
        # Remove header if present
        if "," in base64_str:
            base64_str = base64_str.split(",")[1]
            
        img_data = base64.b64decode(base64_str)
        
        with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
            tmp.write(img_data)
            tmp_path = tmp.name

        try:
            results = guardian_sensory.analyze_screenshot(tmp_path)
            return results.get("text", "")
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

input_processor = InputProcessor()
