from __future__ import annotations

import argparse
import csv
import json
import math
import re
import sys
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd


ROOT = Path(__file__).resolve().parent
MASTER = ROOT / "master"
DOCS = ROOT / "docs"
DEFAULT_REPORT_DIR = ROOT / "reports" / "stage_3_validation"


@dataclass
class Issue:
    severity: str
    rule_id: str
    domain: str
    file: str
    sheet: str
    row: int | str
    column: str
    value: str
    message: str
    suggestion: str


class ValidationContext:
    def __init__(self) -> None:
        self.issues: list[Issue] = []
        self.metrics: dict[str, Any] = {}
        self.relationship_results: list[dict[str, Any]] = []
        self.cross_results: list[dict[str, Any]] = []

    def add(
        self,
        severity: str,
        rule_id: str,
        domain: str,
        file: str,
        sheet: str,
        row: int | str,
        column: str,
        value: Any,
        message: str,
        suggestion: str,
    ) -> None:
        self.issues.append(
            Issue(
                severity=severity,
                rule_id=rule_id,
                domain=domain,
                file=file,
                sheet=sheet,
                row=row,
                column=column,
                value="" if value is None else str(value),
                message=message,
                suggestion=suggestion,
            )
        )


TABLES = {
    "Exercise_Master": ("exercise", "gym_exercise_dataset", "exercise_id", "Exercise"),
    "User_Profile": ("user", "User_Profile", "user_id", "User"),
    "Workout_Plan": ("plan", "Workout_Plan", "plan_id", "Workout Plan"),
    "Workout_Plan_Items": ("plan", "Workout_Plan_Items", "plan_item_id", "Workout Plan"),
    "Workout_History_Sessions": ("history", "Workout_History_Sessions", "history_session_id", "Workout History"),
    "Workout_History_Items": ("history", "Workout_History_Items", "history_item_id", "Workout History"),
    "Workout_History_Summary": ("history", "Workout_History_Summary", "summary_id", "Workout History"),
    "User_Feedback": ("feedback", "User_Feedback", "feedback_id", "User Feedback"),
}

RELATIONSHIPS = [
    ("REL_001", "Workout_Plan", "user_id", "User_Profile", "user_id", True),
    ("REL_002", "Workout_Plan_Items", "plan_id", "Workout_Plan", "plan_id", True),
    ("REL_003", "Workout_Plan_Items", "exercise_id", "Exercise_Master", "exercise_id", True),
    ("REL_004", "Workout_History_Sessions", "user_id", "User_Profile", "user_id", True),
    ("REL_005", "Workout_History_Sessions", "plan_id", "Workout_Plan", "plan_id", True),
    ("REL_006", "Workout_History_Items", "history_session_id", "Workout_History_Sessions", "history_session_id", True),
    ("REL_007", "Workout_History_Items", "user_id", "User_Profile", "user_id", True),
    ("REL_008", "Workout_History_Items", "plan_id", "Workout_Plan", "plan_id", True),
    ("REL_009", "Workout_History_Items", "plan_item_id", "Workout_Plan_Items", "plan_item_id", True),
    ("REL_010", "Workout_History_Items", "exercise_id", "Exercise_Master", "exercise_id", True),
    ("REL_011", "Workout_History_Summary", "user_id", "User_Profile", "user_id", True),
    ("REL_012", "Workout_History_Summary", "plan_id", "Workout_Plan", "plan_id", True),
    ("REL_013", "User_Feedback", "user_id", "User_Profile", "user_id", True),
    ("REL_014", "User_Feedback", "plan_id", "Workout_Plan", "plan_id", False),
    ("REL_015", "User_Feedback", "history_session_id", "Workout_History_Sessions", "history_session_id", False),
    ("REL_016", "User_Feedback", "history_item_id", "Workout_History_Items", "history_item_id", False),
    ("REL_017", "User_Feedback", "plan_item_id", "Workout_Plan_Items", "plan_item_id", False),
    ("REL_018", "User_Feedback", "exercise_id", "Exercise_Master", "exercise_id", False),
]

CROSS_RULES = [
    ("CROSS_001", "Workout_History_Items", "history_session_id", "user_id", "Workout_History_Sessions", "history_session_id", "user_id"),
    ("CROSS_002", "Workout_History_Items", "history_session_id", "plan_id", "Workout_History_Sessions", "history_session_id", "plan_id"),
    ("CROSS_003", "Workout_History_Items", "plan_item_id", "plan_id", "Workout_Plan_Items", "plan_item_id", "plan_id"),
    ("CROSS_004", "Workout_History_Items", "plan_item_id", "exercise_id", "Workout_Plan_Items", "plan_item_id", "exercise_id"),
    ("CROSS_005", "Workout_History_Summary", "plan_id", "user_id", "Workout_Plan", "plan_id", "user_id"),
    ("CROSS_006", "User_Feedback", "history_item_id", "user_id", "Workout_History_Items", "history_item_id", "user_id"),
    ("CROSS_007", "User_Feedback", "history_item_id", "plan_id", "Workout_History_Items", "history_item_id", "plan_id"),
    ("CROSS_008", "User_Feedback", "history_item_id", "plan_item_id", "Workout_History_Items", "history_item_id", "plan_item_id"),
    ("CROSS_009", "User_Feedback", "history_item_id", "exercise_id", "Workout_History_Items", "history_item_id", "exercise_id"),
    ("CROSS_010", "User_Feedback", "history_session_id", "user_id", "Workout_History_Sessions", "history_session_id", "user_id"),
    ("CROSS_011", "User_Feedback", "history_session_id", "plan_id", "Workout_History_Sessions", "history_session_id", "plan_id"),
    ("CROSS_012", "User_Feedback", "plan_item_id", "plan_id", "Workout_Plan_Items", "plan_item_id", "plan_id"),
    ("CROSS_013", "User_Feedback", "plan_item_id", "exercise_id", "Workout_Plan_Items", "plan_item_id", "exercise_id"),
]


def resolve_path(value: str | None, default: Path) -> Path:
    if not value:
        return default
    p = Path(value)
    if p.is_absolute():
        return p
    if p.exists():
        return p.resolve()
    if (MASTER / p).exists():
        return (MASTER / p).resolve()
    if (DOCS / p).exists():
        return (DOCS / p).resolve()
    return (ROOT / p).resolve()


def clean(v: Any) -> str:
    if v is None:
        return ""
    if isinstance(v, float) and math.isnan(v):
        return ""
    return str(v).strip()


def num(v: Any) -> float | None:
    s = clean(v)
    if not s:
        return None
    try:
        return float(s)
    except ValueError:
        return None


def is_true(v: Any) -> bool:
    return clean(v).lower() in {"true", "1", "yes", "y"}


def approx(a: Any, b: Any, tol: float = 0.2) -> bool:
    x, y = num(a), num(b)
    return x is not None and y is not None and abs(x - y) <= tol


def pct(n: int | float, d: int | float) -> float:
    return 0.0 if not d else round(float(n) * 100.0 / float(d), 3)


