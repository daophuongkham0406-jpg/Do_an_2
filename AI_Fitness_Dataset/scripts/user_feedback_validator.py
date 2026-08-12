#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
user_feedback_validator.py

Validator cho user_feedback_master.xlsx.

Mục tiêu:
- Kiểm tra schema của sheet User_Feedback.
- Kiểm tra ID format, enum, range, JSON array, timestamp.
- Kiểm tra logic feedback: scope, sentiment, pain, requested_action.
- Kiểm tra liên kết với user_master, workout_plan_master, workout_history_master, exercise_master nếu được truyền vào.
- Xuất report .txt, .json, .csv.

Cách chạy cơ bản:
    python user_feedback_validator.py user_feedback_master.xlsx

Cách chạy đầy đủ:
    python user_feedback_validator.py user_feedback_master.xlsx ^
        --user-master user_master.xlsx ^
        --plan-master workout_plan_master.xlsx ^
        --history-master workout_history_master.xlsx ^
        --exercise-master exercise_master.xlsx ^
        --report-dir reports/user_feedback

Exit code:
    0 nếu không có ERROR
    1 nếu có ERROR
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import re
import sys
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import pandas as pd


# ============================================================
# CONFIG
# ============================================================

USER_FEEDBACK_SHEET = "User_Feedback"

REQUIRED_COLUMNS = [
    "feedback_id",
    "user_id",
    "plan_id",
    "history_session_id",
    "history_item_id",
    "plan_item_id",
    "exercise_id",
    "feedback_scope",
    "feedback_type",
    "rating",
    "sentiment",
    "difficulty_feedback",
    "enjoyment_rating",
    "fatigue_feedback",
    "pain_feedback",
    "pain_areas",
    "duration_feedback",
    "exercise_preference",
    "progression_preference",
    "requested_action",
    "feedback_text",
    "feedback_reason_tags",
    "source_context",
    "feedback_status",
    "record_source",
    "is_synthetic",
    "created_at",
    "updated_at",
]

# Optional metadata sheets. Không bắt buộc để không làm kẹt pipeline,
# nhưng nếu có thì validator sẽ khuyến nghị cập nhật.
OPTIONAL_SHEETS = [
    "Reference_Lists",
    "Data_Dictionary",
    "Validation_Rules",
    "Schema_Info",
    "Quality_Summary",
    "Alignment_Notes",
]

ENUMS = {
    "feedback_scope": {"Exercise", "Session", "Plan", "General"},
    "feedback_type": {
        "Rating",
        "Preference",
        "Safety",
        "Difficulty",
        "Duration",
        "Progression",
        "Free Text",
    },
    "sentiment": {"Positive", "Neutral", "Negative"},
    "difficulty_feedback": {"Too Easy", "Appropriate", "Too Hard", "Not Applicable"},
    "fatigue_feedback": {"Low", "Moderate", "High", "Excessive", "Not Applicable"},
    "pain_feedback": {"No Pain", "Mild Discomfort", "Pain", "Severe Pain", "Not Applicable"},
    "duration_feedback": {"Too Short", "Appropriate", "Too Long", "Not Applicable"},
    "exercise_preference": {"Like", "Neutral", "Dislike", "Not Applicable"},
    "progression_preference": {
        "Increase Difficulty",
        "Maintain",
        "Reduce Difficulty",
        "Not Applicable",
    },
    "requested_action": {
        "Keep",
        "Increase Difficulty",
        "Reduce Difficulty",
        "Increase Volume",
        "Reduce Volume",
        "Replace Exercise",
        "Change Split",
        "Reduce Session Duration",
        "Increase Session Duration",
        "Review Safety",
        "No Preference",
    },
    "feedback_status": {"Active", "Resolved", "Ignored", "Archived"},
    "record_source": {"Synthetic", "App", "Coach", "Import"},
    "source_context": {
        "after_exercise",
        "after_session",
        "after_plan",
        "weekly_checkin",
        "manual_review",
        "in_app_prompt",
        "unknown",
    },
}

ID_PATTERNS = {
    "feedback_id": re.compile(r"^FB\d{8}$"),
    "user_id": re.compile(r"^U\d{6}$"),
    "plan_id": re.compile(r"^PLAN\d{6}$"),
    "history_session_id": re.compile(r"^WHS\d{8}$"),
    "history_item_id": re.compile(r"^WHI\d{9}$"),
    "plan_item_id": re.compile(r"^WPI\d{8}$"),
    "exercise_id": re.compile(r"^EX\d{4}$"),
}

# Recommended distribution. WARNING only, not ERROR.
SCOPE_TARGETS = {
    "Exercise": (0.55, 0.65),
    "Session": (0.25, 0.35),
    "Plan": (0.05, 0.10),
    "General": (0.01, 0.03),
}

SENTIMENT_TARGETS = {
    "Positive": (0.55, 0.65),
    "Neutral": (0.20, 0.30),
    "Negative": (0.10, 0.18),
}

PAIN_RATE_TARGET = (0.01, 0.04)

BOOLEAN_TRUE = {"true", "yes", "1", "y", "t", "đúng"}
BOOLEAN_FALSE = {"false", "no", "0", "n", "f", "sai"}


# ============================================================
# ISSUE MODEL
# ============================================================

@dataclass
class Issue:
    severity: str
    code: str
    table: str
    excel_row: int | None
    feedback_id: str | None
    user_id: str | None
    plan_id: str | None
    column: str | None
    message: str
    value: Any = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# ============================================================
# HELPERS
# ============================================================

def is_missing(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, float) and math.isnan(value):
        return True
    if isinstance(value, str) and value.strip() == "":
        return True
    return False


