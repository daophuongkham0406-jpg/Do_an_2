from __future__ import annotations

import csv
import json
import math
import re
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any

import pandas as pd


# ============================================================
# 1. ĐƯỜNG DẪN DỰ ÁN
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent
INPUT_FILE = PROJECT_ROOT / "master" / "user_master.xlsx"

REPORT_DIR = PROJECT_ROOT / "reports"
REPORT_TXT_FILE = REPORT_DIR / "user_validation_report.txt"
REPORT_JSON_FILE = REPORT_DIR / "user_validation_report.json"
ISSUES_CSV_FILE = REPORT_DIR / "user_validation_issues.csv"


# ============================================================
# 2. SCHEMA CỦA SHEET USER_PROFILE
# ============================================================

USER_SHEET = "User_Profile"
REFERENCE_SHEET = "Reference_Lists"
GOAL_MAPPING_SHEET = "Goal_Mapping"
DATA_DICTIONARY_SHEET = "Data_Dictionary"

REQUIRED_SHEETS = {
    USER_SHEET,
    REFERENCE_SHEET,
    GOAL_MAPPING_SHEET,
    DATA_DICTIONARY_SHEET,
}

REQUIRED_COLUMNS = [
    "user_id",
    "username",
    "gender",
    "age",
    "height_cm",
    "weight_kg",
    "body_fat_percent",
    "bmi",
    "primary_goal",
    "goal_filter_tags",
    "secondary_goal",
    "training_level",
    "training_experience_months",
    "training_days_per_week",
    "session_duration_minutes",
    "available_training_days",
    "available_equipment",
    "priority_muscles",
    "avoided_muscles",
    "preferred_exercise_types",
    "avoided_exercise_ids",
    "injuries_or_limitations",
    "medical_clearance_required",
    "preferred_split",
    "activity_level",
    "sleep_hours",
    "motivation_level",
    "gym_access_level",
    "progression_strategy",
    "profile_status",
    "created_at",
    "updated_at",
]

REQUIRED_VALUE_COLUMNS = {
    "user_id",
    "username",
    "gender",
    "age",
    "height_cm",
    "weight_kg",
    "bmi",
    "primary_goal",
    "goal_filter_tags",
    "training_level",
    "training_experience_months",
    "training_days_per_week",
    "session_duration_minutes",
    "available_training_days",
    "available_equipment",
    "medical_clearance_required",
    "activity_level",
    "gym_access_level",
    "profile_status",
    "created_at",
    "updated_at",
}

JSON_ARRAY_COLUMNS = {
    "goal_filter_tags",
    "available_training_days",
    "available_equipment",
    "priority_muscles",
    "avoided_muscles",
    "preferred_exercise_types",
    "avoided_exercise_ids",
    "injuries_or_limitations",
}

NON_EMPTY_ARRAY_COLUMNS = {
    "goal_filter_tags",
    "available_training_days",
    "available_equipment",
}

NUMERIC_RULES = {
    "age": (13, 100),
    "height_cm": (100, 250),
    "weight_kg": (25, 400),
    "body_fat_percent": (2, 70),
    "training_experience_months": (0, 600),
    "training_days_per_week": (1, 7),
    "session_duration_minutes": (15, 240),
    "sleep_hours": (0, 24),
}

INTEGER_COLUMNS = {
    "age",
    "training_experience_months",
    "training_days_per_week",
    "session_duration_minutes",
}

VALID_WEEKDAYS = {
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
    "Sunday",
}

USER_ID_PATTERN = re.compile(r"^U\d{6}$")
PLACEHOLDER_PATTERN = re.compile(
    r"^(?:n/?a|na|none|null|unknown|tbd|todo|test|sample|placeholder|-+)$",
    re.IGNORECASE,
)


# ============================================================
# 3. CẤU TRÚC MỘT LỖI
# ============================================================

@dataclass(slots=True)
class Issue:
    severity: str
    code: str
    message: str
    excel_row: int | None = None
    user_id: str = ""
    column: str = ""
    value: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# ============================================================
# 4. CÁC HÀM DÙNG CHUNG
# ============================================================

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
    if is_empty(value):
        return ""
    return re.sub(r"\s+", " ", str(value).strip())


def normalize_key(value: Any) -> str:
    return normalize_space(value).casefold()