def parse_list(value: Any) -> list[str] | None:
    s = clean(value)
    if not s or s in {"[]", "None", "null"}:
        return []
    if s.startswith("[") and s.endswith("]"):
        try:
            data = json.loads(s)
            return [clean(x) for x in data] if isinstance(data, list) else None
        except Exception:
            inner = s[1:-1].strip()
            if not inner:
                return []
            return [x.strip().strip("'\"") for x in inner.split(",") if x.strip()]
    if ";" in s:
        return [x.strip() for x in s.split(";") if x.strip()]
    if "|" in s:
        return [x.strip() for x in s.split("|") if x.strip()]
    if "," in s:
        return [x.strip() for x in s.split(",") if x.strip()]
    return [s]


def read_sheet(path: Path, sheet: str, ctx: ValidationContext, domain: str) -> pd.DataFrame:
    try:
        df = pd.read_excel(path, sheet_name=sheet, dtype=str, engine="openpyxl").fillna("")
        df.columns = [clean(c) for c in df.columns]
        return df
    except FileNotFoundError:
        ctx.add("ERROR", "FILE_001", domain, str(path), sheet, "-", "-", "", "Input file không tồn tại", "Kiểm tra lại đường dẫn file.")
    except ValueError:
        ctx.add("ERROR", "SHEET_001", domain, str(path), sheet, "-", "-", "", "Sheet bắt buộc không tồn tại", "Kiểm tra tên sheet trong workbook.")
    except Exception as exc:
        ctx.add("ERROR", "LOAD_001", domain, str(path), sheet, "-", "-", "", f"Không đọc được sheet: {exc}", "Kiểm tra workbook có bị khóa/hỏng không.")
    return pd.DataFrame()


def load_workbooks(args: argparse.Namespace, ctx: ValidationContext) -> dict[str, Any]:
    paths = {
        "exercise": resolve_path(args.exercise_master, MASTER / "exercise_master.xlsx"),
        "user": resolve_path(args.user_master, MASTER / "user_master.xlsx"),
        "plan": resolve_path(args.plan_master, MASTER / "workout_plan_master.xlsx"),
        "history": resolve_path(args.history_master, MASTER / "workout_history_master.xlsx"),
        "feedback": resolve_path(args.feedback_master, MASTER / "user_feedback_master.xlsx"),
        "stage2_design": resolve_path(args.stage2_design, DOCS / "stage_2_data_relationship_design.md"),
        "relationship_matrix": resolve_path(args.relationship_matrix, DOCS / "relationship_matrix.xlsx"),
        "relationship_rules": resolve_path(args.relationship_rules, DOCS / "relationship_validation_rules.md"),
        "ai_usage_map": resolve_path(args.ai_usage_map, DOCS / "ai_data_usage_map.md"),
    }
    frames = {
        "Exercise_Master": read_sheet(paths["exercise"], "gym_exercise_dataset", ctx, "Exercise"),
        "User_Profile": read_sheet(paths["user"], "User_Profile", ctx, "User"),
        "Workout_Plan": read_sheet(paths["plan"], "Workout_Plan", ctx, "Workout Plan"),
        "Workout_Plan_Items": read_sheet(paths["plan"], "Workout_Plan_Items", ctx, "Workout Plan"),
        "Workout_History_Sessions": read_sheet(paths["history"], "Workout_History_Sessions", ctx, "Workout History"),
        "Workout_History_Items": read_sheet(paths["history"], "Workout_History_Items", ctx, "Workout History"),
        "Workout_History_Summary": read_sheet(paths["history"], "Workout_History_Summary", ctx, "Workout History"),
        "User_Feedback": read_sheet(paths["feedback"], "User_Feedback", ctx, "User Feedback"),
    }
    return {"paths": paths, "frames": frames}


def file_for(table: str, paths: dict[str, Path]) -> str:
    key = TABLES[table][0]
    return paths[key].name


def require_columns(ctx: ValidationContext, df: pd.DataFrame, table: str, columns: list[str], paths: dict[str, Path], domain: str, severity: str = "ERROR") -> None:
    for col in columns:
        if col not in df.columns:
            ctx.add(severity, "SCHEMA_001", domain, file_for(table, paths), TABLES[table][1], "-", col, "", "Cột bắt buộc/quan trọng không tồn tại", "Bổ sung cột hoặc cập nhật validator nếu schema đã đổi có chủ đích.")


def first_existing(df: pd.DataFrame, candidates: list[str]) -> str | None:
    for col in candidates:
        if col in df.columns:
            return col
    return None


def check_pk(ctx: ValidationContext, df: pd.DataFrame, table: str, paths: dict[str, Path], rule_prefix: str) -> None:
    pk = TABLES[table][2]
    domain = TABLES[table][3]
    if pk not in df.columns:
        ctx.add("ERROR", f"{rule_prefix}_PK_SCHEMA", domain, file_for(table, paths), TABLES[table][1], "-", pk, "", "Primary key column không tồn tại", "Bổ sung primary key column.")
        return
    blank = df.index[df[pk].map(clean) == ""].tolist()
    for i in blank[:50]:
        ctx.add("ERROR", f"{rule_prefix}_001", domain, file_for(table, paths), TABLES[table][1], int(i) + 2, pk, "", "Primary key không được blank", "Điền ID hợp lệ.")
    dup_mask = df[pk].map(clean).duplicated(keep=False) & (df[pk].map(clean) != "")
    for i in df.index[dup_mask].tolist()[:50]:
        ctx.add("ERROR", f"{rule_prefix}_002", domain, file_for(table, paths), TABLES[table][1], int(i) + 2, pk, df.at[i, pk], "Primary key bị trùng", "Tạo ID duy nhất.")


def validate_exercise_master(ctx: ValidationContext, data: dict[str, Any]) -> None:
    df, paths = data["frames"]["Exercise_Master"], data["paths"]
    require_columns(ctx, df, "Exercise_Master", ["exercise_id", "exercise_name", "aliases", "category", "movement_pattern", "equipment", "primary_muscles", "secondary_muscles", "recommended_goals", "contraindications", "execution_steps", "common_mistakes", "cues", "progressions", "regressions", "alternatives", "met_value"], paths, "Exercise")
    difficulty_col = first_existing(df, ["difficulty_level", "minimum_training_level"])
    if difficulty_col is None:
        ctx.add("ERROR", "SCHEMA_001", "Exercise", paths["exercise"].name, "gym_exercise_dataset", "-", "difficulty_level/minimum_training_level", "", "Không tìm thấy cột difficulty alias", "Bổ sung difficulty_level hoặc minimum_training_level.")
    check_pk(ctx, df, "Exercise_Master", paths, "EXE")
    valid_difficulty = {"Beginner", "Novice", "Intermediate", "Advanced", "Expert", "All Levels"}
    for i, r in df.iterrows():
        row = int(i) + 2
        if clean(r.get("exercise_name")) == "":
            ctx.add("ERROR", "EXE_003", "Exercise", paths["exercise"].name, "gym_exercise_dataset", row, "exercise_name", "", "exercise_name không được blank", "Điền tên bài tập.")
        if clean(r.get("category")) == "":
            ctx.add("ERROR", "EXE_004", "Exercise", paths["exercise"].name, "gym_exercise_dataset", row, "category", "", "category không được blank", "Gán category hợp lệ.")
        if difficulty_col and clean(r.get(difficulty_col)) not in valid_difficulty:
            ctx.add("WARNING", "EXE_005", "Exercise", paths["exercise"].name, "gym_exercise_dataset", row, difficulty_col, r.get(difficulty_col), "difficulty/minimum_training_level ngoài taxonomy phổ biến", "Kiểm tra lại taxonomy difficulty.")
        for col, rule in [("primary_muscles", "EXE_006"), ("equipment", "EXE_007"), ("recommended_goals", "EXE_008"), ("contraindications", "EXE_009"), ("alternatives", "EXE_014")]:
            if col in df.columns and parse_list(r.get(col)) is None:
                ctx.add("ERROR", rule, "Exercise", paths["exercise"].name, "gym_exercise_dataset", row, col, r.get(col), "Giá trị phải là JSON array hoặc list hợp lệ", "Chuẩn hóa thành JSON/list.")
        for col, rule in [("execution_steps", "EXE_010"), ("common_mistakes", "EXE_011"), ("cues", "EXE_012")]:
            if col in df.columns and len(parse_list(r.get(col)) or []) == 0:
                ctx.add("WARNING", rule, "Exercise", paths["exercise"].name, "gym_exercise_dataset", row, col, "", f"{col} không nên rỗng", "Bổ sung nội dung để AI coach dùng được.")
        met = num(r.get("met_value"))
        if met is not None and not 1 <= met <= 20:
            ctx.add("WARNING", "EXE_013", "Exercise", paths["exercise"].name, "gym_exercise_dataset", row, "met_value", r.get("met_value"), "met_value ngoài khoảng hợp lý", "Kiểm tra MET.")


