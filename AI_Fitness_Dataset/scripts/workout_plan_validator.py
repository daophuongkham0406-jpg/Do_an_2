from __future__ import annotations

import csv
import hashlib
import json
import math
import re
import unicodedata
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from datetime import date, datetime
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any, Iterable

import pandas as pd


# ============================================================
# PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent

WORKOUT_FILE = PROJECT_ROOT / "master" / "workout_plan_master.xlsx"
USER_FILE = PROJECT_ROOT / "master" / "user_master.xlsx"
EXERCISE_FILE = PROJECT_ROOT / "master" / "exercise_master.xlsx"

REPORT_DIR = PROJECT_ROOT / "reports"
REPORT_FILE = REPORT_DIR / "workout_plan_validation_report.txt"
REPORT_JSON_FILE = REPORT_DIR / "workout_plan_validation_report.json"
ISSUES_CSV_FILE = REPORT_DIR / "workout_plan_validation_issues.csv"


# ============================================================
# SHEETS / SCHEMA
# ============================================================

PLAN_SHEET = "Workout_Plan"
ITEM_SHEET = "Workout_Plan_Items"
USER_SHEET = "User_Profile"
EXERCISE_SHEET = "gym_exercise_dataset"

PLAN_REQUIRED_COLUMNS = [
    "plan_id",
    "user_id",
    "username_snapshot",
    "primary_goal_snapshot",
    "secondary_goal_snapshot",
    "training_level_snapshot",
    "plan_name",
    "plan_type",
    "plan_start_date",
    "plan_end_date",
    "duration_weeks",
    "days_per_week",
    "split_type",
    "session_duration_target_min",
    "progression_strategy",
    "weekly_set_target",
    "session_volume_target",
    "deload_strategy",
    "plan_status",
    "generation_source",
    "generator_version",
    "plan_version",
    "exercise_item_count",
    "rationale",
    "safety_notes",
    "created_at",
    "updated_at",
]

ITEM_REQUIRED_COLUMNS = [
    "plan_item_id",
    "plan_id",
    "week_number",
    "day_number",
    "day_name",
    "day_type",
    "session_name",
    "exercise_role",
    "priority_score",
    "selection_reason",
    "focus_muscles",
    "exercise_order",
    "exercise_id",
    "exercise_name_snapshot",
    "exercise_min_level_snapshot",
    "exercise_goals_snapshot",
    "exercise_equipment_snapshot",
    "primary_muscles_snapshot",
    "sets",
    "rep_min",
    "rep_max",
    "duration_seconds",
    "intensity_unit",
    "target_intensity",
    "rest_seconds",
    "tempo",
    "set_type",
    "warmup_sets",
    "is_optional",
    "progression_rule",
    "substitution_exercise_ids",
    "coaching_note",
]

ITEM_JSON_ARRAY_COLUMNS = {
    "focus_muscles",
    "exercise_goals_snapshot",
    "exercise_equipment_snapshot",
    "primary_muscles_snapshot",
    "substitution_exercise_ids",
}

USER_JSON_ARRAY_COLUMNS = {
    "goal_filter_tags",
    "available_training_days",
    "available_equipment",
    "priority_muscles",
    "avoided_muscles",
    "avoided_exercise_ids",
    "injuries_or_limitations",
}

EXERCISE_JSON_ARRAY_COLUMNS = {
    "equipment",
    "primary_muscles",
    "secondary_muscles",
    "recommended_goals",
    "contraindications",
}

PLAN_ID_PATTERN = re.compile(r"^PLAN\d{6,}$")
PLAN_ITEM_ID_PATTERN = re.compile(r"^WPI\d{8,}$")
USER_ID_PATTERN = re.compile(r"^U\d{6,}$")
EXERCISE_ID_PATTERN = re.compile(r"^EX\d{4,}$")

ALLOWED_PLAN_STATUS = {"Draft", "Active", "Completed", "Paused", "Archived"}
ALLOWED_GENERATION_SOURCE = {"AI", "Coach", "User", "Hybrid"}
ALLOWED_DAY_TYPE = {"Training", "Recovery", "Mobility", "Conditioning"}
ALLOWED_EXERCISE_ROLE = {
    "Primary Compound",
    "Secondary Compound",
    "Isolation",
    "Accessory",
    "Core",
    "Conditioning",
    "Mobility/Rehab",
}
ALLOWED_INTENSITY_UNIT = {"RPE", "RIR", "%1RM", "Bodyweight", "Time"}
ALLOWED_SET_TYPE = {"Working", "Warm-up", "Top Set", "Back-off", "AMRAP", "Drop Set"}
ALLOWED_YES_NO = {"Yes", "No"}

LEVEL_RANK = {
    "Beginner": 1,
    "Intermediate": 2,
    "Advanced": 3,
}


# Equipment that does not need to be explicitly declared in User.available_equipment.
# "mat" is intentionally NOT implicit: a mat is still a real equipment/resource constraint.
IMPLICIT_EQUIPMENT = {"bodyweight"}

# Body-region normalization for injury/contraindication matching.
# This is intentionally anatomical: generic words such as "pain", "injury", "mild",
# "previous", etc. must not be sufficient to create a safety conflict.
BODY_REGION_ALIASES = {
    "shoulder": "shoulder",
    "shoulders": "shoulder",
    "rotator": "shoulder",
    "elbow": "elbow",
    "elbows": "elbow",
    "wrist": "wrist",
    "wrists": "wrist",
    "hand": "hand",
    "hands": "hand",
    "finger": "hand",
    "fingers": "hand",
    "neck": "neck",
    "cervical": "neck",
    "back": "back",
    "lumbar": "back",
    "lowerback": "back",
    "lowback": "back",
    "spine": "spine",
    "spinal": "spine",
    "thoracic": "spine",
    "hip": "hip",
    "hips": "hip",
    "groin": "groin",
    "knee": "knee",
    "knees": "knee",
    "patella": "knee",
    "patellar": "knee",
    "ankle": "ankle",
    "ankles": "ankle",
    "achilles": "ankle",
    "foot": "foot",
    "feet": "foot",
}

PLACEHOLDER_PATTERN = re.compile(
    r"^(?:n/?a|na|none|null|unknown|tbd|todo|test|sample|placeholder|-+)$",
    re.IGNORECASE,
)

# Conservative heuristic ranges.
# These are validator heuristics, not universal physiological truths.
# The purpose is to flag suspicious synthetic plans for review, not to act as medical guidance.
WEEKLY_SET_WARNING_BY_LEVEL = {
    "Beginner": (4, 18),
    "Intermediate": (6, 24),
    "Advanced": (6, 30),
}

SESSION_WORKING_SET_WARNING = {
    "Beginner": 20,
    "Intermediate": 26,
    "Advanced": 32,
}

HIGH_FATIGUE_THRESHOLD = 4.0
MAX_HIGH_FATIGUE_EXERCISES_PER_SESSION = 3
NEAR_DUPLICATE_PLAN_THRESHOLD = 0.92


# ============================================================
# ISSUE MODEL
# ============================================================

@dataclass(slots=True)
class Issue:
    severity: str
    code: str
    message: str
    table: str = ""
    excel_row: int | None = None
    plan_id: str = ""
    plan_item_id: str = ""
    user_id: str = ""
    exercise_id: str = ""
    column: str = ""
    value: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# ============================================================
# HELPERS
# ============================================================

def add_issue(
    issues: list[Issue],
    severity: str,
    code: str,
    message: str,
    *,
    table: str = "",
    excel_row: int | None = None,
    plan_id: str = "",
    plan_item_id: str = "",
    user_id: str = "",
    exercise_id: str = "",
    column: str = "",
    value: Any = "",
) -> None:
    issues.append(
        Issue(
            severity=severity,
            code=code,
            message=message,
            table=table,
            excel_row=excel_row,
            plan_id=str(plan_id or ""),
            plan_item_id=str(plan_item_id or ""),
            user_id=str(user_id or ""),
            exercise_id=str(exercise_id or ""),
            column=column,
            value="" if value is None else str(value),
        )
    )


def is_empty(value: Any) -> bool:
    if value is None:
        return True
    try:
        if pd.isna(value):
            return True
    except (TypeError, ValueError):
        pass
    return str(value).strip() == ""


def normalize_space(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value).strip())


def normalize_key(value: Any) -> str:
    text = unicodedata.normalize("NFKC", normalize_space(value))
    return text.casefold()


def extract_body_regions(value: Any) -> set[str]:
    """Map free-text injury/contraindication text to canonical body regions."""
    text = normalize_key(value).replace("-", " ")
    tokens = re.findall(r"[a-z]+", text)

    # Also support common two-word forms before token lookup.
    compact = re.sub(r"[^a-z]+", "", text)
    regions: set[str] = set()

    if "lowerback" in compact or "lowback" in compact:
        regions.add("back")

    for token in tokens:
        canonical = BODY_REGION_ALIASES.get(token)
        if canonical:
            regions.add(canonical)

    return regions


def stable_fingerprint(parts: Iterable[Any]) -> str:
    normalized = "\x1f".join(normalize_key(part) for part in parts)
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def parse_json_array(value: Any) -> tuple[list[Any] | None, str]:
    if is_empty(value):
        return [], ""

    if isinstance(value, list):
        return value, ""

    try:
        parsed = json.loads(str(value))
    except json.JSONDecodeError as error:
        return None, f"JSON không hợp lệ tại ký tự {error.pos}: {error.msg}"

    if not isinstance(parsed, list):
        return None, "Giá trị phải là JSON Array"

    return parsed, ""


