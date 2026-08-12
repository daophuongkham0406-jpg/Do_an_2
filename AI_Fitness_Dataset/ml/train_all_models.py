from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import joblib
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier, RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import LabelEncoder

if __package__ is None or __package__ == "":
    sys.path.append(str(Path(__file__).resolve().parents[1]))
    from ml.evaluation import (
        classification_metrics,
        feature_importance,
        preference_extra_metrics,
        recommendation_safety_metrics,
        safety_extra_metrics,
    )
    from ml.model_schema import RANDOM_STATE, TASKS, project_root
    from ml.preprocessing import build_preprocessor, infer_feature_columns, prepare_xy, transformed_feature_names
else:
    from .evaluation import (
        classification_metrics,
        feature_importance,
        preference_extra_metrics,
        recommendation_safety_metrics,
        safety_extra_metrics,
    )
    from .model_schema import RANDOM_STATE, TASKS, project_root
    from .preprocessing import build_preprocessor, infer_feature_columns, prepare_xy, transformed_feature_names


def read_split(input_dir: Path, task: str, split: str) -> pd.DataFrame:
    spec = TASKS[task]
    path = input_dir / spec[f"{split}_file"]
    if path.exists():
        return pd.read_csv(path, dtype=str, keep_default_na=False, encoding="utf-8-sig")
    dataset = pd.read_csv(input_dir / spec["dataset_file"], dtype=str, keep_default_na=False, encoding="utf-8-sig")
    return dataset


def candidate_models() -> dict[str, Any]:
    return {
        "LogisticRegression": LogisticRegression(class_weight="balanced", max_iter=2000, random_state=RANDOM_STATE),
        "RandomForestClassifier": RandomForestClassifier(class_weight="balanced", n_estimators=300, random_state=RANDOM_STATE),
        "HistGradientBoostingClassifier": HistGradientBoostingClassifier(random_state=RANDOM_STATE),
    }


def model_score(task: str, metrics: dict[str, Any]) -> tuple[float, float, float, float]:
    unsafe_after = metrics.get("unsafe_prediction_count_after_override", 0)
    if task == "safety":
        safety_recall = metrics.get("monitor_review_avoid_recall", 0.0)
        return (-unsafe_after, safety_recall, metrics["macro_f1"], metrics["balanced_accuracy"])
    if task == "preference":
        return (metrics.get("dislike_recall", 0.0), metrics["macro_f1"], metrics["weighted_f1"], metrics["balanced_accuracy"])
    return (-unsafe_after, metrics["macro_f1"], metrics["balanced_accuracy"], metrics["weighted_f1"])


def predict_labels(model: Any, encoder: LabelEncoder, x_transformed: Any) -> list[str]:
    encoded = model.predict(x_transformed)
    return encoder.inverse_transform(encoded).tolist()


def predict_proba(model: Any, encoder: LabelEncoder, x_transformed: Any, row_index: int = 0) -> dict[str, float]:
    if not hasattr(model, "predict_proba"):
        return {}
    probabilities = model.predict_proba(x_transformed[row_index:row_index + 1])[0]
    return {label: float(probabilities[idx]) for idx, label in enumerate(encoder.classes_)}