def normalize_str(value: Any) -> str:
    if is_missing(value):
        return ""
    return str(value).strip()


def bool_value(value: Any) -> bool | None:
    if is_missing(value):
        return None
    if isinstance(value, bool):
        return value
    text = str(value).strip().lower()
    if text in BOOLEAN_TRUE:
        return True
    if text in BOOLEAN_FALSE:
        return False
    return None


def parse_json_array(value: Any) -> tuple[bool, list[Any]]:
    if is_missing(value):
        return True, []
    if isinstance(value, list):
        return True, value
    text = str(value).strip()
    if text == "":
        return True, []
    try:
        parsed = json.loads(text)
        if isinstance(parsed, list):
            return True, parsed
        return False, []
    except Exception:
        return False, []


def numeric_int(value: Any) -> int | None:
    if is_missing(value):
        return None
    try:
        number = float(value)
        if number.is_integer():
            return int(number)
        return None
    except Exception:
        return None


def add_issue(
    issues: list[Issue],
    severity: str,
    code: str,
    table: str,
    excel_row: int | None,
    row: pd.Series | None,
    column: str | None,
    message: str,
    value: Any = None,
) -> None:
    issues.append(
        Issue(
            severity=severity,
            code=code,
            table=table,
            excel_row=excel_row,
            feedback_id=normalize_str(row.get("feedback_id")) if row is not None else None,
            user_id=normalize_str(row.get("user_id")) if row is not None else None,
            plan_id=normalize_str(row.get("plan_id")) if row is not None else None,
            column=column,
            message=message,
            value=value,
        )
    )


def read_excel_sheets(path: Path) -> dict[str, pd.DataFrame]:
    try:
        return pd.read_excel(path, sheet_name=None, dtype=object, engine="openpyxl")
    except Exception as exc:
        raise RuntimeError(f"Không đọc được Excel file: {path}. Lỗi: {exc}") from exc


def clean_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [str(c).strip() for c in df.columns]
    return df


def find_sheet_with_column(sheets: dict[str, pd.DataFrame], column: str) -> pd.DataFrame | None:
    for _, df in sheets.items():
        df = clean_columns(df)
        if column in df.columns:
            return df
    return None


def make_lookup(df: pd.DataFrame | None, key: str) -> set[str]:
    if df is None or key not in df.columns:
        return set()
    return {normalize_str(v) for v in df[key].tolist() if not is_missing(v)}


def make_map(df: pd.DataFrame | None, key: str, cols: list[str]) -> dict[str, dict[str, str]]:
    if df is None or key not in df.columns:
        return {}
    result: dict[str, dict[str, str]] = {}
    for _, row in df.iterrows():
        k = normalize_str(row.get(key))
        if not k:
            continue
        result[k] = {c: normalize_str(row.get(c)) for c in cols if c in df.columns}
    return result


# ============================================================
# VALIDATION
# ============================================================

def validate_schema(sheets: dict[str, pd.DataFrame], issues: list[Issue]) -> pd.DataFrame | None:
    if USER_FEEDBACK_SHEET not in sheets:
        add_issue(
            issues,
            "ERROR",
            "MISSING_SHEET",
            USER_FEEDBACK_SHEET,
            None,
            None,
            None,
            f"Thiếu sheet bắt buộc: {USER_FEEDBACK_SHEET}",
        )
        return None

    df = clean_columns(sheets[USER_FEEDBACK_SHEET])

    missing_cols = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    extra_cols = [c for c in df.columns if c not in REQUIRED_COLUMNS]

    if missing_cols:
        add_issue(
            issues,
            "ERROR",
            "MISSING_REQUIRED_COLUMNS",
            USER_FEEDBACK_SHEET,
            None,
            None,
            None,
            "Thiếu cột bắt buộc trong User_Feedback",
            missing_cols,
        )

    if extra_cols:
        add_issue(
            issues,
            "WARNING",
            "EXTRA_COLUMNS",
            USER_FEEDBACK_SHEET,
            None,
            None,
            None,
            "Có cột ngoài schema chuẩn. Không nhất thiết sai, nhưng cần kiểm tra.",
            extra_cols,
        )

    for sheet in OPTIONAL_SHEETS:
        if sheet not in sheets:
            add_issue(
                issues,
                "WARNING",
                "MISSING_OPTIONAL_METADATA_SHEET",
                sheet,
                None,
                None,
                None,
                f"Thiếu sheet metadata khuyến nghị: {sheet}",
            )

    return df


