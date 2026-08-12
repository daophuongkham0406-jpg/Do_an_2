from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import joblib
import pandas as pd

if __package__ is None or __package__ == "":
    sys.path.append(str(Path(__file__).resolve().parents[1]))
    from ml.model_schema import TASKS, project_root
    from ml.safety_override import apply_safety_override
else:
    from .model_schema import TASKS, project_root
    from .safety_override import apply_safety_override


def load_payload(path: Path, task: str) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, list):
        for item in data:
            if item.get("task") == task:
                return item.get("input_features", item)
        return data[0].get("input_features", data[0])
    if "input_features" in data:
        return data["input_features"]
    return data


def predict(task: str, input_features: dict[str, Any], model_dir: Path) -> dict[str, Any]:
    spec = TASKS[task]
    model = joblib.load(model_dir / spec["model_file"])
    preprocessor = joblib.load(model_dir / spec["preprocessor_file"])
    encoder = joblib.load(model_dir / spec["label_encoder_file"])
    feature_columns = json.loads((model_dir / "feature_columns.json").read_text(encoding="utf-8"))[task]
    columns = feature_columns["numeric_features"] + feature_columns["categorical_features"]
    row = {column: input_features.get(column, "") for column in columns}
    x = pd.DataFrame([row])
    x_t = preprocessor.transform(x)
    pred = encoder.inverse_transform(model.predict(x_t))[0]
    proba = {}
    if hasattr(model, "predict_proba"):
        values = model.predict_proba(x_t)[0]
        proba = {label: float(values[idx]) for idx, label in enumerate(encoder.classes_)}
    final = pred
    explanation = f"{task} model predicted {pred}."
    if task == "recommendation":
        override = apply_safety_override(
            str(pred),
            str(input_features.get("safety_status", "Safe")),
            float(input_features.get("risk_score", 0) or 0),
        )
        final = override["final_action"]
        explanation += f" Safety override applied: {override['was_overridden']}."
    return {
        "task": task,
        "input_features": input_features,
        "raw_prediction": str(pred),
        "prediction_proba": proba,
        "final_prediction_after_safety_override": str(final),
        "explanation": explanation,
    }


def main(argv: list[str] | None = None) -> int:
    root = project_root()
    parser = argparse.ArgumentParser(description="Run Stage 6C model prediction.")
    parser.add_argument("--task", choices=list(TASKS), required=True)
    parser.add_argument("--input-json", required=True)
    parser.add_argument("--model-dir", default=str(root / "models"))
    args = parser.parse_args(argv)
    result = predict(args.task, load_payload(Path(args.input_json), args.task), Path(args.model_dir))
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
