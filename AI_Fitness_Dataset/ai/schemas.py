from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Recommendation:
    recommended_action: str
    confidence: float
    reason_codes: list[str] = field(default_factory=list)
    explanation: str = ""
    safety_flags: list[str] = field(default_factory=list)
    target_changes: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class SafetyReview:
    safety_status: str
    risk_score: float
    risk_flags: list[str] = field(default_factory=list)
    contraindication_matches: list[str] = field(default_factory=list)
    pain_matches: list[str] = field(default_factory=list)
    recommendation: str = "Keep"
    explanation: str = ""

