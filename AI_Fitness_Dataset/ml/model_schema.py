from __future__ import annotations

from pathlib import Path


RANDOM_STATE = 42

TASKS = {
    "recommendation": {
        "label": "recommended_action",
        "train_file": "recommendation_train.csv",
        "validation_file": "recommendation_validation.csv",
        "test_file": "recommendation_test.csv",
        "dataset_file": "recommendation_training_dataset.csv",
        "model_file": "recommendation_model.pkl",
        "preprocessor_file": "recommendation_preprocessor.pkl",
        "label_encoder_file": "recommendation_label_encoder.pkl",
    },
    "preference": {
        "label": "exercise_preference",
        "train_file": "preference_train.csv",
        "validation_file": "preference_validation.csv",
        "test_file": "preference_test.csv",
        "dataset_file": "preference_training_dataset.csv",
        "model_file": "preference_model.pkl",
        "preprocessor_file": "preference_preprocessor.pkl",
        "label_encoder_file": "preference_label_encoder.pkl",
    },
    "safety": {
        "label": "safety_label",
        "train_file": "safety_train.csv",
        "validation_file": "safety_validation.csv",
        "test_file": "safety_test.csv",
        "dataset_file": "safety_training_dataset.csv",
        "model_file": "safety_risk_model.pkl",
        "preprocessor_file": "safety_preprocessor.pkl",
        "label_encoder_file": "safety_label_encoder.pkl",
    },
}

ID_COLUMNS = {
    "sample_id",
    "sample_source",
    "task_type",
    "user_id",
    "plan_id",
    "exercise_id",
    "feedback_id",
    "history_session_id",
    "history_item_id",
    "plan_item_id",
    "label_name",
    "label_value",
}


def project_root() -> Path:
    return Path(__file__).resolve().parents[1]
