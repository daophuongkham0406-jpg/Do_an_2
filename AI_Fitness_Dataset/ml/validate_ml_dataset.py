from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any

import pandas as pd

from .feature_engineering import clean
from .ml_schema import (
    CORE_OUTPUT_FILES,
    VALID_EXERCISE_PREFERENCES,
    VALID_RECOMMENDED_ACTIONS,
    VALID_SAFETY_LABELS,
)


LABEL_SPECS = {
    "recommendation": ("recommended_action", VALID_RECOMMENDED_ACTIONS, True),
    "preference": ("exercise_preference", VALID_EXERCISE_PREFERENCES, True),
    "safety": ("safety_label", VALID_SAFETY_LABELS, True),
}


class IssueLog:
    def __init__(self) -> None:
        self.rows: list[dict[str, Any]] = []

    def add(self, severity: str, dataset: str, column: str, row_id: str, message: str, suggested_fix: str) -> None:
        self.rows.append({
            "issue_id": f"MLISSUE{len(self.rows) + 1:06d}",
            "severity": severity,
            "dataset": dataset,
            "column": column,
            "row_id": row_id,
            "message": message,
            "suggested_fix": suggested_fix,
        })

    def to_frame(self) -> pd.DataFrame:
        columns = ["issue_id", "severity", "dataset", "column", "row_id", "message", "suggested_fix"]
        return pd.DataFrame(self.rows, columns=columns)

    def counts(self) -> dict[str, int]:
        counter = Counter(row["severity"] for row in self.rows)
        return {
            "error_count": counter.get("ERROR", 0),
            "warning_count": counter.get("WARNING", 0),
            "info_count": counter.get("INFO", 0),
        }


def validate_input_files(csv_dir: Path, ai_output_dir: Path, csv_files: dict[str, str], ai_files: dict[str, str], issues: IssueLog) -> None:
    for name, filename in csv_files.items():
        path = csv_dir / filename
        if not path.exists():
            issues.add("ERROR", "input", filename, "", f"Missing CSV input {filename}", "Regenerate Stage 4 CSV exports.")
    for name, filename in ai_files.items():
        path = ai_output_dir / filename
        if not path.exists():
            issues.add("ERROR", "input", filename, "", f"Missing AI output {filename}", "Run Stage 6A Revised pipeline.")


def validate_loaded_inputs(data: dict[str, pd.DataFrame], issues: IssueLog) -> None:
    required_keys = {
        "users": "user_id",
        "exercises": "exercise_id",
        "workout_plans": "plan_id",
        "workout_plan_items": "plan_item_id",
        "workout_history_sessions": "history_session_id",
        "workout_history_items": "history_item_id",
        "workout_history_summary": "summary_id",
        "user_feedback": "feedback_id",
    }
    for name, key_column in required_keys.items():
        frame = data.get(name)
        if frame is None or frame.empty:
            issues.add("ERROR", name, "", "", f"{name} is empty or unreadable.", "Check Stage 4 export.")
            continue
        if key_column not in frame.columns:
            issues.add("ERROR", name, key_column, "", f"Missing primary key column {key_column}.", "Fix export schema.")


def validate_dataset(name: str, frame: pd.DataFrame, label_column: str, valid_labels: set[str], issues: IssueLog) -> None:
    if frame.empty:
        issues.add("ERROR", name, "", "", f"{name} dataset is empty.", "Rebuild dataset from valid inputs.")
        return
    if "sample_id" not in frame.columns:
        issues.add("ERROR", name, "sample_id", "", "Missing sample_id column.", "Add deterministic sample_id.")
    else:
        duplicate_count = int(frame["sample_id"].duplicated().sum())
        if duplicate_count:
            issues.add("ERROR", name, "sample_id", "", f"Duplicate sample_id count: {duplicate_count}.", "Make sample_id unique.")
    if "user_id" not in frame.columns or frame["user_id"].map(clean).eq("").any():
        issues.add("ERROR", name, "user_id", "", "Missing user_id values.", "Join user_id from source rows.")
    if name in {"preference", "safety", "recommendation"} and ("exercise_id" not in frame.columns or frame["exercise_id"].map(clean).eq("").any()):
        issues.add("ERROR", name, "exercise_id", "", "Missing exercise_id values.", "Join exercise context.")
    if label_column not in frame.columns:
        issues.add("ERROR", name, label_column, "", f"Missing label column {label_column}.", "Create label column.")
        return
    missing_label = int(frame[label_column].map(clean).eq("").sum())
    if missing_label:
        issues.add("ERROR", name, label_column, "", f"Missing label count: {missing_label}.", "Fill or remove missing labels.")
    invalid = sorted(set(frame[label_column].map(clean)) - valid_labels - {""})
    if invalid:
        issues.add("ERROR", name, label_column, "", f"Invalid labels: {invalid}.", "Map labels to allowed enum.")
    distribution = frame[label_column].map(clean).value_counts().to_dict()
    for label, count in distribution.items():
        if count < 10:
            issues.add("WARNING", name, label_column, label, f"Low sample count for label {label}: {count}.", "Review class balance before Stage 6C training.")


def validate_splits(split_frames: dict[str, pd.DataFrame], issues: IssueLog) -> int:
    user_sets = {}
    for name, frame in split_frames.items():
        if frame.empty:
            issues.add("WARNING", "split", name, "", f"{name} split is empty.", "Check user split ratios and row counts.")
        user_sets[name] = set(frame["user_id"].map(clean)) if "user_id" in frame.columns else set()
    overlap = len(user_sets.get("train", set()) & user_sets.get("validation", set()))
    overlap += len(user_sets.get("train", set()) & user_sets.get("test", set()))
    overlap += len(user_sets.get("validation", set()) & user_sets.get("test", set()))
    if overlap:
        issues.add("ERROR", "split", "user_id", "", f"User overlap between splits: {overlap}.", "Split by user_id only.")
    return overlap


def validate_outputs_exist(output_dir: Path, issues: IssueLog) -> None:
    for filename in CORE_OUTPUT_FILES:
        if not (output_dir / filename).exists():
            issues.add("ERROR", "output", filename, "", f"Missing output file {filename}.", "Rerun Stage 6B builder.")


def dataset_summary(frame: pd.DataFrame, label_column: str | None = None) -> dict[str, Any]:
    summary = {
        "row_count": int(len(frame)),
        "column_count": int(len(frame.columns)),
    }
    if label_column:
        summary.update({
            "label_column": label_column,
            "label_distribution": frame[label_column].map(clean).value_counts().to_dict() if label_column in frame.columns else {},
            "missing_label_count": int(frame[label_column].map(clean).eq("").sum()) if label_column in frame.columns else len(frame),
            "duplicate_sample_id_count": int(frame["sample_id"].duplicated().sum()) if "sample_id" in frame.columns else len(frame),
        })
    return summary
