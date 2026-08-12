from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd

from .feature_engineering import (
    bmi_category,
    clean,
    first_match,
    index_first,
    index_many,
    infer_exercise_difficulty,
    label_from_risk_score,
    list_count,
    make_sample_id,
    parse_list,
    to_float,
    to_int,
)
from .ml_schema import AI_OUTPUT_FILES, CSV_FILES


def load_csv_inputs(csv_dir: Path) -> dict[str, pd.DataFrame]:
    return {
        name: pd.read_csv(csv_dir / filename, dtype=str, keep_default_na=False, encoding="utf-8-sig")
        for name, filename in CSV_FILES.items()
    }


def load_json_inputs(ai_output_dir: Path) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for name, filename in AI_OUTPUT_FILES.items():
        path = ai_output_dir / filename
        out[name] = json.loads(path.read_text(encoding="utf-8")) if path.exists() else None
    return out


def build_indexes(data: dict[str, pd.DataFrame]) -> dict[str, Any]:
    return {
        "users": index_first(data["users"], "user_id"),
        "plans_by_id": index_first(data["workout_plans"], "plan_id"),
        "plans_by_user": index_first(data["workout_plans"], "user_id"),
        "exercises": index_first(data["exercises"], "exercise_id"),
        "history_items": index_first(data["workout_history_items"], "history_item_id"),
        "history_sessions": index_first(data["workout_history_sessions"], "history_session_id"),
        "plan_items": index_first(data["workout_plan_items"], "plan_item_id"),
        "history_summary_by_user": index_first(data["workout_history_summary"], "user_id"),
        "feedback_by_user": index_many(data["user_feedback"], "user_id"),
    }


def user_features(user: dict[str, Any]) -> dict[str, Any]:
    injuries = parse_list(user.get("injuries_or_limitations"))
    return {
        "training_level": clean(user.get("training_level")),
        "primary_goal": clean(user.get("primary_goal")),
        "secondary_goal": clean(user.get("secondary_goal")),
        "gender": clean(user.get("gender")),
        "age": to_int(user.get("age")),
        "height_cm": to_float(user.get("height_cm")),
        "weight_kg": to_float(user.get("weight_kg")),
        "bmi": to_float(user.get("bmi")),
        "bmi_category": bmi_category(user.get("bmi")),
        "training_days_per_week": to_int(user.get("training_days_per_week")),
        "preferred_split": clean(user.get("preferred_split")),
        "gym_access_level": clean(user.get("gym_access_level")),
        "available_equipment_count": list_count(user.get("available_equipment")),
        "injury_count": len(injuries),
        "limitation_count": len(injuries),
    }


def exercise_features(exercise: dict[str, Any]) -> dict[str, Any]:
    return {
        "exercise_category": clean(exercise.get("category")),
        "exercise_difficulty": infer_exercise_difficulty(exercise),
        "minimum_training_level": clean(exercise.get("minimum_training_level")),
        "primary_muscle_count": list_count(exercise.get("primary_muscles")),
        "secondary_muscle_count": list_count(exercise.get("secondary_muscles")),
        "equipment_count": list_count(exercise.get("equipment")),
        "technical_complexity_score": to_float(exercise.get("technical_complexity_score")),
        "fatigue_score": to_float(exercise.get("systemic_fatigue_score")),
        "mobility_requirement": to_float(exercise.get("mobility_requirement")),
        "balance_requirement": to_float(exercise.get("balance_requirement")),
        "estimated_MET": to_float(exercise.get("met_value")),
        "primary_muscles": clean(exercise.get("primary_muscles")),
        "secondary_muscles": clean(exercise.get("secondary_muscles")),
        "equipment": clean(exercise.get("equipment")),
        "movement_pattern": clean(exercise.get("movement_pattern")),
        "joint_stress_areas": clean(exercise.get("joint_stress_areas")),
        "contraindications": clean(exercise.get("contraindications")),
        "joint_stress_count": list_count(exercise.get("joint_stress_areas")),
        "contraindication_count": list_count(exercise.get("contraindications")),
    }


def history_features(history_summary: dict[str, Any], signal_features: dict[str, Any] | None = None) -> dict[str, Any]:
    signal_features = signal_features or {}
    return {
        "completion_rate": to_float(signal_features.get("completion_rate") or to_float(history_summary.get("session_completion_pct")) / 100),
        "set_completion_rate": to_float(signal_features.get("set_completion_rate") or to_float(history_summary.get("set_completion_pct")) / 100),
        "skipped_rate": to_float(signal_features.get("skipped_rate")),
        "partial_rate": to_float(signal_features.get("partial_rate")),
        "average_rpe": to_float(signal_features.get("average_rpe") or history_summary.get("session_rpe")),
        "average_fatigue": to_float(signal_features.get("average_fatigue") or history_summary.get("fatigue_after")),
        "pain_rate": to_float(signal_features.get("pain_rate")),
        "trend": clean(signal_features.get("trend")),
    }