def validate_user_master(ctx: ValidationContext, data: dict[str, Any]) -> None:
    df, paths = data["frames"]["User_Profile"], data["paths"]
    require_columns(ctx, df, "User_Profile", ["user_id", "age", "gender", "height_cm", "weight_kg", "bmi", "primary_goal", "secondary_goal", "training_level", "training_days_per_week", "available_equipment", "preferred_split", "session_duration_minutes", "injuries_or_limitations", "avoided_exercise_ids", "created_at"], paths, "User")
    check_pk(ctx, df, "User_Profile", paths, "USR")
    for i, r in df.iterrows():
        row = int(i) + 2
        age, height, weight, bmi = num(r.get("age")), num(r.get("height_cm")), num(r.get("weight_kg")), num(r.get("bmi"))
        if age is None or not 13 <= age <= 90:
            ctx.add("ERROR", "USR_003", "User", paths["user"].name, "User_Profile", row, "age", r.get("age"), "age ngoài khoảng hợp lý", "Điền tuổi 13..90.")
        if height is None or not 120 <= height <= 230:
            ctx.add("ERROR", "USR_004", "User", paths["user"].name, "User_Profile", row, "height_cm", r.get("height_cm"), "height_cm ngoài khoảng hợp lý", "Điền chiều cao 120..230 cm.")
        if weight is None or not 30 <= weight <= 250:
            ctx.add("ERROR", "USR_005", "User", paths["user"].name, "User_Profile", row, "weight_kg", r.get("weight_kg"), "weight_kg ngoài khoảng hợp lý", "Điền cân nặng 30..250 kg.")
        if height and weight and bmi and not approx(bmi, weight / ((height / 100.0) ** 2), 0.3):
            ctx.add("ERROR", "USR_006", "User", paths["user"].name, "User_Profile", row, "bmi", r.get("bmi"), "bmi không khớp height/weight", "Tính lại BMI.")
        if clean(r.get("primary_goal")) == "":
            ctx.add("ERROR", "USR_007", "User", paths["user"].name, "User_Profile", row, "primary_goal", "", "primary_goal không được blank", "Điền mục tiêu chính.")
        if clean(r.get("training_level")) == "":
            ctx.add("ERROR", "USR_008", "User", paths["user"].name, "User_Profile", row, "training_level", "", "training_level không được blank", "Điền trình độ.")
        days = num(r.get("training_days_per_week"))
        if days is None or not 1 <= days <= 7:
            ctx.add("ERROR", "USR_009", "User", paths["user"].name, "User_Profile", row, "training_days_per_week", r.get("training_days_per_week"), "training_days_per_week phải từ 1..7", "Sửa số ngày tập.")
        for col, rule in [("available_equipment", "USR_010"), ("injuries_or_limitations", "USR_011"), ("avoided_exercise_ids", "USR_012"), ("preferred_exercise_ids", "USR_013")]:
            if col in df.columns and parse_list(r.get(col)) is None:
                ctx.add("ERROR", rule, "User", paths["user"].name, "User_Profile", row, col, r.get(col), "Giá trị phải là JSON array/list hợp lệ", "Chuẩn hóa list.")
        dur = num(r.get("session_duration_minutes"))
        if dur is None or not 10 <= dur <= 180:
            ctx.add("ERROR", "USR_015", "User", paths["user"].name, "User_Profile", row, "session_duration_minutes", r.get("session_duration_minutes"), "session_duration_minutes không hợp lý", "Điền 10..180 phút.")


