from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

import pandas as pd

if __package__ is None or __package__ == "":
    sys.path.append(str(Path(__file__).resolve().parents[1]))
    from ai.feedback_analyzer import analyze_feedback
    from ai.history_analyzer import analyze_history
    from ai.recommendation_engine import recommend_action as rule_recommend_action
    from ai.safety_review_engine import review_safety
    from ml_integration.feature_builder import build_preference_features, build_recommendation_features, build_safety_features
    from ml_integration.hybrid_decision_engine import decide_final_action
    from ml_integration.ml_predictor import MLPredictor
    from ml_integration.model_loader import MLModelBundle
    from ml_integration.prediction_logger import build_log_row, write_prediction_log
    from ml_integration.safety_override import is_unsafe_final_action
    from ml_integration.schema import CSV_FILES, VALID_FINAL_ACTIONS, project_root
    from ml_integration.utils import clean, index_first, index_many, issue
else:
    from ai.feedback_analyzer import analyze_feedback
    from ai.history_analyzer import analyze_history
    from ai.recommendation_engine import recommend_action as rule_recommend_action
    from ai.safety_review_engine import review_safety
    from .feature_builder import build_preference_features, build_recommendation_features, build_safety_features
    from .hybrid_decision_engine import decide_final_action
    from .ml_predictor import MLPredictor
    from .model_loader import MLModelBundle
    from .prediction_logger import build_log_row, write_prediction_log
    from .safety_override import is_unsafe_final_action
    from .schema import CSV_FILES, VALID_FINAL_ACTIONS, project_root
    from .utils import clean, index_first, index_many, issue


def load_csv_data(csv_dir: Path) -> dict[str, pd.DataFrame]:
    return {name: pd.read_csv(csv_dir / filename, dtype=str, keep_default_na=False, encoding="utf-8-sig") for name, filename in CSV_FILES.items()}


def build_indexes(data: dict[str, pd.DataFrame]) -> dict[str, Any]:
    return {
        "users": index_first(data["users"], "user_id"),
        "plans_by_user": index_first(data["workout_plans"], "user_id"),
        "exercises": index_first(data["exercises"], "exercise_id"),
        "plan_items_by_plan": index_many(data["workout_plan_items"], "plan_id"),
        "sessions_by_user": index_many(data["workout_history_sessions"], "user_id"),
        "history_items_by_user": index_many(data["workout_history_items"], "user_id"),
        "feedback_by_user": index_many(data["user_feedback"], "user_id"),
    }


def select_user_ids(data: dict[str, pd.DataFrame], sample_size: str, user_id: str | None) -> list[str]:
    all_users = [clean(uid) for uid in data["users"]["user_id"].tolist() if clean(uid)]
    if user_id:
        return [clean(user_id)] if clean(user_id) in set(all_users) else []
    if sample_size.lower() == "all":
        return all_users
    return all_users[: max(1, min(int(sample_size), len(all_users)))]


def first_exercise_for_plan(indexes: dict[str, Any], plan_id: str) -> dict[str, Any]:
    items = indexes["plan_items_by_plan"].get(plan_id, [])
    if not items:
        return {}
    exercise_id = clean(items[0].get("exercise_id"))
    return indexes["exercises"].get(exercise_id, {})