def feedback_rollup_features(feedback_rows: list[dict[str, Any]], signal_features: dict[str, Any] | None = None) -> dict[str, Any]:
    signal_features = signal_features or {}
    sentiments = {"Positive": 0, "Neutral": 0, "Negative": 0}
    too_easy = too_hard = 0
    liked: set[str] = set()
    disliked: set[str] = set()
    pain_related: set[str] = set()
    for row in feedback_rows:
        sentiment = clean(row.get("sentiment"))
        if sentiment in sentiments:
            sentiments[sentiment] += 1
        if clean(row.get("difficulty_feedback")) == "Too Easy":
            too_easy += 1
        if clean(row.get("difficulty_feedback")) == "Too Hard":
            too_hard += 1
        exercise_id = clean(row.get("exercise_id"))
        if exercise_id and clean(row.get("exercise_preference")) == "Like":
            liked.add(exercise_id)
        if exercise_id and clean(row.get("exercise_preference")) == "Dislike":
            disliked.add(exercise_id)
        if exercise_id and clean(row.get("pain_feedback")) in {"Mild Discomfort", "Pain", "Severe Pain"}:
            pain_related.add(exercise_id)
    return {
        "sentiment_positive_count": to_int(signal_features.get("sentiment_positive_count"), sentiments["Positive"]),
        "sentiment_neutral_count": to_int(signal_features.get("sentiment_neutral_count"), sentiments["Neutral"]),
        "sentiment_negative_count": to_int(signal_features.get("sentiment_negative_count"), sentiments["Negative"]),
        "too_easy_count": to_int(signal_features.get("too_easy_count"), too_easy),
        "too_hard_count": to_int(signal_features.get("too_hard_count"), too_hard),
        "liked_exercise_count": len(liked),
        "disliked_exercise_count": len(disliked),
        "pain_related_exercise_count": len(pain_related),
    }


def build_recommendation_dataset(data: dict[str, pd.DataFrame], ai: dict[str, Any]) -> pd.DataFrame:
    indexes = build_indexes(data)
    rows: list[dict[str, Any]] = []
    signals = ai.get("ml_signal_samples") or []
    for idx, signal in enumerate(signals, start=1):
        features = signal.get("features", {}) or {}
        user_id = clean(signal.get("user_id"))
        plan_id = clean(signal.get("plan_id"))
        exercise_id = clean(signal.get("exercise_id"))
        user = indexes["users"].get(user_id, {})
        exercise = indexes["exercises"].get(exercise_id, {})
        plan = indexes["plans_by_id"].get(plan_id, {})
        feedback_rows = indexes["feedback_by_user"].get(user_id, [])
        history_summary = indexes["history_summary_by_user"].get(user_id, {})
        safety_flags = signal.get("safety_flags", []) or []
        row = {
            "sample_id": make_sample_id("REC", idx),
            "user_id": user_id,
            "plan_id": plan_id,
            "exercise_id": exercise_id,
            **user_features(user),
            **exercise_features(exercise),
            **history_features(history_summary, features),
            "safety_status": clean(features.get("safety_status")),
            "risk_score": to_float(features.get("risk_score")),
            "risk_flag_count": len(safety_flags),
            "contraindication_match_count": 0,
            "pain_match_count": 0,
            **feedback_rollup_features(feedback_rows, features),
            "recommended_action": clean((signal.get("labels") or {}).get("recommended_action")),
        }
        row["days_per_week"] = to_int(plan.get("days_per_week") or row["training_days_per_week"])
        rows.append(row)
    return pd.DataFrame(rows)