def validate_workout_plan_master(ctx: ValidationContext, data: dict[str, Any]) -> None:
    frames, paths = data["frames"], data["paths"]
    plans, items = frames["Workout_Plan"], frames["Workout_Plan_Items"]
    require_columns(ctx, plans, "Workout_Plan", ["plan_id", "user_id", "primary_goal_snapshot", "training_level_snapshot", "days_per_week", "session_duration_target_min", "plan_status", "progression_strategy", "created_at"], paths, "Workout Plan")
    require_columns(ctx, items, "Workout_Plan_Items", ["plan_item_id", "plan_id", "exercise_id", "exercise_name_snapshot", "week_number", "day_number", "day_name", "exercise_order", "sets", "rep_min", "rep_max", "target_intensity", "rest_seconds"], paths, "Workout Plan")
    check_pk(ctx, plans, "Workout_Plan", paths, "PLAN")
    check_pk(ctx, items, "Workout_Plan_Items", paths, "PLAN_ITEM")
    plan_ids = set(plans.get("plan_id", pd.Series(dtype=str)).map(clean))
    exercise_ids = set(frames["Exercise_Master"].get("exercise_id", pd.Series(dtype=str)).map(clean))
    item_counts = Counter(items.get("plan_id", pd.Series(dtype=str)).map(clean))
    for i, r in plans.iterrows():
        row = int(i) + 2
        if item_counts.get(clean(r.get("plan_id")), 0) == 0:
            ctx.add("ERROR", "PLAN_004", "Workout Plan", paths["plan"].name, "Workout_Plan", row, "plan_id", r.get("plan_id"), "Plan không có plan item", "Bổ sung Workout_Plan_Items.")
        days = num(r.get("days_per_week"))
        if days is None or not 1 <= days <= 7:
            ctx.add("ERROR", "PLAN_020", "Workout Plan", paths["plan"].name, "Workout_Plan", row, "days_per_week", r.get("days_per_week"), "days_per_week phải từ 1..7", "Sửa số ngày/tuần.")
    seen_order: set[tuple[str, str, str, str]] = set()
    for i, r in items.iterrows():
        row = int(i) + 2
        pid, eid = clean(r.get("plan_id")), clean(r.get("exercise_id"))
        if pid not in plan_ids:
            ctx.add("ERROR", "PLAN_007", "Workout Plan", paths["plan"].name, "Workout_Plan_Items", row, "plan_id", pid, "plan_id không tồn tại trong Workout_Plan", "Sửa FK plan_id.")
        if eid not in exercise_ids:
            ctx.add("ERROR", "PLAN_008", "Workout Plan", paths["plan"].name, "Workout_Plan_Items", row, "exercise_id", eid, "exercise_id không tồn tại trong Exercise_Master", "Sửa FK exercise_id.")
        sets, rep_min, rep_max, rpe, rest = num(r.get("sets")), num(r.get("rep_min")), num(r.get("rep_max")), num(r.get("target_intensity")), num(r.get("rest_seconds"))
        if sets is None or sets <= 0:
            ctx.add("ERROR", "PLAN_009", "Workout Plan", paths["plan"].name, "Workout_Plan_Items", row, "sets", r.get("sets"), "sets phải > 0", "Sửa sets.")
        if rep_min is None or rep_max is None or rep_min > rep_max:
            ctx.add("ERROR", "PLAN_010", "Workout Plan", paths["plan"].name, "Workout_Plan_Items", row, "rep_min/rep_max", f"{r.get('rep_min')}/{r.get('rep_max')}", "rep_min phải <= rep_max", "Sửa reps.")
        if rpe is not None and not 1 <= rpe <= 10:
            ctx.add("ERROR", "PLAN_011", "Workout Plan", paths["plan"].name, "Workout_Plan_Items", row, "target_intensity", r.get("target_intensity"), "target_intensity phải trong 1..10 nếu là RPE", "Sửa intensity.")
        if rest is None or not 0 <= rest <= 900:
            ctx.add("ERROR", "PLAN_012", "Workout Plan", paths["plan"].name, "Workout_Plan_Items", row, "rest_seconds", r.get("rest_seconds"), "rest_seconds không hợp lý", "Sửa rest.")
        key = (pid, clean(r.get("week_number")), clean(r.get("day_number")), clean(r.get("exercise_order")))
        if key in seen_order:
            ctx.add("ERROR", "PLAN_013", "Workout Plan", paths["plan"].name, "Workout_Plan_Items", row, "exercise_order", r.get("exercise_order"), "exercise_order trùng trong cùng plan/week/day", "Sửa thứ tự bài.")
        seen_order.add(key)


def validate_workout_history_master(ctx: ValidationContext, data: dict[str, Any]) -> None:
    frames, paths = data["frames"], data["paths"]
    sessions, items, summaries = frames["Workout_History_Sessions"], frames["Workout_History_Items"], frames["Workout_History_Summary"]
    require_columns(ctx, sessions, "Workout_History_Sessions", ["history_session_id", "user_id", "plan_id", "completion_status", "planned_item_count", "completed_item_count", "completion_pct", "planned_working_sets", "completed_working_sets", "set_completion_pct", "pain_reported", "pain_areas", "readiness_score", "recovery_flag", "record_source", "is_synthetic", "created_at"], paths, "Workout History")
    require_columns(ctx, items, "Workout_History_Items", ["history_item_id", "history_session_id", "user_id", "plan_id", "plan_item_id", "exercise_id", "planned_sets", "actual_sets_completed", "actual_reps_json", "actual_rpe", "completion_status", "pain_during_exercise", "pain_areas", "feedback_signal", "record_source", "is_synthetic", "created_at"], paths, "Workout History")
    require_columns(ctx, summaries, "Workout_History_Summary", ["summary_id", "user_id", "plan_id", "session_status", "session_completion_pct", "set_completion_pct", "session_rpe", "fatigue_after", "pain_reported", "progression_recommendation"], paths, "Workout History")
    check_pk(ctx, sessions, "Workout_History_Sessions", paths, "HIS_SESSION")
    check_pk(ctx, items, "Workout_History_Items", paths, "HIS_ITEM")
    valid_status = {"Completed", "Partial", "Skipped"}
    for i, r in sessions.iterrows():
        row = int(i) + 2
        status = clean(r.get("completion_status"))
        if status not in valid_status:
            ctx.add("ERROR", "HIS_007", "Workout History", paths["history"].name, "Workout_History_Sessions", row, "completion_status", status, "completion_status không hợp lệ", "Dùng Completed/Partial/Skipped.")
        if status == "Skipped":
            for col, rule in [("completed_item_count", "HIS_008"), ("completed_working_sets", "HIS_009"), ("completion_pct", "HIS_010"), ("set_completion_pct", "HIS_011")]:
                if num(r.get(col)) != 0:
                    ctx.add("ERROR", rule, "Workout History", paths["history"].name, "Workout_History_Sessions", row, col, r.get(col), "Skipped session phải có chỉ số completed bằng 0", "Sửa aggregate skipped.")
        if clean(r.get("pain_reported")) == "Yes" and len(parse_list(r.get("pain_areas")) or []) == 0:
            ctx.add("ERROR", "HIS_016", "Workout History", paths["history"].name, "Workout_History_Sessions", row, "pain_areas", "", "pain_reported=Yes thì pain_areas không được rỗng", "Bổ sung pain areas.")
    for i, r in items.iterrows():
        row = int(i) + 2
        planned, actual = num(r.get("planned_sets")), num(r.get("actual_sets_completed"))
        if clean(r.get("completion_status")) == "Skipped" and actual != 0:
            ctx.add("ERROR", "HIS_012", "Workout History", paths["history"].name, "Workout_History_Items", row, "actual_sets_completed", r.get("actual_sets_completed"), "Skipped item phải có actual_sets_completed = 0", "Sửa actual_sets.")
        if planned is not None and actual is not None and actual > planned:
            ctx.add("ERROR", "HIS_013", "Workout History", paths["history"].name, "Workout_History_Items", row, "actual_sets_completed", r.get("actual_sets_completed"), "actual_sets_completed lớn hơn planned_sets", "Sửa actual/planned sets.")
        reps = parse_list(r.get("actual_reps_json"))
        if reps is None or (actual is not None and len(reps) != int(actual)):
            ctx.add("ERROR", "HIS_014", "Workout History", paths["history"].name, "Workout_History_Items", row, "actual_reps_json", r.get("actual_reps_json"), "actual_reps_json length phải bằng actual_sets_completed", "Sửa reps JSON.")
        rpe = num(r.get("actual_rpe"))
        if rpe is not None and not 1 <= rpe <= 10:
            ctx.add("ERROR", "HIS_015", "Workout History", paths["history"].name, "Workout_History_Items", row, "actual_rpe", r.get("actual_rpe"), "actual_rpe ngoài 1..10", "Sửa RPE.")
        if clean(r.get("pain_during_exercise")) == "Yes" and len(parse_list(r.get("pain_areas")) or []) == 0:
            ctx.add("ERROR", "HIS_016", "Workout History", paths["history"].name, "Workout_History_Items", row, "pain_areas", "", "pain_during_exercise=Yes thì pain_areas không được rỗng", "Bổ sung pain areas.")
    validate_history_aggregates(ctx, data)


