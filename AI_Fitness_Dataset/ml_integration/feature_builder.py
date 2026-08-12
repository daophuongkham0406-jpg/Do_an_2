from __future__ import annotations

from collections import Counter
from typing import Any

from .utils import bmi_category, clean, list_count, parse_list, to_float, to_int


class FeatureBuildResult(dict):
    @property
    def missing_count(self) -> int:
        return int(self.get("_missing_feature_count", 0))


def _user_features(user: dict[str, Any]) -> dict[str, Any]:
    injuries = parse_list(user.get("injuries_or_limitations"))
    return {
        "training_level": clean(user.get("training_level")) or "Unknown",
        "primary_goal": clean(user.get("primary_goal")) or "Unknown",
        "secondary_goal": clean(user.get("secondary_goal")) or "Unknown",
        "gender": clean(user.get("gender")) or "Unknown",
        "age": to_int(user.get("age")),
        "height_cm": to_float(user.get("height_cm")),
        "weight_kg": to_float(user.get("weight_kg")),
        "bmi": to_float(user.get("bmi")),
        "bmi_category": bmi_category(user.get("bmi")),
        "training_days_per_week": to_int(user.get("training_days_per_week")),
        "preferred_split": clean(user.get("preferred_split")) or "Unknown",
        "gym_access_level": clean(user.get("gym_access_level")) or "Unknown",
        "available_equipment_count": list_count(user.get("available_equipment")),
        "injury_count": len(injuries),
        "limitation_count": len(injuries),
    }


def _exercise_features(exercise: dict[str, Any]) -> dict[str, Any]:
    return {
        "exercise_category": clean(exercise.get("category")) or "Unknown",
        "exercise_difficulty": clean(exercise.get("minimum_training_level")) or "Unknown",
        "minimum_training_level": clean(exercise.get("minimum_training_level")) or "Unknown",
        "primary_muscle_count": list_count(exercise.get("primary_muscles")),
        "secondary_muscle_count": list_count(exercise.get("secondary_muscles")),
        "equipment_count": list_count(exercise.get("equipment")),
        "technical_complexity_score": to_float(exercise.get("technical_complexity_score")),
        "fatigue_score": to_float(exercise.get("systemic_fatigue_score")),
        "mobility_requirement": to_float(exercise.get("mobility_requirement")),
        "balance_requirement": to_float(exercise.get("balance_requirement")),
        "estimated_MET": to_float(exercise.get("met_value")),
        "primary_muscles": clean(exercise.get("primary_muscles")) or "Unknown",
        "secondary_muscles": clean(exercise.get("secondary_muscles")) or "Unknown",
        "equipment": clean(exercise.get("equipment")) or "Unknown",
        "movement_pattern": clean(exercise.get("movement_pattern")) or "Unknown",
        "joint_stress_areas": clean(exercise.get("joint_stress_areas")) or "Unknown",
        "contraindications": clean(exercise.get("contraindications")) or "Unknown",
        "joint_stress_count": list_count(exercise.get("joint_stress_areas")),
        "contraindication_count": list_count(exercise.get("contraindications")),
    }


def _history_features(history: dict[str, Any]) -> dict[str, Any]:
    return {
        "completion_rate": to_float(history.get("completion_rate")),
        "set_completion_rate": to_float(history.get("set_completion_rate")),
        "skipped_rate": to_float(history.get("skipped_rate")),
        "partial_rate": to_float(history.get("partial_rate")),
        "average_rpe": to_float(history.get("average_rpe")),
        "average_fatigue": to_float(history.get("average_fatigue")),
        "pain_rate": to_float(history.get("pain_rate")),
        "trend": clean(history.get("trend")) or "Unknown",
    }


def _feedback_rollup(feedback: dict[str, Any]) -> dict[str, Any]:
    sentiments = Counter(feedback.get("sentiment_summary", {}) or {})
    recent = feedback.get("recent_feedback", []) or []
    difficulty = Counter(clean(row.get("difficulty_feedback")) for row in recent)
    return {
        "sentiment_positive_count": int(sentiments.get("Positive", 0)),
        "sentiment_neutral_count": int(sentiments.get("Neutral", 0)),
        "sentiment_negative_count": int(sentiments.get("Negative", 0)),
        "too_easy_count": int(difficulty.get("Too Easy", 0)),
        "too_hard_count": int(difficulty.get("Too Hard", 0)),
        "liked_exercise_count": len(feedback.get("liked_exercises", []) or []),
        "disliked_exercise_count": len(feedback.get("disliked_exercises", []) or []),
        "pain_related_exercise_count": len(feedback.get("pain_related_exercises", []) or []),
    }


def _latest_feedback(feedback_context: dict[str, Any]) -> dict[str, Any]:
    if "recent_feedback" in feedback_context:
        rows = feedback_context.get("recent_feedback") or []
        return rows[-1] if rows else {}
    return feedback_context