def run_for_user(user_id: str, indexes: dict[str, Any], model_bundle: MLModelBundle, predictor: MLPredictor) -> tuple[dict[str, Any], dict[str, Any]]:
    user = indexes["users"].get(user_id, {})
    current_plan = indexes["plans_by_user"].get(user_id, {})
    plan_id = clean(current_plan.get("plan_id"))
    exercise = first_exercise_for_plan(indexes, plan_id)
    exercise_id = clean(exercise.get("exercise_id"))
    sessions = indexes["sessions_by_user"].get(user_id, [])
    history_items = indexes["history_items_by_user"].get(user_id, [])
    feedback_rows = indexes["feedback_by_user"].get(user_id, [])
    history_analysis = analyze_history(user_id, sessions, history_items)
    feedback_analysis = analyze_feedback(user_id, feedback_rows)
    feedback_context = feedback_analysis.get("recent_feedback", [{}])[-1] if feedback_analysis.get("recent_feedback") else {}
    safety_review = review_safety(user, exercise, history_analysis, feedback_context)
    rule_rec = rule_recommend_action({
        "user_profile": user,
        "current_plan": current_plan,
        "history_summary": history_analysis,
        "recent_feedback": feedback_analysis.get("recent_feedback", []),
        "exercise_context": exercise,
        "safety_review": safety_review,
    })
    feature_columns = model_bundle.feature_columns
    rec_features = build_recommendation_features(user, current_plan, exercise, history_analysis, feedback_analysis, safety_review, feature_columns)
    pref_features = build_preference_features(user, exercise, feedback_analysis, history_analysis, feature_columns)
    safety_features = build_safety_features(user, exercise, history_analysis, feedback_analysis, safety_review, feature_columns)
    ml_rec = predictor.predict("recommendation", rec_features)
    ml_pref = predictor.predict("preference", pref_features)
    ml_safety = predictor.predict("safety", safety_features)
    decision = decide_final_action(user_id, exercise_id, ml_rec, ml_pref, ml_safety, rule_rec, safety_review)
    diagnostics = {
        "user_id": user_id,
        "plan_id": plan_id,
        "exercise_id": exercise_id,
        "missing_feature_count": rec_features.get("_missing_feature_count", 0) + pref_features.get("_missing_feature_count", 0) + safety_features.get("_missing_feature_count", 0),
        "prediction_success": all(pred.get("status") == "OK" for pred in [ml_rec, ml_pref, ml_safety]),
        "feature_build_success": True,
    }
    return decision, diagnostics


def summarize(results: list[dict[str, Any]], diagnostics: list[dict[str, Any]], model_validation: dict[str, Any], issues: list[dict[str, Any]]) -> dict[str, Any]:
    final_actions = Counter(result.get("final_action") for result in results)
    decision_sources = Counter(result.get("decision_source") for result in results)
    ml_rec_dist = Counter(result.get("ml_recommendation", {}).get("raw_prediction") for result in results)
    rule_safety_dist = Counter(result.get("rule_safety_review", {}).get("safety_status") for result in results)
    unsafe = 0
    invalid = 0
    overrides = 0
    fallback = 0
    for result in results:
        final_action = result.get("final_action", "")
        rule_safety = result.get("rule_safety_review", {})
        if final_action not in VALID_FINAL_ACTIONS:
            invalid += 1
        if result.get("was_overridden"):
            overrides += 1
        if result.get("decision_source") == "fallback_to_rule_based":
            fallback += 1
        if is_unsafe_final_action(final_action, rule_safety.get("safety_status", ""), float(rule_safety.get("risk_score", 0) or 0), rule_safety.get("risk_flags", [])):
            unsafe += 1
    schema_errors = sum(1 for row in diagnostics if not row.get("feature_build_success") or not row.get("prediction_success"))
    missing_features = sum(int(row.get("missing_feature_count", 0)) for row in diagnostics)
    error_count = sum(1 for row in issues if row["severity"] == "ERROR")
    warning_count = sum(1 for row in issues if row["severity"] == "WARNING")
    if not model_validation.get("model_load_success"):
        error_count += 1
    if missing_features:
        warning_count += 1
    status = "NEED FIX" if unsafe or invalid or schema_errors or error_count else "PASS WITH NOTES" if warning_count else "PASS"
    return {
        "stage_6d_status": status,
        "ready_for_backend_app": status in {"PASS", "PASS WITH NOTES"},
        "tested_user_count": len(results),
        "model_load_success": bool(model_validation.get("model_load_success")),
        "feature_build_success_count": sum(1 for row in diagnostics if row.get("feature_build_success")),
        "prediction_success_count": sum(1 for row in diagnostics if row.get("prediction_success")),
        "final_decision_count": len(results),
        "unsafe_final_action_count": unsafe,
        "safety_override_count": overrides,
        "fallback_to_rule_count": fallback,
        "schema_error_count": schema_errors,
        "missing_feature_count": missing_features,
        "invalid_action_count": invalid,
        "decision_source_distribution": dict(decision_sources),
        "final_action_distribution": dict(final_actions),
        "ml_recommendation_distribution": dict(ml_rec_dist),
        "rule_safety_distribution": dict(rule_safety_dist),
        "issues": {
            "error_count": error_count,
            "warning_count": warning_count,
            "info_count": sum(1 for row in issues if row["severity"] == "INFO"),
        },
    }


