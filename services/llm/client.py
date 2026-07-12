from django.conf import settings


class GeminiClient:
    def __init__(self, *, api_key=None, model_name=None, timeout_seconds=None):
        self.api_key = api_key or getattr(settings, "GEMINI_API_KEY", "")
        self.model_name = model_name or getattr(settings, "GEMINI_MODEL", "gemini-2.0-flash")
        self.timeout_seconds = timeout_seconds or getattr(settings, "GEMINI_TIMEOUT_SECONDS", 20)

    def generate_structured_triage(self, *, system_instruction: str, prompt: str) -> dict:
        try:
            from google import genai
        except ImportError as exc:
            raise RuntimeError("google-genai is not installed") from exc

        client = genai.Client(api_key=self.api_key)
        response = client.models.generate_content(
            model=self.model_name,
            contents=[system_instruction, prompt],
        )

        return getattr(response, "parsed", None) or {}