def validate_json_array_cell(
    issues: list[Issue],
    value: Any,
    *,
    table: str,
    excel_row: int,
    plan_id: str,
    plan_item_id: str,
    column: str,
) -> list[str]:
    parsed, error = parse_json_array(value)

    if parsed is None:
        add_issue(
            issues,
            "ERROR",
            "JSON_ARRAY_INVALID",
            error,
            table=table,
            excel_row=excel_row,
            plan_id=plan_id,
            plan_item_id=plan_item_id,
            column=column,
            value=value,
        )
        return []

    output: list[str] = []
    seen: set[str] = set()

    for element in parsed:
        if not isinstance(element, str):
            add_issue(
                issues,
                "ERROR",
                "JSON_ARRAY_NON_STRING",
                "Mảng phải chỉ chứa chuỗi",
                table=table,
                excel_row=excel_row,
                plan_id=plan_id,
                plan_item_id=plan_item_id,
                column=column,
                value=element,
            )
            continue

        text = normalize_space(element)
        if not text:
            add_issue(
                issues,
                "ERROR",
                "JSON_ARRAY_EMPTY_ELEMENT",
                "Mảng chứa phần tử rỗng",
                table=table,
                excel_row=excel_row,
                plan_id=plan_id,
                plan_item_id=plan_item_id,
                column=column,
            )
            continue

        if PLACEHOLDER_PATTERN.fullmatch(text):
            add_issue(
                issues,
                "ERROR",
                "PLACEHOLDER_VALUE",
                "Không nên dùng placeholder trong dữ liệu train",
                table=table,
                excel_row=excel_row,
                plan_id=plan_id,
                plan_item_id=plan_item_id,
                column=column,
                value=text,
            )

        key = normalize_key(text)
        if key in seen:
            add_issue(
                issues,
                "WARNING",
                "DUPLICATE_ARRAY_ELEMENT",
                "Mảng chứa phần tử trùng lặp",
                table=table,
                excel_row=excel_row,
                plan_id=plan_id,
                plan_item_id=plan_item_id,
                column=column,
                value=text,
            )
        else:
            seen.add(key)
            output.append(text)

    return output


def parse_date(value: Any) -> date | None:
    if is_empty(value):
        return None

    if isinstance(value, pd.Timestamp):
        return value.date()
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value

    text = str(value).strip()

    for fmt in (
        "%Y-%m-%d",
        "%Y-%m-%dT%H:%M",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d %H:%M:%S",
    ):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue

    try:
        return pd.to_datetime(value).date()
    except Exception:
        return None


def numeric(value: Any) -> float | None:
    if is_empty(value):
        return None
    try:
        result = float(value)
        if math.isnan(result) or math.isinf(result):
            return None
        return result
    except (TypeError, ValueError):
        return None


def integer_like(value: Any) -> int | None:
    n = numeric(value)
    if n is None:
        return None
    if not float(n).is_integer():
        return None
    return int(n)


def load_sheet(path: Path, sheet_name: str) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Không tìm thấy file: {path}")

    try:
        dataframe = pd.read_excel(path, sheet_name=sheet_name, dtype=object)
    except ValueError as exc:
        raise ValueError(f"Không tìm thấy sheet '{sheet_name}' trong {path.name}") from exc

    dataframe.columns = [normalize_space(column) for column in dataframe.columns]
    return dataframe


def validate_required_columns(
    issues: list[Issue],
    dataframe: pd.DataFrame,
    required_columns: list[str],
    *,
    table: str,
) -> bool:
    missing = [column for column in required_columns if column not in dataframe.columns]

    for column in missing:
        add_issue(
            issues,
            "ERROR",
            "MISSING_REQUIRED_COLUMN",
            f"Thiếu cột bắt buộc: {column}",
            table=table,
            column=column,
        )

    return not missing


def canonical_json_list(values: Iterable[str]) -> str:
    return json.dumps(list(values), ensure_ascii=False, separators=(",", ":"))


# ============================================================
# SOURCE MASTER LOADING
# ============================================================

def load_user_master(issues: list[Issue]) -> tuple[pd.DataFrame, dict[str, dict[str, Any]]]:
    dataframe = load_sheet(USER_FILE, USER_SHEET)

    required = [
        "user_id",
        "username",
        "primary_goal",
        "goal_filter_tags",
        "training_level",
        "training_days_per_week",
        "session_duration_minutes",
        "available_training_days",
        "available_equipment",
        "priority_muscles",
        "avoided_muscles",
        "avoided_exercise_ids",
        "injuries_or_limitations",
        "medical_clearance_required",
        "preferred_split",
        "progression_strategy",
        "profile_status",
    ]

    validate_required_columns(issues, dataframe, required, table=USER_SHEET)

    lookup: dict[str, dict[str, Any]] = {}

    if "user_id" not in dataframe.columns:
        return dataframe, lookup

    for index, row in dataframe.iterrows():
        user_id = normalize_space(row.get("user_id", ""))
        if not user_id:
            continue

        record = row.to_dict()

        for column in USER_JSON_ARRAY_COLUMNS:
            if column in dataframe.columns:
                parsed, _ = parse_json_array(row.get(column))
                record[column] = parsed or []

        lookup[user_id] = record

    return dataframe, lookup


def load_exercise_master(
    issues: list[Issue],
) -> tuple[pd.DataFrame, dict[str, dict[str, Any]]]:
    dataframe = load_sheet(EXERCISE_FILE, EXERCISE_SHEET)

    required = [
        "exercise_id",
        "exercise_name",
        "mechanics_type",
        "movement_pattern",
        "equipment",
        "primary_muscles",
        "minimum_training_level",
        "technical_complexity_score",
        "systemic_fatigue_score",
        "recommended_goals",
        "relative_injury_risk",
        "contraindications",
        "record_status",
    ]

    validate_required_columns(issues, dataframe, required, table=EXERCISE_SHEET)

    lookup: dict[str, dict[str, Any]] = {}

    if "exercise_id" not in dataframe.columns:
        return dataframe, lookup

    for index, row in dataframe.iterrows():
        exercise_id = normalize_space(row.get("exercise_id", ""))
        if not exercise_id:
            continue

        record = row.to_dict()

        for column in EXERCISE_JSON_ARRAY_COLUMNS:
            if column in dataframe.columns:
                parsed, _ = parse_json_array(row.get(column))
                record[column] = parsed or []

        lookup[exercise_id] = record

    return dataframe, lookup


# ============================================================
# PLAN VALIDATION
# ============================================================

