from __future__ import annotations

from typing import Any


BLOCKED_ACTIONS = {"Increase Difficulty", "Increase Volume"}
BLOCKING_FLAGS = {
    "INJURY_CONTRAINDICATION_MATCH",
    "PAIN_REPORTED",
    "PAIN_AREA_MATCH",
    "LEVEL_TOO_HIGH",
}


def apply_safety_lock(
    candidate_action: str,
    rule_safety_status: str,
    ml_safety_prediction: str | None = None,
    risk_score: float = 0.0,
    risk_flags: list[str] | None = None,
) -> dict[str, Any]:
    risk_flags = risk_flags or []
    final_action = candidate_action
    reason = ""
    if candidate_action in BLOCKED_ACTIONS:
        if rule_safety_status in {"Review", "Avoid"}:
            final_action = "Review Safety"
            reason = f"Blocked increase due to rule safety {rule_safety_status}"
        elif ml_safety_prediction in {"Review", "Avoid"}:
            final_action = "Review Safety"
            reason = f"Blocked increase due to ML safety {ml_safety_prediction}"
        elif risk_score >= 0.45:
            final_action = "Review Safety"
            reason = f"Blocked increase due to risk_score {risk_score}"
        elif any(flag in BLOCKING_FLAGS for flag in risk_flags):
            final_action = "Review Safety"
            reason = f"Blocked increase due to risk flags {risk_flags}"
    return {
        "original_action": candidate_action,
        "final_action": final_action,
        "was_overridden": final_action != candidate_action,
        "override_reason": reason,
    }


def is_unsafe_final_action(final_action: str, rule_safety_status: str, risk_score: float, risk_flags: list[str] | None = None) -> bool:
    risk_flags = risk_flags or []
    return final_action in BLOCKED_ACTIONS and (
        rule_safety_status in {"Review", "Avoid"}
        or risk_score >= 0.45
        or any(flag in BLOCKING_FLAGS for flag in risk_flags)
    )
