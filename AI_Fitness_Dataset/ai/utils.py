from __future__ import annotations

import json
import math
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import pandas as pd

try:
    from .config import CSV_DIR
except ImportError:  # pragma: no cover
    from config import CSV_DIR


def clean(v: Any) -> str:
    if v is None:
        return ""
    if isinstance(v, float) and math.isnan(v):
        return ""
    return str(v).strip()


def parse_list(value: Any) -> list[str]:
    s = clean(value)
    if not s or s in {"[]", "null", "None"}:
        return []
    if s.startswith("[") and s.endswith("]"):
        try:
            data = json.loads(s)
            if isinstance(data, list):
                return [clean(x) for x in data if clean(x)]
        except Exception:
            pass
    if ";" in s:
        return [x.strip() for x in s.split(";") if x.strip()]
    if "|" in s:
        return [x.strip() for x in s.split("|") if x.strip()]
    if "," in s:
        return [x.strip().strip("'\"") for x in s.strip("[]").split(",") if x.strip()]
    return [s]


def to_float(value: Any, default: float = 0.0) -> float:
    try:
        s = clean(value)
        return float(s) if s else default
    except Exception:
        return default


def pct(n: float, d: float) -> float:
    return 0.0 if not d else round(n / d, 4)


def load_csv_exports(csv_dir: Path = CSV_DIR) -> dict[str, pd.DataFrame]:
    files = {
        "exercises": "exercises.csv",
        "users": "users.csv",
        "workout_plans": "workout_plans.csv",
        "workout_plan_items": "workout_plan_items.csv",
        "workout_history_sessions": "workout_history_sessions.csv",
        "workout_history_items": "workout_history_items.csv",
        "workout_history_summary": "workout_history_summary.csv",
        "user_feedback": "user_feedback.csv",
    }
    return {
        name: pd.read_csv(csv_dir / file, dtype=str, keep_default_na=False, encoding="utf-8-sig")
        for name, file in files.items()
    }


def rows_for(df: pd.DataFrame, column: str, value: str) -> list[dict[str, Any]]:
    if column not in df.columns:
        return []
    return df[df[column].map(clean) == clean(value)].to_dict(orient="records")


def latest_rows(df: pd.DataFrame, column: str, value: str, n: int = 10) -> list[dict[str, Any]]:
    rows = rows_for(df, column, value)
    return rows[-n:]


def majority(counter: Counter, default: str = "Unknown") -> str:
    return counter.most_common(1)[0][0] if counter else default