def validate_plans(
    issues: list[Issue],
    plans: pd.DataFrame,
    items: pd.DataFrame,
    users: dict[str, dict[str, Any]],
) -> None:
    if not validate_required_columns(
        issues, plans, PLAN_REQUIRED_COLUMNS, table=PLAN_SHEET
    ):
        return

    plan_id_rows: dict[str, int] = {}
    items_by_plan = defaultdict(list)

    if "plan_id" in items.columns:
        for item_index, item_row in items.iterrows():
            item_plan_id = normalize_space(item_row.get("plan_id", ""))
            if item_plan_id:
                items_by_plan[item_plan_id].append((item_index, item_row))

    for index, row in plans.iterrows():
        excel_row = index + 2
        plan_id = normalize_space(row.get("plan_id", ""))
        user_id = normalize_space(row.get("user_id", ""))

        if not plan_id:
            add_issue(
                issues,
                "ERROR",
                "REQUIRED_VALUE_EMPTY",
                "plan_id đang trống",
                table=PLAN_SHEET,
                excel_row=excel_row,
                column="plan_id",
            )
            continue

        if not PLAN_ID_PATTERN.fullmatch(plan_id):
            add_issue(
                issues,
                "ERROR",
                "INVALID_PLAN_ID",
                "plan_id không đúng pattern PLANxxxxxx",
                table=PLAN_SHEET,
                excel_row=excel_row,
                plan_id=plan_id,
                column="plan_id",
                value=plan_id,
            )

        if plan_id in plan_id_rows:
            add_issue(
                issues,
                "ERROR",
                "DUPLICATE_PLAN_ID",
                f"plan_id đã xuất hiện ở dòng {plan_id_rows[plan_id]}",
                table=PLAN_SHEET,
                excel_row=excel_row,
                plan_id=plan_id,
                column="plan_id",
            )
        else:
            plan_id_rows[plan_id] = excel_row

        if not user_id:
            add_issue(
                issues,
                "ERROR",
                "REQUIRED_VALUE_EMPTY",
                "user_id đang trống",
                table=PLAN_SHEET,
                excel_row=excel_row,
                plan_id=plan_id,
                column="user_id",
            )
        elif user_id not in users:
            add_issue(
                issues,
                "ERROR",
                "UNKNOWN_USER_ID",
                "user_id không tồn tại trong User Master",
                table=PLAN_SHEET,
                excel_row=excel_row,
                plan_id=plan_id,
                user_id=user_id,
                column="user_id",
                value=user_id,
            )

        # Required scalar values
        for column in [
            "plan_name",
            "plan_type",
            "plan_start_date",
            "plan_end_date",
            "duration_weeks",
            "days_per_week",
            "split_type",
            "session_duration_target_min",
            "progression_strategy",
            "deload_strategy",
            "plan_status",
            "generation_source",
            "plan_version",
            "rationale",
            "safety_notes",
        ]:
            if is_empty(row.get(column)):
                add_issue(
                    issues,
                    "ERROR",
                    "REQUIRED_VALUE_EMPTY",
                    f"{column} đang trống",
                    table=PLAN_SHEET,
                    excel_row=excel_row,
                    plan_id=plan_id,
                    user_id=user_id,
                    column=column,
                )

        # Dates
        start_date = parse_date(row.get("plan_start_date"))
        end_date = parse_date(row.get("plan_end_date"))

        if start_date is None:
            add_issue(
                issues,
                "ERROR",
                "INVALID_PLAN_START_DATE",
                "plan_start_date không đọc được",
                table=PLAN_SHEET,
                excel_row=excel_row,
                plan_id=plan_id,
                column="plan_start_date",
                value=row.get("plan_start_date"),
            )

        if end_date is None:
            add_issue(
                issues,
                "ERROR",
                "INVALID_PLAN_END_DATE",
                "plan_end_date không đọc được",
                table=PLAN_SHEET,
                excel_row=excel_row,
                plan_id=plan_id,
                column="plan_end_date",
                value=row.get("plan_end_date"),
            )

        if start_date and end_date and end_date < start_date:
            add_issue(
                issues,
                "ERROR",
                "INVALID_PLAN_DATE_RANGE",
                "plan_end_date phải >= plan_start_date",
                table=PLAN_SHEET,
                excel_row=excel_row,
                plan_id=plan_id,
            )

        duration_weeks = integer_like(row.get("duration_weeks"))
        if duration_weeks is None or not (1 <= duration_weeks <= 52):
            add_issue(
                issues,
                "ERROR",
                "INVALID_DURATION_WEEKS",
                "duration_weeks phải là số nguyên 1-52",
                table=PLAN_SHEET,
                excel_row=excel_row,
                plan_id=plan_id,
                column="duration_weeks",
                value=row.get("duration_weeks"),
            )

        days_per_week = integer_like(row.get("days_per_week"))
        if days_per_week is None or not (1 <= days_per_week <= 7):
            add_issue(
                issues,
                "ERROR",
                "INVALID_DAYS_PER_WEEK",
                "days_per_week phải là số nguyên 1-7",
                table=PLAN_SHEET,
                excel_row=excel_row,
                plan_id=plan_id,
                column="days_per_week",
                value=row.get("days_per_week"),
            )

        session_duration = numeric(row.get("session_duration_target_min"))
        if session_duration is None or session_duration <= 0:
            add_issue(
                issues,
                "ERROR",
                "INVALID_SESSION_DURATION",
                "session_duration_target_min phải > 0",
                table=PLAN_SHEET,
                excel_row=excel_row,
                plan_id=plan_id,
                column="session_duration_target_min",
                value=row.get("session_duration_target_min"),
            )

        plan_status = normalize_space(row.get("plan_status", ""))
        if plan_status and plan_status not in ALLOWED_PLAN_STATUS:
            add_issue(
                issues,
                "ERROR",
                "INVALID_PLAN_STATUS",
                "plan_status không thuộc taxonomy chuẩn",
                table=PLAN_SHEET,
                excel_row=excel_row,
                plan_id=plan_id,
                column="plan_status",
                value=plan_status,
            )

        generation_source = normalize_space(row.get("generation_source", ""))
        if generation_source and generation_source not in ALLOWED_GENERATION_SOURCE:
            add_issue(
                issues,
                "ERROR",
                "INVALID_GENERATION_SOURCE",
                "generation_source không thuộc taxonomy chuẩn",
                table=PLAN_SHEET,
                excel_row=excel_row,
                plan_id=plan_id,
                column="generation_source",
                value=generation_source,
            )

        # User snapshots / source alignment
        user = users.get(user_id)

        if user:
            snapshot_checks = [
                ("username_snapshot", "username"),
                ("primary_goal_snapshot", "primary_goal"),
                ("training_level_snapshot", "training_level"),
            ]

            for plan_column, user_column in snapshot_checks:
                actual = normalize_space(row.get(plan_column, ""))
                expected = normalize_space(user.get(user_column, ""))

                if actual and expected and normalize_key(actual) != normalize_key(expected):
                    add_issue(
                        issues,
                        "ERROR",
                        "USER_SNAPSHOT_MISMATCH",
                        f"{plan_column} không khớp User Master.{user_column}",
                        table=PLAN_SHEET,
                        excel_row=excel_row,
                        plan_id=plan_id,
                        user_id=user_id,
                        column=plan_column,
                        value=f"{actual} != {expected}",
                    )

            user_training_days = integer_like(user.get("training_days_per_week"))
            available_days = user.get("available_training_days", [])

            if (
                days_per_week is not None
                and user_training_days is not None
                and days_per_week > user_training_days
            ):
                add_issue(
                    issues,
                    "ERROR",
                    "PLAN_EXCEEDS_USER_TRAINING_DAYS",
                    "Plan có nhiều buổi/tuần hơn User Master cho phép",
                    table=PLAN_SHEET,
                    excel_row=excel_row,
                    plan_id=plan_id,
                    user_id=user_id,
                    column="days_per_week",
                    value=days_per_week,
                )

            if days_per_week is not None and available_days and days_per_week > len(available_days):
                add_issue(
                    issues,
                    "ERROR",
                    "PLAN_EXCEEDS_AVAILABLE_DAYS",
                    "Plan yêu cầu nhiều ngày hơn available_training_days",
                    table=PLAN_SHEET,
                    excel_row=excel_row,
                    plan_id=plan_id,
                    user_id=user_id,
                )

            user_session_duration = numeric(user.get("session_duration_minutes"))
            if (
                session_duration is not None
                and user_session_duration is not None
                and session_duration > user_session_duration * 1.20
            ):
                add_issue(
                    issues,
                    "WARNING",
                    "SESSION_DURATION_EXCEEDS_USER_BUDGET",
                    "Thời lượng plan vượt đáng kể thời gian user khai báo",
                    table=PLAN_SHEET,
                    excel_row=excel_row,
                    plan_id=plan_id,
                    user_id=user_id,
                    column="session_duration_target_min",
                    value=session_duration,
                )

            preferred_split = normalize_space(user.get("preferred_split", ""))
            split_type = normalize_space(row.get("split_type", ""))

            if (
                preferred_split
                and preferred_split != "Auto"
                and split_type
                and normalize_key(preferred_split) != normalize_key(split_type)
            ):
                add_issue(
                    issues,
                    "WARNING",
                    "SPLIT_PREFERENCE_MISMATCH",
                    "split_type khác preferred_split của user",
                    table=PLAN_SHEET,
                    excel_row=excel_row,
                    plan_id=plan_id,
                    user_id=user_id,
                    column="split_type",
                    value=f"{split_type} != {preferred_split}",
                )

            user_progression = normalize_space(user.get("progression_strategy", ""))
            plan_progression = normalize_space(row.get("progression_strategy", ""))

            if (
                user_progression
                and user_progression != "Auto"
                and plan_progression
                and normalize_key(user_progression) != normalize_key(plan_progression)
            ):
                add_issue(
                    issues,
                    "WARNING",
                    "PROGRESSION_PREFERENCE_MISMATCH",
                    "progression_strategy khác lựa chọn của user",
                    table=PLAN_SHEET,
                    excel_row=excel_row,
                    plan_id=plan_id,
                    user_id=user_id,
                )

            medical_required = normalize_space(
                user.get("medical_clearance_required", "")
            )

            if medical_required == "Yes" and plan_status == "Active":
                add_issue(
                    issues,
                    "ERROR",
                    "MEDICAL_CLEARANCE_REQUIRED",
                    "User cần medical clearance nhưng plan đang Active",
                    table=PLAN_SHEET,
                    excel_row=excel_row,
                    plan_id=plan_id,
                    user_id=user_id,
                    column="plan_status",
                )

        # Plan-to-items integrity
        plan_items = items_by_plan.get(plan_id, [])
        expected_count = integer_like(row.get("exercise_item_count"))

        if expected_count is not None and expected_count != len(plan_items):
            add_issue(
                issues,
                "ERROR",
                "EXERCISE_ITEM_COUNT_MISMATCH",
                "exercise_item_count không khớp số dòng Workout_Plan_Items",
                table=PLAN_SHEET,
                excel_row=excel_row,
                plan_id=plan_id,
                column="exercise_item_count",
                value=f"{expected_count} != {len(plan_items)}",
            )

        if len(plan_items) == 0:
            add_issue(
                issues,
                "ERROR",
                "PLAN_WITHOUT_ITEMS",
                "Plan không có Workout_Plan_Items",
                table=PLAN_SHEET,
                excel_row=excel_row,
                plan_id=plan_id,
            )

        # Representative week working-set totals
        week1_items = [
            item_row
            for _, item_row in plan_items
            if integer_like(item_row.get("week_number")) == 1
            and normalize_space(item_row.get("day_type", "")) == "Training"
        ]

        actual_weekly_sets = sum(
            integer_like(item_row.get("sets")) or 0
            for item_row in week1_items
            if normalize_space(item_row.get("set_type", "")) != "Warm-up"
        )

        weekly_set_target = numeric(row.get("weekly_set_target"))

        if weekly_set_target is not None and abs(weekly_set_target - actual_weekly_sets) > 0.01:
            add_issue(
                issues,
                "ERROR",
                "WEEKLY_SET_TARGET_MISMATCH",
                "weekly_set_target không khớp tổng working sets tuần 1",
                table=PLAN_SHEET,
                excel_row=excel_row,
                plan_id=plan_id,
                column="weekly_set_target",
                value=f"{weekly_set_target} != {actual_weekly_sets}",
            )

        if days_per_week:
            session_volume_target = numeric(row.get("session_volume_target"))
            expected_session_volume = actual_weekly_sets / days_per_week

            if (
                session_volume_target is not None
                and abs(session_volume_target - expected_session_volume) > 0.2
            ):
                add_issue(
                    issues,
                    "ERROR",
                    "SESSION_VOLUME_TARGET_MISMATCH",
                    "session_volume_target không khớp weekly_set_target / days_per_week",
                    table=PLAN_SHEET,
                    excel_row=excel_row,
                    plan_id=plan_id,
                    column="session_volume_target",
                    value=f"{session_volume_target} != {expected_session_volume:.2f}",
                )


