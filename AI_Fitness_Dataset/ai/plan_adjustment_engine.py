from __future__ import annotations

from collections import Counter
from typing import Any

try:
    from .recommendation_engine import recommend_action
    from .utils import clean
except ImportError:  # pragma: no cover
    from recommendation_engine import recommend_action
    from utils import clean


RISK_FLAGS_BLOCKING_INCREASE = {
    "INJURY_CONTRAINDICATION_MATCH",
    "PAIN_REPORTED",
    "PAIN_AREA_MATCH",
    "LEVEL_TOO_HIGH",
}


def adjust_plan(
    user_profile: dict[str, Any],
    current_plan: dict[str, Any],
    plan_items: list[dict[str, Any]],
    history_analysis: dict[str, Any],
    feedback_analysis: dict[str, Any],
    safety_review: dict[str, Any] | None = None,
) -> dict[str, Any]:
    recent_feedback = feedback_analysis.get("recent_feedback", [])
    safety = safety_review or {"safety_status": "Safe", "risk_flags": []}
    rec = recommend_action({
        "user_profile": user_profile,
        "current_plan": current_plan,
        "history_summary": history_analysis,
        "recent_feedback": recent_feedback,
        "safety_review": safety,
    })
    safety_status = clean(safety.get("safety_status")) or "Safe"
    safety_flags = set(safety.get("risk_flags", []) or [])
    safety_blocks_increase = safety_status in {"Avoid", "Review"} or bool(safety_flags & RISK_FLAGS_BLOCKING_INCREASE)
    increase_blocked_by_safety = False
    if safety_blocks_increase and rec["recommended_action"] in {"Increase Difficulty", "Increase Volume"}:
        increase_blocked_by_safety = True
        rec["recommended_action"] = "Review Safety" if safety_status in {"Avoid", "Review"} else "Reduce Difficulty"
        rec["reason_codes"] = sorted(set(rec.get("reason_codes", []) + ["INCREASE_BLOCKED_BY_SAFETY"]))
    exercise_changes = []
    disliked = set(feedback_analysis.get("disliked_exercises", []))
    too_easy = set(feedback_analysis.get("too_easy_exercises", []))
    too_hard = set(feedback_analysis.get("too_hard_exercises", []))
    pain = set(feedback_analysis.get("pain_related_exercises", []))
    for item in plan_items[:30]:
        eid = clean(item.get("exercise_id"))
        action = "Keep"
        if eid in pain:
            action = "Review Safety"
        elif eid in disliked:
            action = "Replace"
        elif eid in too_easy and not safety_blocks_increase:
            action = "Increase Difficulty"
        elif eid in too_easy and safety_blocks_increase:
            action = "Review Safety"
        elif eid in too_hard:
            action = "Reduce Difficulty"
        exercise_changes.append({"exercise_id": eid, "action": action, "reason": "Derived from user feedback and history.", "replacement_candidates": []})
    global_changes = []
    if rec["recommended_action"] in {"Reduce Volume", "Change Split", "Increase Difficulty", "Reduce Difficulty"}:
        global_changes.append({"action": rec["recommended_action"], "reason_codes": rec["reason_codes"]})
    status = "Review" if rec["recommended_action"] == "Review Safety" or safety_status in {"Avoid", "Review"} else "Adjust" if global_changes or any(c["action"] != "Keep" for c in exercise_changes) else "Maintain"
    safety_notes = []
    if status == "Review":
        safety_notes.append(f"Safety review status is {safety_status}; flags: {sorted(safety_flags)}.")
    elif safety_blocks_increase:
        safety_notes.append(f"Increase blocked by safety flags: {sorted(safety_flags)}.")
    return {
        "plan_id": clean(current_plan.get("plan_id")),
        "adjustment_status": status,
        "global_changes": global_changes,
        "exercise_changes": exercise_changes,
        "safety_notes": safety_notes,
        "increase_blocked_by_safety": increase_blocked_by_safety,
        "summary": f"Plan adjustment status: {status}.",
    }
