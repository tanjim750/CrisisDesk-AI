from core.constants.categories import ReportCategory
from core.constants.languages import SupportedLanguage
from core.constants.urgencies import UrgencyLevel

ALLOWED_CATEGORIES = {choice.value for choice in ReportCategory}
ALLOWED_URGENCY_LEVELS = {choice.value for choice in UrgencyLevel}
ALLOWED_LANGUAGES = {choice.value for choice in SupportedLanguage}

MAX_DESCRIPTION_LENGTH = 4000
MAX_LOCATION_LENGTH = 500
MAX_SUMMARY_LENGTH = 500
MAX_SUGGESTED_ACTION_LENGTH = 700

DEFAULT_GEMINI_MODEL = "gemini-2.0-flash"
DEFAULT_GEMINI_TIMEOUT_SECONDS = 20
DEFAULT_GEMINI_MAX_RETRIES = 1
DEFAULT_GEMINI_TEMPERATURE = 0.1

AI_STATUS_COMPLETED = "completed"
AI_STATUS_FALLBACK = "fallback"

FEATURE_FIELDS = {
    "people_trapped",
    "injury_reported",
    "casualty_reported",
    "fire_spreading",
    "road_blocked",
    "affected_people_count",
    "landmark",
}

URGENCY_RANK = {
    UrgencyLevel.LOW: 1,
    UrgencyLevel.MEDIUM: 2,
    UrgencyLevel.HIGH: 3,
    UrgencyLevel.CRITICAL: 4,
}
