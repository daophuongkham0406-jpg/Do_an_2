from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
from sklearn.metrics import (
    accuracy_score,
    balanced_accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
)

from .safety_override import apply_safety_override, is_unsafe_action


def classification_metrics(y_true: list[str], y_pred: list[str], labels: list[str]) -> dict[str, Any]:
    return {
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "balanced_accuracy": float(balanced_accuracy_score(y_true, y_pred)),
        "macro_f1": float(f1_score(y_true, y_pred, average="macro", zero_division=0)),
        "weighted_f1": float(f1_score(y_true, y_pred, average="weighted", zero_division=0)),
        "classification_report": classification_report(y_true, y_pred, labels=labels, output_dict=True, zero_division=0),
        "confusion_matrix": confusion_matrix(y_true, y_pred, labels=labels).tolist(),
        "labels": labels,
    }


def recommendation_safety_metrics(frame: pd.DataFrame, predictions: list[str]) -> dict[str, Any]:
    before = 0
    after = 0
    overrides = 0
    rows = []
    for idx, pred in enumerate(predictions):
        row = frame.iloc[idx]
        safety_status = str(row.get("safety_status", "Safe")).strip()
        risk_score = float(pd.to_numeric(pd.Series([row.get("risk_score", 0)]), errors="coerce").fillna(0).iloc[0])
        unsafe_before = is_unsafe_action(pred, safety_status, risk_score)
        if unsafe_before:
            before += 1
        overridden = apply_safety_override(pred, safety_status, risk_score)
        if overridden["was_overridden"]:
            overrides += 1
        unsafe_after = is_unsafe_action(overridden["final_action"], safety_status, risk_score)
        if unsafe_after:
            after += 1
        if unsafe_before or unsafe_after or overridden["was_overridden"]:
            rows.append({
                "sample_id": row.get("sample_id", ""),
                "predicted_action": pred,
                "safety_status": safety_status,
                "risk_score": risk_score,
                "unsafe_before_override": unsafe_before,
                "unsafe_after_override": unsafe_after,
                **overridden,
            })
    return {
        "unsafe_prediction_count_before_override": before,
        "unsafe_prediction_count_after_override": after,
        "safety_override_count": overrides,
        "unsafe_rows": rows,
    }


def preference_extra_metrics(report: dict[str, Any]) -> dict[str, float]:
    return {
        "dislike_recall": float(report.get("Dislike", {}).get("recall", 0.0)),
        "like_precision": float(report.get("Like", {}).get("precision", 0.0)),
    }


def safety_extra_metrics(report: dict[str, Any]) -> dict[str, float]:
    recalls = [float(report.get(label, {}).get("recall", 0.0)) for label in ("Monitor", "Review", "Avoid") if label in report]
    return {
        "monitor_review_avoid_recall": float(sum(recalls) / len(recalls)) if recalls else 0.0,
        "monitor_recall": float(report.get("Monitor", {}).get("recall", 0.0)),
        "review_recall": float(report.get("Review", {}).get("recall", 0.0)),
        "avoid_recall": float(report.get("Avoid", {}).get("recall", 0.0)),
    }


def feature_importance(model: Any, feature_names: list[str], top_n: int = 30) -> dict[str, Any]:
    values = None
    if hasattr(model, "feature_importances_"):
        values = np.asarray(model.feature_importances_)
    elif hasattr(model, "coef_"):
        values = np.mean(np.abs(np.asarray(model.coef_)), axis=0)
    if values is None or len(values) != len(feature_names):
        return {"feature_importance_available": False, "top_features": []}
    order = np.argsort(values)[::-1][:top_n]
    return {
        "feature_importance_available": True,
        "top_features": [
            {"feature": feature_names[i], "importance": float(values[i])}
            for i in order
        ],
    }