def add_issue(
    issues: list[Issue],
    severity: str,
    code: str,
    message: str,
    *,
    excel_row: int | None = None,
    user_id: str = "",
    column: str = "",
    value: Any = "",
) -> None:
    issues.append(
        Issue(
            severity=severity,
            code=code,
            message=message,
            excel_row=excel_row,
            user_id=user_id,
            column=column,
            value="" if is_empty(value) else str(value)[:500],
        )
    )


def parse_json_array(value: Any) -> tuple[list[Any] | None, str]:
    if is_empty(value):
        return None, "Giá trị đang trống"

    if isinstance(value, list):
        return value, ""

    try:
        parsed = json.loads(str(value))
    except json.JSONDecodeError as error:
        return None, f"JSON không hợp lệ tại ký tự {error.pos}: {error.msg}"

    if not isinstance(parsed, list):
        return None, "Giá trị phải là JSON Array"

    return parsed, ""


def parse_date(value: Any) -> date | None:
    if is_empty(value):
        return None

    if isinstance(value, datetime):
        return value.date()

    if isinstance(value, date):
        return value

    parsed = pd.to_datetime(value, errors="coerce")

    if pd.isna(parsed):
        return None

    return parsed.date()


def read_reference_values(
    reference_df: pd.DataFrame,
    column: str,
) -> set[str]:
    if column not in reference_df.columns:
        return set()

    return {
        normalize_space(value)
        for value in reference_df[column]
        if not is_empty(value)
    }


# ============================================================
# 5. ĐỌC TAXONOMY TỪ REFERENCE_LISTS
# ============================================================

def build_taxonomies(reference_df: pd.DataFrame) -> dict[str, set[str]]:
    return {
        "gender": read_reference_values(reference_df, "gender"),
        "primary_goal": read_reference_values(reference_df, "primary_goal_ui"),
        "training_level": read_reference_values(reference_df, "training_level"),
        "preferred_split": read_reference_values(reference_df, "preferred_split"),
        "activity_level": read_reference_values(reference_df, "activity_level"),
        "motivation_level": read_reference_values(reference_df, "motivation_level"),
        "profile_status": read_reference_values(reference_df, "profile_status"),
        "gym_access_level": read_reference_values(reference_df, "gym_access_level"),
        "progression_strategy": read_reference_values(
            reference_df,
            "progression_strategy",
        ),
        "yes_no": read_reference_values(reference_df, "yes_no"),
        "canonical_goals": read_reference_values(
            reference_df,
            "canonical_recommended_goals",
        ),
        "canonical_equipment": read_reference_values(
            reference_df,
            "canonical_equipment",
        ),
        "canonical_muscles": read_reference_values(
            reference_df,
            "canonical_muscles",
        ),
        "exercise_ids": read_reference_values(reference_df, "exercise_id"),
    }


# ============================================================
# 6. KIỂM TRA JSON ARRAY
# ============================================================

def validate_json_array(
    issues: list[Issue],
    value: Any,
    *,
    excel_row: int,
    user_id: str,
    column: str,
) -> list[str]:
    parsed, error = parse_json_array(value)

    if parsed is None:
        severity = "ERROR" if column in NON_EMPTY_ARRAY_COLUMNS else "WARNING"

        add_issue(
            issues,
            severity,
            "JSON_ARRAY_INVALID",
            error,
            excel_row=excel_row,
            user_id=user_id,
            column=column,
            value=value,
        )
        return []

    if not parsed and column in NON_EMPTY_ARRAY_COLUMNS:
        add_issue(
            issues,
            "ERROR",
            "REQUIRED_ARRAY_EMPTY",
            "JSON Array bắt buộc không được rỗng",
            excel_row=excel_row,
            user_id=user_id,
            column=column,
            value=value,
        )

    cleaned: list[str] = []
    normalized_items: list[str] = []

    for position, item in enumerate(parsed, start=1):
        if not isinstance(item, str):
            add_issue(
                issues,
                "ERROR",
                "ARRAY_ITEM_NOT_STRING",
                f"Phần tử thứ {position} phải là chuỗi",
                excel_row=excel_row,
                user_id=user_id,
                column=column,
                value=item,
            )
            continue

        text = normalize_space(item)

        if not text:
            add_issue(
                issues,
                "ERROR",
                "ARRAY_ITEM_EMPTY",
                f"Phần tử thứ {position} đang rỗng",
                excel_row=excel_row,
                user_id=user_id,
                column=column,
            )
            continue

        cleaned.append(text)
        normalized_items.append(normalize_key(text))

    duplicates = sorted(
        item
        for item, count in Counter(normalized_items).items()
        if count > 1
    )

    if duplicates:
        add_issue(
            issues,
            "WARNING",
            "DUPLICATE_ARRAY_ITEMS",
            "Có phần tử trùng trong cùng JSON Array",
            excel_row=excel_row,
            user_id=user_id,
            column=column,
            value=", ".join(duplicates),
        )

    return cleaned