def build_preference_dataset(data: dict[str, pd.DataFrame]) -> pd.DataFrame:
    indexes = build_indexes(data)
    rows: list[dict[str, Any]] = []
    source = data["user_feedback"]
    feedback_rows = source[source["exercise_id"].map(clean) != ""].to_dict(orient="records")
    for idx, feedback in enumerate(feedback_rows, start=1):
        user_id = clean(feedback.get("user_id"))
        exercise_id = clean(feedback.get("exercise_id"))
        plan_id = clean(feedback.get("plan_id"))
        history_item = indexes["history_items"].get(clean(feedback.get("history_item_id")), {})
        history_session = indexes["history_sessions"].get(clean(feedback.get("history_session_id")), {})
        plan_item = indexes["plan_items"].get(clean(feedback.get("plan_item_id")), {})
        exercise = indexes["exercises"].get(exercise_id, {})
        user = indexes["users"].get(user_id, {})
        row = {
            "sample_id": make_sample_id("PREF", idx),
            "feedback_id": clean(feedback.get("feedback_id")),
            "user_id": user_id,
            "exercise_id": exercise_id,
            "plan_id": plan_id,
            "history_session_id": clean(feedback.get("history_session_id")),
            "history_item_id": clean(feedback.get("history_item_id")),
            "plan_item_id": clean(feedback.get("plan_item_id")),
            **user_features(user),
            **exercise_features(exercise),
            "rating": to_int(feedback.get("rating")),
            "sentiment": clean(feedback.get("sentiment")),
            "difficulty_feedback": clean(feedback.get("difficulty_feedback")),
            "enjoyment_rating": to_int(feedback.get("enjoyment_rating")),
            "fatigue_feedback": clean(feedback.get("fatigue_feedback")),
            "pain_feedback": clean(feedback.get("pain_feedback")),
            "duration_feedback": clean(feedback.get("duration_feedback")),
            "progression_preference": clean(feedback.get("progression_preference")),
            "requested_action": clean(feedback.get("requested_action")),
            "feedback_reason_tag_count": list_count(feedback.get("feedback_reason_tags")),
            "actual_rpe": to_float(history_item.get("actual_rpe")),
            "actual_load_kg": to_float(history_item.get("actual_load_kg")),
            "difficulty_rating": to_int(history_item.get("difficulty_rating")),
            "exercise_enjoyment": to_int(history_item.get("exercise_enjoyment")),
            "pain_during_exercise": clean(history_item.get("pain_during_exercise")),
            "technique_quality": clean(history_item.get("technique_quality")),
            "session_rpe": to_float(history_session.get("session_rpe")),
            "session_completion_pct": to_float(history_session.get("completion_pct")),
            "plan_item_role": clean(plan_item.get("exercise_role")),
            "exercise_preference": clean(feedback.get("exercise_preference")),
        }
        rows.append(row)
    return pd.DataFrame(rows)


def build_safety_dataset(data: dict[str, pd.DataFrame], ai: dict[str, Any]) -> pd.DataFrame:
    indexes = build_indexes(data)
    rows: list[dict[str, Any]] = []
    signals = ai.get("ml_signal_samples") or []
    for idx, signal in enumerate(signals, start=1):
        features = signal.get("features", {}) or {}
        user_id = clean(signal.get("user_id"))
        exercise_id = clean(signal.get("exercise_id"))
        user = indexes["users"].get(user_id, {})
        exercise = indexes["exercises"].get(exercise_id, {})
        feedback = first_match(indexes["feedback_by_user"].get(user_id, []), "exercise_id", exercise_id)
        safety_label = clean(features.get("safety_status")) or label_from_risk_score(features.get("risk_score"))
        row = {
            "sample_id": make_sample_id("SAFE", idx),
            "user_id": user_id,
            "exercise_id": exercise_id,
            **user_features(user),
            **exercise_features(exercise),
            "pain_rate": to_float(features.get("pain_rate")),
            "pain_feedback": clean(feedback.get("pain_feedback")),
            "pain_area_count": list_count(feedback.get("pain_areas")),
            "pain_during_exercise": "",
            "pain_match_count": 0,
            "contraindication_match_count": 0,
            "risk_flag_count": len(signal.get("safety_flags", []) or []),
            "risk_score": to_float(features.get("risk_score")),
            "safety_label": safety_label,
        }
        rows.append(row)
    return pd.DataFrame(rows)


def build_unified_dataset(recommendation: pd.DataFrame, preference: pd.DataFrame, safety: pd.DataFrame) -> pd.DataFrame:
    frames: list[pd.DataFrame] = []
    task_specs = [
        ("recommendation", recommendation, "recommended_action"),
        ("preference", preference, "exercise_preference"),
        ("safety", safety, "safety_label"),
    ]
    for task_type, frame, label_column in task_specs:
        if frame.empty:
            continue
        task = frame.copy()
        task.insert(1, "sample_source", f"{task_type}_training_dataset")
        task.insert(2, "task_type", task_type)
        task["label_name"] = label_column
        task["label_value"] = task[label_column]
        frames.append(task)
    return pd.concat(frames, ignore_index=True, sort=False) if frames else pd.DataFrame()