def validate_rows(
    df: pd.DataFrame,
    issues: list[Issue],
    *,
    user_ids: set[str],
    plan_ids: set[str],
    session_map: dict[str, dict[str, str]],
    item_map: dict[str, dict[str, str]],
    plan_item_map: dict[str, dict[str, str]],
    exercise_ids: set[str],
) -> None:
    # Duplicate feedback IDs
    if "feedback_id" in df.columns:
        counts = Counter(normalize_str(v) for v in df["feedback_id"].tolist() if not is_missing(v))
        for feedback_id, count in counts.items():
            if count > 1:
                # Mark the first visible duplicated ID as a dataset-level issue.
                add_issue(
                    issues,
                    "ERROR",
                    "DUPLICATE_FEEDBACK_ID",
                    USER_FEEDBACK_SHEET,
                    None,
                    None,
                    "feedback_id",
                    "feedback_id bị trùng",
                    {"feedback_id": feedback_id, "count": count},
                )

    # Duplicate exact link/type/scope feedback. WARNING only.
    duplicate_keys = Counter()
    for _, row in df.iterrows():
        key = (
            normalize_str(row.get("user_id")),
            normalize_str(row.get("plan_id")),
            normalize_str(row.get("history_session_id")),
            normalize_str(row.get("history_item_id")),
            normalize_str(row.get("feedback_scope")),
            normalize_str(row.get("feedback_type")),
        )
        if any(key):
            duplicate_keys[key] += 1

    for key, count in duplicate_keys.items():
        if count > 1 and key[0]:
            add_issue(
                issues,
                "WARNING",
                "POSSIBLE_DUPLICATE_FEEDBACK_CONTEXT",
                USER_FEEDBACK_SHEET,
                None,
                None,
                None,
                "Nhiều feedback có cùng user/plan/session/item/scope/type. Có thể hợp lệ nếu user phản hồi nhiều lần, nhưng cần kiểm tra.",
                {"key": key, "count": count},
            )

    for idx, row in df.iterrows():
        excel_row = idx + 2  # header is row 1

        # Required values
        always_required = [
            "feedback_id",
            "user_id",
            "feedback_scope",
            "feedback_type",
            "rating",
            "sentiment",
            "requested_action",
            "feedback_status",
            "record_source",
            "is_synthetic",
            "created_at",
        ]
        for col in always_required:
            if col in df.columns and is_missing(row.get(col)):
                add_issue(
                    issues,
                    "ERROR",
                    "REQUIRED_VALUE_EMPTY",
                    USER_FEEDBACK_SHEET,
                    excel_row,
                    row,
                    col,
                    f"Cột bắt buộc bị trống: {col}",
                )

        # ID patterns
        for col, pattern in ID_PATTERNS.items():
            if col not in df.columns:
                continue
            value = normalize_str(row.get(col))
            if value and not pattern.match(value):
                add_issue(
                    issues,
                    "ERROR",
                    "INVALID_ID_FORMAT",
                    USER_FEEDBACK_SHEET,
                    excel_row,
                    row,
                    col,
                    f"ID không đúng định dạng cho {col}",
                    value,
                )

        # Enums
        for col, allowed in ENUMS.items():
            if col not in df.columns:
                continue
            value = normalize_str(row.get(col))
            if value and value not in allowed:
                add_issue(
                    issues,
                    "ERROR",
                    "INVALID_ENUM_VALUE",
                    USER_FEEDBACK_SHEET,
                    excel_row,
                    row,
                    col,
                    f"Giá trị enum không hợp lệ cho {col}",
                    {"value": value, "allowed": sorted(allowed)},
                )

        # Ratings
        for col in ["rating", "enjoyment_rating"]:
            if col not in df.columns:
                continue
            value = row.get(col)
            if is_missing(value):
                continue
            n = numeric_int(value)
            if n is None or not (1 <= n <= 5):
                add_issue(
                    issues,
                    "ERROR",
                    "RATING_OUT_OF_RANGE",
                    USER_FEEDBACK_SHEET,
                    excel_row,
                    row,
                    col,
                    f"{col} phải là số nguyên từ 1 đến 5",
                    value,
                )

        # JSON array fields
        for col in ["pain_areas", "feedback_reason_tags"]:
            if col not in df.columns:
                continue
            ok, arr = parse_json_array(row.get(col))
            if not ok:
                add_issue(
                    issues,
                    "ERROR",
                    "INVALID_JSON_ARRAY",
                    USER_FEEDBACK_SHEET,
                    excel_row,
                    row,
                    col,
                    f"{col} phải là JSON array, ví dụ [] hoặc [\"Shoulder\"]",
                    row.get(col),
                )
            elif any(is_missing(x) for x in arr):
                add_issue(
                    issues,
                    "WARNING",
                    "JSON_ARRAY_HAS_EMPTY_VALUE",
                    USER_FEEDBACK_SHEET,
                    excel_row,
                    row,
                    col,
                    f"{col} có phần tử rỗng",
                    arr,
                )

        # Boolean
        b = bool_value(row.get("is_synthetic"))
        if b is None:
            add_issue(
                issues,
                "ERROR",
                "INVALID_BOOLEAN",
                USER_FEEDBACK_SHEET,
                excel_row,
                row,
                "is_synthetic",
                "is_synthetic phải là True/False",
                row.get("is_synthetic"),
            )

        record_source = normalize_str(row.get("record_source"))
        if record_source == "Synthetic" and b is not True:
            add_issue(
                issues,
                "ERROR",
                "SYNTHETIC_SOURCE_FLAG_MISMATCH",
                USER_FEEDBACK_SHEET,
                excel_row,
                row,
                "is_synthetic",
                "record_source = Synthetic thì is_synthetic phải là True",
                row.get("is_synthetic"),
            )

        if record_source in {"App", "Coach", "Import"} and b is True:
            add_issue(
                issues,
                "WARNING",
                "REAL_SOURCE_MARKED_SYNTHETIC",
                USER_FEEDBACK_SHEET,
                excel_row,
                row,
                "is_synthetic",
                "record_source không phải Synthetic nhưng is_synthetic = True",
                {"record_source": record_source, "is_synthetic": row.get("is_synthetic")},
            )

        # Timestamp
        created = pd.to_datetime(row.get("created_at"), errors="coerce")
        updated = pd.to_datetime(row.get("updated_at"), errors="coerce") if "updated_at" in df.columns else pd.NaT

        if pd.isna(created):
            add_issue(
                issues,
                "ERROR",
                "INVALID_TIMESTAMP",
                USER_FEEDBACK_SHEET,
                excel_row,
                row,
                "created_at",
                "created_at không parse được thành datetime",
                row.get("created_at"),
            )

        if not is_missing(row.get("updated_at")) and pd.isna(updated):
            add_issue(
                issues,
                "ERROR",
                "INVALID_TIMESTAMP",
                USER_FEEDBACK_SHEET,
                excel_row,
                row,
                "updated_at",
                "updated_at không parse được thành datetime",
                row.get("updated_at"),
            )

        if not pd.isna(created) and not pd.isna(updated) and updated < created:
            add_issue(
                issues,
                "ERROR",
                "UPDATED_BEFORE_CREATED",
                USER_FEEDBACK_SHEET,
                excel_row,
                row,
                "updated_at",
                "updated_at không được trước created_at",
                {"created_at": str(created), "updated_at": str(updated)},
            )

        # Scope logic
        scope = normalize_str(row.get("feedback_scope"))
        history_session_id = normalize_str(row.get("history_session_id"))
        history_item_id = normalize_str(row.get("history_item_id"))
        plan_item_id = normalize_str(row.get("plan_item_id"))
        exercise_id = normalize_str(row.get("exercise_id"))
        plan_id = normalize_str(row.get("plan_id"))
        user_id = normalize_str(row.get("user_id"))

        if scope == "Exercise":
            for col in ["history_session_id", "history_item_id", "plan_item_id", "exercise_id", "plan_id"]:
                if is_missing(row.get(col)):
                    add_issue(
                        issues,
                        "ERROR",
                        "SCOPE_REQUIRED_LINK_MISSING",
                        USER_FEEDBACK_SHEET,
                        excel_row,
                        row,
                        col,
                        "Exercise feedback phải gắn với session, item, plan_item và exercise",
                    )

        elif scope == "Session":
            if not history_session_id:
                add_issue(
                    issues,
                    "ERROR",
                    "SCOPE_REQUIRED_LINK_MISSING",
                    USER_FEEDBACK_SHEET,
                    excel_row,
                    row,
                    "history_session_id",
                    "Session feedback phải có history_session_id",
                )
            if history_item_id or exercise_id:
                add_issue(
                    issues,
                    "WARNING",
                    "SESSION_SCOPE_HAS_ITEM_FIELDS",
                    USER_FEEDBACK_SHEET,
                    excel_row,
                    row,
                    None,
                    "Session feedback thường không nên có history_item_id/exercise_id",
                    {"history_item_id": history_item_id, "exercise_id": exercise_id},
                )

        elif scope == "Plan":
            if not plan_id:
                add_issue(
                    issues,
                    "ERROR",
                    "SCOPE_REQUIRED_LINK_MISSING",
                    USER_FEEDBACK_SHEET,
                    excel_row,
                    row,
                    "plan_id",
                    "Plan feedback phải có plan_id",
                )
            if history_item_id or exercise_id:
                add_issue(
                    issues,
                    "WARNING",
                    "PLAN_SCOPE_HAS_ITEM_FIELDS",
                    USER_FEEDBACK_SHEET,
                    excel_row,
                    row,
                    None,
                    "Plan feedback thường không nên có history_item_id/exercise_id",
                    {"history_item_id": history_item_id, "exercise_id": exercise_id},
                )

        elif scope == "General":
            # General vẫn cần user_id, các link khác có thể blank.
            if plan_id or history_session_id or history_item_id or exercise_id:
                add_issue(
                    issues,
                    "WARNING",
                    "GENERAL_SCOPE_HAS_SPECIFIC_LINKS",
                    USER_FEEDBACK_SHEET,
                    excel_row,
                    row,
                    None,
                    "General feedback thường không cần gắn với plan/session/item cụ thể",
                    {
                        "plan_id": plan_id,
                        "history_session_id": history_session_id,
                        "history_item_id": history_item_id,
                        "exercise_id": exercise_id,
                    },
                )

        # Foreign keys
        if user_ids and user_id and user_id not in user_ids:
            add_issue(
                issues,
                "ERROR",
                "UNKNOWN_USER_ID",
                USER_FEEDBACK_SHEET,
                excel_row,
                row,
                "user_id",
                "user_id không tồn tại trong user_master",
                user_id,
            )

        if plan_ids and plan_id and plan_id not in plan_ids:
            add_issue(
                issues,
                "ERROR",
                "UNKNOWN_PLAN_ID",
                USER_FEEDBACK_SHEET,
                excel_row,
                row,
                "plan_id",
                "plan_id không tồn tại trong workout_plan_master",
                plan_id,
            )

        if session_map and history_session_id and history_session_id not in session_map:
            add_issue(
                issues,
                "ERROR",
                "UNKNOWN_HISTORY_SESSION_ID",
                USER_FEEDBACK_SHEET,
                excel_row,
                row,
                "history_session_id",
                "history_session_id không tồn tại trong workout_history_master",
                history_session_id,
            )

        if item_map and history_item_id and history_item_id not in item_map:
            add_issue(
                issues,
                "ERROR",
                "UNKNOWN_HISTORY_ITEM_ID",
                USER_FEEDBACK_SHEET,
                excel_row,
                row,
                "history_item_id",
                "history_item_id không tồn tại trong workout_history_master",
                history_item_id,
            )

        if plan_item_map and plan_item_id and plan_item_id not in plan_item_map:
            add_issue(
                issues,
                "ERROR",
                "UNKNOWN_PLAN_ITEM_ID",
                USER_FEEDBACK_SHEET,
                excel_row,
                row,
                "plan_item_id",
                "plan_item_id không tồn tại trong workout_plan_master",
                plan_item_id,
            )

        if exercise_ids and exercise_id and exercise_id not in exercise_ids:
            add_issue(
                issues,
                "ERROR",
                "UNKNOWN_EXERCISE_ID",
                USER_FEEDBACK_SHEET,
                excel_row,
                row,
                "exercise_id",
                "exercise_id không tồn tại trong exercise_master",
                exercise_id,
            )

        # Cross consistency from history item
        if item_map and history_item_id and history_item_id in item_map:
            item = item_map[history_item_id]
            for col, expected in [
                ("history_session_id", item.get("history_session_id")),
                ("user_id", item.get("user_id")),
                ("plan_id", item.get("plan_id")),
                ("plan_item_id", item.get("plan_item_id")),
                ("exercise_id", item.get("exercise_id")),
            ]:
                actual = normalize_str(row.get(col))
                if expected and actual and actual != expected:
                    add_issue(
                        issues,
                        "ERROR",
                        "HISTORY_ITEM_LINK_MISMATCH",
                        USER_FEEDBACK_SHEET,
                        excel_row,
                        row,
                        col,
                        f"{col} không khớp với dòng Workout_History_Items của history_item_id",
                        {"actual": actual, "expected": expected, "history_item_id": history_item_id},
                    )

        # Cross consistency from history session
        if session_map and history_session_id and history_session_id in session_map:
            session = session_map[history_session_id]
            for col, expected in [
                ("user_id", session.get("user_id")),
                ("plan_id", session.get("plan_id")),
            ]:
                actual = normalize_str(row.get(col))
                if expected and actual and actual != expected:
                    add_issue(
                        issues,
                        "ERROR",
                        "HISTORY_SESSION_LINK_MISMATCH",
                        USER_FEEDBACK_SHEET,
                        excel_row,
                        row,
                        col,
                        f"{col} không khớp với dòng Workout_History_Sessions của history_session_id",
                        {"actual": actual, "expected": expected, "history_session_id": history_session_id},
                    )

        # Cross consistency from plan item
        if plan_item_map and plan_item_id and plan_item_id in plan_item_map:
            pitem = plan_item_map[plan_item_id]
            for col, expected in [
                ("plan_id", pitem.get("plan_id")),
                ("exercise_id", pitem.get("exercise_id")),
            ]:
                actual = normalize_str(row.get(col))
                if expected and actual and actual != expected:
                    add_issue(
                        issues,
                        "ERROR",
                        "PLAN_ITEM_LINK_MISMATCH",
                        USER_FEEDBACK_SHEET,
                        excel_row,
                        row,
                        col,
                        f"{col} không khớp với Workout_Plan_Items của plan_item_id",
                        {"actual": actual, "expected": expected, "plan_item_id": plan_item_id},
                    )

        # Sentiment/rating consistency
        rating = numeric_int(row.get("rating"))
        sentiment = normalize_str(row.get("sentiment"))
        if rating is not None:
            if rating >= 4 and sentiment == "Negative":
                add_issue(
                    issues,
                    "WARNING",
                    "RATING_SENTIMENT_MISMATCH",
                    USER_FEEDBACK_SHEET,
                    excel_row,
                    row,
                    "sentiment",
                    "rating cao nhưng sentiment Negative",
                    {"rating": rating, "sentiment": sentiment},
                )
            if rating <= 2 and sentiment == "Positive":
                add_issue(
                    issues,
                    "WARNING",
                    "RATING_SENTIMENT_MISMATCH",
                    USER_FEEDBACK_SHEET,
                    excel_row,
                    row,
                    "sentiment",
                    "rating thấp nhưng sentiment Positive",
                    {"rating": rating, "sentiment": sentiment},
                )

        # Pain logic
        pain_feedback = normalize_str(row.get("pain_feedback"))
        ok, pain_areas = parse_json_array(row.get("pain_areas"))
        requested_action = normalize_str(row.get("requested_action"))

        if pain_feedback == "No Pain" and ok and len(pain_areas) > 0:
            add_issue(
                issues,
                "ERROR",
                "NO_PAIN_WITH_PAIN_AREAS",
                USER_FEEDBACK_SHEET,
                excel_row,
                row,
                "pain_areas",
                "pain_feedback = No Pain thì pain_areas phải rỗng []",
                pain_areas,
            )

        if pain_feedback in {"Mild Discomfort", "Pain", "Severe Pain"} and ok and len(pain_areas) == 0:
            add_issue(
                issues,
                "ERROR",
                "PAIN_WITHOUT_PAIN_AREAS",
                USER_FEEDBACK_SHEET,
                excel_row,
                row,
                "pain_areas",
                "Có pain/discomfort thì pain_areas không được rỗng",
                row.get("pain_areas"),
            )

        if pain_feedback in {"Pain", "Severe Pain"} and sentiment == "Positive":
            add_issue(
                issues,
                "ERROR",
                "PAIN_WITH_POSITIVE_SENTIMENT",
                USER_FEEDBACK_SHEET,
                excel_row,
                row,
                "sentiment",
                "Pain/Severe Pain không nên đi với Positive sentiment",
                {"pain_feedback": pain_feedback, "sentiment": sentiment},
            )

        if pain_feedback == "Severe Pain" and requested_action != "Review Safety":
            add_issue(
                issues,
                "WARNING",
                "SEVERE_PAIN_ACTION_NOT_REVIEW_SAFETY",
                USER_FEEDBACK_SHEET,
                excel_row,
                row,
                "requested_action",
                "Severe Pain nên requested_action = Review Safety",
                requested_action,
            )

        # Requested action logic
        difficulty = normalize_str(row.get("difficulty_feedback"))
        progression = normalize_str(row.get("progression_preference"))
        duration = normalize_str(row.get("duration_feedback"))
        preference = normalize_str(row.get("exercise_preference"))

        if requested_action == "Review Safety" and pain_feedback in {"No Pain", "Not Applicable", ""}:
            add_issue(
                issues,
                "WARNING",
                "REVIEW_SAFETY_WITHOUT_PAIN_SIGNAL",
                USER_FEEDBACK_SHEET,
                excel_row,
                row,
                "requested_action",
                "Review Safety nên có pain hoặc reason tag liên quan safety",
                {"pain_feedback": pain_feedback},
            )

        if requested_action == "Replace Exercise" and scope != "Exercise":
            add_issue(
                issues,
                "WARNING",
                "REPLACE_EXERCISE_NON_EXERCISE_SCOPE",
                USER_FEEDBACK_SHEET,
                excel_row,
                row,
                "requested_action",
                "Replace Exercise thường nên đi với feedback_scope = Exercise",
                scope,
            )

        if requested_action == "Reduce Difficulty" and difficulty not in {"Too Hard", "Not Applicable"} and progression != "Reduce Difficulty":
            add_issue(
                issues,
                "WARNING",
                "REDUCE_DIFFICULTY_WEAK_SIGNAL",
                USER_FEEDBACK_SHEET,
                excel_row,
                row,
                "requested_action",
                "Reduce Difficulty nên có difficulty_feedback = Too Hard hoặc progression_preference = Reduce Difficulty",
                {"difficulty_feedback": difficulty, "progression_preference": progression},
            )

        if requested_action == "Increase Difficulty" and difficulty != "Too Easy" and progression != "Increase Difficulty":
            add_issue(
                issues,
                "WARNING",
                "INCREASE_DIFFICULTY_WEAK_SIGNAL",
                USER_FEEDBACK_SHEET,
                excel_row,
                row,
                "requested_action",
                "Increase Difficulty nên có difficulty_feedback = Too Easy hoặc progression_preference = Increase Difficulty",
                {"difficulty_feedback": difficulty, "progression_preference": progression},
            )

        if requested_action == "Reduce Session Duration" and duration != "Too Long":
            add_issue(
                issues,
                "WARNING",
                "REDUCE_DURATION_WEAK_SIGNAL",
                USER_FEEDBACK_SHEET,
                excel_row,
                row,
                "requested_action",
                "Reduce Session Duration nên có duration_feedback = Too Long",
                duration,
            )

        if requested_action == "Increase Session Duration" and duration != "Too Short":
            add_issue(
                issues,
                "WARNING",
                "INCREASE_DURATION_WEAK_SIGNAL",
                USER_FEEDBACK_SHEET,
                excel_row,
                row,
                "requested_action",
                "Increase Session Duration nên có duration_feedback = Too Short",
                duration,
            )

        if requested_action == "Keep":
            if sentiment == "Negative" or rating is not None and rating <= 2 or preference == "Dislike":
                add_issue(
                    issues,
                    "WARNING",
                    "KEEP_WITH_NEGATIVE_SIGNAL",
                    USER_FEEDBACK_SHEET,
                    excel_row,
                    row,
                    "requested_action",
                    "requested_action = Keep nhưng feedback có tín hiệu tiêu cực",
                    {
                        "rating": rating,
                        "sentiment": sentiment,
                        "exercise_preference": preference,
                    },
                )

        # Feedback text quality
        feedback_text = normalize_str(row.get("feedback_text"))
        if scope != "General" and len(feedback_text) < 10:
            add_issue(
                issues,
                "WARNING",
                "FEEDBACK_TEXT_TOO_THIN",
                USER_FEEDBACK_SHEET,
                excel_row,
                row,
                "feedback_text",
                "feedback_text quá ngắn; synthetic data nên có text đủ tín hiệu",
                feedback_text,
            )


