from __future__ import annotations

import json
import sys
import argparse
from collections import Counter
from pathlib import Path
from typing import Any

import pandas as pd

if __package__ is None or __package__ == "":
    sys.path.append(str(Path(__file__).resolve().parents[1]))
    from ai.ai_coach_rag import answer_user_question
    from ai.config import OUTPUT_DIR, VALID_ACTIONS
    from ai.feedback_analyzer import analyze_feedback
    from ai.history_analyzer import analyze_history
    from ai.ml_signal_builder import build_ml_signal_sample
    from ai.plan_adjustment_engine import adjust_plan
    from ai.recommendation_engine import recommend_action
    from ai.safety_review_engine import review_safety
    from ai.utils import clean, load_csv_exports, rows_for
    from ai.workout_generator import generate_workout_plan
else:
    from .ai_coach_rag import answer_user_question
    from .config import OUTPUT_DIR, VALID_ACTIONS
    from .feedback_analyzer import analyze_feedback
    from .history_analyzer import analyze_history
    from .ml_signal_builder import build_ml_signal_sample
    from .plan_adjustment_engine import adjust_plan
    from .recommendation_engine import recommend_action
    from .safety_review_engine import review_safety
    from .utils import clean, load_csv_exports, rows_for
    from .workout_generator import generate_workout_plan


def first_row(df: pd.DataFrame, column: str, value: str) -> dict[str, Any]:
    rows = df[df[column].map(clean) == clean(value)]
    return rows.iloc[0].to_dict() if not rows.empty else {}


def index_first(df: pd.DataFrame, column: str) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    if column not in df.columns:
        return out
    for row in df.to_dict(orient="records"):
        key = clean(row.get(column))
        if key and key not in out:
            out[key] = row
    return out


def index_many(df: pd.DataFrame, column: str) -> dict[str, list[dict[str, Any]]]:
    out: dict[str, list[dict[str, Any]]] = {}
    if column not in df.columns:
        return out
    for row in df.to_dict(orient="records"):
        key = clean(row.get(column))
        if key:
            out.setdefault(key, []).append(row)
    return out


