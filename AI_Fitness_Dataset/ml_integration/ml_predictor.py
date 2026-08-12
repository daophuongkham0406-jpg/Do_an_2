from __future__ import annotations

from typing import Any

import pandas as pd

from .model_loader import MLModelBundle


class MLPredictor:
    def __init__(self, bundle: MLModelBundle):
        self.bundle = bundle

    def predict(self, task: str, features: dict[str, Any]) -> dict[str, Any]:
        try:
            task_bundle = self.bundle.get_bundle(task)
            spec = task_bundle["feature_columns"]
            columns = spec.get("numeric_features", []) + spec.get("categorical_features", [])
            row = {column: features.get(column, 0 if column in spec.get("numeric_features", []) else "Unknown") for column in columns}
            frame = pd.DataFrame([row])
            transformed = task_bundle["preprocessor"].transform(frame)
            encoded = task_bundle["model"].predict(transformed)[0]
            prediction = str(task_bundle["label_encoder"].inverse_transform([encoded])[0])
            proba = {}
            confidence = 0.0
            proba_available = hasattr(task_bundle["model"], "predict_proba")
            if proba_available:
                values = task_bundle["model"].predict_proba(transformed)[0]
                labels = task_bundle["label_encoder"].classes_
                proba = {str(label): float(values[index]) for index, label in enumerate(labels)}
                confidence = float(max(values))
            return {
                "task": task,
                "raw_prediction": prediction,
                "confidence": round(confidence, 4),
                "prediction_proba": proba,
                "prediction_proba_available": proba_available,
                "model_type": task_bundle["model_type"],
                "status": "OK",
            }
        except Exception as exc:
            return {
                "task": task,
                "raw_prediction": "",
                "confidence": 0.0,
                "prediction_proba": {},
                "prediction_proba_available": False,
                "model_type": "",
                "status": "ERROR",
                "error": str(exc),
            }