def validate_distribution(df: pd.DataFrame, issues: list[Issue]) -> dict[str, Any]:
    stats: dict[str, Any] = {}

    n = len(df)
    stats["row_count"] = n

    if n == 0:
        add_issue(
            issues,
            "ERROR",
            "EMPTY_FEEDBACK_DATASET",
            USER_FEEDBACK_SHEET,
            None,
            None,
            None,
            "Sheet User_Feedback không có dòng dữ liệu",
        )
        return stats

    for col in ["feedback_scope", "sentiment", "requested_action", "pain_feedback", "record_source"]:
        if col in df.columns:
            counts = Counter(normalize_str(v) for v in df[col].tolist() if not is_missing(v))
            stats[col] = dict(counts)

    # Distribution target warning
    if "feedback_scope" in df.columns:
        counts = Counter(normalize_str(v) for v in df["feedback_scope"].tolist())
        for value, (lo, hi) in SCOPE_TARGETS.items():
            rate = counts.get(value, 0) / n
            if rate < lo or rate > hi:
                add_issue(
                    issues,
                    "WARNING",
                    "SCOPE_DISTRIBUTION_OUT_OF_TARGET",
                    USER_FEEDBACK_SHEET,
                    None,
                    None,
                    "feedback_scope",
                    f"Tỷ lệ {value} nằm ngoài khoảng khuyến nghị {lo:.0%}–{hi:.0%}",
                    {"value": value, "rate": round(rate, 4), "count": counts.get(value, 0)},
                )

    if "sentiment" in df.columns:
        counts = Counter(normalize_str(v) for v in df["sentiment"].tolist())
        for value, (lo, hi) in SENTIMENT_TARGETS.items():
            rate = counts.get(value, 0) / n
            if rate < lo or rate > hi:
                add_issue(
                    issues,
                    "WARNING",
                    "SENTIMENT_DISTRIBUTION_OUT_OF_TARGET",
                    USER_FEEDBACK_SHEET,
                    None,
                    None,
                    "sentiment",
                    f"Tỷ lệ {value} nằm ngoài khoảng khuyến nghị {lo:.0%}–{hi:.0%}",
                    {"value": value, "rate": round(rate, 4), "count": counts.get(value, 0)},
                )

    if "pain_feedback" in df.columns:
        pain_counts = Counter(normalize_str(v) for v in df["pain_feedback"].tolist())
        pain_count = sum(pain_counts.get(v, 0) for v in ["Mild Discomfort", "Pain", "Severe Pain"])
        pain_rate = pain_count / n
        stats["pain_signal_rate"] = pain_rate
        lo, hi = PAIN_RATE_TARGET
        if pain_rate < lo or pain_rate > hi:
            add_issue(
                issues,
                "WARNING",
                "PAIN_RATE_OUT_OF_TARGET",
                USER_FEEDBACK_SHEET,
                None,
                None,
                "pain_feedback",
                f"Tỷ lệ pain/discomfort nằm ngoài khoảng khuyến nghị {lo:.0%}–{hi:.0%}",
                {"pain_rate": round(pain_rate, 4), "pain_count": pain_count},
            )

    return stats


