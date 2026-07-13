import re
import unicodedata


INVISIBLE_CHARACTERS_PATTERN = re.compile(r"[\u200b-\u200f\u202a-\u202e\ufeff]")


def normalize_description(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value or "")
    normalized = INVISIBLE_CHARACTERS_PATTERN.sub("", normalized)
    normalized = re.sub(r"\s+", " ", normalized)
    normalized = re.sub(r"([!?.,])\1+", r"\1", normalized)

    return normalized.strip()


def normalize_location(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value or "")
    normalized = normalized.strip().lower()
    normalized = re.sub(r"[^\w\s,-]", " ", normalized)
    normalized = re.sub(r"\s+", " ", normalized)

    return normalized.strip()