# ============================================================
# ITEM / CROSS-MASTER VALIDATION
# ============================================================

def validate_items(
    issues: list[Issue],
    plans: pd.DataFrame,
    items: pd.DataFrame,
    users: dict[str, dict[str, Any]],
    exercises: dict[str, dict[str, Any]],
) -> None:
    if not validate_required_columns(
        issues, items, ITEM_REQUIRED_COLUMNS, table=ITEM_SHEET
    ):
        return

    plan_lookup = {
        normalize_space(row.get("plan_id", "")): row.to_dict()
        for _, row in plans.iterrows()
        if not is_empty(row.get("plan_id"))
    }

    seen_item_ids: dict[str, int] = {}
    ordering_registry: dict[tuple[str, int, int, int], int] = {}
    exercise_session_registry: Counter[tuple[str, int, int, str]] = Counter()

    for index, row in items.iterrows():
        excel_row = index + 2
        plan_item_id = normalize_space(row.get("plan_item_id", ""))
        plan_id = normalize_space(row.get("plan_id", ""))
        exercise_id = normalize_space(row.get("exercise_id", ""))

        if not plan_item_id:
            add_issue(
                issues,
                "ERROR",
                "REQUIRED_VALUE_EMPTY",
                "plan_item_id đang trống",
                table=ITEM_SHEET,
                excel_row=excel_row,
                column="plan_item_id",
            )
            continue

        if not PLAN_ITEM_ID_PATTERN.fullmatch(plan_item_id):
            add_issue(
                issues,
                "ERROR",
                "INVALID_PLAN_ITEM_ID",
                "plan_item_id không đúng pattern WPIxxxxxxxx",
                table=ITEM_SHEET,
                excel_row=excel_row,
                plan_item_id=plan_item_id,
                column="plan_item_id",
                value=plan_item_id,
            )

        if plan_item_id in seen_item_ids:
            add_issue(
                issues,
                "ERROR",
                "DUPLICATE_PLAN_ITEM_ID",
                f"plan_item_id đã xuất hiện ở dòng {seen_item_ids[plan_item_id]}",
                table=ITEM_SHEET,
                excel_row=excel_row,
                plan_item_id=plan_item_id,
            )
        else:
            seen_item_ids[plan_item_id] = excel_row

        if plan_id not in plan_lookup:
            add_issue(
                issues,
                "ERROR",
                "UNKNOWN_PLAN_ID",
                "plan_id không tồn tại trong Workout_Plan",
                table=ITEM_SHEET,
                excel_row=excel_row,
                plan_item_id=plan_item_id,
                plan_id=plan_id,
                column="plan_id",
                value=plan_id,
            )
            parent_plan = None
            user = None
            user_id = ""
        else:
            parent_plan = plan_lookup[plan_id]
            user_id = normalize_space(parent_plan.get("user_id", ""))
            user = users.get(user_id)

        if exercise_id not in exercises:
            add_issue(
                issues,
                "ERROR",
                "UNKNOWN_EXERCISE_ID",
                "exercise_id không tồn tại trong Exercise Master",
                table=ITEM_SHEET,
                excel_row=excel_row,
                plan_id=plan_id,
                plan_item_id=plan_item_id,
                exercise_id=exercise_id,
                column="exercise_id",
                value=exercise_id,
            )
            exercise = None
        else:
            exercise = exercises[exercise_id]

        # JSON arrays
        arrays: dict[str, list[str]] = {}

        for column in ITEM_JSON_ARRAY_COLUMNS:
            arrays[column] = validate_json_array_cell(
                issues,
                row.get(column),
                table=ITEM_SHEET,
                excel_row=excel_row,
                plan_id=plan_id,
                plan_item_id=plan_item_id,
                column=column,
            )

        # Enum/range checks
        day_type = normalize_space(row.get("day_type", ""))
        if day_type not in ALLOWED_DAY_TYPE:
            add_issue(
                issues,
                "ERROR",
                "INVALID_DAY_TYPE",
                "day_type không thuộc taxonomy chuẩn",
                table=ITEM_SHEET,
                excel_row=excel_row,
                plan_id=plan_id,
                plan_item_id=plan_item_id,
                column="day_type",
                value=day_type,
            )

        exercise_role = normalize_space(row.get("exercise_role", ""))
        if exercise_role not in ALLOWED_EXERCISE_ROLE:
            add_issue(
                issues,
                "ERROR",
                "INVALID_EXERCISE_ROLE",
                "exercise_role không thuộc taxonomy chuẩn",
                table=ITEM_SHEET,
                excel_row=excel_row,
                plan_id=plan_id,
                plan_item_id=plan_item_id,
                column="exercise_role",
                value=exercise_role,
            )

        priority_score = integer_like(row.get("priority_score"))
        if priority_score is None or not (1 <= priority_score <= 5):
            add_issue(
                issues,
                "ERROR",
                "INVALID_PRIORITY_SCORE",
                "priority_score phải là số nguyên 1-5",
                table=ITEM_SHEET,
                excel_row=excel_row,
                plan_id=plan_id,
                plan_item_id=plan_item_id,
                column="priority_score",
                value=row.get("priority_score"),
            )

        intensity_unit = normalize_space(row.get("intensity_unit", ""))
        if intensity_unit not in ALLOWED_INTENSITY_UNIT:
            add_issue(
                issues,
                "ERROR",
                "INVALID_INTENSITY_UNIT",
                "intensity_unit không thuộc taxonomy chuẩn",
                table=ITEM_SHEET,
                excel_row=excel_row,
                plan_id=plan_id,
                plan_item_id=plan_item_id,
                column="intensity_unit",
                value=intensity_unit,
            )

        set_type = normalize_space(row.get("set_type", ""))
        if set_type not in ALLOWED_SET_TYPE:
            add_issue(
                issues,
                "ERROR",
                "INVALID_SET_TYPE",
                "set_type không thuộc taxonomy chuẩn",
                table=ITEM_SHEET,
                excel_row=excel_row,
                plan_id=plan_id,
                plan_item_id=plan_item_id,
                column="set_type",
                value=set_type,
            )

        optional = normalize_space(row.get("is_optional", ""))
        if optional not in ALLOWED_YES_NO:
            add_issue(
                issues,
                "ERROR",
                "INVALID_YES_NO",
                "is_optional phải là Yes/No",
                table=ITEM_SHEET,
                excel_row=excel_row,
                plan_id=plan_id,
                plan_item_id=plan_item_id,
                column="is_optional",
                value=optional,
            )

        sets = integer_like(row.get("sets"))
        rep_min = integer_like(row.get("rep_min"))
        rep_max = integer_like(row.get("rep_max"))
        rest_seconds = integer_like(row.get("rest_seconds"))
        warmup_sets = integer_like(row.get("warmup_sets"))

        if sets is None or not (1 <= sets <= 20):
            add_issue(
                issues,
                "ERROR",
                "INVALID_SETS",
                "sets phải là số nguyên 1-20",
                table=ITEM_SHEET,
                excel_row=excel_row,
                plan_id=plan_id,
                plan_item_id=plan_item_id,
                column="sets",
                value=row.get("sets"),
            )

        if rep_min is not None and rep_max is not None and rep_max < rep_min:
            add_issue(
                issues,
                "ERROR",
                "INVALID_REP_RANGE",
                "rep_max phải >= rep_min",
                table=ITEM_SHEET,
                excel_row=excel_row,
                plan_id=plan_id,
                plan_item_id=plan_item_id,
                value=f"{rep_min}-{rep_max}",
            )

        if rest_seconds is None or not (0 <= rest_seconds <= 600):
            add_issue(
                issues,
                "ERROR",
                "INVALID_REST_SECONDS",
                "rest_seconds phải trong khoảng 0-600",
                table=ITEM_SHEET,
                excel_row=excel_row,
                plan_id=plan_id,
                plan_item_id=plan_item_id,
                column="rest_seconds",
                value=row.get("rest_seconds"),
            )

        if warmup_sets is None or not (0 <= warmup_sets <= 10):
            add_issue(
                issues,
                "ERROR",
                "INVALID_WARMUP_SETS",
                "warmup_sets phải trong khoảng 0-10",
                table=ITEM_SHEET,
                excel_row=excel_row,
                plan_id=plan_id,
                plan_item_id=plan_item_id,
                column="warmup_sets",
                value=row.get("warmup_sets"),
            )

        selection_reason = normalize_space(row.get("selection_reason", ""))
        if len(selection_reason) < 10:
            add_issue(
                issues,
                "WARNING",
                "SELECTION_REASON_TOO_THIN",
                "selection_reason quá ngắn để dùng làm nhãn giải thích tốt cho AI",
                table=ITEM_SHEET,
                excel_row=excel_row,
                plan_id=plan_id,
                plan_item_id=plan_item_id,
                column="selection_reason",
                value=selection_reason,
            )

        progression_rule = normalize_space(row.get("progression_rule", ""))
        if day_type == "Training" and sets and len(progression_rule) < 15:
            add_issue(
                issues,
                "ERROR",
                "PROGRESSION_RULE_MISSING_OR_THIN",
                "Training item cần progression_rule rõ ràng",
                table=ITEM_SHEET,
                excel_row=excel_row,
                plan_id=plan_id,
                plan_item_id=plan_item_id,
                column="progression_rule",
                value=progression_rule,
            )

        # Ordering uniqueness
        week_number = integer_like(row.get("week_number"))
        day_number = integer_like(row.get("day_number"))
        exercise_order = integer_like(row.get("exercise_order"))

        if week_number is None or not (1 <= week_number <= 52):
            add_issue(
                issues,
                "ERROR",
                "INVALID_WEEK_NUMBER",
                "week_number phải là số nguyên 1-52",
                table=ITEM_SHEET,
                excel_row=excel_row,
                plan_id=plan_id,
                plan_item_id=plan_item_id,
                column="week_number",
                value=row.get("week_number"),
            )

        if day_number is None or not (1 <= day_number <= 7):
            add_issue(
                issues,
                "ERROR",
                "INVALID_DAY_NUMBER",
                "day_number phải là số nguyên 1-7",
                table=ITEM_SHEET,
                excel_row=excel_row,
                plan_id=plan_id,
                plan_item_id=plan_item_id,
                column="day_number",
                value=row.get("day_number"),
            )

        if exercise_order is None or exercise_order < 1:
            add_issue(
                issues,
                "ERROR",
                "INVALID_EXERCISE_ORDER",
                "exercise_order phải >= 1",
                table=ITEM_SHEET,
                excel_row=excel_row,
                plan_id=plan_id,
                plan_item_id=plan_item_id,
                column="exercise_order",
                value=row.get("exercise_order"),
            )

        if week_number and day_number and exercise_order:
            order_key = (plan_id, week_number, day_number, exercise_order)

            if order_key in ordering_registry:
                add_issue(
                    issues,
                    "ERROR",
                    "DUPLICATE_EXERCISE_ORDER",
                    f"Thứ tự exercise đã dùng ở dòng {ordering_registry[order_key]}",
                    table=ITEM_SHEET,
                    excel_row=excel_row,
                    plan_id=plan_id,
                    plan_item_id=plan_item_id,
                )
            else:
                ordering_registry[order_key] = excel_row

        # Duplicate exercise same session
        if week_number and day_number and exercise_id:
            session_ex_key = (plan_id, week_number, day_number, exercise_id)
            exercise_session_registry[session_ex_key] += 1

            if exercise_session_registry[session_ex_key] > 1:
                add_issue(
                    issues,
                    "WARNING",
                    "DUPLICATE_EXERCISE_IN_SESSION",
                    "Cùng exercise xuất hiện nhiều lần trong một session",
                    table=ITEM_SHEET,
                    excel_row=excel_row,
                    plan_id=plan_id,
                    plan_item_id=plan_item_id,
                    exercise_id=exercise_id,
                )

        if exercise:
            # Snapshot consistency
            snapshot_checks = [
                ("exercise_name_snapshot", "exercise_name"),
                ("exercise_min_level_snapshot", "minimum_training_level"),
            ]

            for item_column, exercise_column in snapshot_checks:
                actual = normalize_space(row.get(item_column, ""))
                expected = normalize_space(exercise.get(exercise_column, ""))

                if actual and expected and normalize_key(actual) != normalize_key(expected):
                    add_issue(
                        issues,
                        "ERROR",
                        "EXERCISE_SNAPSHOT_MISMATCH",
                        f"{item_column} không khớp Exercise Master.{exercise_column}",
                        table=ITEM_SHEET,
                        excel_row=excel_row,
                        plan_id=plan_id,
                        plan_item_id=plan_item_id,
                        exercise_id=exercise_id,
                        column=item_column,
                        value=f"{actual} != {expected}",
                    )

            snapshot_array_checks = [
                ("exercise_goals_snapshot", "recommended_goals"),
                ("exercise_equipment_snapshot", "equipment"),
                ("primary_muscles_snapshot", "primary_muscles"),
            ]

            for item_column, exercise_column in snapshot_array_checks:
                actual = {normalize_key(x) for x in arrays.get(item_column, [])}
                expected = {
                    normalize_key(x) for x in exercise.get(exercise_column, [])
                }

                if actual != expected:
                    add_issue(
                        issues,
                        "ERROR",
                        "EXERCISE_ARRAY_SNAPSHOT_MISMATCH",
                        f"{item_column} không khớp Exercise Master.{exercise_column}",
                        table=ITEM_SHEET,
                        excel_row=excel_row,
                        plan_id=plan_id,
                        plan_item_id=plan_item_id,
                        exercise_id=exercise_id,
                        column=item_column,
                    )

            record_status = normalize_space(exercise.get("record_status", ""))

            if record_status in {"Deprecated", "Draft", "Reviewing"}:
                add_issue(
                    issues,
                    "ERROR",
                    "NON_APPROVED_EXERCISE_IN_PLAN",
                    f"Exercise record_status={record_status}; không nên dùng trong positive training plan",
                    table=ITEM_SHEET,
                    excel_row=excel_row,
                    plan_id=plan_id,
                    plan_item_id=plan_item_id,
                    exercise_id=exercise_id,
                )

        if user and exercise:
            user_level = normalize_space(user.get("training_level", ""))
            minimum_level = normalize_space(exercise.get("minimum_training_level", ""))

            if (
                user_level in LEVEL_RANK
                and minimum_level in LEVEL_RANK
                and LEVEL_RANK[minimum_level] > LEVEL_RANK[user_level]
            ):
                add_issue(
                    issues,
                    "ERROR",
                    "TRAINING_LEVEL_MISMATCH",
                    f"{minimum_level} exercise không phù hợp {user_level} user",
                    table=ITEM_SHEET,
                    excel_row=excel_row,
                    plan_id=plan_id,
                    plan_item_id=plan_item_id,
                    user_id=user_id,
                    exercise_id=exercise_id,
                )

            user_equipment = {
                normalize_key(x) for x in user.get("available_equipment", [])
            }
            exercise_equipment = {
                normalize_key(x)
                for x in exercise.get("equipment", [])
                if normalize_key(x) not in {"none"}
            }

            # Bodyweight is implicit, but every other required resource must be
            # explicitly present in User.available_equipment.
            #
            # Important: an exercise such as ["Bodyweight", "Pull-up Bar"]
            # still REQUIRES a Pull-up Bar. The old "bodyweight_only" shortcut
            # incorrectly exempted such mixed-equipment exercises.
            missing_equipment = (
                exercise_equipment
                - user_equipment
                - IMPLICIT_EQUIPMENT
            )

            if missing_equipment:
                add_issue(
                    issues,
                    "ERROR",
                    "EQUIPMENT_MISMATCH",
                    "User không có đủ equipment cho exercise",
                    table=ITEM_SHEET,
                    excel_row=excel_row,
                    plan_id=plan_id,
                    plan_item_id=plan_item_id,
                    user_id=user_id,
                    exercise_id=exercise_id,
                    value=", ".join(sorted(missing_equipment)),
                )

            avoided_exercises = {
                normalize_key(x) for x in user.get("avoided_exercise_ids", [])
            }

            if normalize_key(exercise_id) in avoided_exercises:
                add_issue(
                    issues,
                    "ERROR",
                    "AVOIDED_EXERCISE_SELECTED",
                    "Exercise nằm trong avoided_exercise_ids của user",
                    table=ITEM_SHEET,
                    excel_row=excel_row,
                    plan_id=plan_id,
                    plan_item_id=plan_item_id,
                    user_id=user_id,
                    exercise_id=exercise_id,
                )

            avoided_muscles = {
                normalize_key(x) for x in user.get("avoided_muscles", [])
            }
            exercise_primary = {
                normalize_key(x) for x in exercise.get("primary_muscles", [])
            }

            overlap = avoided_muscles & exercise_primary

            if overlap:
                add_issue(
                    issues,
                    "ERROR",
                    "AVOIDED_MUSCLE_CONFLICT",
                    "Exercise target trùng avoided_muscles của user",
                    table=ITEM_SHEET,
                    excel_row=excel_row,
                    plan_id=plan_id,
                    plan_item_id=plan_item_id,
                    user_id=user_id,
                    exercise_id=exercise_id,
                    value=", ".join(sorted(overlap)),
                )

            user_goal_tags = {
                normalize_key(x) for x in user.get("goal_filter_tags", [])
            }
            exercise_goals = {
                normalize_key(x) for x in exercise.get("recommended_goals", [])
            }

            if user_goal_tags and exercise_goals and not (user_goal_tags & exercise_goals):
                add_issue(
                    issues,
                    "WARNING",
                    "WEAK_GOAL_ALIGNMENT",
                    "Exercise không có recommended_goals giao với user.goal_filter_tags",
                    table=ITEM_SHEET,
                    excel_row=excel_row,
                    plan_id=plan_id,
                    plan_item_id=plan_item_id,
                    user_id=user_id,
                    exercise_id=exercise_id,
                )

            user_priority_muscles = {
                normalize_key(x) for x in user.get("priority_muscles", [])
            }

            if priority_score >= 4 and user_priority_muscles:
                goal_match = bool(user_goal_tags & exercise_goals)
                muscle_match = bool(user_priority_muscles & exercise_primary)

                if not goal_match and not muscle_match:
                    add_issue(
                        issues,
                        "WARNING",
                        "PRIORITY_SCORE_NOT_SUPPORTED",
                        "priority_score cao nhưng không thấy goal/muscle priority match rõ ràng",
                        table=ITEM_SHEET,
                        excel_row=excel_row,
                        plan_id=plan_id,
                        plan_item_id=plan_item_id,
                        user_id=user_id,
                        exercise_id=exercise_id,
                    )

            # Safety: textual contraindication overlap
            injuries = [
                normalize_key(x) for x in user.get("injuries_or_limitations", [])
            ]
            contraindications = [
                normalize_key(x) for x in exercise.get("contraindications", [])
            ]

            for injury in injuries:
                if not injury:
                    continue

                for contraindication in contraindications:
                    if not contraindication:
                        continue

                    # Safety matching is based on anatomical region, not generic
                    # words such as pain/injury/mild/previous. This sharply reduces
                    # false positives while preserving clinically relevant conflicts.
                    injury_regions = extract_body_regions(injury)
                    contra_regions = extract_body_regions(contraindication)
                    region_overlap = injury_regions & contra_regions

                    if region_overlap:
                        add_issue(
                            issues,
                            "ERROR",
                            "POSSIBLE_INJURY_CONTRAINDICATION_CONFLICT",
                            "Injury/limitation và contraindication cùng liên quan vùng cơ thể",
                            table=ITEM_SHEET,
                            excel_row=excel_row,
                            plan_id=plan_id,
                            plan_item_id=plan_item_id,
                            user_id=user_id,
                            exercise_id=exercise_id,
                            value=(
                                f"{injury} ↔ {contraindication} | "
                                f"region={', '.join(sorted(region_overlap))}"
                            ),
                        )
                        break

            risk = normalize_space(exercise.get("relative_injury_risk", ""))
            complexity = numeric(exercise.get("technical_complexity_score"))

            if (
                user_level == "Beginner"
                and risk == "High"
                and complexity is not None
                and complexity >= 4
            ):
                add_issue(
                    issues,
                    "ERROR",
                    "HIGH_RISK_COMPLEX_EXERCISE_FOR_BEGINNER",
                    "Beginner được gán exercise vừa high-risk vừa technical complexity cao",
                    table=ITEM_SHEET,
                    excel_row=excel_row,
                    plan_id=plan_id,
                    plan_item_id=plan_item_id,
                    user_id=user_id,
                    exercise_id=exercise_id,
                )


