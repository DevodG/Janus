import logging
from typing import Dict, List, Any, Optional
from huggingface_hub import InferenceClient
from app.config import HUGGINGFACE_API_KEY, HUGGINGFACE_MODEL

logger = logging.getLogger(__name__)

# Models that are usually available on the free serverless Inference API
MODEL_LADDER = [
    "Qwen/Qwen2.5-72B-Instruct",
    "meta-llama/Llama-3.1-8B-Instruct",
    "deepseek-ai/DeepSeek-R1",
    HUGGINGFACE_MODEL,
]

class HuggingFaceInferenceClient:
    """HuggingFace Inference API client using the official hub library."""

    def __init__(self, model: str = HUGGINGFACE_MODEL):
        self.default_model = model
        self.client = InferenceClient(token=HUGGINGFACE_API_KEY)

    def chat(self, messages: List[Dict[str, str]], **kwargs) -> str:
        last_error = None
        for model in dict.fromkeys(MODEL_LADDER):
            try:
                logger.info(f"[HF] Attempting chat with model: {model}")
                response = ""
                for chunk in self.client.chat_completion(
                    messages=messages,
                    model=model,
                    max_tokens=kwargs.get("max_tokens", 4096),
                    temperature=kwargs.get("temperature", 0.7),
                    stream=True,
                ):
                    if chunk.choices[0].delta.content:
                        response += chunk.choices[0].delta.content
                
                if response:
                    return response
            except Exception as e:
                last_error = e
                logger.warning(f"[HF] Model {model} failed: {e}")
                continue
        
        raise RuntimeError(f"All HF models exhausted. Last error: {last_error}")

    def reason(self, messages: List[Dict[str, str]], **kwargs) -> str:
        # For high-end reasoning, we try the ladder with higher tokens
        return self.chat(
            messages,
            temperature=kwargs.get("temperature", 0.9),
            max_tokens=kwargs.get("max_tokens", 8192),
        )

    def is_available(self) -> bool:
        return bool(HUGGINGFACE_API_KEY)

hf_client = HuggingFaceInferenceClient()

