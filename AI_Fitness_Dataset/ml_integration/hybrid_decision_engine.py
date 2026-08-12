from __future__ import annotations

from typing import Any

from .safety_override import apply_safety_lock


def decide_final_action(
    user_id: str,
    exercise_id: str,
    ml_recommendation: dict[str, Any],
    ml_preference: dict[str, Any],
    ml_safety: dict[str, Any],
    rule_based_recommendation: dict[str, Any],
    rule_safety_review: dict[str, Any],
    recommendation_confidence_threshold: float = 0.60,
    preference_confidence_threshold: float = 0.60,
    safety_confidence_threshold: float = 0.60,
) -> dict[str, Any]:
    rule_action = rule_based_recommendation.get("recommended_action", "Keep")
    ml_action = ml_recommendation.get("raw_prediction", "")
    rule_safety_status = rule_safety_review.get("safety_status", "Safe")
    ml_safety_prediction = ml_safety.get("raw_prediction", "")
    risk_score = float(rule_safety_review.get("risk_score", 0) or 0)
    risk_flags = rule_safety_review.get("risk_flags", []) or []
    decision_source = "rule_based"
    final_confidence = float(rule_based_recommendation.get("confidence", 0.7) or 0.7)

    if rule_safety_status in {"Avoid", "Review"}:
        candidate_action = "Review Safety"
        decision_source = "rule_safety_priority"
        final_confidence = 0.95
    elif ml_recommendation.get("status") != "OK" or ml_recommendation.get("confidence", 0) < recommendation_confidence_threshold:
        candidate_action = rule_action
        decision_source = "fallback_to_rule_based"
    elif ml_action == rule_action:
        candidate_action = ml_action
        decision_source = "ml_and_rule_agree"
        final_confidence = min(0.99, max(float(ml_recommendation.get("confidence", 0)), final_confidence) + 0.05)
    else:
        candidate_action = ml_action
        decision_source = "ml_recommendation"
        final_confidence = float(ml_recommendation.get("confidence", 0))

    if (
        ml_preference.get("status") == "OK"
        and ml_preference.get("raw_prediction") == "Dislike"
        and ml_preference.get("confidence", 0) >= preference_confidence_threshold
        and candidate_action in {"Keep", "Increase Difficulty", "Increase Volume"}
    ):
        candidate_action = "Replace Exercise"
        decision_source = "preference_dislike_adjustment"
        final_confidence = min(final_confidence, float(ml_preference.get("confidence", final_confidence)))

    if (
        ml_safety.get("status") == "OK"
        and ml_safety_prediction in {"Review", "Avoid"}
        and ml_safety.get("confidence", 0) >= safety_confidence_threshold
        and candidate_action in {"Increase Difficulty", "Increase Volume"}
    ):
        candidate_action = "Review Safety"
        decision_source = "ml_safety_guard"

    safety_lock = apply_safety_lock(candidate_action, rule_safety_status, ml_safety_prediction, risk_score, risk_flags)
    final_action = safety_lock["final_action"]
    if safety_lock["was_overridden"]:
        decision_source = "safety_lock_override"
        final_confidence = 0.95

    return {
        "user_id": user_id,
        "exercise_id": exercise_id,
        "ml_recommendation": ml_recommendation,
        "ml_preference": ml_preference,
        "ml_safety": ml_safety,
        "rule_based_recommendation": rule_based_recommendation,
        "rule_safety_review": rule_safety_review,
        "candidate_action": candidate_action,
        "final_action": final_action,
        "final_confidence": round(final_confidence, 4),
        "was_overridden": safety_lock["was_overridden"],
        "decision_source": decision_source,
        "safety_lock": safety_lock,
        "explanation": _explain(decision_source, final_action, safety_lock),
    }


def _explain(decision_source: str, final_action: str, safety_lock: dict[str, Any]) -> str:
    if safety_lock.get("was_overridden"):
        return f"Safety lock overrode the candidate action. Final action is {final_action}."
    if decision_source == "ml_and_rule_agree":
        return "ML and rule-based recommendation agree; safety lock did not override."
    if decision_source == "fallback_to_rule_based":
        return "ML confidence was low or prediction failed; fallback rule-based action was used."
    if decision_source == "preference_dislike_adjustment":
        return "Preference model predicted Dislike with sufficient confidence; final action was adjusted."
    if decision_source == "rule_safety_priority":
        return "Rule-based safety status requires review; final action prioritizes safety."
    return f"Final action selected by {decision_source} with safety lock applied."
