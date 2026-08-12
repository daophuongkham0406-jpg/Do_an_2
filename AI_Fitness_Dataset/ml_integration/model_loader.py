from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import joblib

from .schema import MODEL_FILES, TASKS


class MLModelBundle:
    def __init__(self, model_dir: str | Path = "models"):
        self.model_dir = Path(model_dir)
        self.bundles: dict[str, dict[str, Any]] = {}
        self.feature_columns: dict[str, Any] = {}
        self.errors: list[str] = []

    def load_all(self) -> None:
        self.errors = []
        feature_path = self.model_dir / "feature_columns.json"
        if not feature_path.exists():
            self.errors.append(f"Missing feature_columns.json in {self.model_dir}")
        else:
            self.feature_columns = json.loads(feature_path.read_text(encoding="utf-8"))
        for task in TASKS:
            spec = MODEL_FILES[task]
            try:
                self.bundles[task] = {
                    "model": joblib.load(self.model_dir / spec["model"]),
                    "preprocessor": joblib.load(self.model_dir / spec["preprocessor"]),
                    "label_encoder": joblib.load(self.model_dir / spec["label_encoder"]),
                    "feature_columns": self.feature_columns.get(task, {}),
                    "model_type": "",
                }
                self.bundles[task]["model_type"] = type(self.bundles[task]["model"]).__name__
            except Exception as exc:
                self.errors.append(f"{task} load failed: {exc}")

    def validate(self) -> dict[str, Any]:
        tasks_ok = {}
        for task in TASKS:
            bundle = self.bundles.get(task, {})
            tasks_ok[task] = all(key in bundle for key in ["model", "preprocessor", "label_encoder", "feature_columns"])
        return {
            "model_load_success": all(tasks_ok.values()) and not self.errors,
            "tasks": tasks_ok,
            "errors": self.errors,
        }

    def get_bundle(self, task: str) -> dict[str, Any]:
        if task not in TASKS:
            raise ValueError(f"Unknown ML task: {task}")
        if task not in self.bundles:
            raise RuntimeError(f"Model bundle for {task} is not loaded")
        return self.bundles[task]
