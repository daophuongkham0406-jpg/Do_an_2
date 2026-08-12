from __future__ import annotations

from pathlib import Path


RANDOM_SEED = 42

CSV_FILES = {
    "exercises": "exercises.csv",
    "users": "users.csv",
    "workout_plans": "workout_plans.csv",
    "workout_plan_items": "workout_plan_items.csv",
    "workout_history_sessions": "workout_history_sessions.csv",
    "workout_history_items": "workout_history_items.csv",
    "workout_history_summary": "workout_history_summary.csv",
    "user_feedback": "user_feedback.csv",
}

AI_OUTPUT_FILES = {
    "ml_signal_samples": "ml_signal_samples.json",
    "recommendation_examples": "recommendation_examples.json",
    "safety_review_examples": "safety_review_examples.json",
    "plan_adjustment_examples": "plan_adjustment_examples.json",
    "feedback_analysis_examples": "feedback_analysis_examples.json",
    "history_analysis_examples": "history_analysis_examples.json",
    "ai_evaluation_summary": "ai_evaluation_summary.json",
}

VALID_RECOMMENDED_ACTIONS = {
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

VALID_EXERCISE_PREFERENCES = {"Like", "Neutral", "Dislike", "Not Applicable"}
VALID_SAFETY_LABELS = {"Safe", "Monitor", "Review", "Avoid"}

CORE_OUTPUT_FILES = [
    "ml_training_dataset.csv",
    "recommendation_training_dataset.csv",
    "preference_training_dataset.csv",
    "safety_training_dataset.csv",
    "train.csv",
    "validation.csv",
    "test.csv",
    "recommendation_train.csv",
    "recommendation_validation.csv",
    "recommendation_test.csv",
    "preference_train.csv",
    "preference_validation.csv",
    "preference_test.csv",
    "safety_train.csv",
    "safety_validation.csv",
    "safety_test.csv",
    "feature_dictionary.json",
    "ml_dataset_summary.json",
    "ml_dataset_report.md",
    "ml_dataset_issues.csv",
    "README_outputs.md",
]


def resolve_project_root() -> Path:
    return Path(__file__).resolve().parents[1]