def average(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def run_for_user(data: dict[str, pd.DataFrame], user_id: str) -> dict[str, Any]:
    users = data["users"]
    plans = data["workout_plans"]
    plan_items = data["workout_plan_items"]
    sessions = data["workout_history_sessions"]
    items = data["workout_history_items"]
    feedback = data["user_feedback"]
    exercises = data["exercises"]
    user = data.get("_users_by_id", {}).get(clean(user_id)) or first_row(users, "user_id", user_id)
    current_plan = data.get("_plans_by_user_id", {}).get(clean(user_id)) or first_row(plans, "user_id", user_id)
    pid = clean(current_plan.get("plan_id"))
    current_items = (data.get("_plan_items_by_plan_id", {}).get(pid) or rows_for(plan_items, "plan_id", pid))[:40]
    session_records = data.get("_sessions_by_user_id", {}).get(clean(user_id))
    if session_records is None:
        session_records = sessions.to_dict(orient="records")
    item_records = data.get("_history_items_by_user_id", {}).get(clean(user_id))
    if item_records is None:
        item_records = items.to_dict(orient="records")
    feedback_records = data.get("_feedback_by_user_id", {}).get(clean(user_id))
    if feedback_records is None:
        feedback_records = feedback.to_dict(orient="records")
    history_analysis = analyze_history(user_id, session_records, item_records)
    feedback_analysis = analyze_feedback(user_id, feedback_records)
    generated_plan = generate_workout_plan(user, exercises)
    exercise_id = clean(current_items[0].get("exercise_id")) if current_items else ""
    exercise_context = data.get("_exercises_by_id", {}).get(exercise_id) or first_row(exercises, "exercise_id", exercise_id)
    safety_feedback = feedback_analysis.get("recent_feedback", [{}])[-1] if feedback_analysis.get("recent_feedback") else {}
    safety_review = review_safety(user, exercise_context, history_analysis, safety_feedback)
    recommendation = recommend_action({
        "user_profile": user,
        "current_plan": current_plan,
        "history_summary": history_analysis,
        "recent_feedback": feedback_analysis.get("recent_feedback", []),
        "exercise_context": exercise_context,
        "safety_review": safety_review,
    })
    adjustment = adjust_plan(user, current_plan, current_items, history_analysis, feedback_analysis, safety_review=safety_review)
    coach = answer_user_question("Hôm nay tôi mệt, có nên tập không?", {
        "user_profile": user,
        "current_plan": current_plan,
        "history_analysis": history_analysis,
        "feedback_analysis": feedback_analysis,
        "recommendation": recommendation,
        "safety_review": safety_review,
    })
    return {
        "user_id": user_id,
        "user_profile": user,
        "current_plan": current_plan,
        "exercise_context": exercise_context,
        "generated_plan": generated_plan,
        "history_analysis": history_analysis,
        "feedback_analysis": feedback_analysis,
        "safety_review": safety_review,
        "recommendation": recommendation,
        "plan_adjustment": adjustment,
        "ai_coach": coach,
    }


def evaluate(results: list[dict[str, Any]]) -> dict[str, Any]:
    actions = Counter(r["recommendation"].get("recommended_action") for r in results)
    safety_status = Counter(r["safety_review"].get("safety_status") for r in results)
    adjustment_status = Counter(r["plan_adjustment"].get("adjustment_status") for r in results)
    invalid = sum(1 for r in results if r["recommendation"].get("recommended_action") not in VALID_ACTIONS)
    missing_expl = sum(1 for r in results if not r["recommendation"].get("explanation") or not r["ai_coach"].get("answer"))
    unsafe = 0
    increase_blocked = 0
    empty_plans = 0
    empty_sessions = 0
    duplicate_in_session = 0
    missing_safety_note = 0
    for r in results:
        action = r["recommendation"].get("recommended_action")
        safety = r["safety_review"].get("safety_status")
        if safety in {"Avoid", "Review"} and action in {"Increase Difficulty", "Increase Volume"}:
            unsafe += 1
        if r["plan_adjustment"].get("increase_blocked_by_safety"):
            increase_blocked += 1
        generated = r.get("generated_plan", {}) or {}
        sessions = generated.get("sessions", []) or []
        if not sessions:
            empty_plans += 1
        for session in sessions:
            exercises = session.get("exercises", []) or []
            if not exercises:
                empty_sessions += 1
            ids = [clean(ex.get("exercise_id")) for ex in exercises if clean(ex.get("exercise_id"))]
            duplicate_in_session += len(ids) - len(set(ids))
        adjustment = r.get("plan_adjustment", {}) or {}
        if safety in {"Avoid", "Review"} and not adjustment.get("safety_notes"):
            missing_safety_note += 1
    schema_errors = 0
    for r in results:
        for key in ["generated_plan", "history_analysis", "feedback_analysis", "safety_review", "recommendation", "plan_adjustment", "ai_coach"]:
            if key not in r or not isinstance(r[key], dict):
                schema_errors += 1
    hard_fail = unsafe or schema_errors or invalid or missing_expl or empty_plans or empty_sessions or duplicate_in_session
    status = "PASS" if hard_fail == 0 else "NEED FIX"
    confidences = [float(r["recommendation"].get("confidence", 0)) for r in results]
    risk_scores = [float(r["safety_review"].get("risk_score", 0)) for r in results]
    return {
        "stage_6_status": status,
        "stage_6a_revised_status": status,
        "ready_for_integration_backend_app": status == "PASS",
        "ready_for_stage_6b_ml_dataset_builder": status == "PASS",
        "tested_user_count": len(results),
        "recommendation_count": len(results),
        "recommendation_action_distribution": dict(actions),
        "safety_review_count": len(results),
        "safety_status_distribution": dict(safety_status),
        "adjustment_status_distribution": dict(adjustment_status),
        "coach_response_count": len(results),
        "average_recommendation_confidence": round(average(confidences), 4),
        "average_safety_risk_score": round(average(risk_scores), 4),
        "review_or_avoid_count": safety_status.get("Review", 0) + safety_status.get("Avoid", 0),
        "increase_blocked_by_safety_count": increase_blocked,
        "empty_generated_plan_count": empty_plans,
        "empty_exercise_session_count": empty_sessions,
        "duplicate_exercise_in_session_count": duplicate_in_session,
        "missing_safety_note_count": missing_safety_note,
        "plans_generated_count": len(results),
        "plan_adjustments_count": len(results),
        "invalid_recommendation_count": invalid,
        "unsafe_recommendation_count": unsafe,
        "missing_explanation_count": missing_expl,
        "schema_error_count": schema_errors,
    }


def write_outputs(results: list[dict[str, Any]], evaluation: dict[str, Any]) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    def dump(name: str, obj: Any) -> None:
        (OUTPUT_DIR / name).write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")
    dump("generated_plan_examples.json", [r["generated_plan"] for r in results])
    dump("recommendation_examples.json", [r["recommendation"] for r in results])
    dump("history_analysis_examples.json", [r["history_analysis"] for r in results])
    dump("feedback_analysis_examples.json", [r["feedback_analysis"] for r in results])
    dump("plan_adjustment_examples.json", [r["plan_adjustment"] for r in results])
    dump("safety_review_examples.json", [r["safety_review"] for r in results])
    dump("ai_coach_examples.json", [r["ai_coach"] for r in results])
    dump("ml_signal_samples.json", [build_ml_signal_sample(r) for r in results])
    dump("ai_evaluation_summary.json", evaluation)
    report = [
        "# Stage 6 AI Evaluation Report",
        "",
        f"Stage 6 Status: **{evaluation['stage_6_status']}**",
        f"Ready for integration/backend/app: **{'YES' if evaluation['ready_for_integration_backend_app'] else 'NO'}**",
        "",
        f"- Recommendations generated: {evaluation['recommendation_count']}",
        f"- Users tested: {evaluation['tested_user_count']}",
        f"- Safety reviews generated: {evaluation['safety_review_count']}",
        f"- Plans generated: {evaluation['plans_generated_count']}",
        f"- Plan adjustments: {evaluation['plan_adjustments_count']}",
        f"- Invalid recommendations: {evaluation['invalid_recommendation_count']}",
        f"- Unsafe recommendations: {evaluation['unsafe_recommendation_count']}",
        f"- Schema errors: {evaluation['schema_error_count']}",
        f"- Missing explanations: {evaluation['missing_explanation_count']}",
        f"- Empty generated plans: {evaluation['empty_generated_plan_count']}",
        f"- Empty exercise sessions: {evaluation['empty_exercise_session_count']}",
        f"- Duplicate exercises in sessions: {evaluation['duplicate_exercise_in_session_count']}",
        f"- Average recommendation confidence: {evaluation['average_recommendation_confidence']}",
        f"- Average safety risk score: {evaluation['average_safety_risk_score']}",
        "",
        f"Recommendation action distribution: `{evaluation['recommendation_action_distribution']}`",
        f"Safety status distribution: `{evaluation['safety_status_distribution']}`",
        f"Adjustment status distribution: `{evaluation['adjustment_status_distribution']}`",
    ]
    (OUTPUT_DIR / "ai_evaluation_report.md").write_text("\n".join(report) + "\n", encoding="utf-8")


def select_user_ids(data: dict[str, pd.DataFrame], sample_size: str, user_id: str | None) -> list[str]:
    users = [clean(uid) for uid in data["users"]["user_id"].tolist() if clean(uid)]
    if user_id:
        target = clean(user_id)
        return [target] if target in set(users) else []
    if sample_size.lower() == "all":
        return users
    try:
        n = int(sample_size)
    except ValueError as exc:
        raise ValueError("--sample-size must be an integer or 'all'") from exc
    return users[: max(1, min(n, len(users)))]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run Stage 6A rule-based AI baseline evaluation.")
    parser.add_argument("--sample-size", default="100", help="Number of users to test, or 'all'. Default: 100.")
    parser.add_argument("--user-id", default=None, help="Run evaluation for one user_id only.")
    args = parser.parse_args(argv)
    data = load_csv_exports()
    data["_users_by_id"] = index_first(data["users"], "user_id")
    data["_plans_by_user_id"] = index_first(data["workout_plans"], "user_id")
    data["_exercises_by_id"] = index_first(data["exercises"], "exercise_id")
    data["_plan_items_by_plan_id"] = index_many(data["workout_plan_items"], "plan_id")
    data["_sessions_by_user_id"] = index_many(data["workout_history_sessions"], "user_id")
    data["_history_items_by_user_id"] = index_many(data["workout_history_items"], "user_id")
    data["_feedback_by_user_id"] = index_many(data["user_feedback"], "user_id")
    user_ids = select_user_ids(data, args.sample_size, args.user_id)
    if not user_ids:
        print("No matching users found for the requested evaluation.")
        return 1
    results = [run_for_user(data, uid) for uid in user_ids]
    evaluation = evaluate(results)
    write_outputs(results, evaluation)
    print("=" * 72)
    print("AI FITNESS DATASET STAGE 6 PIPELINE")
    print("=" * 72)
    print(f"Users tested                 : {len(user_ids)}")
    print(f"Plans generated              : {evaluation['plans_generated_count']}")
    print(f"Recommendations generated    : {evaluation['recommendation_count']}")
    print(f"Safety reviews generated     : {evaluation['safety_review_count']}")
    print(f"AI coach responses generated : {len(results)}")
    print(f"Invalid recommendations      : {evaluation['invalid_recommendation_count']}")
    print(f"Unsafe recommendations       : {evaluation['unsafe_recommendation_count']}")
    print(f"Schema errors                : {evaluation['schema_error_count']}")
    print(f"Missing explanations         : {evaluation['missing_explanation_count']}")
    print(f"Empty generated plans        : {evaluation['empty_generated_plan_count']}")
    print(f"Empty exercise sessions      : {evaluation['empty_exercise_session_count']}")
    print(f"Duplicate exercises/session  : {evaluation['duplicate_exercise_in_session_count']}")
    print(f"Average rec confidence       : {evaluation['average_recommendation_confidence']}")
    print(f"Average safety risk score    : {evaluation['average_safety_risk_score']}")
    print(f"Stage 6A Revised Status      : {evaluation['stage_6a_revised_status']}")
    print(f"Ready integration/backend    : {'YES' if evaluation['ready_for_integration_backend_app'] else 'NO'}")
    print(f"Ready Stage 6B ML Dataset    : {'YES' if evaluation['ready_for_stage_6b_ml_dataset_builder'] else 'NO'}")
    print(f"Output dir                   : {OUTPUT_DIR}")
    print("=" * 72)
    return 0 if evaluation["stage_6_status"] in {"PASS", "PASS WITH NOTES"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