# ============================================================
# 7. KIỂM TRA SỐ
# ============================================================

def validate_numeric_value(
    issues: list[Issue],
    value: Any,
    *,
    excel_row: int,
    user_id: str,
    column: str,
    minimum: float,
    maximum: float,
) -> float | None:
    if is_empty(value):
        if column in REQUIRED_VALUE_COLUMNS:
            add_issue(
                issues,
                "ERROR",
                "REQUIRED_VALUE_EMPTY",
                "Giá trị bắt buộc đang trống",
                excel_row=excel_row,
                user_id=user_id,
                column=column,
            )
        return None

    try:
        number = float(value)
    except (TypeError, ValueError):
        add_issue(
            issues,
            "ERROR",
            "VALUE_NOT_NUMERIC",
            "Giá trị phải là số",
            excel_row=excel_row,
            user_id=user_id,
            column=column,
            value=value,
        )
        return None

    if not math.isfinite(number):
        add_issue(
            issues,
            "ERROR",
            "VALUE_NOT_FINITE",
            "Giá trị phải là số hữu hạn",
            excel_row=excel_row,
            user_id=user_id,
            column=column,
            value=value,
        )
        return None

    if number < minimum or number > maximum:
        add_issue(
            issues,
            "ERROR",
            "VALUE_OUT_OF_RANGE",
            f"Giá trị phải nằm trong khoảng {minimum}-{maximum}",
            excel_row=excel_row,
            user_id=user_id,
            column=column,
            value=value,
        )

    if column in INTEGER_COLUMNS and not number.is_integer():
        add_issue(
            issues,
            "ERROR",
            "INTEGER_REQUIRED",
            "Giá trị phải là số nguyên",
            excel_row=excel_row,
            user_id=user_id,
            column=column,
            value=value,
        )

    return number


# ============================================================
# 8. KIỂM TRA TAXONOMY
# ============================================================

def validate_enum(
    issues: list[Issue],
    value: Any,
    allowed_values: set[str],
    *,
    excel_row: int,
    user_id: str,
    column: str,
    required: bool,
) -> None:
    if is_empty(value):
        if required:
            add_issue(
                issues,
                "ERROR",
                "REQUIRED_VALUE_EMPTY",
                "Giá trị bắt buộc đang trống",
                excel_row=excel_row,
                user_id=user_id,
                column=column,
            )
        return

    text = normalize_space(value)

    if text not in allowed_values:
        add_issue(
            issues,
            "ERROR",
            "UNKNOWN_TAXONOMY_VALUE",
            "Giá trị không tồn tại trong Reference_Lists",
            excel_row=excel_row,
            user_id=user_id,
            column=column,
            value=text,
        )


def validate_array_taxonomy(
    issues: list[Issue],
    values: list[str],
    allowed_values: set[str],
    *,
    excel_row: int,
    user_id: str,
    column: str,
    error_code: str,
) -> None:
    for item in values:
        if item not in allowed_values:
            add_issue(
                issues,
                "ERROR",
                error_code,
                "Phần tử không tồn tại trong taxonomy chuẩn",
                excel_row=excel_row,
                user_id=user_id,
                column=column,
                value=item,
            )


# ============================================================
# 9. GHI BÁO CÁO
# ============================================================

