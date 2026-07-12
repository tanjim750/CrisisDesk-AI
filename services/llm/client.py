import json

from django.conf import settings

from services.llm.constants import (
    DEFAULT_GEMINI_MAX_RETRIES,
    DEFAULT_GEMINI_MODEL,
    DEFAULT_GEMINI_TEMPERATURE,
    DEFAULT_GEMINI_TIMEOUT_SECONDS,
)
from services.llm.exceptions import LLMProviderUnavailableError, LLMTimeoutError


class GeminiClient:
    def __init__(
        self,
        *,
        api_key=None,
        model_name=None,
        timeout_seconds=None,
        temperature=None,
        max_retries=None,
    ):
        self.api_key = api_key if api_key is not None else getattr(settings, "GEMINI_API_KEY", "")
        self.model_name = model_name or getattr(settings, "GEMINI_MODEL", DEFAULT_GEMINI_MODEL)
        self.timeout_seconds = timeout_seconds or getattr(
            settings,
            "GEMINI_TIMEOUT_SECONDS",
            DEFAULT_GEMINI_TIMEOUT_SECONDS,
        )
        self.temperature = temperature if temperature is not None else getattr(
            settings,
            "GEMINI_TEMPERATURE",
            DEFAULT_GEMINI_TEMPERATURE,
        )
        self.max_retries = max_retries if max_retries is not None else getattr(
            settings,
            "GEMINI_MAX_RETRIES",
            DEFAULT_GEMINI_MAX_RETRIES,
        )

    def generate_triage(self, *, system_instruction: str, payload: dict, response_schema=None) -> dict:
        if not self.api_key:
            raise LLMProviderUnavailableError("GEMINI_API_KEY is not configured")

        try:
            from google import genai
            from google.genai import types
        except ImportError as exc:
            raise LLMProviderUnavailableError("google-genai is not installed") from exc

        try:
            client = genai.Client(api_key=self.api_key)
            response = client.models.generate_content(
                model=self.model_name,
                contents=json.dumps(payload, ensure_ascii=False),
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    response_mime_type="application/json",
                    temperature=self.temperature,
                ),
            )
        except TimeoutError as exc:
            raise LLMTimeoutError("Gemini request timed out") from exc
        except Exception as exc:
            raise LLMProviderUnavailableError("Gemini request failed") from exc

        return _extract_json_payload(response)

    def generate_structured_triage(self, *, system_instruction: str, prompt: str) -> dict:
        try:
            payload = json.loads(prompt)
        except json.JSONDecodeError:
            payload = {"report": prompt}

        return self.generate_triage(
            system_instruction=system_instruction,
            payload=payload,
        )


def _extract_json_payload(response) -> dict:
    parsed = getattr(response, "parsed", None)
    if isinstance(parsed, dict):
        return parsed

    text = getattr(response, "text", None)
    if text:
        try:
            return json.loads(text)
        except json.JSONDecodeError as exc:
            raise LLMProviderUnavailableError("Gemini returned invalid JSON") from exc

    raise LLMProviderUnavailableError("Gemini returned an empty response")