def _match_schema(values: dict[str, Any], task_spec: dict[str, Any]) -> FeatureBuildResult:
    numeric = task_spec.get("numeric_features", []) or []
    categorical = task_spec.get("categorical_features", []) or []
    out: FeatureBuildResult = FeatureBuildResult()
    missing = 0
    for column in numeric:
        if column not in values or clean(values.get(column)) == "":
            out[column] = 0.0
            missing += 1
        else:
            out[column] = to_float(values.get(column))
    for column in categorical:
        if column not in values or clean(values.get(column)) == "":
            out[column] = "Unknown"
            missing += 1
        else:
            out[column] = clean(values.get(column))
    out["_missing_feature_count"] = missing
    out["_extra_features"] = sorted(set(values) - set(numeric) - set(categorical))
    return out


def build_recommendation_features(
    user_profile: dict[str, Any],
    current_plan: dict[str, Any],
    exercise_context: dict[str, Any],
    history_analysis: dict[str, Any],
    feedback_analysis: dict[str, Any],
    safety_review: dict[str, Any],
    feature_columns: dict[str, Any],
) -> dict[str, Any]:
    values = {
        **_user_features(user_profile),
        **_exercise_features(exercise_context),
        **_history_features(history_analysis),
        **_feedback_rollup(feedback_analysis),
        "safety_status": clean(safety_review.get("safety_status")) or "Unknown",
        "risk_score": to_float(safety_review.get("risk_score")),
        "risk_flag_count": len(safety_review.get("risk_flags", []) or []),
        "contraindication_match_count": len(safety_review.get("contraindication_matches", []) or []),
        "pain_match_count": len(safety_review.get("pain_matches", []) or []),
        "days_per_week": to_int(current_plan.get("days_per_week") or user_profile.get("training_days_per_week")),
    }
    return _match_schema(values, feature_columns["recommendation"])


def build_preference_features(
    user_profile: dict[str, Any],
    exercise_context: dict[str, Any],
    feedback_context: dict[str, Any],
    history_context: dict[str, Any],
    feature_columns: dict[str, Any],
) -> dict[str, Any]:
    feedback = _latest_feedback(feedback_context)
    values = {
        **_user_features(user_profile),
        **_exercise_features(exercise_context),
        "rating": to_int(feedback.get("rating")),
        "enjoyment_rating": to_int(feedback.get("enjoyment_rating")),
        "feedback_reason_tag_count": list_count(feedback.get("feedback_reason_tags")),
        "actual_rpe": to_float(history_context.get("actual_rpe") or history_context.get("average_rpe")),
        "actual_load_kg": to_float(history_context.get("actual_load_kg")),
        "difficulty_rating": to_int(history_context.get("difficulty_rating")),
        "exercise_enjoyment": to_int(history_context.get("exercise_enjoyment")),
        "session_rpe": to_float(history_context.get("session_rpe") or history_context.get("average_rpe")),
        "session_completion_pct": to_float(history_context.get("completion_pct")),
        "sentiment": clean(feedback.get("sentiment")) or "Unknown",
        "difficulty_feedback": clean(feedback.get("difficulty_feedback")) or "Unknown",
        "fatigue_feedback": clean(feedback.get("fatigue_feedback")) or "Unknown",
        "pain_feedback": clean(feedback.get("pain_feedback")) or "Unknown",
        "duration_feedback": clean(feedback.get("duration_feedback")) or "Unknown",
        "progression_preference": clean(feedback.get("progression_preference")) or "Unknown",
        "requested_action": clean(feedback.get("requested_action")) or "Unknown",
        "pain_during_exercise": clean(history_context.get("pain_during_exercise")) or "Unknown",
        "technique_quality": clean(history_context.get("technique_quality")) or "Unknown",
        "plan_item_role": clean(history_context.get("plan_item_role")) or "Unknown",
    }
    return _match_schema(values, feature_columns["preference"])


def build_safety_features(
    user_profile: dict[str, Any],
    exercise_context: dict[str, Any],
    history_analysis: dict[str, Any],
    feedback_context: dict[str, Any],
    safety_review: dict[str, Any],
    feature_columns: dict[str, Any],
) -> dict[str, Any]:
    feedback = _latest_feedback(feedback_context)
    values = {
        **_user_features(user_profile),
        **_exercise_features(exercise_context),
        "pain_rate": to_float(history_analysis.get("pain_rate")),
        "pain_feedback": clean(feedback.get("pain_feedback")) or "Unknown",
        "pain_area_count": list_count(feedback.get("pain_areas")),
        "pain_during_exercise": clean(feedback.get("pain_during_exercise")) or "Unknown",
        "pain_match_count": len(safety_review.get("pain_matches", []) or []),
        "contraindication_match_count": len(safety_review.get("contraindication_matches", []) or []),
        "risk_flag_count": len(safety_review.get("risk_flags", []) or []),
        "risk_score": to_float(safety_review.get("risk_score")),
    }
    return _match_schema(values, feature_columns["safety"])