def write_reports(
    issues: list[Issue],
    total_rows: int,
    dataframe: pd.DataFrame,
) -> None:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    severity_counts = Counter(issue.severity for issue in issues)
    code_counts = Counter(issue.code for issue in issues)

    completeness: dict[str, float] = {}

    for column in dataframe.columns:
        non_empty = sum(not is_empty(value) for value in dataframe[column])

        completeness[column] = round(
            (non_empty / total_rows * 100) if total_rows else 0,
            2,
        )

    summary = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "input_file": str(INPUT_FILE),
        "total_users": total_rows,
        "total_columns": len(dataframe.columns),
        "errors": severity_counts.get("ERROR", 0),
        "warnings": severity_counts.get("WARNING", 0),
        "info": severity_counts.get("INFO", 0),
        "issue_codes": dict(sorted(code_counts.items())),
        "column_completeness_percent": completeness,
        "dataset_ready": severity_counts.get("ERROR", 0) == 0,
    }

    text_lines = [
        "USER DATASET VALIDATION REPORT",
        "=" * 76,
        f"Thời gian: {summary['generated_at']}",
        f"File: {INPUT_FILE}",
        f"Tổng số user: {total_rows}",
        f"Tổng số cột: {len(dataframe.columns)}",
        f"Số ERROR: {summary['errors']}",
        f"Số WARNING: {summary['warnings']}",
        (
            "Trạng thái: ĐẠT"
            if summary["dataset_ready"]
            else "Trạng thái: CHƯA ĐẠT"
        ),
        "",
        "THỐNG KÊ THEO MÃ LỖI",
        "-" * 76,
    ]

    if code_counts:
        text_lines.extend(
            f"{code}: {count}"
            for code, count in sorted(code_counts.items())
        )
    else:
        text_lines.append("Không phát hiện vấn đề.")

    text_lines.extend(["", "CHI TIẾT", "-" * 76])

    if issues:
        for number, issue in enumerate(issues, start=1):
            location_parts: list[str] = []

            if issue.excel_row is not None:
                location_parts.append(f"dòng {issue.excel_row}")

            if issue.user_id:
                location_parts.append(issue.user_id)

            if issue.column:
                location_parts.append(issue.column)

            location = (
                f" ({' | '.join(location_parts)})"
                if location_parts
                else ""
            )

            text_lines.append(
                f"{number}. [{issue.severity}] "
                f"{issue.code}{location}: {issue.message}"
            )

            if issue.value:
                text_lines.append(f"    Giá trị: {issue.value}")
    else:
        text_lines.append("Không phát hiện lỗi hoặc cảnh báo.")

    text_lines.extend(["", "ĐỘ ĐẦY ĐỦ THEO CỘT", "-" * 76])

    for column, percent in completeness.items():
        text_lines.append(f"{column}: {percent:.2f}%")

    REPORT_TXT_FILE.write_text(
        "\n".join(text_lines),
        encoding="utf-8",
    )

    REPORT_JSON_FILE.write_text(
        json.dumps(
            {
                "summary": summary,
                "issues": [issue.to_dict() for issue in issues],
            },
            ensure_ascii=False,
            indent=2,
            default=str,
        ),
        encoding="utf-8",
    )

    with ISSUES_CSV_FILE.open(
        "w",
        encoding="utf-8-sig",
        newline="",
    ) as file:
        writer = csv.DictWriter(
            file,
            fieldnames=[
                "severity",
                "code",
                "message",
                "excel_row",
                "user_id",
                "column",
                "value",
            ],
        )

        writer.writeheader()

        for issue in issues:
            writer.writerow(issue.to_dict())


# ============================================================
# 10. HÀM KIỂM TRA CHÍNH
# ============================================================