# ============================================================
# PROGRAMMING QUALITY
# ============================================================

def validate_programming_quality(
    issues: list[Issue],
    plans: pd.DataFrame,
    items: pd.DataFrame,
    users: dict[str, dict[str, Any]],
    exercises: dict[str, dict[str, Any]],
) -> None:
    if "plan_id" not in plans.columns or "plan_id" not in items.columns:
        return

    plan_lookup = {
        normalize_space(row.get("plan_id", "")): row.to_dict()
        for _, row in plans.iterrows()
        if not is_empty(row.get("plan_id"))
    }

    for plan_id, group in items.groupby(items["plan_id"].astype(str)):
        plan_id = normalize_space(plan_id)
        parent = plan_lookup.get(plan_id)

        if not parent:
            continue

        user_id = normalize_space(parent.get("user_id", ""))
        user = users.get(user_id, {})
        user_level = normalize_space(user.get("training_level", ""))
        split_type = normalize_space(parent.get("split_type", ""))
        primary_goal = normalize_space(parent.get("primary_goal_snapshot", ""))

        week1 = group[
            pd.to_numeric(group["week_number"], errors="coerce").fillna(-1) == 1
        ].copy()

        training_items = week1[
            week1["day_type"].astype(str).str.strip().eq("Training")
        ]

        if training_items.empty:
            add_issue(
                issues,
                "ERROR",
                "NO_TRAINING_ITEMS_IN_REPRESENTATIVE_WEEK",
                "Tuần 1 không có Training items",
                table=ITEM_SHEET,
                plan_id=plan_id,
                user_id=user_id,
            )
            continue

        # Actual days represented
        day_numbers = {
            integer_like(v)
            for v in training_items["day_number"].tolist()
            if integer_like(v) is not None
        }

        expected_days = integer_like(parent.get("days_per_week"))

        if expected_days is not None and len(day_numbers) != expected_days:
            add_issue(
                issues,
                "ERROR",
                "TRAINING_DAY_COUNT_MISMATCH",
                "Số training day ở tuần 1 không bằng days_per_week",
                table=ITEM_SHEET,
                plan_id=plan_id,
                user_id=user_id,
                value=f"{len(day_numbers)} != {expected_days}",
            )

        # Volume by primary muscle
        muscle_sets: Counter[str] = Counter()
        movement_sets: Counter[str] = Counter()
        body_region_sets: Counter[str] = Counter()

        for _, item in training_items.iterrows():
            exercise_id = normalize_space(item.get("exercise_id", ""))
            exercise = exercises.get(exercise_id)

            if not exercise:
                continue

            sets = integer_like(item.get("sets")) or 0

            if normalize_space(item.get("set_type", "")) == "Warm-up":
                continue

            primary_muscles = exercise.get("primary_muscles", [])
            movement_pattern = normalize_space(exercise.get("movement_pattern", ""))
            body_region = normalize_space(exercise.get("body_region", ""))

            for muscle in primary_muscles:
                muscle_sets[normalize_space(muscle)] += sets

            if movement_pattern:
                movement_sets[movement_pattern] += sets

            if body_region:
                body_region_sets[body_region] += sets

        # Suspicious volume per muscle
        lower, upper = WEEKLY_SET_WARNING_BY_LEVEL.get(user_level, (4, 24))

        for muscle, weekly_sets in muscle_sets.items():
            if weekly_sets > upper:
                add_issue(
                    issues,
                    "WARNING",
                    "HIGH_WEEKLY_MUSCLE_VOLUME",
                    f"{muscle} có {weekly_sets} working sets/tuần; vượt heuristic cho {user_level or 'unknown'}",
                    table=ITEM_SHEET,
                    plan_id=plan_id,
                    user_id=user_id,
                    value=f"{muscle}: {weekly_sets}",
                )

        # Priority muscles with zero direct primary work
        priority_muscles = [
            normalize_space(x) for x in user.get("priority_muscles", [])
        ]

        for priority in priority_muscles:
            if priority and muscle_sets.get(priority, 0) == 0:
                add_issue(
                    issues,
                    "WARNING",
                    "PRIORITY_MUSCLE_NOT_COVERED",
                    "priority_muscle của user không có direct primary work trong tuần 1",
                    table=ITEM_SHEET,
                    plan_id=plan_id,
                    user_id=user_id,
                    value=priority,
                )

        # Full body coverage heuristics
        if split_type == "Full Body" and len(day_numbers) >= 2:
            lower_body_sets = sum(
                sets
                for region, sets in body_region_sets.items()
                if normalize_key(region) == "lower body"
            )
            upper_body_sets = sum(
                sets
                for region, sets in body_region_sets.items()
                if normalize_key(region) == "upper body"
            )

            if lower_body_sets == 0:
                add_issue(
                    issues,
                    "ERROR",
                    "FULL_BODY_WITHOUT_LOWER_BODY",
                    "Full Body plan nhưng tuần 1 không có lower-body primary work",
                    table=ITEM_SHEET,
                    plan_id=plan_id,
                    user_id=user_id,
                )

            if upper_body_sets == 0:
                add_issue(
                    issues,
                    "ERROR",
                    "FULL_BODY_WITHOUT_UPPER_BODY",
                    "Full Body plan nhưng tuần 1 không có upper-body primary work",
                    table=ITEM_SHEET,
                    plan_id=plan_id,
                    user_id=user_id,
                )

            pattern_keys = {normalize_key(k) for k in movement_sets}
            has_push = any("push" in p for p in pattern_keys)
            has_pull = any("pull" in p or "row" in p for p in pattern_keys)
            has_knee = any(
                any(token in p for token in ["squat", "lunge", "knee extension", "knee flexion"])
                for p in pattern_keys
            )
            has_hinge = any("hinge" in p or "hip extension" in p for p in pattern_keys)

            if not has_push:
                add_issue(
                    issues,
                    "WARNING",
                    "MOVEMENT_PATTERN_MISSING_PUSH",
                    "Full Body plan thiếu rõ rệt push pattern trong tuần 1",
                    table=ITEM_SHEET,
                    plan_id=plan_id,
                )

            if not has_pull:
                add_issue(
                    issues,
                    "WARNING",
                    "MOVEMENT_PATTERN_MISSING_PULL",
                    "Full Body plan thiếu rõ rệt pull pattern trong tuần 1",
                    table=ITEM_SHEET,
                    plan_id=plan_id,
                )

            if not has_knee:
                add_issue(
                    issues,
                    "WARNING",
                    "MOVEMENT_PATTERN_MISSING_KNEE_DOMINANT",
                    "Full Body plan thiếu knee-dominant work trong tuần 1",
                    table=ITEM_SHEET,
                    plan_id=plan_id,
                )

            if not has_hinge:
                add_issue(
                    issues,
                    "WARNING",
                    "MOVEMENT_PATTERN_MISSING_HINGE",
                    "Full Body plan thiếu hip-hinge/posterior-chain work trong tuần 1",
                    table=ITEM_SHEET,
                    plan_id=plan_id,
                )

        # Session-level checks
        for (week_number, day_number), session in training_items.groupby(
            ["week_number", "day_number"]
        ):
            total_working_sets = 0
            high_fatigue_exercises = 0
            patterns: Counter[str] = Counter()
            primary_muscles: Counter[str] = Counter()
            compound_orders: list[int] = []
            isolation_orders: list[int] = []

            estimated_minutes = 0.0

            for _, item in session.iterrows():
                exercise_id = normalize_space(item.get("exercise_id", ""))
                exercise = exercises.get(exercise_id)

                if not exercise:
                    continue

                sets = integer_like(item.get("sets")) or 0
                warmup_sets = integer_like(item.get("warmup_sets")) or 0
                rest_seconds = integer_like(item.get("rest_seconds")) or 0
                rep_min = integer_like(item.get("rep_min"))
                rep_max = integer_like(item.get("rep_max"))
                order = integer_like(item.get("exercise_order")) or 999

                if normalize_space(item.get("set_type", "")) != "Warm-up":
                    total_working_sets += sets

                systemic_fatigue = numeric(exercise.get("systemic_fatigue_score"))
                if systemic_fatigue is not None and systemic_fatigue >= HIGH_FATIGUE_THRESHOLD:
                    high_fatigue_exercises += 1

                pattern = normalize_space(exercise.get("movement_pattern", ""))
                if pattern:
                    patterns[pattern] += 1

                for muscle in exercise.get("primary_muscles", []):
                    primary_muscles[normalize_space(muscle)] += 1

                mechanics = normalize_space(exercise.get("mechanics_type", ""))
                if mechanics == "Compound":
                    compound_orders.append(order)
                elif mechanics == "Isolation":
                    isolation_orders.append(order)

                # Rough time estimate:
                # ~35 sec work per set + rest, plus ~45 sec transition per exercise.
                total_sets = sets + warmup_sets
                estimated_minutes += total_sets * (35 + rest_seconds) / 60.0 + 0.75

            session_limit = SESSION_WORKING_SET_WARNING.get(user_level, 26)

            if total_working_sets > session_limit:
                add_issue(
                    issues,
                    "WARNING",
                    "HIGH_SESSION_WORKING_SET_COUNT",
                    f"Session có {total_working_sets} working sets; có thể quá dày cho {user_level or 'unknown'}",
                    table=ITEM_SHEET,
                    plan_id=plan_id,
                    user_id=user_id,
                    value=f"week={week_number}, day={day_number}",
                )

            if high_fatigue_exercises > MAX_HIGH_FATIGUE_EXERCISES_PER_SESSION:
                add_issue(
                    issues,
                    "WARNING",
                    "HIGH_SYSTEMIC_FATIGUE_STACK",
                    "Có quá nhiều high-systemic-fatigue exercises trong cùng session",
                    table=ITEM_SHEET,
                    plan_id=plan_id,
                    user_id=user_id,
                    value=f"{high_fatigue_exercises} exercises",
                )

            for pattern, count in patterns.items():
                if count >= 4:
                    add_issue(
                        issues,
                        "WARNING",
                        "MOVEMENT_PATTERN_REDUNDANCY",
                        "Một session có nhiều exercise cùng movement_pattern",
                        table=ITEM_SHEET,
                        plan_id=plan_id,
                        user_id=user_id,
                        value=f"{pattern}: {count}",
                    )

            for muscle, count in primary_muscles.items():
                if count >= 4:
                    add_issue(
                        issues,
                        "WARNING",
                        "MUSCLE_EXERCISE_REDUNDANCY",
                        "Một session có nhiều exercise trực tiếp cho cùng primary muscle",
                        table=ITEM_SHEET,
                        plan_id=plan_id,
                        user_id=user_id,
                        value=f"{muscle}: {count}",
                    )

            if compound_orders and isolation_orders:
                if min(compound_orders) > min(isolation_orders):
                    add_issue(
                        issues,
                        "WARNING",
                        "COMPOUND_AFTER_ISOLATION",
                        "Compound exercise xuất hiện sau isolation ngay từ đầu session; cần xác nhận có chủ đích",
                        table=ITEM_SHEET,
                        plan_id=plan_id,
                        user_id=user_id,
                        value=f"week={week_number}, day={day_number}",
                    )

            session_budget = numeric(parent.get("session_duration_target_min"))

            if session_budget and estimated_minutes > session_budget * 1.25:
                add_issue(
                    issues,
                    "WARNING",
                    "SESSION_TIME_ESTIMATE_EXCEEDS_BUDGET",
                    "Ước lượng thời gian session vượt >25% session_duration_target_min",
                    table=ITEM_SHEET,
                    plan_id=plan_id,
                    user_id=user_id,
                    value=f"estimate={estimated_minutes:.1f} min, target={session_budget:.1f}",
                )

        # Goal-specific basic checks
        if primary_goal == "Strength":
            compound_count = 0
            strength_rep_count = 0

            for _, item in training_items.iterrows():
                exercise = exercises.get(normalize_space(item.get("exercise_id", "")))

                if exercise and normalize_space(exercise.get("mechanics_type", "")) == "Compound":
                    compound_count += 1

                rep_max = integer_like(item.get("rep_max"))
                if rep_max is not None and rep_max <= 8:
                    strength_rep_count += 1

            if compound_count == 0:
                add_issue(
                    issues,
                    "WARNING",
                    "STRENGTH_PLAN_WITHOUT_COMPOUND",
                    "Strength goal nhưng representative week không có compound exercise",
                    table=ITEM_SHEET,
                    plan_id=plan_id,
                )

            if strength_rep_count == 0:
                add_issue(
                    issues,
                    "WARNING",
                    "STRENGTH_PLAN_NO_LOW_MODERATE_REP_WORK",
                    "Strength goal nhưng không có rep prescription <= 8 trong representative week",
                    table=ITEM_SHEET,
                    plan_id=plan_id,
                )

        if primary_goal == "Muscular Endurance":
            endurance_items = 0

            for _, item in training_items.iterrows():
                rep_min = integer_like(item.get("rep_min"))
                if rep_min is not None and rep_min >= 12:
                    endurance_items += 1

            if endurance_items == 0:
                add_issue(
                    issues,
                    "WARNING",
                    "ENDURANCE_PLAN_WITHOUT_HIGHER_REP_WORK",
                    "Muscular Endurance goal nhưng không có higher-rep prescription rõ ràng",
                    table=ITEM_SHEET,
                    plan_id=plan_id,
                )


