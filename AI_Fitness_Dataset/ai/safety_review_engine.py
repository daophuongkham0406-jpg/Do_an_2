from __future__ import annotations

from typing import Any

try:
    from .config import LEVEL_RANK
    from .utils import clean, parse_list, to_float
except ImportError:  # pragma: no cover
    from config import LEVEL_RANK
    from utils import clean, parse_list, to_float


def overlap(a: list[str], b: list[str]) -> list[str]:
    aa = {x.lower() for x in a if x}
    matches = []
    for item in b:
        low = item.lower()
        if low in aa or any(x in low or low in x for x in aa):
            matches.append(item)
    return matches


def review_safety(user_profile: dict[str, Any], exercise: dict[str, Any], history_context: dict[str, Any] | None = None, feedback_context: dict[str, Any] | None = None) -> dict[str, Any]:
    history_context = history_context or {}
    feedback_context = feedback_context or {}
    injuries = parse_list(user_profile.get("injuries_or_limitations"))
    contraindications = parse_list(exercise.get("contraindications"))
    joint_stress = parse_list(exercise.get("joint_stress_areas"))
    pain_areas = parse_list(history_context.get("pain_areas")) + parse_list(feedback_context.get("pain_areas"))
    risk_flags: list[str] = []
    contraindication_matches = overlap(injuries, contraindications + joint_stress)
    pain_matches = overlap(pain_areas, contraindications + joint_stress + parse_list(exercise.get("primary_muscles")))
    risk_score = 0.0
    if contraindication_matches:
        risk_score += 0.55
        risk_flags.append("INJURY_CONTRAINDICATION_MATCH")
    if clean(feedback_context.get("pain_feedback")) in {"Pain", "Severe Pain"}:
        risk_score += 0.45
        risk_flags.append("PAIN_REPORTED")
    elif clean(feedback_context.get("pain_feedback")) == "Mild Discomfort":
        risk_score += 0.25
        risk_flags.append("MILD_DISCOMFORT")
    if pain_matches:
        risk_score += 0.25
        risk_flags.append("PAIN_AREA_MATCH")
    user_level = LEVEL_RANK.get(clean(user_profile.get("training_level")), 1)
    ex_level = LEVEL_RANK.get(clean(exercise.get("minimum_training_level")), 1)
    if ex_level > user_level:
        risk_score += 0.15
        risk_flags.append("LEVEL_TOO_HIGH")
    if to_float(exercise.get("technical_complexity_score")) >= 4 and user_level == 1:
        risk_score += 0.1
        risk_flags.append("HIGH_TECHNICAL_COMPLEXITY")
    risk_score = min(1.0, round(risk_score, 3))
    if risk_score >= 0.75:
        status, rec = "Avoid", "Replace"
    elif risk_score >= 0.45:
        status, rec = "Review", "Review Safety"
    elif risk_score >= 0.2:
        status, rec = "Monitor", "Modify"
    else:
        status, rec = "Safe", "Keep"
    return {
        "safety_status": status,
        "risk_score": risk_score,
        "risk_flags": risk_flags,
        "contraindication_matches": contraindication_matches,
        "pain_matches": pain_matches,
        "recommendation": rec,
        "explanation": "Safety reviewed from injuries, contraindications, pain feedback and exercise complexity.",
    }