def validate_user_dataset(input_file: Path | None = None) -> bool:
    global INPUT_FILE

    if input_file is not None:
        INPUT_FILE = Path(input_file)

    issues: list[Issue] = []

    if not INPUT_FILE.exists():
        raise FileNotFoundError(f"Không tìm thấy file:\n{INPUT_FILE}")

    workbook = pd.ExcelFile(INPUT_FILE)
    existing_sheets = set(workbook.sheet_names)

    for sheet_name in sorted(REQUIRED_SHEETS - existing_sheets):
        add_issue(
            issues,
            "ERROR",
            "MISSING_REQUIRED_SHEET",
            f"Thiếu sheet bắt buộc: {sheet_name}",
            column=sheet_name,
        )

    if USER_SHEET not in existing_sheets:
        empty_df = pd.DataFrame()
        write_reports(issues, 0, empty_df)
        return False

    user_df = pd.read_excel(
        INPUT_FILE,
        sheet_name=USER_SHEET,
        dtype=object,
    )

    user_df = user_df.dropna(how="all")
    user_df.columns = [
        normalize_space(column)
        for column in user_df.columns
    ]

    reference_df = (
        pd.read_excel(
            INPUT_FILE,
            sheet_name=REFERENCE_SHEET,
            dtype=object,
        ).dropna(how="all")
        if REFERENCE_SHEET in existing_sheets
        else pd.DataFrame()
    )

    goal_mapping_df = (
        pd.read_excel(
            INPUT_FILE,
            sheet_name=GOAL_MAPPING_SHEET,
            dtype=object,
        ).dropna(how="all")
        if GOAL_MAPPING_SHEET in existing_sheets
        else pd.DataFrame()
    )

    taxonomies = build_taxonomies(reference_df)

    goal_mapping: dict[str, list[str]] = {}

    if not goal_mapping_df.empty:
        for _, mapping_row in goal_mapping_df.iterrows():
            user_goal = normalize_space(mapping_row.get("user_goal", ""))

            if not user_goal:
                continue

            parsed, error = parse_json_array(
                mapping_row.get("exercise_goal_tags_json")
            )

            if parsed is None:
                add_issue(
                    issues,
                    "ERROR",
                    "GOAL_MAPPING_JSON_INVALID",
                    error,
                    column="exercise_goal_tags_json",
                    value=mapping_row.get("exercise_goal_tags_json"),
                )
                continue

            goal_mapping[user_goal] = [
                normalize_space(item)
                for item in parsed
                if isinstance(item, str) and normalize_space(item)
            ]

    # --------------------------------------------------------
    # 10.1 Kiểm tra schema
    # --------------------------------------------------------

    duplicate_columns = [
        column
        for column, count in Counter(user_df.columns).items()
        if count > 1
    ]

    for column in duplicate_columns:
        add_issue(
            issues,
            "ERROR",
            "DUPLICATE_COLUMN",
            "Tên cột bị trùng",
            column=column,
        )

    for column in REQUIRED_COLUMNS:
        if column not in user_df.columns:
            add_issue(
                issues,
                "ERROR",
                "MISSING_REQUIRED_COLUMN",
                f"Thiếu cột bắt buộc: {column}",
                column=column,
            )

    for column in user_df.columns:
        if column not in REQUIRED_COLUMNS:
            add_issue(
                issues,
                "INFO",
                "EXTRA_COLUMN",
                "Cột mở rộng không nằm trong schema chuẩn",
                column=column,
            )

    if "user_id" not in user_df.columns:
        write_reports(issues, len(user_df), user_df)
        return False

    # --------------------------------------------------------
    # 10.2 Kiểm tra từng dòng user
    # --------------------------------------------------------

    user_id_rows: dict[str, list[int]] = {}
    username_rows: dict[str, list[int]] = {}

    for index, row in user_df.iterrows():
        excel_row = index + 2
        user_id = normalize_space(row.get("user_id", ""))
        username = normalize_space(row.get("username", ""))

        user_id_rows.setdefault(normalize_key(user_id), []).append(excel_row)

        if username:
            username_rows.setdefault(
                normalize_key(username),
                [],
            ).append(excel_row)

        # User ID
        if not user_id:
            add_issue(
                issues,
                "ERROR",
                "USER_ID_EMPTY",
                "user_id đang trống",
                excel_row=excel_row,
                column="user_id",
            )
        elif not USER_ID_PATTERN.fullmatch(user_id):
            add_issue(
                issues,
                "ERROR",
                "INVALID_USER_ID",
                "user_id phải đúng dạng U000001",
                excel_row=excel_row,
                user_id=user_id,
                column="user_id",
                value=user_id,
            )

        # Required values
        for column in REQUIRED_VALUE_COLUMNS:
            if column not in user_df.columns:
                continue

            if is_empty(row.get(column)):
                add_issue(
                    issues,
                    "ERROR",
                    "REQUIRED_VALUE_EMPTY",
                    "Giá trị bắt buộc đang trống",
                    excel_row=excel_row,
                    user_id=user_id,
                    column=column,
                )

        # Placeholder and whitespace
        for column in user_df.columns:
            value = row.get(column)

            if is_empty(value):
                continue

            text = str(value)

            if text != text.strip() or re.search(r"\s{2,}", text):
                add_issue(
                    issues,
                    "WARNING",
                    "NON_CANONICAL_WHITESPACE",
                    "Có khoảng trắng thừa",
                    excel_row=excel_row,
                    user_id=user_id,
                    column=column,
                    value=value,
                )

            if (
                column not in JSON_ARRAY_COLUMNS
                and PLACEHOLDER_PATTERN.fullmatch(text.strip())
            ):
                add_issue(
                    issues,
                    "WARNING",
                    "PLACEHOLDER_VALUE",
                    "Giá trị có vẻ là dữ liệu tạm",
                    excel_row=excel_row,
                    user_id=user_id,
                    column=column,
                    value=value,
                )

        # Numeric fields
        numeric_values: dict[str, float | None] = {}

        for column, (minimum, maximum) in NUMERIC_RULES.items():
            if column not in user_df.columns:
                continue

            numeric_values[column] = validate_numeric_value(
                issues,
                row.get(column),
                excel_row=excel_row,
                user_id=user_id,
                column=column,
                minimum=minimum,
                maximum=maximum,
            )

        # BMI
        bmi_value = None

        if "bmi" in user_df.columns and not is_empty(row.get("bmi")):
            try:
                bmi_value = float(row.get("bmi"))

                if not math.isfinite(bmi_value) or bmi_value <= 0:
                    raise ValueError
            except (TypeError, ValueError):
                add_issue(
                    issues,
                    "ERROR",
                    "BMI_INVALID",
                    "BMI phải là số hữu hạn lớn hơn 0",
                    excel_row=excel_row,
                    user_id=user_id,
                    column="bmi",
                    value=row.get("bmi"),
                )
                bmi_value = None

        height = numeric_values.get("height_cm")
        weight = numeric_values.get("weight_kg")

        if height and weight and bmi_value is not None:
            calculated_bmi = weight / ((height / 100) ** 2)

            if abs(calculated_bmi - bmi_value) > 0.15:
                add_issue(
                    issues,
                    "ERROR",
                    "BMI_MISMATCH",
                    (
                        f"BMI không khớp. Giá trị đúng xấp xỉ "
                        f"{calculated_bmi:.2f}"
                    ),
                    excel_row=excel_row,
                    user_id=user_id,
                    column="bmi",
                    value=bmi_value,
                )

        # Enum fields
        enum_rules = {
            "gender": ("gender", True),
            "primary_goal": ("primary_goal", True),
            "secondary_goal": ("primary_goal", False),
            "training_level": ("training_level", True),
            "preferred_split": ("preferred_split", False),
            "activity_level": ("activity_level", True),
            "motivation_level": ("motivation_level", False),
            "gym_access_level": ("gym_access_level", True),
            "progression_strategy": ("progression_strategy", False),
            "profile_status": ("profile_status", True),
            "medical_clearance_required": ("yes_no", True),
        }

        for column, (taxonomy_name, required) in enum_rules.items():
            if column not in user_df.columns:
                continue

            validate_enum(
                issues,
                row.get(column),
                taxonomies.get(taxonomy_name, set()),
                excel_row=excel_row,
                user_id=user_id,
                column=column,
                required=required,
            )

        # JSON arrays
        arrays: dict[str, list[str]] = {}

        for column in JSON_ARRAY_COLUMNS:
            if column not in user_df.columns:
                continue

            arrays[column] = validate_json_array(
                issues,
                row.get(column),
                excel_row=excel_row,
                user_id=user_id,
                column=column,
            )

        # Taxonomy inside JSON arrays
        validate_array_taxonomy(
            issues,
            arrays.get("goal_filter_tags", []),
            taxonomies.get("canonical_goals", set()),
            excel_row=excel_row,
            user_id=user_id,
            column="goal_filter_tags",
            error_code="INVALID_GOAL_TAG",
        )

        validate_array_taxonomy(
            issues,
            arrays.get("available_equipment", []),
            taxonomies.get("canonical_equipment", set()),
            excel_row=excel_row,
            user_id=user_id,
            column="available_equipment",
            error_code="INVALID_EQUIPMENT",
        )

        validate_array_taxonomy(
            issues,
            arrays.get("priority_muscles", []),
            taxonomies.get("canonical_muscles", set()),
            excel_row=excel_row,
            user_id=user_id,
            column="priority_muscles",
            error_code="INVALID_PRIORITY_MUSCLE",
        )

        validate_array_taxonomy(
            issues,
            arrays.get("avoided_muscles", []),
            taxonomies.get("canonical_muscles", set()),
            excel_row=excel_row,
            user_id=user_id,
            column="avoided_muscles",
            error_code="INVALID_AVOIDED_MUSCLE",
        )

        validate_array_taxonomy(
            issues,
            arrays.get("avoided_exercise_ids", []),
            taxonomies.get("exercise_ids", set()),
            excel_row=excel_row,
            user_id=user_id,
            column="avoided_exercise_ids",
            error_code="INVALID_EXERCISE_REFERENCE",
        )

        validate_array_taxonomy(
            issues,
            arrays.get("available_training_days", []),
            VALID_WEEKDAYS,
            excel_row=excel_row,
            user_id=user_id,
            column="available_training_days",
            error_code="INVALID_WEEKDAY",
        )

        # Goal Mapping
        primary_goal = normalize_space(row.get("primary_goal", ""))
        expected_goal_tags = goal_mapping.get(primary_goal)

        if expected_goal_tags is not None:
            actual_tags = arrays.get("goal_filter_tags", [])

            if set(actual_tags) != set(expected_goal_tags):
                add_issue(
                    issues,
                    "ERROR",
                    "GOAL_MAPPING_MISMATCH",
                    (
                        "goal_filter_tags không khớp với "
                        "Goal_Mapping của primary_goal"
                    ),
                    excel_row=excel_row,
                    user_id=user_id,
                    column="goal_filter_tags",
                    value=json.dumps(actual_tags, ensure_ascii=False),
                )

        # Logic: số ngày
        training_days = numeric_values.get("training_days_per_week")
        available_days = arrays.get("available_training_days", [])

        if (
            training_days is not None
            and training_days > len(set(available_days))
        ):
            add_issue(
                issues,
                "ERROR",
                "INSUFFICIENT_AVAILABLE_DAYS",
                (
                    "training_days_per_week lớn hơn số ngày khả dụng "
                    "trong available_training_days"
                ),
                excel_row=excel_row,
                user_id=user_id,
                column="training_days_per_week",
                value=training_days,
            )

        # Logic: goal chính và phụ không trùng
        secondary_goal = normalize_space(row.get("secondary_goal", ""))

        if (
            primary_goal
            and secondary_goal
            and primary_goal == secondary_goal
        ):
            add_issue(
                issues,
                "WARNING",
                "DUPLICATE_PRIMARY_SECONDARY_GOAL",
                "primary_goal và secondary_goal đang giống nhau",
                excel_row=excel_row,
                user_id=user_id,
                column="secondary_goal",
                value=secondary_goal,
            )

        # Logic: priority và avoided muscle không trùng
        priority_set = {
            normalize_key(item)
            for item in arrays.get("priority_muscles", [])
        }

        avoided_set = {
            normalize_key(item)
            for item in arrays.get("avoided_muscles", [])
        }

        overlap = sorted(priority_set & avoided_set)

        if overlap:
            add_issue(
                issues,
                "ERROR",
                "MUSCLE_PREFERENCE_CONFLICT",
                "Cùng một nhóm cơ vừa được ưu tiên vừa bị tránh",
                excel_row=excel_row,
                user_id=user_id,
                column="priority_muscles",
                value=", ".join(overlap),
            )

        # Logic: level và kinh nghiệm
        level = normalize_space(row.get("training_level", ""))
        experience = numeric_values.get("training_experience_months")

        if experience is not None:
            if level == "Advanced" and experience < 24:
                add_issue(
                    issues,
                    "WARNING",
                    "LEVEL_EXPERIENCE_MISMATCH",
                    "Advanced nhưng kinh nghiệm dưới 24 tháng",
                    excel_row=excel_row,
                    user_id=user_id,
                    column="training_level",
                    value=experience,
                )

            if level == "Intermediate" and experience < 4:
                add_issue(
                    issues,
                    "WARNING",
                    "LEVEL_EXPERIENCE_MISMATCH",
                    "Intermediate nhưng kinh nghiệm dưới 4 tháng",
                    excel_row=excel_row,
                    user_id=user_id,
                    column="training_level",
                    value=experience,
                )

            if level == "Beginner" and experience > 36:
                add_issue(
                    issues,
                    "WARNING",
                    "LEVEL_EXPERIENCE_MISMATCH",
                    "Beginner nhưng kinh nghiệm trên 36 tháng",
                    excel_row=excel_row,
                    user_id=user_id,
                    column="training_level",
                    value=experience,
                )

        # Logic: ngày tạo và ngày cập nhật
        created_at = parse_date(row.get("created_at"))
        updated_at = parse_date(row.get("updated_at"))

        if created_at is None:
            add_issue(
                issues,
                "ERROR",
                "INVALID_CREATED_DATE",
                "created_at trống hoặc không đọc được",
                excel_row=excel_row,
                user_id=user_id,
                column="created_at",
                value=row.get("created_at"),
            )

        if updated_at is None:
            add_issue(
                issues,
                "ERROR",
                "INVALID_UPDATED_DATE",
                "updated_at trống hoặc không đọc được",
                excel_row=excel_row,
                user_id=user_id,
                column="updated_at",
                value=row.get("updated_at"),
            )

        if created_at and updated_at and updated_at < created_at:
            add_issue(
                issues,
                "ERROR",
                "UPDATED_BEFORE_CREATED",
                "updated_at không được nhỏ hơn created_at",
                excel_row=excel_row,
                user_id=user_id,
                column="updated_at",
                value=updated_at,
            )

    # --------------------------------------------------------
    # 10.3 Kiểm tra trùng toàn dataset
    # --------------------------------------------------------

    for user_id_key, rows in user_id_rows.items():
        if user_id_key and len(rows) > 1:
            add_issue(
                issues,
                "ERROR",
                "DUPLICATE_USER_ID",
                f"user_id bị trùng tại các dòng: {rows}",
                user_id=user_id_key,
            )

    for username_key, rows in username_rows.items():
        if username_key and len(rows) > 1:
            add_issue(
                issues,
                "WARNING",
                "DUPLICATE_USERNAME",
                f"username bị trùng tại các dòng: {rows}",
                value=username_key,
            )

    duplicate_full_rows = user_df.astype(str).duplicated(keep=False)

    for index in user_df.index[duplicate_full_rows]:
        add_issue(
            issues,
            "ERROR",
            "DUPLICATE_FULL_ROW",
            "Toàn bộ bản ghi bị trùng với bản ghi khác",
            excel_row=index + 2,
            user_id=normalize_space(user_df.at[index, "user_id"]),
        )

    # --------------------------------------------------------
    # 10.4 Missing rate
    # --------------------------------------------------------

    total_rows = len(user_df)

    for column in user_df.columns:
        missing_count = sum(
            is_empty(value)
            for value in user_df[column]
        )

        ratio = (
            missing_count / total_rows
            if total_rows
            else 0
        )

        if ratio >= 0.20:
            severity = (
                "ERROR"
                if column in REQUIRED_VALUE_COLUMNS
                else "WARNING"
            )

            add_issue(
                issues,
                severity,
                "HIGH_MISSING_RATE",
                (
                    f"Cột có tỷ lệ thiếu {ratio:.1%} "
                    f"({missing_count}/{total_rows})"
                ),
                column=column,
            )

    write_reports(issues, total_rows, user_df)

    error_count = sum(
        issue.severity == "ERROR"
        for issue in issues
    )

    warning_count = sum(
        issue.severity == "WARNING"
        for issue in issues
    )

    print("=" * 60)
    print("KẾT QUẢ KIỂM TRA USER DATASET")
    print("=" * 60)
    print(f"Tổng user: {total_rows}")
    print(f"ERROR: {error_count}")
    print(f"WARNING: {warning_count}")
    print(f"Báo cáo TXT: {REPORT_TXT_FILE}")
    print(f"Báo cáo JSON: {REPORT_JSON_FILE}")
    print(f"Danh sách lỗi CSV: {ISSUES_CSV_FILE}")

    if error_count:
        print("Trạng thái: CHƯA ĐẠT")
        return False

    print("Trạng thái: ĐẠT")
    return True


if __name__ == "__main__":
    validate_user_dataset()
