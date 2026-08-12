from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

if __package__ is None or __package__ == "":
    sys.path.append(str(Path(__file__).resolve().parents[1]))
    from ml.build_ml_dataset import (
        build_preference_dataset,
        build_recommendation_dataset,
        build_safety_dataset,
        build_unified_dataset,
        load_csv_inputs,
        load_json_inputs,
    )
    from ml.dataset_split import assign_user_splits, split_dataframe
    from ml.feature_engineering import clean
    from ml.ml_schema import AI_OUTPUT_FILES, CSV_FILES, RANDOM_SEED, resolve_project_root
    from ml.validate_ml_dataset import (
        IssueLog,
        dataset_summary,
        validate_dataset,
        validate_input_files,
        validate_loaded_inputs,
        validate_outputs_exist,
        validate_splits,
    )
else:
    from .build_ml_dataset import (
        build_preference_dataset,
        build_recommendation_dataset,
        build_safety_dataset,
        build_unified_dataset,
        load_csv_inputs,
        load_json_inputs,
    )
    from .dataset_split import assign_user_splits, split_dataframe
    from .feature_engineering import clean
    from .ml_schema import AI_OUTPUT_FILES, CSV_FILES, RANDOM_SEED, resolve_project_root
    from .validate_ml_dataset import (
        IssueLog,
        dataset_summary,
        validate_dataset,
        validate_input_files,
        validate_loaded_inputs,
        validate_outputs_exist,
        validate_splits,
    )


def write_csv(frame: pd.DataFrame, path: Path) -> None:
    frame.to_csv(path, index=False, encoding="utf-8-sig")


def feature_type(series: pd.Series) -> str:
    if series.empty:
        return "unknown"
    numeric = pd.to_numeric(series, errors="coerce")
    if numeric.notna().mean() >= 0.95:
        return "numeric"
    return "categorical"


