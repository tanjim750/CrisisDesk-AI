from core.exceptions.exceptions import AIProcessingError
from services.llm.client import GeminiClient
from services.llm.fallback import manual_review_result
from services.llm.prompts import build_report_prompt, build_system_instruction
from services.llm.schemas import TriageResult
from services.llm.validators import apply_safety_rules, validate_triage_output


def analyze(*, description: str, location: str, submitted_language: str, client=None) -> TriageResult:
    llm_client = client or GeminiClient()
    system_instruction = build_system_instruction()
    prompt = build_report_prompt(
        description=description,
        location=location,
        submitted_language=submitted_language,
    )

    try:
        payload = llm_client.generate_structured_triage(
            system_instruction=system_instruction,
            prompt=prompt,
        )
        payload = validate_triage_output(payload)
        payload = apply_safety_rules(payload, description=description)
        return TriageResult(**payload)
    except Exception as exc:
        fallback = manual_review_result(description=description, location=location)
        raise AIProcessingError(errors={"fallback": fallback}) from exc
