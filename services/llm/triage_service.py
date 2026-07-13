from services.llm.client import GeminiClient
from services.llm.exceptions import LLMError, LLMInvalidOutputError
from services.llm.fallback import manual_review_result
from services.llm.prompts import (
    build_correction_instruction,
    build_system_instruction,
    build_triage_input,
)
from services.llm.schemas import TriageResult
from services.llm.validators import (
    apply_safety_rules,
    normalize_triage_input,
    validate_triage_output,
)


class TriageService:
    def __init__(self, *, client=None, max_retries=None):
        self.client = client or GeminiClient()
        self.max_retries = max_retries if max_retries is not None else getattr(self.client, "max_retries", 1)

    def analyze(self, *, description: str, location: str, submitted_language: str) -> TriageResult:
        normalized_input = normalize_triage_input(
            description=description,
            location=location,
            submitted_language=submitted_language,
        )
        payload = build_triage_input(**normalized_input)
        system_instruction = build_system_instruction()

        for attempt in range(self.max_retries + 1):
            try:
                instruction = system_instruction
                if attempt > 0:
                    instruction = f"{system_instruction}\n\n{build_correction_instruction()}"

                raw_output = self.client.generate_triage(
                    system_instruction=instruction,
                    payload=payload,
                    response_schema=TriageResult,
                )
                result = validate_triage_output(raw_output)
                return apply_safety_rules(result, description=normalized_input["description"])
            except LLMInvalidOutputError:
                continue
            except LLMError:
                continue

        return manual_review_result(
            description=normalized_input["description"],
            location=normalized_input["location"],
        )


def analyze(*, description: str, location: str, submitted_language: str, client=None) -> TriageResult:
    return TriageService(client=client).analyze(
        description=description,
        location=location,
        submitted_language=submitted_language,
    )