# ============================================================
# DATASET-LEVEL AI TRAINING QUALITY
# ============================================================

def validate_dataset_quality(
    issues: list[Issue],
    plans: pd.DataFrame,
    items: pd.DataFrame,
) -> dict[str, Any]:
    statistics: dict[str, Any] = {}

    if plans.empty:
        return statistics

    statistics["plan_count"] = int(len(plans))
    statistics["plan_item_count"] = int(len(items))

    for column in [
        "primary_goal_snapshot",
        "training_level_snapshot",
        "split_type",
        "generation_source",
    ]:
        if column in plans.columns:
            counts = plans[column].fillna("<EMPTY>").astype(str).value_counts()
            statistics[column] = counts.to_dict()

            if len(plans) >= 20 and not counts.empty:
                top_value = counts.index[0]
                top_count = int(counts.iloc[0])
                share = top_count / len(plans)

                if share >= 0.75:
                    add_issue(
                        issues,
                        "WARNING",
                        "PLAN_CLASS_IMBALANCE",
                        f"'{top_value}' chiếm {share:.1%} ở {column}",
                        table=PLAN_SHEET,
                        column=column,
                        value=top_value,
                    )

    if "exercise_id" in items.columns and len(items) >= 100:
        exercise_counts = items["exercise_id"].fillna("<EMPTY>").astype(str).value_counts()
        statistics["top_exercises"] = exercise_counts.head(20).to_dict()

        total_items = len(items)
        for exercise_id, count in exercise_counts.head(10).items():
            share = int(count) / total_items

            if share >= 0.20:
                add_issue(
                    issues,
                    "WARNING",
                    "EXERCISE_OVERREPRESENTATION",
                    f"{exercise_id} xuất hiện trong {share:.1%} plan items",
                    table=ITEM_SHEET,
                    exercise_id=exercise_id,
                    value=count,
                )

    # Exact / near duplicate plan composition
    if {"plan_id", "exercise_id"}.issubset(items.columns) and len(plans) >= 10:
        plan_signatures: dict[str, str] = {}
        plan_sequences: dict[str, list[str]] = {}

        for plan_id, group in items.groupby(items["plan_id"].astype(str)):
            sequence = [
                normalize_space(x)
                for x in group.sort_values(
                    ["week_number", "day_number", "exercise_order"],
                    kind="stable",
                )["exercise_id"].tolist()
            ]

            plan_sequences[str(plan_id)] = sequence
            signature = stable_fingerprint(sequence)

            if signature in plan_signatures:
                add_issue(
                    issues,
                    "WARNING",
                    "EXACT_DUPLICATE_PLAN",
                    f"Plan có exercise sequence giống hệt {plan_signatures[signature]}",
                    table=PLAN_SHEET,
                    plan_id=str(plan_id),
                )
            else:
                plan_signatures[signature] = str(plan_id)

        # Bounded pairwise comparison to avoid O(n²) explosion on huge datasets.
        plan_ids = list(plan_sequences)

        if len(plan_ids) <= 500:
            for i in range(len(plan_ids)):
                left_id = plan_ids[i]
                left = "|".join(plan_sequences[left_id])

                for j in range(i + 1, len(plan_ids)):
                    right_id = plan_ids[j]
                    right = "|".join(plan_sequences[right_id])

                    similarity = SequenceMatcher(None, left, right).ratio()

                    if similarity >= NEAR_DUPLICATE_PLAN_THRESHOLD:
                        add_issue(
                            issues,
                            "WARNING",
                            "NEAR_DUPLICATE_PLAN",
                            f"Plan rất giống {right_id} ({similarity:.0%})",
                            table=PLAN_SHEET,
                            plan_id=left_id,
                            value=right_id,
                        )

    return statistics


