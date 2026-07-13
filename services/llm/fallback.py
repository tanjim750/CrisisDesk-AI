from core.constants.categories import ReportCategory
from core.constants.languages import SupportedLanguage
from core.constants.urgencies import UrgencyLevel
from services.llm.constants import AI_STATUS_FALLBACK
from services.llm.schemas import ExtractedFeatures, TriageResult


def manual_review_result(*, description: str, location: str) -> TriageResult:
    return TriageResult(
        detected_language=SupportedLanguage.UNKNOWN,
        category=ReportCategory.OTHER,
        urgency=UrgencyLevel.MEDIUM,
        summary="The submitted report requires manual review.",
        suggested_action="Assign this report to a human operator for assessment.",
        confidence=0.0,
        features=ExtractedFeatures(),
        ai_status=AI_STATUS_FALLBACK,
        requires_manual_review=True,
    )
