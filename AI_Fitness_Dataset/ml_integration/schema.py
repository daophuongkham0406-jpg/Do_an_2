from __future__ import annotations

from pathlib import Path


TASKS = ("recommendation", "preference", "safety")

VALID_FINAL_ACTIONS = {
    "Keep",
    "Increase Difficulty",
    "Reduce Difficulty",
    "Increase Volume",
    "Reduce Volume",
    "Replace Exercise",
    "Change Split",
    "Review Safety",
    "No Preference",
}

MODEL_FILES = {
    "recommendation": {
        "model": "recommendation_model.pkl",
        "preprocessor": "recommendation_preprocessor.pkl",
        "label_encoder": "recommendation_label_encoder.pkl",
    },
    "preference": {
        "model": "preference_model.pkl",
        "preprocessor": "preference_preprocessor.pkl",
        "label_encoder": "preference_label_encoder.pkl",
    },
    "safety": {
        "model": "safety_risk_model.pkl",
        "preprocessor": "safety_preprocessor.pkl",
        "label_encoder": "safety_label_encoder.pkl",
    },
}

CSV_FILES = {
    "users": "users.csv",
    "exercises": "exercises.csv",
    "workout_plans": "workout_plans.csv",
    "workout_plan_items": "workout_plan_items.csv",
    "workout_history_sessions": "workout_history_sessions.csv",
    "workout_history_items": "workout_history_items.csv",
    "workout_history_summary": "workout_history_summary.csv",
    "user_feedback": "user_feedback.csv",
}

LOG_COLUMNS = [
    "prediction_id",
    "timestamp",
    "user_id",
    "plan_id",
    "exercise_id",
    "raw_ml_recommendation",
    "ml_recommendation_confidence",
    "ml_preference_prediction",
    "ml_preference_confidence",
    "ml_safety_prediction",
    "ml_safety_confidence",
    "rule_based_action",
    "rule_safety_status",
    "risk_score",
    "final_action",
    "was_overridden",
    "override_reason",
    "decision_source",
    "user_feedback_after_action",
]


def project_root() -> Path:
    return Path(__file__).resolve().parents[1]
