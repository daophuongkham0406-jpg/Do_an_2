from __future__ import annotations

import json
import math
from typing import Any

import pandas as pd


def clean(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and math.isnan(value):
        return ""
    return str(value).strip()


def to_float(value: Any, default: float = 0.0) -> float:
    try:
        text = clean(value)
        return float(text) if text else default
    except Exception:
        return default


def to_int(value: Any, default: int = 0) -> int:
    try:
        text = clean(value)
        return int(float(text)) if text else default
    except Exception:
        return default


def parse_list(value: Any) -> list[str]:
    text = clean(value)
    if not text or text in {"[]", "null", "None", "nan"}:
        return []
    if text.startswith("[") and text.endswith("]"):
        try:
            parsed = json.loads(text)
            if isinstance(parsed, list):
                return [clean(item) for item in parsed if clean(item)]
        except Exception:
            pass
    for separator in (";", "|", ","):
        if separator in text:
            return [part.strip().strip("'\"") for part in text.strip("[]").split(separator) if part.strip()]
    return [text]


def list_count(value: Any) -> int:
    return len(parse_list(value))


def bmi_category(bmi: Any) -> str:
    value = to_float(bmi)
    if value <= 0:
        return "Unknown"
    if value < 18.5:
        return "Underweight"
    if value < 25:
        return "Normal"
    if value < 30:
        return "Overweight"
    return "Obese"


def index_first(df: pd.DataFrame, column: str) -> dict[str, dict[str, Any]]:
    if column not in df.columns:
        return {}
    out: dict[str, dict[str, Any]] = {}
    for row in df.to_dict(orient="records"):
        key = clean(row.get(column))
        if key and key not in out:
            out[key] = row
    return out


def index_many(df: pd.DataFrame, column: str) -> dict[str, list[dict[str, Any]]]:
    if column not in df.columns:
        return {}
    out: dict[str, list[dict[str, Any]]] = {}
    for row in df.to_dict(orient="records"):
        key = clean(row.get(column))
        if key:
            out.setdefault(key, []).append(row)
    return out


def first_match(rows: list[dict[str, Any]], column: str, value: str) -> dict[str, Any]:
    target = clean(value)
    for row in rows:
        if clean(row.get(column)) == target:
            return row
    return {}


def label_from_risk_score(risk_score: Any) -> str:
    value = to_float(risk_score)
    if value >= 0.75:
        return "Avoid"
    if value >= 0.45:
        return "Review"
    if value >= 0.20:
        return "Monitor"
    return "Safe"


def infer_exercise_difficulty(exercise: dict[str, Any]) -> str:
    level = clean(exercise.get("minimum_training_level"))
    if level:
        return level
    complexity = to_float(exercise.get("technical_complexity_score"))
    if complexity >= 4:
        return "Advanced"
    if complexity >= 3:
        return "Intermediate"
    return "Beginner"


def make_sample_id(prefix: str, number: int) -> str:
    return f"{prefix}{number:07d}"