def validate_history_aggregates(ctx: ValidationContext, data: dict[str, Any]) -> None:
    paths = data["paths"]
    sessions = data["frames"]["Workout_History_Sessions"]
    items = data["frames"]["Workout_History_Items"]
    grouped = items.groupby("history_session_id", dropna=False)
    for i, s in sessions.iterrows():
        sid = clean(s.get("history_session_id"))
        if sid not in grouped.groups:
            continue
        g = grouped.get_group(sid)
        planned_items = len(g)
        completed_items = int((g["completion_status"].map(clean) != "Skipped").sum())
        planned_sets = sum(num(v) or 0 for v in g["planned_sets"])
        completed_sets = sum(num(v) or 0 for v in g["actual_sets_completed"])
        row = int(i) + 2
        checks = [
            ("HIS_017", "planned_item_count", planned_items),
            ("HIS_018", "completed_item_count", completed_items),
            ("HIS_019", "completed_working_sets", completed_sets),
            ("HIS_020", "completion_pct", pct(completed_items, planned_items)),
            ("HIS_021", "set_completion_pct", pct(completed_sets, planned_sets)),
        ]
        if not approx(s.get("planned_working_sets"), planned_sets):
            ctx.add("ERROR", "HIS_017", "Workout History", paths["history"].name, "Workout_History_Sessions", row, "planned_working_sets", s.get("planned_working_sets"), "planned_working_sets không khớp item aggregate", "Tính lại aggregate.")
        for rule, col, expected in checks:
            if not approx(s.get(col), expected):
                ctx.add("ERROR", rule, "Workout History", paths["history"].name, "Workout_History_Sessions", row, col, s.get(col), f"{col} không khớp item aggregate expected={expected}", "Tính lại aggregate.")


def validate_user_feedback_master(ctx: ValidationContext, data: dict[str, Any]) -> None:
    df, paths = data["frames"]["User_Feedback"], data["paths"]
    require_columns(ctx, df, "User_Feedback", ["feedback_id", "user_id", "plan_id", "history_session_id", "history_item_id", "plan_item_id", "exercise_id", "feedback_scope", "feedback_type", "rating", "sentiment", "difficulty_feedback", "enjoyment_rating", "fatigue_feedback", "pain_feedback", "pain_areas", "duration_feedback", "exercise_preference", "progression_preference", "requested_action", "feedback_text", "feedback_reason_tags", "source_context", "feedback_status", "record_source", "is_synthetic", "created_at", "updated_at"], paths, "User Feedback")
    check_pk(ctx, df, "User_Feedback", paths, "FB")
    valid_scope = {"Exercise", "Session", "Plan", "General"}
    valid_sentiment = {"Positive", "Neutral", "Negative"}
    valid_actions = {"Keep", "Replace Exercise", "Reduce Difficulty", "Increase Difficulty", "Reduce Volume", "Increase Volume", "Reduce Session Duration", "Increase Session Duration", "Review Safety", "No Preference", "Maintain", "Change Split"}
    for i, r in df.iterrows():
        row = int(i) + 2
        scope, sentiment, pain = clean(r.get("feedback_scope")), clean(r.get("sentiment")), clean(r.get("pain_feedback"))
        rating, enjoyment = num(r.get("rating")), num(r.get("enjoyment_rating"))
        if scope not in valid_scope:
            ctx.add("ERROR", "FB_009", "User Feedback", paths["feedback"].name, "User_Feedback", row, "feedback_scope", scope, "feedback_scope không hợp lệ", "Dùng Exercise/Session/Plan/General.")
        if sentiment not in valid_sentiment:
            ctx.add("ERROR", "FB_013", "User Feedback", paths["feedback"].name, "User_Feedback", row, "sentiment", sentiment, "sentiment không hợp lệ", "Dùng Positive/Neutral/Negative.")
        if rating is None or not 1 <= rating <= 5:
            ctx.add("ERROR", "FB_011", "User Feedback", paths["feedback"].name, "User_Feedback", row, "rating", r.get("rating"), "rating phải từ 1..5", "Sửa rating.")
        if enjoyment is not None and not 1 <= enjoyment <= 5:
            ctx.add("ERROR", "FB_012", "User Feedback", paths["feedback"].name, "User_Feedback", row, "enjoyment_rating", r.get("enjoyment_rating"), "enjoyment_rating phải từ 1..5 nếu có", "Sửa enjoyment.")
        if rating is not None and rating <= 2 and sentiment == "Positive":
            ctx.add("WARNING", "FB_014", "User Feedback", paths["feedback"].name, "User_Feedback", row, "sentiment", sentiment, "rating thấp không nên đi với Positive", "Kiểm tra sentiment/rating.")
        if rating is not None and rating >= 4 and sentiment == "Negative":
            ctx.add("WARNING", "FB_015", "User Feedback", paths["feedback"].name, "User_Feedback", row, "sentiment", sentiment, "rating cao không nên đi với Negative", "Kiểm tra sentiment/rating.")
        pain_areas = parse_list(r.get("pain_areas")) or []
        if pain == "No Pain" and pain_areas:
            ctx.add("ERROR", "FB_016", "User Feedback", paths["feedback"].name, "User_Feedback", row, "pain_areas", r.get("pain_areas"), "No Pain thì pain_areas phải rỗng", "Xóa pain_areas hoặc đổi pain_feedback.")
        if pain in {"Pain", "Severe Pain"} and not pain_areas:
            ctx.add("ERROR", "FB_017", "User Feedback", paths["feedback"].name, "User_Feedback", row, "pain_areas", "", "Pain/Severe Pain thì pain_areas không được rỗng", "Bổ sung pain_areas.")
        if scope == "Exercise" and (not clean(r.get("history_item_id")) or not clean(r.get("plan_item_id")) or not clean(r.get("exercise_id"))):
            ctx.add("ERROR", "FB_019", "User Feedback", paths["feedback"].name, "User_Feedback", row, "feedback_scope", scope, "Exercise scope thiếu history_item_id/plan_item_id/exercise_id", "Bổ sung FK cho exercise feedback.")
        if scope == "Session" and not clean(r.get("history_session_id")):
            ctx.add("ERROR", "FB_020", "User Feedback", paths["feedback"].name, "User_Feedback", row, "history_session_id", "", "Session scope phải có history_session_id", "Bổ sung session FK.")
        if scope == "Plan" and not clean(r.get("plan_id")):
            ctx.add("ERROR", "FB_021", "User Feedback", paths["feedback"].name, "User_Feedback", row, "plan_id", "", "Plan scope phải có plan_id", "Bổ sung plan FK.")
        if clean(r.get("requested_action")) not in valid_actions:
            ctx.add("ERROR", "FB_023", "User Feedback", paths["feedback"].name, "User_Feedback", row, "requested_action", r.get("requested_action"), "requested_action ngoài taxonomy", "Chuẩn hóa requested_action.")
        if clean(r.get("feedback_text")) == "":
            ctx.add("WARNING", "FB_025", "User Feedback", paths["feedback"].name, "User_Feedback", row, "feedback_text", "", "feedback_text không nên rỗng", "Bổ sung text nếu dùng AI Coach.")
        if parse_list(r.get("feedback_reason_tags")) is None:
            ctx.add("ERROR", "FB_026", "User Feedback", paths["feedback"].name, "User_Feedback", row, "feedback_reason_tags", r.get("feedback_reason_tags"), "feedback_reason_tags phải là JSON array/list hợp lệ", "Sửa tags.")