# ============================================================
# READINESS
# ============================================================

def compute_readiness(issues: list[Issue]) -> dict[str, Any]:
    schema_codes = {
        "MISSING_REQUIRED_COLUMN",
        "REQUIRED_VALUE_EMPTY",
        "JSON_ARRAY_INVALID",
        "JSON_ARRAY_NON_STRING",
        "INVALID_PLAN_ID",
        "INVALID_PLAN_ITEM_ID",
        "DUPLICATE_PLAN_ID",
        "DUPLICATE_PLAN_ITEM_ID",
        "INVALID_PLAN_DATE_RANGE",
        "INVALID_DURATION_WEEKS",
        "INVALID_DAYS_PER_WEEK",
        "INVALID_SETS",
        "INVALID_REP_RANGE",
    }

    reference_codes = {
        "UNKNOWN_USER_ID",
        "UNKNOWN_PLAN_ID",
        "UNKNOWN_EXERCISE_ID",
        "USER_SNAPSHOT_MISMATCH",
        "EXERCISE_SNAPSHOT_MISMATCH",
        "EXERCISE_ARRAY_SNAPSHOT_MISMATCH",
        "EXERCISE_ITEM_COUNT_MISMATCH",
    }

    safety_codes = {
        "TRAINING_LEVEL_MISMATCH",
        "EQUIPMENT_MISMATCH",
        "AVOIDED_EXERCISE_SELECTED",
        "AVOIDED_MUSCLE_CONFLICT",
        "POSSIBLE_INJURY_CONTRAINDICATION_CONFLICT",
        "HIGH_RISK_COMPLEX_EXERCISE_FOR_BEGINNER",
        "MEDICAL_CLEARANCE_REQUIRED",
        "NON_APPROVED_EXERCISE_IN_PLAN",
    }

    programming_codes = {
        "PLAN_WITHOUT_ITEMS",
        "NO_TRAINING_ITEMS_IN_REPRESENTATIVE_WEEK",
        "TRAINING_DAY_COUNT_MISMATCH",
        "FULL_BODY_WITHOUT_LOWER_BODY",
        "FULL_BODY_WITHOUT_UPPER_BODY",
        "PROGRESSION_RULE_MISSING_OR_THIN",
        "WEEKLY_SET_TARGET_MISMATCH",
        "SESSION_VOLUME_TARGET_MISMATCH",
    }

    error_codes = {issue.code for issue in issues if issue.severity == "ERROR"}

    schema_ready = not bool(error_codes & schema_codes)
    references_ready = not bool(error_codes & reference_codes)
    safety_ready = not bool(error_codes & safety_codes)
    programming_ready = not bool(error_codes & programming_codes)

    total_errors = sum(issue.severity == "ERROR" for issue in issues)

    return {
        "schema_ready": schema_ready,
        "references_ready": references_ready,
        "safety_ready": safety_ready,
        "programming_ready": programming_ready,
        "ai_training_ready": (
            schema_ready
            and references_ready
            and safety_ready
            and programming_ready
            and total_errors == 0
        ),
    }


