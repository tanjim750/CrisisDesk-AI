from django.db import models


class SupportedLanguage(models.TextChoices):
    ENGLISH = "en", "English"
    BANGLA = "bn", "Bangla"
    UNKNOWN = "unknown", "Unknown"


SUPPORTED_RESPONSE_LANGUAGES = {"en", "bn"}
DEFAULT_RESPONSE_LANGUAGE = "en"