def validate_relationships(ctx: ValidationContext, data: dict[str, Any]) -> None:
    frames, paths = data["frames"], data["paths"]
    pk_sets = {table: set(df[TABLES[table][2]].map(clean)) if TABLES[table][2] in df.columns else set() for table, df in frames.items()}
    for rid, src, scol, tgt, tcol, required in RELATIONSHIPS:
        df = frames[src]
        checked = blank = missing = 0
        if scol not in df.columns:
            ctx.add("ERROR", rid, "Relationship", file_for(src, paths), TABLES[src][1], "-", scol, "", "Source FK column không tồn tại", "Bổ sung FK column.")
            continue
        target_values = pk_sets[tgt] if tcol == TABLES[tgt][2] else set(frames[tgt][tcol].map(clean))
        for i, v in df[scol].items():
            val = clean(v)
            if not val:
                blank += 1
                if required:
                    missing += 1
                    ctx.add("ERROR", rid, "Relationship", file_for(src, paths), TABLES[src][1], int(i) + 2, scol, val, f"{src}.{scol} không được blank", "Điền FK hợp lệ.")
                continue
            checked += 1
            if val not in target_values:
                missing += 1
                ctx.add("ERROR", rid, "Relationship", file_for(src, paths), TABLES[src][1], int(i) + 2, scol, val, f"{src}.{scol} không tồn tại trong {tgt}.{tcol}", "Sửa hoặc loại bỏ orphan row.")
        ctx.relationship_results.append({"rule_id": rid, "source": src, "source_column": scol, "target": tgt, "target_column": tcol, "checked_count": checked, "blank_count": blank, "missing_count": missing, "status": "PASS" if missing == 0 else "FAIL"})


def validate_cross_consistency(ctx: ValidationContext, data: dict[str, Any]) -> None:
    frames, paths = data["frames"], data["paths"]
    maps = {}
    for table, df in frames.items():
        pk = TABLES[table][2]
        maps[table] = {clean(r.get(pk)): r for _, r in df.iterrows() if clean(r.get(pk))}
    for rid, src, join_col, src_col, tgt, tgt_key, tgt_col in CROSS_RULES:
        checked = missing_target = mismatch = blank = 0
        df = frames[src]
        for i, r in df.iterrows():
            join_val = clean(r.get(join_col))
            if not join_val:
                blank += 1
                continue
            target = maps[tgt].get(join_val)
            if target is None:
                missing_target += 1
                continue
            a, b = clean(r.get(src_col)), clean(target.get(tgt_col))
            if a and b:
                checked += 1
                if a != b:
                    mismatch += 1
                    ctx.add("ERROR", rid, "Relationship", file_for(src, paths), TABLES[src][1], int(i) + 2, src_col, a, f"{src}.{src_col} không khớp {tgt}.{tgt_col} qua {join_col}", "Sửa snapshot hoặc FK.")
        ctx.cross_results.append({"rule_id": rid, "source": src, "target": tgt, "join_column": join_col, "checked_count": checked, "missing_target_count": missing_target, "mismatch_count": mismatch, "blank_count": blank, "status": "PASS" if missing_target == 0 and mismatch == 0 else "FAIL"})


def validate_distribution(ctx: ValidationContext, data: dict[str, Any]) -> None:
    frames, paths = data["frames"], data["paths"]
    sessions, items, feedback, plans, plan_items, exercises = frames["Workout_History_Sessions"], frames["Workout_History_Items"], frames["User_Feedback"], frames["Workout_Plan"], frames["Workout_Plan_Items"], frames["Exercise_Master"]
    def check_range(rule: str, domain: str, file: str, sheet: str, metric: str, value: float, low: float, high: float) -> None:
        if value < low or value > high:
            ctx.add("WARNING", rule, domain, file, sheet, "-", metric, value, f"{metric}={value}% ngoài khoảng khuyến nghị {low}..{high}%", "Kiểm tra distribution nếu dùng cho AI training.")
    status_dist = Counter(sessions.get("completion_status", pd.Series(dtype=str)).map(clean))
    total_sessions = len(sessions)
    check_range("DIST_HIS_001", "Distribution", paths["history"].name, "Workout_History_Sessions", "Completed", pct(status_dist["Completed"], total_sessions), 78, 87)
    check_range("DIST_HIS_002", "Distribution", paths["history"].name, "Workout_History_Sessions", "Partial", pct(status_dist["Partial"], total_sessions), 8, 15)
    check_range("DIST_HIS_003", "Distribution", paths["history"].name, "Workout_History_Sessions", "Skipped", pct(status_dist["Skipped"], total_sessions), 3, 8)
    pain_pct = pct((sessions.get("pain_reported", pd.Series(dtype=str)).map(clean) == "Yes").sum(), total_sessions)
    check_range("DIST_HIS_004", "Distribution", paths["history"].name, "Workout_History_Sessions", "Pain sessions", pain_pct, 1, 4)
    feedback_signal = Counter(items.get("feedback_signal", pd.Series(dtype=str)).map(clean))
    total_items = len(items)
    check_range("DIST_HIS_005", "Distribution", paths["history"].name, "Workout_History_Items", "Positive item feedback_signal", pct(feedback_signal["Positive"], total_items), 55, 72)
    check_range("DIST_HIS_006", "Distribution", paths["history"].name, "Workout_History_Items", "Neutral item feedback_signal", pct(feedback_signal["Neutral"], total_items), 18, 32)
    check_range("DIST_HIS_007", "Distribution", paths["history"].name, "Workout_History_Items", "Negative item feedback_signal", pct(feedback_signal["Negative"], total_items), 5, 15)
    scope = Counter(feedback.get("feedback_scope", pd.Series(dtype=str)).map(clean))
    sent = Counter(feedback.get("sentiment", pd.Series(dtype=str)).map(clean))
    total_fb = len(feedback)
    check_range("DIST_FB_001", "Distribution", paths["feedback"].name, "User_Feedback", "Exercise feedback", pct(scope["Exercise"], total_fb), 55, 65)
    check_range("DIST_FB_002", "Distribution", paths["feedback"].name, "User_Feedback", "Session feedback", pct(scope["Session"], total_fb), 25, 35)
    check_range("DIST_FB_003", "Distribution", paths["feedback"].name, "User_Feedback", "Plan feedback", pct(scope["Plan"], total_fb), 5, 10)
    check_range("DIST_FB_004", "Distribution", paths["feedback"].name, "User_Feedback", "General feedback", pct(scope["General"], total_fb), 1, 3)
    check_range("DIST_FB_005", "Distribution", paths["feedback"].name, "User_Feedback", "Positive sentiment", pct(sent["Positive"], total_fb), 55, 65)
    check_range("DIST_FB_006", "Distribution", paths["feedback"].name, "User_Feedback", "Neutral sentiment", pct(sent["Neutral"], total_fb), 20, 30)
    check_range("DIST_FB_007", "Distribution", paths["feedback"].name, "User_Feedback", "Negative sentiment", pct(sent["Negative"], total_fb), 10, 18)
    pain_fb = feedback.get("pain_feedback", pd.Series(dtype=str)).map(clean).isin({"Mild Discomfort", "Pain", "Severe Pain"}).sum()
    check_range("DIST_FB_008", "Distribution", paths["feedback"].name, "User_Feedback", "Pain/discomfort feedback", pct(pain_fb, total_fb), 1, 4)
    ctx.metrics["distributions"] = {
        "completion_status_distribution": dict(status_dist),
        "history_feedback_signal_distribution": dict(feedback_signal),
        "feedback_scope_distribution": dict(scope),
        "sentiment_distribution": dict(sent),
        "plan_goal_distribution": dict(Counter(plans.get("primary_goal_snapshot", pd.Series(dtype=str)).map(clean))),
        "training_level_distribution": dict(Counter(plans.get("training_level_snapshot", pd.Series(dtype=str)).map(clean))),
        "exercise_category_distribution": dict(Counter(exercises.get("category", pd.Series(dtype=str)).map(clean))),
        "exercise_difficulty_distribution": dict(Counter(exercises.get(first_existing(exercises, ["difficulty_level", "minimum_training_level"]) or "difficulty_level", pd.Series(dtype=str)).map(clean))),
        "items_per_plan": summarize_counts(Counter(plan_items.get("plan_id", pd.Series(dtype=str)).map(clean))),
    }