def load_references(args: argparse.Namespace) -> dict[str, Any]:
    refs: dict[str, Any] = {
        "user_ids": set(),
        "plan_ids": set(),
        "session_map": {},
        "item_map": {},
        "plan_item_map": {},
        "exercise_ids": set(),
    }

    if args.user_master:
        sheets = read_excel_sheets(Path(args.user_master))
        df = find_sheet_with_column(sheets, "user_id")
        refs["user_ids"] = make_lookup(df, "user_id")

    if args.exercise_master:
        sheets = read_excel_sheets(Path(args.exercise_master))
        df = find_sheet_with_column(sheets, "exercise_id")
        refs["exercise_ids"] = make_lookup(df, "exercise_id")

    if args.plan_master:
        sheets = read_excel_sheets(Path(args.plan_master))
        plans_df = find_sheet_with_column(sheets, "plan_id")
        refs["plan_ids"] = make_lookup(plans_df, "plan_id")

        plan_items_df = find_sheet_with_column(sheets, "plan_item_id")
        if plan_items_df is not None:
            plan_items_df = clean_columns(plan_items_df)
            refs["plan_item_map"] = make_map(
                plan_items_df,
                "plan_item_id",
                ["plan_id", "exercise_id", "user_id"],
            )

    if args.history_master:
        sheets = read_excel_sheets(Path(args.history_master))

        # Prefer explicit sheet names, fallback to column discovery.
        sessions_df = sheets.get("Workout_History_Sessions")
        if sessions_df is None:
            sessions_df = find_sheet_with_column(sheets, "history_session_id")
        if sessions_df is not None:
            sessions_df = clean_columns(sessions_df)
            refs["session_map"] = make_map(
                sessions_df,
                "history_session_id",
                ["user_id", "plan_id", "completion_status"],
            )

        items_df = sheets.get("Workout_History_Items")
        if items_df is None:
            items_df = find_sheet_with_column(sheets, "history_item_id")
        if items_df is not None:
            items_df = clean_columns(items_df)
            refs["item_map"] = make_map(
                items_df,
                "history_item_id",
                [
                    "history_session_id",
                    "user_id",
                    "plan_id",
                    "plan_item_id",
                    "exercise_id",
                    "completion_status",
                    "pain_during_exercise",
                    "feedback_signal",
                ],
            )

    return refs