def build_feature_dictionary(datasets: dict[str, tuple[pd.DataFrame, str]]) -> dict[str, Any]:
    identifier_columns = {
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
    out: dict[str, Any] = {}
    for name, (frame, label_column) in datasets.items():
        features: dict[str, dict[str, str]] = {}
        for column in frame.columns:
            if column in identifier_columns or column == label_column:
                continue
            kind = feature_type(frame[column])
            encoding = "standard_scaler" if kind == "numeric" else "one_hot"
            features[column] = {
                "type": kind,
                "description": f"{name} feature: {column}",
                "stage_6c_encoding": encoding,
            }
        out[name] = {"label": label_column, "features": features}
    return out


def label_distribution(frame: pd.DataFrame, label_column: str) -> dict[str, int]:
    if label_column not in frame.columns:
        return {}
    return {str(k): int(v) for k, v in frame[label_column].map(clean).value_counts().to_dict().items()}


def make_summary(
    recommendation: pd.DataFrame,
    preference: pd.DataFrame,
    safety: pd.DataFrame,
    unified: pd.DataFrame,
    unified_splits: dict[str, pd.DataFrame],
    split_overlap: int,
    issues: IssueLog,
) -> dict[str, Any]:
    counts = issues.counts()
    status = "NEED FIX" if counts["error_count"] else "PASS WITH NOTES" if counts["warning_count"] else "PASS"
    return {
        "stage_6b_status": status,
        "ready_for_stage_6c_training": status in {"PASS", "PASS WITH NOTES"},
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "random_seed": RANDOM_SEED,
        "datasets": {
            "recommendation": dataset_summary(recommendation, "recommended_action"),
            "preference": dataset_summary(preference, "exercise_preference"),
            "safety": dataset_summary(safety, "safety_label"),
            "unified": dataset_summary(unified),
        },
        "splits": {
            "train": {
                "row_count": int(len(unified_splits["train"])),
                "user_count": int(unified_splits["train"]["user_id"].map(clean).nunique()) if "user_id" in unified_splits["train"].columns else 0,
            },
            "validation": {
                "row_count": int(len(unified_splits["validation"])),
                "user_count": int(unified_splits["validation"]["user_id"].map(clean).nunique()) if "user_id" in unified_splits["validation"].columns else 0,
            },
            "test": {
                "row_count": int(len(unified_splits["test"])),
                "user_count": int(unified_splits["test"]["user_id"].map(clean).nunique()) if "user_id" in unified_splits["test"].columns else 0,
            },
            "user_overlap_count": split_overlap,
        },
        "issues": counts,
    }


def make_report(summary: dict[str, Any], input_status: dict[str, bool], feature_dictionary: dict[str, Any]) -> str:
    datasets = summary["datasets"]
    issues = summary["issues"]
    lines = [
        "# Stage 6B ML Dataset Report",
        "",
        "## 1. Executive Summary",
        f"Stage 6B Status: **{summary['stage_6b_status']}**",
        f"Ready for Stage 6C Training: **{'YES' if summary['ready_for_stage_6c_training'] else 'NO'}**",
        f"Error count: {issues['error_count']}",
        f"Warning count: {issues['warning_count']}",
        "",
        "## 2. Input Files",
    ]
    for path, exists in input_status.items():
        lines.append(f"- {path}: {'FOUND' if exists else 'MISSING'}")
    lines += [
        "",
        "## 3. Dataset Outputs",
    ]
    for name, info in datasets.items():
        lines.append(f"- {name}: {info['row_count']} rows, {info['column_count']} columns")
    lines += [
        "",
        "## 4. Label Distribution",
        f"- recommended_action: `{datasets['recommendation'].get('label_distribution', {})}`",
        f"- exercise_preference: `{datasets['preference'].get('label_distribution', {})}`",
        f"- safety_label: `{datasets['safety'].get('label_distribution', {})}`",
        "",
        "## 5. Feature Groups",
        "- User features: demographics, body metrics, goals, level, schedule, equipment and limitations.",
        "- Exercise features: category, level, muscles, equipment, movement pattern, complexity and joint stress.",
        "- History features: completion, set completion, skipped/partial rate, RPE, fatigue, pain and trend.",
        "- Feedback features: sentiment, difficulty, enjoyment, fatigue, pain, duration and preference signals.",
        "- Safety features: safety status, risk score, risk flags, contraindication and pain matching counts.",
        "",
        "## 6. Split Summary",
        f"- Train: {summary['splits']['train']['row_count']} rows, {summary['splits']['train']['user_count']} users",
        f"- Validation: {summary['splits']['validation']['row_count']} rows, {summary['splits']['validation']['user_count']} users",
        f"- Test: {summary['splits']['test']['row_count']} rows, {summary['splits']['test']['user_count']} users",
        f"- User overlap: {summary['splits']['user_overlap_count']}",
        "",
        "## 7. Data Quality Issues",
        f"- ERROR: {issues['error_count']}",
        f"- WARNING: {issues['warning_count']}",
        f"- INFO: {issues['info_count']}",
        "",
        "## 8. Leakage Check",
    ]
    for name, spec in feature_dictionary.items():
        label = spec["label"]
        leaked = label in spec["features"]
        lines.append(f"- {name}: label `{label}` in feature list = {leaked}")
    lines += [
        "",
        "## 9. Limitations",
        "Dữ liệu hiện tại còn synthetic và một số class có thể imbalance, cần cân nhắc class weighting hoặc sampling ở Stage 6C.",
        "",
        "## 10. Next Step",
        "Proceed to Stage 6C — Train ML Models nếu status là PASS hoặc PASS WITH NOTES; nếu NEED FIX thì xử lý `ml_dataset_issues.csv` trước.",
    ]
    return "\n".join(lines) + "\n"


def make_outputs_readme(summary: dict[str, Any]) -> str:
    return "\n".join([
        "# Stage 6B ML Outputs",
        "",
        "Thư mục này chứa dataset huấn luyện cho Stage 6C. Stage 6B chỉ build dữ liệu, chưa train model và không tạo file `.pkl`.",
        "",
        "- `recommendation_training_dataset.csv`: feature -> `recommended_action`.",
        "- `preference_training_dataset.csv`: feature -> `exercise_preference`.",
        "- `safety_training_dataset.csv`: feature -> `safety_label`.",
        "- `ml_training_dataset.csv`: unified dataset gồm recommendation/preference/safety.",
        "- `train.csv`, `validation.csv`, `test.csv`: split theo `user_id` cho unified dataset.",
        "- `feature_dictionary.json`: mô tả feature và encoding gợi ý cho Stage 6C.",
        "- `ml_dataset_summary.json`: summary chạy gần nhất.",
        "- `ml_dataset_issues.csv`: danh sách issues nếu có.",
        "",
        f"Stage 6B Status: {summary['stage_6b_status']}",
        f"Ready for Stage 6C Training: {'YES' if summary['ready_for_stage_6c_training'] else 'NO'}",
        "",
    ])


def run(input_csv_dir: Path, ai_output_dir: Path, output_dir: Path) -> int:
    output_dir.mkdir(parents=True, exist_ok=True)
    issues = IssueLog()
    validate_input_files(input_csv_dir, ai_output_dir, CSV_FILES, AI_OUTPUT_FILES, issues)
    input_status = {
        str(input_csv_dir / filename): (input_csv_dir / filename).exists()
        for filename in CSV_FILES.values()
    }
    input_status.update({
        str(ai_output_dir / filename): (ai_output_dir / filename).exists()
        for filename in AI_OUTPUT_FILES.values()
    })

    data = load_csv_inputs(input_csv_dir)
    ai = load_json_inputs(ai_output_dir)
    validate_loaded_inputs(data, issues)

    recommendation = build_recommendation_dataset(data, ai)
    preference = build_preference_dataset(data)
    safety = build_safety_dataset(data, ai)
    preference_filtered = preference[preference["exercise_preference"].map(clean) != "Not Applicable"].copy() if not preference.empty else preference
    unified = build_unified_dataset(recommendation, preference, safety)

    validate_dataset("recommendation", recommendation, "recommended_action", {
        "Keep", "Increase Difficulty", "Reduce Difficulty", "Increase Volume", "Reduce Volume", "Replace Exercise", "Change Split", "Review Safety", "No Preference"
    }, issues)
    validate_dataset("preference", preference, "exercise_preference", {"Like", "Neutral", "Dislike", "Not Applicable"}, issues)
    validate_dataset("safety", safety, "safety_label", {"Safe", "Monitor", "Review", "Avoid"}, issues)

    all_users = unified["user_id"].tolist() if "user_id" in unified.columns else []
    user_splits = assign_user_splits(all_users, RANDOM_SEED)
    unified_splits = split_dataframe(unified, user_splits)
    recommendation_splits = split_dataframe(recommendation, user_splits)
    preference_splits = split_dataframe(preference, user_splits)
    safety_splits = split_dataframe(safety, user_splits)
    split_overlap = validate_splits(unified_splits, issues)

    write_csv(recommendation, output_dir / "recommendation_training_dataset.csv")
    write_csv(preference, output_dir / "preference_training_dataset.csv")
    write_csv(preference_filtered, output_dir / "preference_training_dataset_filtered.csv")
    write_csv(safety, output_dir / "safety_training_dataset.csv")
    write_csv(unified, output_dir / "ml_training_dataset.csv")
    for split_name, frame in unified_splits.items():
        write_csv(frame, output_dir / f"{split_name}.csv")
    for split_name, frame in recommendation_splits.items():
        write_csv(frame, output_dir / f"recommendation_{split_name}.csv")
    for split_name, frame in preference_splits.items():
        write_csv(frame, output_dir / f"preference_{split_name}.csv")
    for split_name, frame in safety_splits.items():
        write_csv(frame, output_dir / f"safety_{split_name}.csv")

    feature_dictionary = build_feature_dictionary({
        "recommendation": (recommendation, "recommended_action"),
        "preference": (preference, "exercise_preference"),
        "safety": (safety, "safety_label"),
    })
    (output_dir / "feature_dictionary.json").write_text(json.dumps(feature_dictionary, ensure_ascii=False, indent=2), encoding="utf-8")

    summary = make_summary(recommendation, preference, safety, unified, unified_splits, split_overlap, issues)
    (output_dir / "ml_dataset_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    (output_dir / "ml_dataset_report.md").write_text(make_report(summary, input_status, feature_dictionary), encoding="utf-8")
    (output_dir / "README_outputs.md").write_text(make_outputs_readme(summary), encoding="utf-8")
    write_csv(issues.to_frame(), output_dir / "ml_dataset_issues.csv")
    validate_outputs_exist(output_dir, issues)
    summary = make_summary(recommendation, preference, safety, unified, unified_splits, split_overlap, issues)
    (output_dir / "ml_dataset_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    (output_dir / "ml_dataset_report.md").write_text(make_report(summary, input_status, feature_dictionary), encoding="utf-8")
    (output_dir / "README_outputs.md").write_text(make_outputs_readme(summary), encoding="utf-8")
    write_csv(issues.to_frame(), output_dir / "ml_dataset_issues.csv")

    print("=" * 72)
    print("AI FITNESS DATASET STAGE 6B - ML DATASET BUILDER")
    print("=" * 72)
    print(f"Input CSV dir        : {input_csv_dir}")
    print(f"AI output dir        : {ai_output_dir}")
    print(f"Output dir           : {output_dir}")
    print(f"Recommendation rows  : {len(recommendation)}")
    print(f"Preference rows      : {len(preference)}")
    print(f"Safety rows          : {len(safety)}")
    print(f"Unified rows         : {len(unified)}")
    print(f"Train rows           : {len(unified_splits['train'])}")
    print(f"Validation rows      : {len(unified_splits['validation'])}")
    print(f"Test rows            : {len(unified_splits['test'])}")
    print(f"ERROR count          : {summary['issues']['error_count']}")
    print(f"WARNING count        : {summary['issues']['warning_count']}")
    print(f"Stage 6B Status      : {summary['stage_6b_status']}")
    print(f"Ready Stage 6C       : {'YES' if summary['ready_for_stage_6c_training'] else 'NO'}")
    print("=" * 72)
    return 0 if summary["stage_6b_status"] in {"PASS", "PASS WITH NOTES"} else 1


def main(argv: list[str] | None = None) -> int:
    root = resolve_project_root()
    parser = argparse.ArgumentParser(description="Build Stage 6B ML training datasets.")
    parser.add_argument("--input-csv-dir", default=str(root / "exports" / "csv"))
    parser.add_argument("--ai-output-dir", default=str(root / "ai_outputs"))
    parser.add_argument("--output-dir", default=str(root / "ml_outputs"))
    args = parser.parse_args(argv)
    return run(Path(args.input_csv_dir), Path(args.ai_output_dir), Path(args.output_dir))


if __name__ == "__main__":
    raise SystemExit(main())