def train_task(task: str, input_dir: Path, model_dir: Path, output_dir: Path) -> dict[str, Any]:
    spec = TASKS[task]
    label = spec["label"]
    train_df = read_split(input_dir, task, "train")
    validation_df = read_split(input_dir, task, "validation")
    test_df = read_split(input_dir, task, "test")
    if task == "preference":
        train_df = train_df[train_df[label] != "Not Applicable"].copy()
        validation_df = validation_df[validation_df[label] != "Not Applicable"].copy()
        test_df = test_df[test_df[label] != "Not Applicable"].copy()
    for name, frame in [("train", train_df), ("validation", validation_df), ("test", test_df)]:
        if frame.empty:
            raise ValueError(f"{task} {name} split is empty.")
        if label not in frame.columns:
            raise ValueError(f"{task} split missing label {label}.")
        if frame[label].astype(str).str.strip().eq("").any():
            raise ValueError(f"{task} split has missing labels.")

    feature_spec = infer_feature_columns(train_df, label)
    preprocessor = build_preprocessor(feature_spec["numeric_features"], feature_spec["categorical_features"])
    x_train, y_train = prepare_xy(train_df, label, feature_spec)
    x_val, y_val = prepare_xy(validation_df, label, feature_spec)
    x_test, y_test = prepare_xy(test_df, label, feature_spec)

    encoder = LabelEncoder()
    encoder.fit(pd.concat([y_train, y_val, y_test], ignore_index=True))
    y_train_enc = encoder.transform(y_train)
    x_train_t = preprocessor.fit_transform(x_train)
    x_val_t = preprocessor.transform(x_val)
    x_test_t = preprocessor.transform(x_test)

    candidate_results: list[dict[str, Any]] = []
    for model_name, model in candidate_models().items():
        model.fit(x_train_t, y_train_enc)
        val_pred = predict_labels(model, encoder, x_val_t)
        metrics = classification_metrics(y_val.tolist(), val_pred, encoder.classes_.tolist())
        if task == "recommendation":
            metrics.update(recommendation_safety_metrics(validation_df, val_pred))
        elif task == "preference":
            metrics.update(preference_extra_metrics(metrics["classification_report"]))
        elif task == "safety":
            metrics.update(safety_extra_metrics(metrics["classification_report"]))
            metrics.update({
                "unsafe_prediction_count_before_override": 0,
                "unsafe_prediction_count_after_override": 0,
                "safety_override_count": 0,
            })
        candidate_results.append({"model_name": model_name, "model": model, "validation_metrics": metrics})

    best = sorted(candidate_results, key=lambda item: model_score(task, item["validation_metrics"]), reverse=True)[0]
    best_model = best["model"]
    test_pred = predict_labels(best_model, encoder, x_test_t)
    test_metrics = classification_metrics(y_test.tolist(), test_pred, encoder.classes_.tolist())
    unsafe_rows: list[dict[str, Any]] = []
    if task == "recommendation":
        safety_metrics = recommendation_safety_metrics(test_df, test_pred)
        unsafe_rows = safety_metrics.pop("unsafe_rows")
        test_metrics.update(safety_metrics)
    elif task == "preference":
        test_metrics.update(preference_extra_metrics(test_metrics["classification_report"]))
    elif task == "safety":
        test_metrics.update(safety_extra_metrics(test_metrics["classification_report"]))
        test_metrics.update({
            "unsafe_prediction_count_before_override": 0,
            "unsafe_prediction_count_after_override": 0,
            "safety_override_count": 0,
        })

    model_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)
    joblib.dump(best_model, model_dir / spec["model_file"])
    joblib.dump(preprocessor, model_dir / spec["preprocessor_file"])
    joblib.dump(encoder, model_dir / spec["label_encoder_file"])

    names = transformed_feature_names(preprocessor)
    importance = feature_importance(best_model, names)
    result = {
        "task": task,
        "label": label,
        "best_model_type": best["model_name"],
        "model_path": str(Path("models") / spec["model_file"]),
        "preprocessor_path": str(Path("models") / spec["preprocessor_file"]),
        "label_encoder_path": str(Path("models") / spec["label_encoder_file"]),
        "feature_spec": feature_spec,
        "train_rows": int(len(train_df)),
        "validation_rows": int(len(validation_df)),
        "test_rows": int(len(test_df)),
        "label_distribution": {
            "train": train_df[label].value_counts().to_dict(),
            "validation": validation_df[label].value_counts().to_dict(),
            "test": test_df[label].value_counts().to_dict(),
        },
        "candidate_metrics": [
            {
                "model_name": item["model_name"],
                "accuracy": item["validation_metrics"]["accuracy"],
                "balanced_accuracy": item["validation_metrics"]["balanced_accuracy"],
                "macro_f1": item["validation_metrics"]["macro_f1"],
                "weighted_f1": item["validation_metrics"]["weighted_f1"],
            }
            for item in candidate_results
        ],
        "metrics": test_metrics,
        "classification_report": test_metrics["classification_report"],
        "confusion_matrix": {"labels": encoder.classes_.tolist(), "matrix": test_metrics["confusion_matrix"]},
        "feature_importance": importance,
        "unsafe_rows": unsafe_rows,
        "prediction_example": build_prediction_example(task, test_df, x_test_t, best_model, encoder, test_pred),
    }
    return result


