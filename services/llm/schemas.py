from dataclasses import dataclass, field


@dataclass(frozen=True)
class TriageResult:
    category: str
    urgency: str
    summary: str
    suggested_action: str
    confidence: float
    features: dict = field(default_factory=dict)
    needs_manual_review: bool = False