def readiness(issues: list[Issue]) -> dict[str, bool]:
    error_codes = {i.code for i in issues if i.severity == "ERROR"}

    schema_codes = {
        "MISSING_SHEET",
        "MISSING_REQUIRED_COLUMNS",
        "REQUIRED_VALUE_EMPTY",
        "INVALID_ENUM_VALUE",
        "INVALID_ID_FORMAT",
        "INVALID_BOOLEAN",
        "INVALID_TIMESTAMP",
        "UPDATED_BEFORE_CREATED",
    }

    reference_codes = {
        "UNKNOWN_USER_ID",
        "UNKNOWN_PLAN_ID",
        "UNKNOWN_HISTORY_SESSION_ID",
        "UNKNOWN_HISTORY_ITEM_ID",
        "UNKNOWN_PLAN_ITEM_ID",
        "UNKNOWN_EXERCISE_ID",
        "HISTORY_ITEM_LINK_MISMATCH",
        "HISTORY_SESSION_LINK_MISMATCH",
        "PLAN_ITEM_LINK_MISMATCH",
    }

    logic_codes = {
        "SCOPE_REQUIRED_LINK_MISSING",
        "RATING_OUT_OF_RANGE",
        "INVALID_JSON_ARRAY",
        "SYNTHETIC_SOURCE_FLAG_MISMATCH",
        "NO_PAIN_WITH_PAIN_AREAS",
        "PAIN_WITHOUT_PAIN_AREAS",
        "PAIN_WITH_POSITIVE_SENTIMENT",
        "EMPTY_FEEDBACK_DATASET",
        "DUPLICATE_FEEDBACK_ID",
    }

    return {
        "schema_ready": not bool(error_codes & schema_codes),
        "references_ready": not bool(error_codes & reference_codes),
        "logic_ready": not bool(error_codes & logic_codes),
        "ai_training_ready": len(error_codes) == 0,
    }


