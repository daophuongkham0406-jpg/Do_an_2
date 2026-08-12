from __future__ import annotations

from typing import Any


BLOCKED_ACTIONS = {"Increase Difficulty", "Increase Volume"}
BLOCKING_FLAGS = {
    "INJURY_CONTRAINDICATION_MATCH",
    "PAIN_REPORTED",
    "PAIN_AREA_MATCH",
    "LEVEL_TOO_HIGH",
}


def apply_safety_override(
    predicted_action: str,
    safety_status: str,
    risk_score: float,
    risk_flags: list[str] | None = None,
) -> dict[str, Any]:
    risk_flags = risk_flags or []
    final_action = predicted_action
    reason = ""
    if predicted_action in BLOCKED_ACTIONS and safety_status in {"Avoid", "Review"}:
        final_action = "Review Safety"
        reason = f"safety_status={safety_status}"
    elif predicted_action in BLOCKED_ACTIONS and risk_score >= 0.45:
        final_action = "Review Safety"
        reason = f"risk_score={risk_score}"
    elif predicted_action in BLOCKED_ACTIONS and any(flag in BLOCKING_FLAGS for flag in risk_flags):
        final_action = "Review Safety"
        reason = f"risk_flags={risk_flags}"
    return {
        "original_action": predicted_action,
        "final_action": final_action,
        "was_overridden": final_action != predicted_action,
        "override_reason": reason,
    }


def is_unsafe_action(predicted_action: str, safety_status: str, risk_score: float) -> bool:
    return predicted_action in BLOCKED_ACTIONS and (safety_status in {"Avoid", "Review"} or risk_score >= 0.45)
