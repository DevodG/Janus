try:
    import google.generativeai as genai
except ImportError:
    genai = None

from app.config import GEMINI_API_KEY, MODEL_NAME

if genai and GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)


def call_model(prompt: str) -> str:
    if not GEMINI_API_KEY:
        return "GEMINI_API_KEY is missing. Please add it in backend/.env."

    if not genai:
        return "google.generativeai is not installed; unable to call Gemini."

    model = genai.GenerativeModel(MODEL_NAME)
    response = model.generate_content(prompt)

    if hasattr(response, "text") and response.text:
        return response.text.strip()

    return "No response generated."