def summarize_counts(counter: Counter) -> dict[str, float]:
    vals = list(counter.values())
    return {"min": min(vals) if vals else 0, "max": max(vals) if vals else 0, "mean": round(sum(vals) / len(vals), 3) if vals else 0}


def validate_metadata(ctx: ValidationContext, data: dict[str, Any]) -> None:
    paths = data["paths"]
    for doc_key, rule in [("stage2_design", "META_001"), ("relationship_matrix", "META_002"), ("relationship_rules", "META_003"), ("ai_usage_map", "META_004")]:
        if not paths[doc_key].exists():
            ctx.add("WARNING", rule, "Metadata", paths[doc_key].name, "-", "-", "-", "", "Stage 2 artifact không tồn tại", "Tạo lại Stage 2 artifact trước khi audit chính thức.")
    for workbook_key in ["history", "feedback"]:
        try:
            xls = pd.ExcelFile(paths[workbook_key], engine="openpyxl")
            if "Generation_Exceptions" in xls.sheet_names:
                ex = pd.read_excel(paths[workbook_key], sheet_name="Generation_Exceptions", dtype=str, engine="openpyxl").fillna("")
                if len(ex) > 0:
                    ctx.add("WARNING", "META_005", "Metadata", paths[workbook_key].name, "Generation_Exceptions", "-", "-", len(ex), "Generation_Exceptions có dòng dữ liệu", "Đọc exception và quyết định có cần regenerate không.")
        except Exception:
            pass


def build_statistics(data: dict[str, Any], ctx: ValidationContext) -> dict[str, Any]:
    f = data["frames"]
    stats = {
        "exercise_count": len(f["Exercise_Master"]),
        "user_count": len(f["User_Profile"]),
        "plan_count": len(f["Workout_Plan"]),
        "plan_item_count": len(f["Workout_Plan_Items"]),
        "history_session_count": len(f["Workout_History_Sessions"]),
        "history_item_count": len(f["Workout_History_Items"]),
        "history_summary_count": len(f["Workout_History_Summary"]),
        "feedback_count": len(f["User_Feedback"]),
    }
    stats.update(ctx.metrics.get("distributions", {}))
    stats["exercise_coverage"] = {
        "exercises_in_plan_items": int(f["Workout_Plan_Items"]["exercise_id"].map(clean).nunique()),
        "exercises_in_history_items": int(f["Workout_History_Items"]["exercise_id"].map(clean).nunique()),
        "exercises_in_feedback": int(f["User_Feedback"]["exercise_id"].map(clean).replace("", pd.NA).dropna().nunique()),
    }
    stats["user_coverage"] = {
        "users_with_plans": int(f["Workout_Plan"]["user_id"].map(clean).nunique()),
        "users_with_history": int(f["Workout_History_Sessions"]["user_id"].map(clean).nunique()),
        "users_with_feedback": int(f["User_Feedback"]["user_id"].map(clean).nunique()),
    }
    return stats


def domain_summary(issues: list[Issue]) -> dict[str, dict[str, Any]]:
    domains = ["Exercise", "User", "Workout Plan", "Workout History", "User Feedback", "Relationship", "Distribution", "Metadata"]
    out = {}
    for d in domains:
        e = sum(1 for x in issues if x.domain == d and x.severity == "ERROR")
        w = sum(1 for x in issues if x.domain == d and x.severity == "WARNING")
        info = sum(1 for x in issues if x.domain == d and x.severity == "INFO")
        out[d.lower().replace(" ", "_")] = {"status": "FAIL" if e else "PASS WITH WARNINGS" if w else "PASS", "errors": e, "warnings": w, "info": info}
    return out


