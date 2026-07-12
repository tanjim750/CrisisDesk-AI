def build_system_instruction() -> str:
    return (
        "You are a crisis report triage assistant. Return only structured data "
        "that matches the expected schema. Do not invent facts."
    )


def build_report_prompt(*, description: str, location: str, submitted_language: str) -> str:
    return (
        f"Description: {description}\n"
        f"Location: {location}\n"
        f"Submitted language: {submitted_language}\n"
        "Classify category, urgency, summary, suggested action, confidence, and features."
    )