def write_reports(
    issues: list[Issue],
    stats: dict[str, Any],
    ready: dict[str, bool],
    report_dir: Path,
) -> None:
    report_dir.mkdir(parents=True, exist_ok=True)

    severity_counts = Counter(i.severity for i in issues)
    code_counts = Counter(i.code for i in issues)

    txt_path = report_dir / "user_feedback_validation_report.txt"
    json_path = report_dir / "user_feedback_validation_report.json"
    csv_path = report_dir / "user_feedback_validation_issues.csv"

    lines: list[str] = []
    lines.append("=" * 88)
    lines.append("USER FEEDBACK VALIDATION REPORT")
    lines.append("=" * 88)
    lines.append("")
    lines.append(f"Rows    : {stats.get('row_count', 0)}")
    lines.append(f"ERROR   : {severity_counts.get('ERROR', 0)}")
    lines.append(f"WARNING : {severity_counts.get('WARNING', 0)}")
    lines.append(f"INFO    : {severity_counts.get('INFO', 0)}")
    lines.append("")
    lines.append("READINESS")
    lines.append("-" * 88)
    for k, v in ready.items():
        lines.append(f"{k}: {'PASS' if v else 'FAIL'}")

    lines.append("")
    lines.append("ISSUE COUNTS")
    lines.append("-" * 88)
    if code_counts:
        for code, count in code_counts.most_common():
            lines.append(f"{code}: {count}")
    else:
        lines.append("Không phát hiện issue.")

    lines.append("")
    lines.append("DATASET STATISTICS")
    lines.append("-" * 88)
    lines.append(json.dumps(stats, ensure_ascii=False, indent=2, default=str))

    lines.append("")
    lines.append("DETAILS")
    lines.append("-" * 88)
    if issues:
        for number, issue in enumerate(issues, start=1):
            location = []
            if issue.table:
                location.append(issue.table)
            if issue.excel_row is not None:
                location.append(f"dòng {issue.excel_row}")
            if issue.feedback_id:
                location.append(issue.feedback_id)
            if issue.user_id:
                location.append(issue.user_id)
            if issue.plan_id:
                location.append(issue.plan_id)
            if issue.column:
                location.append(issue.column)
            loc_text = f" ({' | '.join(location)})" if location else ""
            lines.append(f"{number}. [{issue.severity}] {issue.code}{loc_text}: {issue.message}")
            if issue.value is not None:
                lines.append(f"    Giá trị: {issue.value}")
    else:
        lines.append("Không phát hiện lỗi/cảnh báo.")

    txt_path.write_text("\n".join(lines), encoding="utf-8")

    payload = {
        "summary": {
            "row_count": stats.get("row_count", 0),
            "error_count": severity_counts.get("ERROR", 0),
            "warning_count": severity_counts.get("WARNING", 0),
            "info_count": severity_counts.get("INFO", 0),
        },
        "readiness": ready,
        "issue_counts": dict(code_counts),
        "statistics": stats,
        "issues": [i.to_dict() for i in issues],
    }
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str), encoding="utf-8")

    with csv_path.open("w", encoding="utf-8-sig", newline="") as f:
        fieldnames = list(Issue.__dataclass_fields__.keys())
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for issue in issues:
            writer.writerow(issue.to_dict())


