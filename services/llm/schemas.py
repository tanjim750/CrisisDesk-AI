from dataclasses import dataclass, field

from services.llm.constants import AI_STATUS_COMPLETED


@dataclass(frozen=True)
class ExtractedFeatures:
    people_trapped: bool | None = None
    injury_reported: bool | None = None
    casualty_reported: bool | None = None
    fire_spreading: bool | None = None
    road_blocked: bool | None = None
    affected_people_count: int | None = None
    landmark: str | None = None

    @classmethod
    def from_payload(cls, payload: dict | None):
        payload = payload or {}

        return cls(
            people_trapped=_nullable_bool(payload.get("people_trapped")),
            injury_reported=_nullable_bool(payload.get("injury_reported")),
            casualty_reported=_nullable_bool(payload.get("casualty_reported")),
            fire_spreading=_nullable_bool(payload.get("fire_spreading")),
            road_blocked=_nullable_bool(payload.get("road_blocked")),
            affected_people_count=_nullable_non_negative_int(payload.get("affected_people_count")),
            landmark=_nullable_string(payload.get("landmark")),
        )

    def to_dict(self) -> dict:
        return {
            "people_trapped": self.people_trapped,
            "injury_reported": self.injury_reported,
            "casualty_reported": self.casualty_reported,
            "fire_spreading": self.fire_spreading,
            "road_blocked": self.road_blocked,
            "affected_people_count": self.affected_people_count,
            "landmark": self.landmark,
        }


@dataclass(frozen=True)
class TriageResult:
    detected_language: str
    category: str
    urgency: str
    summary: str
    suggested_action: str
    confidence: float
    features: ExtractedFeatures = field(default_factory=ExtractedFeatures)
    ai_status: str = AI_STATUS_COMPLETED
    requires_manual_review: bool = False

    def to_dict(self) -> dict:
        return {
            "detected_language": self.detected_language,
            "category": self.category,
            "urgency": self.urgency,
            "summary": self.summary,
            "suggested_action": self.suggested_action,
            "confidence": self.confidence,
            "features": self.features.to_dict(),
            "ai_status": self.ai_status,
            "requires_manual_review": self.requires_manual_review,
        }


def _nullable_bool(value):
    if value is None or isinstance(value, bool):
        return value

    return None


def _nullable_non_negative_int(value):
    if value is None:
        return None
    if isinstance(value, int) and value >= 0:
        return value

    return None


def _nullable_string(value):
    if value is None:
        return None

    value = str(value).strip()
    return value or None