def write_outputs(output_dir: Path, results: list[dict[str, Any]], logs: list[dict[str, Any]], issues: list[dict[str, Any]], summary: dict[str, Any], model_validation: dict[str, Any]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "ml_integration_examples.json").write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    (output_dir / "final_recommendation_examples.json").write_text(json.dumps([{
        "user_id": r["user_id"],
        "exercise_id": r["exercise_id"],
        "candidate_action": r["candidate_action"],
        "final_action": r["final_action"],
        "decision_source": r["decision_source"],
        "final_confidence": r["final_confidence"],
        "explanation": r["explanation"],
    } for r in results], ensure_ascii=False, indent=2), encoding="utf-8")
    (output_dir / "safety_override_examples.json").write_text(json.dumps([r["safety_lock"] for r in results if r.get("was_overridden")][:50], ensure_ascii=False, indent=2), encoding="utf-8")
    write_prediction_log(logs, str(output_dir / "prediction_log_sample.csv"))
    pd.DataFrame(issues, columns=["issue_id", "severity", "component", "user_id", "exercise_id", "message", "suggested_fix"]).to_csv(output_dir / "integration_issues.csv", index=False, encoding="utf-8-sig")
    (output_dir / "integration_test_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    (output_dir / "integration_test_report.md").write_text(build_report(summary, model_validation), encoding="utf-8")
    (output_dir / "README_integration_outputs.md").write_text(
        "# Stage 6D Integration Outputs\n\nPrediction logs are not ground truth until paired with real user feedback after action.\n",
        encoding="utf-8",
    )


def build_report(summary: dict[str, Any], model_validation: dict[str, Any]) -> str:
    return "\n".join([
        "# Stage 6D Integration Test Report",
        "",
        "## 1. Executive Summary",
        f"Stage 6D Status: **{summary['stage_6d_status']}**",
        f"Ready for Backend/App: **{'YES' if summary['ready_for_backend_app'] else 'NO'}**",
        f"Users tested: {summary['tested_user_count']}",
        f"Unsafe final actions: {summary['unsafe_final_action_count']}",
        f"Errors: {summary['issues']['error_count']}",
        f"Warnings: {summary['issues']['warning_count']}",
        "",
        "## 2. Model Loading",
        f"Model files loaded: {model_validation.get('tasks', {})}",
        f"Load errors: {model_validation.get('errors', [])}",
        "",
        "## 3. Feature Builder",
        f"Missing features filled: {summary['missing_feature_count']}",
        "Schema matching: feature rows are aligned to `models/feature_columns.json`.",
        "",
        "## 4. ML Prediction",
        f"Prediction success count: {summary['prediction_success_count']}",
        f"ML recommendation distribution: `{summary['ml_recommendation_distribution']}`",
        "",
        "## 5. Hybrid Decision Engine",
        f"Decision source distribution: `{summary['decision_source_distribution']}`",
        f"Fallback to rule count: {summary['fallback_to_rule_count']}",
        "",
        "## 6. Safety Lock",
        f"Override count: {summary['safety_override_count']}",
        f"Unsafe final action count: {summary['unsafe_final_action_count']}",
        f"Rule safety distribution: `{summary['rule_safety_distribution']}`",
        "",
        "## 7. Final Action Distribution",
        f"`{summary['final_action_distribution']}`",
        "",
        "## 8. Prediction Logging",
        "Log file: `prediction_log_sample.csv`",
        "Ground truth limitation: prediction logs become training signal only after real user feedback after action is attached.",
        "",
        "## 9. API / Backend Integration",
        "Mock Flask routes are available in `ml_integration/api_routes.py`.",
        "",
        "## 10. Limitations",
        "Recommendation macro F1 still low. Preference model has proxy leakage risk. Safety model may be rule distillation. Guarded mode required.",
        "",
        "## 11. Next Step",
        "Proceed to backend/app integration or collect real feedback for retraining.",
        "",
    ])


def run(sample_size: str, user_id: str | None, csv_dir: Path, model_dir: Path, output_dir: Path) -> int:
    issues: list[dict[str, Any]] = []
    data = load_csv_data(csv_dir)
    indexes = build_indexes(data)
    model_bundle = MLModelBundle(model_dir)
    model_bundle.load_all()
    model_validation = model_bundle.validate()
    predictor = MLPredictor(model_bundle)
    user_ids = select_user_ids(data, sample_size, user_id)
    results: list[dict[str, Any]] = []
    diagnostics: list[dict[str, Any]] = []
    logs: list[dict[str, Any]] = []
    for index, uid in enumerate(user_ids, start=1):
        try:
            decision, diag = run_for_user(uid, indexes, model_bundle, predictor)
            results.append(decision)
            diagnostics.append(diag)
            logs.append(build_log_row(f"PRED{index:07d}", decision, diag.get("plan_id", "")))
            if diag.get("missing_feature_count", 0):
                issues.append(issue(len(issues) + 1, "WARNING", "feature_builder", uid, diag.get("exercise_id", ""), f"Filled {diag['missing_feature_count']} missing features with fallback values.", "Review feature source coverage."))
        except Exception as exc:
            issues.append(issue(len(issues) + 1, "ERROR", "integration_pipeline", uid, "", str(exc), "Inspect user data and model inputs."))
    summary = summarize(results, diagnostics, model_validation, issues)
    if summary["fallback_to_rule_count"] > 0:
        issues.append(issue(len(issues) + 1, "WARNING", "hybrid_decision_engine", "", "", f"{summary['fallback_to_rule_count']} predictions fell back to rule-based recommendation.", "Monitor ML confidence and low-confidence cases."))
        summary = summarize(results, diagnostics, model_validation, issues)
    write_outputs(output_dir, results, logs, issues, summary, model_validation)
    print("=" * 72)
    print("AI FITNESS DATASET STAGE 6D - GUARDED ML INTEGRATION")
    print("=" * 72)
    print("Model loading:")
    for task, ok in model_validation.get("tasks", {}).items():
        print(f"- {task.title()} model: {'OK' if ok else 'FAIL'}")
    print("")
    print(f"Users tested          : {summary['tested_user_count']}")
    print(f"Feature build success : {summary['feature_build_success_count']}")
    print(f"Prediction success    : {summary['prediction_success_count']}")
    print(f"Final decisions       : {summary['final_decision_count']}")
    print(f"Unsafe final actions  : {summary['unsafe_final_action_count']}")
    print(f"Safety overrides      : {summary['safety_override_count']}")
    print(f"Fallback to rule      : {summary['fallback_to_rule_count']}")
    print(f"Schema errors         : {summary['schema_error_count']}")
    print(f"Invalid actions       : {summary['invalid_action_count']}")
    print(f"Stage 6D Status       : {summary['stage_6d_status']}")
    print(f"Ready Backend/App     : {'YES' if summary['ready_for_backend_app'] else 'NO'}")
    print(f"Output dir            : {output_dir}")
    print("=" * 72)
    return 0 if summary["stage_6d_status"] in {"PASS", "PASS WITH NOTES"} else 1


def main(argv: list[str] | None = None) -> int:
    root = project_root()
    parser = argparse.ArgumentParser(description="Run Stage 6D guarded ML integration.")
    parser.add_argument("--sample-size", default="100")
    parser.add_argument("--user-id", default=None)
    parser.add_argument("--csv-dir", default=str(root / "exports" / "csv"))
    parser.add_argument("--model-dir", default=str(root / "models"))
    parser.add_argument("--output-dir", default=str(root / "integration_outputs"))
    args = parser.parse_args(argv)
    return run(args.sample_size, args.user_id, Path(args.csv_dir), Path(args.model_dir), Path(args.output_dir))


if __name__ == "__main__":
    raise SystemExit(main())