def build_prediction_example(task: str, frame: pd.DataFrame, x_transformed: Any, model: Any, encoder: LabelEncoder, predictions: list[str]) -> dict[str, Any]:
    row = frame.iloc[0].to_dict()
    proba = predict_proba(model, encoder, x_transformed)
    final_prediction = predictions[0]
    explanation = f"{task} model predicted {final_prediction}."
    if task == "recommendation":
        from ml.safety_override import apply_safety_override
        override = apply_safety_override(final_prediction, str(row.get("safety_status", "Safe")), float(row.get("risk_score", 0) or 0))
        final_prediction = override["final_action"]
        explanation += f" Safety override applied: {override['was_overridden']}."
    return {
        "task": task,
        "input_features": {k: v for k, v in row.items() if k not in {"recommended_action", "exercise_preference", "safety_label"}},
        "raw_prediction": predictions[0],
        "prediction_proba": proba,
        "final_prediction_after_safety_override": final_prediction,
        "explanation": explanation,
    }


def compact_model_summary(result: dict[str, Any]) -> dict[str, Any]:
    metrics = result["metrics"]
    status = "NEED FIX" if metrics.get("unsafe_prediction_count_after_override", 0) else "PASS WITH NOTES"
    return {
        "best_model_type": result["best_model_type"],
        "model_path": result["model_path"],
        "preprocessor_path": result["preprocessor_path"],
        "label_encoder_path": result["label_encoder_path"],
        "accuracy": metrics["accuracy"],
        "balanced_accuracy": metrics["balanced_accuracy"],
        "macro_f1": metrics["macro_f1"],
        "weighted_f1": metrics["weighted_f1"],
        "unsafe_prediction_count_before_override": metrics.get("unsafe_prediction_count_before_override", 0),
        "unsafe_prediction_count_after_override": metrics.get("unsafe_prediction_count_after_override", 0),
        "safety_override_count": metrics.get("safety_override_count", 0),
        "dislike_recall": metrics.get("dislike_recall", 0.0),
        "like_precision": metrics.get("like_precision", 0.0),
        "monitor_review_avoid_recall": metrics.get("monitor_review_avoid_recall", 0.0),
        "status": status,
    }