# ============================================================
# REPORTING
# ============================================================

def issue_location(issue: Issue) -> str:
    parts: list[str] = []

    if issue.table:
        parts.append(issue.table)
    if issue.excel_row is not None:
        parts.append(f"dòng {issue.excel_row}")
    if issue.plan_id:
        parts.append(issue.plan_id)
    if issue.plan_item_id:
        parts.append(issue.plan_item_id)
    if issue.user_id:
        parts.append(issue.user_id)
    if issue.exercise_id:
        parts.append(issue.exercise_id)
    if issue.column:
        parts.append(issue.column)

    return " | ".join(parts)


def write_reports(
    issues: list[Issue],
    *,
    statistics: dict[str, Any],
    readiness: dict[str, Any],
    plan_count: int,
    item_count: int,
) -> None:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    severity_counts = Counter(issue.severity for issue in issues)
    code_counts = Counter(issue.code for issue in issues)

    lines: list[str] = []

    lines.append("=" * 88)
    lines.append("WORKOUT PLAN VALIDATION REPORT")
    lines.append("=" * 88)
    lines.append("")
    lines.append(f"Workout plans : {plan_count}")
    lines.append(f"Plan items    : {item_count}")
    lines.append(f"ERROR         : {severity_counts.get('ERROR', 0)}")
    lines.append(f"WARNING       : {severity_counts.get('WARNING', 0)}")
    lines.append(f"INFO          : {severity_counts.get('INFO', 0)}")
    lines.append("")
    lines.append("READINESS")
    lines.append("-" * 88)

    for key, value in readiness.items():
        lines.append(f"{key}: {'PASS' if value else 'FAIL'}")

    lines.append("")
    lines.append("ISSUE COUNTS")
    lines.append("-" * 88)

    if code_counts:
        for code, count in code_counts.most_common():
            lines.append(f"{code}: {count}")
    else:
        lines.append("Không phát hiện issue.")

    lines.append("")
    lines.append("CHI TIẾT")
    lines.append("-" * 88)

    if issues:
        for number, issue in enumerate(issues, start=1):
            location = issue_location(issue)
            location_text = f" ({location})" if location else ""

            lines.append(
                f"{number}. [{issue.severity}] {issue.code}{location_text}: "
                f"{issue.message}"
            )

            if issue.value:
                lines.append(f"    Giá trị: {issue.value}")
    else:
        lines.append("Không phát hiện lỗi/cảnh báo.")

    lines.append("")
    lines.append("DATASET STATISTICS")
    lines.append("-" * 88)
    lines.append(json.dumps(statistics, ensure_ascii=False, indent=2, default=str))
    lines.append("")
    lines.append("=" * 88)

    REPORT_FILE.write_text("\n".join(lines), encoding="utf-8")

    payload = {
        "summary": {
            "plan_count": plan_count,
            "item_count": item_count,
            "error_count": severity_counts.get("ERROR", 0),
            "warning_count": severity_counts.get("WARNING", 0),
            "info_count": severity_counts.get("INFO", 0),
        },
        "readiness": readiness,
        "issue_counts": dict(code_counts),
        "statistics": statistics,
        "issues": [issue.to_dict() for issue in issues],
    }

    REPORT_JSON_FILE.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )

    with ISSUES_CSV_FILE.open("w", encoding="utf-8-sig", newline="") as file:
        fieldnames = list(Issue.__dataclass_fields__.keys())
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()

        for issue in issues:
            writer.writerow(issue.to_dict())


# ============================================================
# MAIN VALIDATION PIPELINE
# ============================================================

def validate_workout_plan_dataset() -> int:
    issues: list[Issue] = []

    try:
        plans = load_sheet(WORKOUT_FILE, PLAN_SHEET)
        items = load_sheet(WORKOUT_FILE, ITEM_SHEET)
        _, users = load_user_master(issues)
        _, exercises = load_exercise_master(issues)
    except Exception as exc:
        print(f"[FATAL] {exc}")
        return 2

    validate_required_columns(
        issues, plans, PLAN_REQUIRED_COLUMNS, table=PLAN_SHEET
    )
    validate_required_columns(
        issues, items, ITEM_REQUIRED_COLUMNS, table=ITEM_SHEET
    )

    validate_plans(issues, plans, items, users)
    validate_items(issues, plans, items, users, exercises)
    validate_programming_quality(issues, plans, items, users, exercises)
    statistics = validate_dataset_quality(issues, plans, items)

    readiness = compute_readiness(issues)

    write_reports(
        issues,
        statistics=statistics,
        readiness=readiness,
        plan_count=len(plans),
        item_count=len(items),
    )

    error_count = sum(issue.severity == "ERROR" for issue in issues)
    warning_count = sum(issue.severity == "WARNING" for issue in issues)

    print("=" * 72)
    print("WORKOUT PLAN VALIDATION")
    print("=" * 72)
    print(f"Plans     : {len(plans)}")
    print(f"Plan items: {len(items)}")
    print(f"ERROR     : {error_count}")
    print(f"WARNING   : {warning_count}")
    print("")
    print(
        "Schema       :",
        "PASS" if readiness["schema_ready"] else "FAIL",
    )
    print(
        "References   :",
        "PASS" if readiness["references_ready"] else "FAIL",
    )
    print(
        "Safety       :",
        "PASS" if readiness["safety_ready"] else "FAIL",
    )
    print(
        "Programming  :",
        "PASS" if readiness["programming_ready"] else "FAIL",
    )
    print(
        "AI TRAIN READY:",
        "YES" if readiness["ai_training_ready"] else "NO",
    )
    print("")
    print(f"Report TXT : {REPORT_FILE}")
    print(f"Report JSON: {REPORT_JSON_FILE}")
    print(f"Issues CSV : {ISSUES_CSV_FILE}")
    print("=" * 72)

    return 1 if error_count > 0 else 0


if __name__ == "__main__":
    raise SystemExit(validate_workout_plan_dataset())
