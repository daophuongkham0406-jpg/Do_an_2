from __future__ import annotations

from collections import Counter
from typing import Any

try:
    from .utils import clean, to_float
except ImportError:  # pragma: no cover
    from utils import clean, to_float


def build_ml_signal_sample(result: dict[str, Any]) -> dict[str, Any]:
    user = result.get("user_profile", {}) or {}
    plan = result.get("current_plan", {}) or {}
    exercise = result.get("exercise_context", {}) or {}
    history = result.get("history_analysis", {}) or {}
    feedback = result.get("feedback_analysis", {}) or {}
    safety = result.get("safety_review", {}) or {}
    recommendation = result.get("recommendation", {}) or {}
    adjustment = result.get("plan_adjustment", {}) or {}
    sentiments = Counter(feedback.get("sentiment_summary", {}) or {})

    recent = feedback.get("recent_feedback", []) or []
    difficulty = Counter(clean(row.get("difficulty_feedback")) for row in recent)

    return {
        "user_id": clean(result.get("user_id") or user.get("user_id")),
        "plan_id": clean(plan.get("plan_id")),
        "exercise_id": clean(exercise.get("exercise_id")),
        "features": {
            "training_level": clean(user.get("training_level")),
            "primary_goal": clean(user.get("primary_goal")),
            "bmi": to_float(user.get("bmi")),
            "completion_rate": to_float(history.get("completion_rate")),
            "set_completion_rate": to_float(history.get("set_completion_rate")),
            "average_rpe": to_float(history.get("average_rpe")),
            "average_fatigue": to_float(history.get("average_fatigue")),
            "pain_rate": to_float(history.get("pain_rate")),
            "safety_status": clean(safety.get("safety_status")),
            "risk_score": to_float(safety.get("risk_score")),
            "sentiment_positive_count": int(sentiments.get("Positive", 0)),
            "sentiment_negative_count": int(sentiments.get("Negative", 0)),
            "too_easy_count": int(difficulty.get("Too Easy", 0)),
            "too_hard_count": int(difficulty.get("Too Hard", 0)),
        },
        "labels": {
            "recommended_action": clean(recommendation.get("recommended_action")),
            "safety_recommendation": clean(safety.get("recommendation")),
            "adjustment_status": clean(adjustment.get("adjustment_status")),
        },
        "reason_codes": recommendation.get("reason_codes", []) or [],
        "safety_flags": safety.get("risk_flags", []) or [],
    }
