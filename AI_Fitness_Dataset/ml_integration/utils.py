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
    if not text or text in {"[]", "None", "null", "nan"}:
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


def bmi_category(value: Any) -> str:
    bmi = to_float(value)
    if bmi <= 0:
        return "Unknown"
    if bmi < 18.5:
        return "Underweight"
    if bmi < 25:
        return "Normal"
    if bmi < 30:
        return "Overweight"
    return "Obese"


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


def issue(issue_id: int, severity: str, component: str, user_id: str, exercise_id: str, message: str, suggested_fix: str) -> dict[str, Any]:
    return {
        "issue_id": f"INTISSUE{issue_id:06d}",
        "severity": severity,
        "component": component,
        "user_id": user_id,
        "exercise_id": exercise_id,
        "message": message,
        "suggested_fix": suggested_fix,
    }