def generate_reports(ctx: ValidationContext, data: dict[str, Any], report_dir: Path) -> dict[str, Any]:
    report_dir.mkdir(parents=True, exist_ok=True)
    issues = ctx.issues
    sev = Counter(i.severity for i in issues)
    overall = "FAIL" if sev["ERROR"] else "PASS WITH WARNINGS" if sev["WARNING"] else "PASS"
    ready = sev["ERROR"] == 0
    domains = domain_summary(issues)
    stats = build_statistics(data, ctx)
    generated_at = datetime.now().isoformat(timespec="seconds")
    summary = {
        "generated_at": generated_at,
        "overall_status": overall,
        "ai_training_ready": ready,
        "export_ready": ready,
        "stage_4_ready": ready,
        "issue_summary": {"ERROR": sev["ERROR"], "WARNING": sev["WARNING"], "INFO": sev["INFO"]},
        "domains": domains,
        "relationships": ctx.relationship_results,
        "cross_consistency": ctx.cross_results,
    }
    (report_dir / "validation_report.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    (report_dir / "dataset_statistics.json").write_text(json.dumps(stats, ensure_ascii=False, indent=2), encoding="utf-8")
    readiness = {
        "stage_3_status": overall,
        "ready_for_stage_4_export": ready,
        "ready_for_ai_training": ready,
        "blocking_issues": [asdict(i) for i in issues if i.severity == "ERROR"][:100],
        "non_blocking_issues": [asdict(i) for i in issues if i.severity == "WARNING"][:100],
        "recommended_next_steps": ["Proceed to Stage 4 Export"] if ready else ["Fix ERROR issues before Stage 4 Export"],
    }
    (report_dir / "readiness_report.json").write_text(json.dumps(readiness, ensure_ascii=False, indent=2), encoding="utf-8")
    with (report_dir / "validation_issues.csv").open("w", newline="", encoding="utf-8-sig") as fh:
        writer = csv.DictWriter(fh, fieldnames=["severity", "rule_id", "domain", "file", "sheet", "row", "column", "value", "message", "suggestion"])
        writer.writeheader()
        for issue in issues:
            writer.writerow(asdict(issue))
    top = issues[:20]
    lines = [
        "AI Fitness Dataset Validation Report",
        "=" * 72,
        f"Generated at: {generated_at}",
        f"Overall Status: {overall}",
        f"AI Training Ready: {'YES' if ready else 'NO'}",
        f"Export Ready: {'YES' if ready else 'NO'}",
        f"Stage 4 Ready: {'YES' if ready else 'NO'}",
        "",
        "Summary:",
    ]
    for d, result in domains.items():
        lines.append(f"- {d}: {result['status']} (ERROR={result['errors']}, WARNING={result['warnings']}, INFO={result['info']})")
    lines += ["", "Issue Summary:", f"ERROR: {sev['ERROR']}", f"WARNING: {sev['WARNING']}", f"INFO: {sev['INFO']}", "", "Dataset Statistics:"]
    for k in ["exercise_count", "user_count", "plan_count", "plan_item_count", "history_session_count", "history_item_count", "history_summary_count", "feedback_count"]:
        lines.append(f"- {k}: {stats[k]}")
    lines += ["", "Relationship Summary:"]
    for r in ctx.relationship_results:
        lines.append(f"- {r['rule_id']}: {r['status']} checked={r['checked_count']} blank={r['blank_count']} missing={r['missing_count']}")
    lines += ["", "Top Issues:"]
    if not top:
        lines.append("- No ERROR/WARNING issues found.")
    else:
        for i, issue in enumerate(top, 1):
            lines.append(f"{i}. [{issue.severity}] {issue.rule_id} {issue.domain} {issue.file}/{issue.sheet} row={issue.row} col={issue.column}: {issue.message} value={issue.value}")
    (report_dir / "validation_report.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    write_readme(report_dir)
    write_config(report_dir, data)
    return summary


def write_config(report_dir: Path, data: dict[str, Any]) -> None:
    config = {
        "inputs": {k: str(v) for k, v in data["paths"].items()},
        "outputs": ["validation_report.txt", "validation_report.json", "validation_issues.csv", "dataset_statistics.json", "readiness_report.json"],
        "distribution_thresholds": {
            "history_completed_pct": [78, 87],
            "history_partial_pct": [8, 15],
            "history_skipped_pct": [3, 8],
            "history_pain_pct": [1, 4],
            "feedback_scope_exercise_pct": [55, 65],
            "feedback_scope_session_pct": [25, 35],
            "feedback_scope_plan_pct": [5, 10],
            "feedback_scope_general_pct": [1, 3],
            "feedback_sentiment_positive_pct": [55, 65],
            "feedback_sentiment_neutral_pct": [20, 30],
            "feedback_sentiment_negative_pct": [10, 18],
        },
    }
    (report_dir / "validation_config.json").write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")


def write_readme(report_dir: Path) -> None:
    text = """# README Validator

## 1. Validator dùng để làm gì
`validate.py` kiểm tra tổng hợp 5 master dataset, relationship, cross-consistency, distribution, metadata và readiness cho Stage 4 Export.

## 2. File input cần có
`exercise_master.xlsx`, `user_master.xlsx`, `workout_plan_master.xlsx`, `workout_history_master.xlsx`, `user_feedback_master.xlsx` và các artifact Stage 2 trong `docs/`.

## 3. Cách chạy
Chạy nhanh từ thư mục project:

```bash
python validate.py
```

Chạy đầy đủ với path tùy chỉnh:

```bash
python validate.py --exercise-master master/exercise_master.xlsx --user-master master/user_master.xlsx --plan-master master/workout_plan_master.xlsx --history-master master/workout_history_master.xlsx --feedback-master master/user_feedback_master.xlsx --report-dir reports/stage_3_validation
```

## 4. Output tạo ra
`validation_report.txt`, `validation_report.json`, `validation_issues.csv`, `dataset_statistics.json`, `readiness_report.json`, `validation_config.json`.

## 5. Ý nghĩa ERROR / WARNING / INFO
ERROR là lỗi blocking cần sửa trước export/training. WARNING là lệch nhẹ hoặc metadata/phân bố cần xem xét. INFO là ghi chú không chặn.

## 6. Điều kiện PASS
ERROR = 0 và WARNING = 0.

## 7. Điều kiện AI Training Ready
ERROR = 0. WARNING nếu có phải là non-blocking và được chấp nhận.

## 8. Điều kiện Ready for Stage 4
ERROR = 0, relationship PASS và cross-consistency PASS.

## 9. Cách đọc validation_issues.csv
Mỗi dòng có `severity, rule_id, domain, file, sheet, row, column, value, message, suggestion`.

## 10. Cách thêm rule mới
Thêm logic vào hàm domain tương ứng hoặc thêm FK vào `RELATIONSHIPS`, cross rule vào `CROSS_RULES`, sau đó chạy lại `python validate.py`.
"""
    (report_dir / "README_validator.md").write_text(text, encoding="utf-8")


def validate_all(args: argparse.Namespace) -> tuple[ValidationContext, dict[str, Any], dict[str, Any]]:
    ctx = ValidationContext()
    data = load_workbooks(args, ctx)
    validate_exercise_master(ctx, data)
    validate_user_master(ctx, data)
    validate_workout_plan_master(ctx, data)
    validate_workout_history_master(ctx, data)
    validate_user_feedback_master(ctx, data)
    validate_relationships(ctx, data)
    validate_cross_consistency(ctx, data)
    validate_distribution(ctx, data)
    validate_metadata(ctx, data)
    report_dir = resolve_path(args.report_dir, DEFAULT_REPORT_DIR)
    summary = generate_reports(ctx, data, report_dir)
    return ctx, data, summary


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Stage 3 tổng hợp validator cho AI Fitness Dataset")
    p.add_argument("--exercise-master")
    p.add_argument("--user-master")
    p.add_argument("--plan-master")
    p.add_argument("--history-master")
    p.add_argument("--feedback-master")
    p.add_argument("--stage2-design")
    p.add_argument("--relationship-matrix")
    p.add_argument("--relationship-rules")
    p.add_argument("--ai-usage-map")
    p.add_argument("--report-dir")
    return p


def main() -> int:
    args = build_parser().parse_args()
    ctx, _, summary = validate_all(args)
    sev = Counter(i.severity for i in ctx.issues)
    report_dir = resolve_path(args.report_dir, DEFAULT_REPORT_DIR)
    print("=" * 72)
    print("AI FITNESS DATASET STAGE 3 VALIDATION")
    print("=" * 72)
    print(f"Overall Status : {summary['overall_status']}")
    print(f"ERROR          : {sev['ERROR']}")
    print(f"WARNING        : {sev['WARNING']}")
    print(f"INFO           : {sev['INFO']}")
    print(f"AI TRAIN READY : {'YES' if summary['ai_training_ready'] else 'NO'}")
    print(f"STAGE 4 READY  : {'YES' if summary['stage_4_ready'] else 'NO'}")
    print(f"Report dir     : {report_dir}")
    print("=" * 72)
    return 1 if sev["ERROR"] else 0


if __name__ == "__main__":
    sys.exit(main())