def validate_user_feedback(args: argparse.Namespace) -> int:
    issues: list[Issue] = []

    user_feedback_path = Path(args.user_feedback_master)
    if not user_feedback_path.exists():
        print(f"Không tìm thấy file: {user_feedback_path}", file=sys.stderr)
        return 1

    try:
        sheets = read_excel_sheets(user_feedback_path)
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    df = validate_schema(sheets, issues)
    if df is None:
        stats = {"row_count": 0}
        ready = readiness(issues)
        write_reports(issues, stats, ready, Path(args.report_dir))
        return 1

    # Chỉ validate các cột chuẩn nếu schema thiếu thì vẫn tiếp tục phần nào được.
    refs = load_references(args)

    validate_rows(
        df,
        issues,
        user_ids=refs["user_ids"],
        plan_ids=refs["plan_ids"],
        session_map=refs["session_map"],
        item_map=refs["item_map"],
        plan_item_map=refs["plan_item_map"],
        exercise_ids=refs["exercise_ids"],
    )

    stats = validate_distribution(df, issues)
    ready = readiness(issues)

    write_reports(issues, stats, ready, Path(args.report_dir))

    severity_counts = Counter(i.severity for i in issues)
    print("=" * 88)
    print("USER FEEDBACK VALIDATION SUMMARY")
    print("=" * 88)
    print(f"Rows    : {stats.get('row_count', 0)}")
    print(f"ERROR   : {severity_counts.get('ERROR', 0)}")
    print(f"WARNING : {severity_counts.get('WARNING', 0)}")
    print(f"INFO    : {severity_counts.get('INFO', 0)}")
    print("")
    for k, v in ready.items():
        print(f"{k}: {'PASS' if v else 'FAIL'}")
    print("")
    print(f"Report dir: {Path(args.report_dir).resolve()}")

    return 1 if severity_counts.get("ERROR", 0) > 0 else 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate user_feedback_master.xlsx")
    parser.add_argument("user_feedback_master", help="Path tới user_feedback_master.xlsx")

    parser.add_argument("--user-master", default=None, help="Path tới user_master.xlsx")
    parser.add_argument("--plan-master", default=None, help="Path tới workout_plan_master.xlsx")
    parser.add_argument("--history-master", default=None, help="Path tới workout_history_master.xlsx")
    parser.add_argument("--exercise-master", default=None, help="Path tới exercise_master.xlsx")
    parser.add_argument("--report-dir", default="reports/user_feedback", help="Thư mục xuất report")

    return parser.parse_args()


if __name__ == "__main__":
    sys.exit(validate_user_feedback(parse_args()))
