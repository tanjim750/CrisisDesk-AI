from core.constants.categories import ReportCategory
from core.constants.urgencies import UrgencyLevel
from services.llm.schemas import TriageResult


def manual_review_result(*, description: str, location: str) -> TriageResult:
    return TriageResult(
        category=ReportCategory.OTHER,
        urgency=UrgencyLevel.MEDIUM,
        summary=description[:240],
        suggested_action="Manual review required before dispatch.",
        confidence=0.0,
        features={"location": location},
        needs_manual_review=True,
    )