def write_report(summary: dict[str, Any], results: dict[str, dict[str, Any]], output_dir: Path, model_dir: Path) -> None:
    lines = [
        "# Stage 6C Model Evaluation Report",
        "",
        "## 1. Executive Summary",
        f"Stage 6C Status: **{summary['stage_6c_status']}**",
        f"Ready for Stage 6D Integration: **{'YES' if summary['ready_for_stage_6d_integration'] else 'NO'}**",
        f"Models trained: {len(results)}",
        f"Errors: {summary['issues']['error_count']}",
        f"Warnings: {summary['issues']['warning_count']}",
        "",
        "## 2. Input Datasets",
    ]
    for task, result in results.items():
        lines.append(f"- {task}: train={result['train_rows']}, validation={result['validation_rows']}, test={result['test_rows']}, labels={result['label_distribution']}")
    for title, task in [("Recommendation Model", "recommendation"), ("Preference Model", "preference"), ("Safety Model", "safety")]:
        result = results[task]
        metrics = result["metrics"]
        lines += [
            "",
            f"## { {'recommendation': 3, 'preference': 4, 'safety': 5}[task] }. {title}",
            f"Best model: {result['best_model_type']}",
            f"Accuracy: {metrics['accuracy']:.4f}",
            f"Balanced accuracy: {metrics['balanced_accuracy']:.4f}",
            f"Macro F1: {metrics['macro_f1']:.4f}",
            f"Weighted F1: {metrics['weighted_f1']:.4f}",
            f"Confusion matrix labels: `{result['confusion_matrix']['labels']}`",
            f"Confusion matrix: `{result['confusion_matrix']['matrix']}`",
        ]
        if task in {"recommendation", "safety"}:
            lines.append(f"Unsafe before/after override: {metrics.get('unsafe_prediction_count_before_override', 0)} / {metrics.get('unsafe_prediction_count_after_override', 0)}")
        if task == "preference":
            lines.append(f"Dislike recall: {metrics.get('dislike_recall', 0):.4f}")
        if task == "safety":
            lines.append(f"Monitor/Review/Avoid recall: {metrics.get('monitor_review_avoid_recall', 0):.4f}")
        lines.append(f"Feature importance available: {result['feature_importance']['feature_importance_available']}")
    lines += [
        "",
        "## 6. Safety Override",
        "Rule-based Safety Engine remains the final guardrail over ML predictions.",
        f"Override count: {summary['models']['recommendation']['safety_override_count']}",
        f"Unsafe after override: {summary['models']['recommendation']['unsafe_prediction_count_after_override']}",
        "",
        "## 7. Saved Model Files",
    ]
    for path in sorted(model_dir.glob("*")):
        lines.append(f"- `{path.name}`")
    lines += [
        "",
        "## 8. How The Machine Learned",
        "Models learned from user profile, exercise attributes, history adherence, feedback sentiment/difficulty and safety risk features. Rare classes remain harder to learn because Stage 6B has low sample counts for some labels.",
        "",
        "## 9. Limitations",
        "- Synthetic data",
        "- Class imbalance",
        "- Low sample class",
        "- Safety ML only supports; rule-based safety remains final",
        "",
        "## 10. Next Step",
        "Proceed to Stage 6D — ML Integration with Safety Engine.",
    ]
    (output_dir / "model_evaluation_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def run(input_dir: Path, model_dir: Path, output_dir: Path, task_filter: str = "all") -> int:
    model_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)
    tasks = list(TASKS) if task_filter == "all" else [task_filter]
    results: dict[str, dict[str, Any]] = {}
    log_lines = [
        "AI FITNESS DATASET STAGE 6C - TRAIN ML MODELS",
        f"Input dir: {input_dir}",
        f"Model dir: {model_dir}",
        f"Output dir: {output_dir}",
    ]
    for task in tasks:
        log_lines.append(f"Training {task} model...")
        result = train_task(task, input_dir, model_dir, output_dir)
        results[task] = result
        metrics = result["metrics"]
        log_lines.append(f"Best model: {result['best_model_type']}")
        log_lines.append(f"Metrics: accuracy={metrics['accuracy']:.4f}, macro_f1={metrics['macro_f1']:.4f}, balanced_accuracy={metrics['balanced_accuracy']:.4f}")
        log_lines.append(f"Saved: {result['model_path']}")

    feature_columns = {task: result["feature_spec"] for task, result in results.items()}
    model_metrics = {task: result["metrics"] for task, result in results.items()}
    registry = {
        task: {
            "model_type": result["best_model_type"],
            "model_path": result["model_path"],
            "preprocessor_path": result["preprocessor_path"],
            "label_encoder_path": result["label_encoder_path"],
            "trained_at": datetime.now().isoformat(timespec="seconds"),
        }
        for task, result in results.items()
    }
    (model_dir / "feature_columns.json").write_text(json.dumps(feature_columns, ensure_ascii=False, indent=2), encoding="utf-8")
    (model_dir / "model_metrics.json").write_text(json.dumps(model_metrics, ensure_ascii=False, indent=2), encoding="utf-8")
    (model_dir / "model_registry.json").write_text(json.dumps(registry, ensure_ascii=False, indent=2), encoding="utf-8")
    (output_dir / "confusion_matrices.json").write_text(json.dumps({task: result["confusion_matrix"] for task, result in results.items()}, ensure_ascii=False, indent=2), encoding="utf-8")
    (output_dir / "feature_importance.json").write_text(json.dumps({task: result["feature_importance"] for task, result in results.items()}, ensure_ascii=False, indent=2), encoding="utf-8")
    for task, result in results.items():
        (output_dir / f"{task}_classification_report.json").write_text(json.dumps(result["classification_report"], ensure_ascii=False, indent=2), encoding="utf-8")
    unsafe_report = {
        "recommendation": results.get("recommendation", {}).get("unsafe_rows", []),
        "safety_override_rule": "Review/Avoid or risk_score>=0.45 blocks Increase Difficulty/Increase Volume.",
    }
    (output_dir / "unsafe_prediction_report.json").write_text(json.dumps(unsafe_report, ensure_ascii=False, indent=2), encoding="utf-8")
    (output_dir / "prediction_examples.json").write_text(json.dumps([result["prediction_example"] for result in results.values()], ensure_ascii=False, indent=2), encoding="utf-8")

    compact = {task: compact_model_summary(result) for task, result in results.items()}
    unsafe_after = sum(item.get("unsafe_prediction_count_after_override", 0) for item in compact.values())
    notes = []
    for task, result in results.items():
        for label, count in result["label_distribution"]["train"].items():
            if count < 10:
                notes.append(f"{task} train class {label} has low sample count: {count}")
    status = "NEED FIX" if unsafe_after else "PASS WITH NOTES" if notes else "PASS"
    summary = {
        "stage_6c_status": status,
        "ready_for_stage_6d_integration": status in {"PASS", "PASS WITH NOTES"},
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "models": compact,
        "issues": {
            "error_count": 1 if status == "NEED FIX" else 0,
            "warning_count": len(notes),
            "notes": notes,
        },
    }
    (output_dir / "model_evaluation_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    write_report(summary, results, output_dir, model_dir)
    (output_dir / "README_model_outputs.md").write_text(
        "# Stage 6C Model Outputs\n\nThese files contain trained sklearn models, preprocessors, label encoders, metrics, reports and prediction examples for Stage 6D integration.\n",
        encoding="utf-8",
    )
    log_lines += [
        "Safety override check:",
        f"unsafe after: {unsafe_after}",
        f"Stage 6C Status: {status}",
        f"Ready for Stage 6D Integration: {'YES' if summary['ready_for_stage_6d_integration'] else 'NO'}",
    ]
    (output_dir / "model_training_log.txt").write_text("\n".join(log_lines) + "\n", encoding="utf-8")

    print("=" * 72)
    print("AI FITNESS DATASET STAGE 6C - TRAIN ML MODELS")
    print("=" * 72)
    print(f"Input dir  : {input_dir}")
    print(f"Model dir  : {model_dir}")
    print(f"Output dir : {output_dir}")
    for task in tasks:
        item = compact[task]
        print("")
        print(f"{task.title()} model:")
        print(f"- Best model: {item['best_model_type']}")
        print(f"- Accuracy: {item['accuracy']:.4f}")
        print(f"- Macro F1: {item['macro_f1']:.4f}")
        if task == "recommendation":
            print(f"- Unsafe before override: {item['unsafe_prediction_count_before_override']}")
            print(f"- Unsafe after override: {item['unsafe_prediction_count_after_override']}")
        if task == "preference":
            print(f"- Dislike recall: {item['dislike_recall']:.4f}")
        if task == "safety":
            print(f"- Monitor/Review recall: {item['monitor_review_avoid_recall']:.4f}")
    print("")
    print("Files saved:")
    print("- models/recommendation_model.pkl")
    print("- models/preference_model.pkl")
    print("- models/safety_risk_model.pkl")
    print(f"Stage 6C Status: {status}")
    print(f"Ready Stage 6D Integration: {'YES' if summary['ready_for_stage_6d_integration'] else 'NO'}")
    print("=" * 72)
    return 0 if status in {"PASS", "PASS WITH NOTES"} else 1


def main(argv: list[str] | None = None) -> int:
    root = project_root()
    parser = argparse.ArgumentParser(description="Train Stage 6C ML models.")
    parser.add_argument("--input-dir", default=str(root / "ml_outputs"))
    parser.add_argument("--model-dir", default=str(root / "models"))
    parser.add_argument("--output-dir", default=str(root / "model_outputs"))
    parser.add_argument("--task", choices=["all", "recommendation", "preference", "safety"], default="all")
    args = parser.parse_args(argv)
    return run(Path(args.input_dir), Path(args.model_dir), Path(args.output_dir), args.task)


if __name__ == "__main__":
    raise SystemExit(main())
