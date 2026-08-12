from __future__ import annotations

import argparse
import csv
import json
import math
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd


ROOT = Path(__file__).resolve().parent
MASTER = ROOT / "master"
DEFAULT_EXPORTS = ROOT / "exports"
DEFAULT_VALIDATION = ROOT / "reports" / "stage_3_validation" / "validation_report.json"
DEFAULT_READINESS = ROOT / "reports" / "stage_3_validation" / "readiness_report.json"

TABLES = {
    "exercises": ("exercise", "gym_exercise_dataset", "exercise_id"),
    "users": ("user", "User_Profile", "user_id"),
    "workout_plans": ("plan", "Workout_Plan", "plan_id"),
    "workout_plan_items": ("plan", "Workout_Plan_Items", "plan_item_id"),
    "workout_history_sessions": ("history", "Workout_History_Sessions", "history_session_id"),
    "workout_history_items": ("history", "Workout_History_Items", "history_item_id"),
    "workout_history_summary": ("history", "Workout_History_Summary", "summary_id"),
    "user_feedback": ("feedback", "User_Feedback", "feedback_id"),
}

LIST_FIELDS = {
    "aliases", "equipment", "primary_muscles", "secondary_muscles", "stabilizer_muscles",
    "movement_planes", "joint_actions", "recommended_goals", "joint_stress_areas",
    "contraindications", "execution_steps", "common_mistakes", "cues", "progressions",
    "regressions", "alternatives", "available_equipment", "priority_muscles",
    "avoided_muscles", "preferred_exercise_types", "avoided_exercise_ids",
    "preferred_exercise_ids", "injuries_or_limitations", "actual_reps_json",
    "pain_areas", "feedback_reason_tags", "substitution_exercise_ids", "focus_muscles",
    "exercise_goals_snapshot", "exercise_equipment_snapshot", "primary_muscles_snapshot",
    "goal_filter_tags",
}

INT_FIELDS = {
    "age", "training_experience_months", "training_days_per_week", "session_duration_minutes",
    "duration_weeks", "days_per_week", "weekly_set_target", "session_volume_target",
    "exercise_item_count", "week_number", "day_number", "exercise_order", "sets",
    "rep_min", "rep_max", "duration_seconds", "rest_seconds", "warmup_sets",
    "planned_item_count", "completed_item_count", "planned_working_sets",
    "completed_working_sets", "actual_duration_min", "energy_before", "fatigue_after",
    "planned_sets", "planned_rep_min", "planned_rep_max", "planned_rest_seconds",
    "actual_sets_completed", "difficulty_rating", "exercise_enjoyment",
    "representative_week", "representative_day", "positive_items", "neutral_items",
    "negative_items", "rating", "enjoyment_rating",
}

FLOAT_FIELDS = {
    "height_cm", "weight_kg", "body_fat_percent", "bmi", "sleep_hours",
    "technical_complexity_score", "coordination_requirement",
    "stability_requirement", "mobility_requirement", "balance_requirement",
    "systemic_fatigue_score", "local_fatigue_score", "met_value",
    "priority_score", "target_intensity", "completion_pct",
    "set_completion_pct", "session_duration_target_min", "session_rpe",
    "sleep_hours_snapshot", "body_weight_kg_snapshot", "readiness_score",
    "planned_target_rpe", "actual_load_kg", "actual_rpe", "session_completion_pct",
    "avg_difficulty", "avg_enjoyment",
}

BOOL_FIELDS = {"is_optional", "is_synthetic", "medical_clearance_required"}

SQL_TABLE_ORDER = [
    "exercises", "users", "workout_plans", "workout_plan_items",
    "workout_history_sessions", "workout_history_items", "workout_history_summary",
    "user_feedback",
]

SQL_TABLE_NAMES = {
    "exercises": "exercises",
    "users": "users",
    "workout_plans": "workout_plans",
    "workout_plan_items": "workout_plan_items",
    "workout_history_sessions": "workout_history_sessions",
    "workout_history_items": "workout_history_items",
    "workout_history_summary": "workout_history_summary",
    "user_feedback": "user_feedback",
}


class ExportState:
    def __init__(self) -> None:
        self.warnings: list[str] = []
        self.files: list[dict[str, Any]] = []
        self.row_counts: dict[str, int] = {}
        self.validation_status: dict[str, Any] = {}

    def warn(self, message: str) -> None:
        self.warnings.append(message)

    def add_file(self, path: Path, fmt: str, rows: int | None = None) -> None:
        self.files.append({
            "path": str(path.relative_to(ROOT)).replace("\\", "/") if path.is_absolute() else str(path).replace("\\", "/"),
            "format": fmt,
            "rows": rows,
            "size_bytes": path.stat().st_size if path.exists() else 0,
            "status": "OK" if path.exists() and path.stat().st_size > 0 else "EMPTY",
        })


def resolve(value: str | None, default: Path) -> Path:
    if not value:
        return default
    p = Path(value)
    if p.is_absolute():
        return p
    return (ROOT / p).resolve()


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def check_readiness(args: argparse.Namespace, output_dir: Path, state: ExportState) -> bool:
    validation = read_json(resolve(args.validation_report, DEFAULT_VALIDATION))
    readiness = read_json(resolve(args.readiness_report, DEFAULT_READINESS))
    issue_summary = validation.get("issue_summary", {})
    error_count = int(issue_summary.get("ERROR", 0) or 0)
    ok = (
        validation.get("overall_status") in {"PASS", "PASS WITH WARNINGS"}
        and error_count == 0
        and validation.get("export_ready") is True
        and validation.get("stage_4_ready") is True
        and readiness.get("ready_for_stage_4_export") is True
    )
    state.validation_status = {
        "overall_status": validation.get("overall_status"),
        "error_count": error_count,
        "export_ready": validation.get("export_ready"),
        "stage_4_ready": validation.get("stage_4_ready"),
        "ready_for_stage_4_export": readiness.get("ready_for_stage_4_export"),
    }
    if not ok:
        output_dir.mkdir(parents=True, exist_ok=True)
        report = [
            "AI Fitness Dataset Export Report",
            "=" * 72,
            f"Generated at: {datetime.now().isoformat(timespec='seconds')}",
            "",
            "Export Status: BLOCKED",
            f"Validation Status: {state.validation_status}",
            "",
            "Reason: Stage 3 readiness is not sufficient for export.",
        ]
        (output_dir / "export_report.txt").write_text("\n".join(report) + "\n", encoding="utf-8")
    return ok


def read_workbooks(args: argparse.Namespace, state: ExportState) -> dict[str, pd.DataFrame]:
    paths = {
        "exercise": resolve(args.exercise_master, MASTER / "exercise_master.xlsx"),
        "user": resolve(args.user_master, MASTER / "user_master.xlsx"),
        "plan": resolve(args.plan_master, MASTER / "workout_plan_master.xlsx"),
        "history": resolve(args.history_master, MASTER / "workout_history_master.xlsx"),
        "feedback": resolve(args.feedback_master, MASTER / "user_feedback_master.xlsx"),
    }
    frames: dict[str, pd.DataFrame] = {}
    for name, (workbook_key, sheet, _) in TABLES.items():
        path = paths[workbook_key]
        df = pd.read_excel(path, sheet_name=sheet, dtype=str, engine="openpyxl").fillna("")
        df.columns = [str(c).strip() for c in df.columns]
        frames[name] = df
        state.row_counts[name] = len(df)
    state.source_files = {k: str(v.relative_to(ROOT)).replace("\\", "/") for k, v in paths.items()}  # type: ignore[attr-defined]
    return frames


def clean(v: Any) -> str:
    if v is None:
        return ""
    if isinstance(v, float) and math.isnan(v):
        return ""
    return str(v).strip()


def parse_list(value: Any, field: str, state: ExportState) -> list[Any] | str | None:
    s = clean(value)
    if not s:
        return None
    if s in {"[]", "null", "None"}:
        return []
    if s.startswith("[") and s.endswith("]"):
        try:
            data = json.loads(s)
            return data if isinstance(data, list) else [data]
        except Exception:
            inner = s[1:-1].strip()
            if not inner:
                return []
            return [x.strip().strip("'\"") for x in inner.split(",") if x.strip()]
    if ";" in s:
        return [x.strip() for x in s.split(";") if x.strip()]
    if "|" in s:
        return [x.strip() for x in s.split("|") if x.strip()]
    if "," in s and field not in {"feedback_text", "rationale", "safety_notes", "notes"}:
        return [x.strip() for x in s.split(",") if x.strip()]
    return [s]


def convert_value(value: Any, field: str, state: ExportState) -> Any:
    s = clean(value)
    if not s:
        return None
    if field in LIST_FIELDS:
        return parse_list(s, field, state)
    if field in BOOL_FIELDS:
        return s.lower() in {"true", "1", "yes", "y"}
    if field in INT_FIELDS:
        try:
            return int(float(s))
        except ValueError:
            state.warn(f"Cannot parse int field {field} value={s}; keeping original")
            return s
    if field in FLOAT_FIELDS:
        try:
            return float(s)
        except ValueError:
            state.warn(f"Cannot parse float field {field} value={s}; keeping original")
            return s
    return s


def records(df: pd.DataFrame, state: ExportState) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for row in df.to_dict(orient="records"):
        out.append({k: convert_value(v, k, state) for k, v in row.items()})
    return out


def write_json(path: Path, data: Any, state: ExportState, rows: int | None = None, fmt: str = "json") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    state.add_file(path, fmt, rows)


def write_jsonl(path: Path, rows: list[dict[str, Any]], state: ExportState) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    state.add_file(path, "jsonl", len(rows))


def export_csv(frames: dict[str, pd.DataFrame], output_dir: Path, state: ExportState) -> None:
    csv_dir = output_dir / "csv"
    csv_dir.mkdir(parents=True, exist_ok=True)
    for name, df in frames.items():
        path = csv_dir / f"{name}.csv"
        df.to_csv(path, index=False, encoding="utf-8-sig", quoting=csv.QUOTE_MINIMAL)
        if len(pd.read_csv(path, dtype=str, encoding="utf-8-sig")) != len(df):
            state.warn(f"CSV row count mismatch: {path}")
        state.add_file(path, "csv", len(df))


def export_json_flat(frames: dict[str, pd.DataFrame], output_dir: Path, state: ExportState) -> dict[str, list[dict[str, Any]]]:
    flat_dir = output_dir / "json" / "flat"
    flat: dict[str, list[dict[str, Any]]] = {}
    for name, df in frames.items():
        recs = records(df, state)
        flat[name] = recs
        write_json(flat_dir / f"{name}.json", recs, state, len(recs), "json_flat")
    return flat


def index_by(rows: list[dict[str, Any]], key: str) -> dict[str, dict[str, Any]]:
    return {str(r.get(key)): r for r in rows if r.get(key) is not None}


def group_by(rows: list[dict[str, Any]], key: str) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        val = row.get(key)
        if val is not None:
            grouped[str(val)].append(row)
    return grouped


def export_json_nested(flat: dict[str, list[dict[str, Any]]], output_dir: Path, state: ExportState) -> None:
    nested_dir = output_dir / "json" / "nested"
    plan_items_by_plan = group_by(flat["workout_plan_items"], "plan_id")
    plans_with_items = []
    for plan in flat["workout_plans"]:
        p = dict(plan)
        p["plan_items"] = plan_items_by_plan.get(str(plan.get("plan_id")), [])
        plans_with_items.append(p)
    write_json(nested_dir / "plans_with_items.json", plans_with_items, state, len(plans_with_items), "json_nested")

    plans_by_user = group_by(flat["workout_plans"], "user_id")
    users_with_plans = []
    plan_summary_cols = {"plan_id", "user_id", "plan_name", "primary_goal_snapshot", "training_level_snapshot", "days_per_week", "split_type", "plan_status"}
    for user in flat["users"]:
        u = {"user_id": user.get("user_id"), "profile": user, "plans": [{k: v for k, v in p.items() if k in plan_summary_cols} for p in plans_by_user.get(str(user.get("user_id")), [])]}
        users_with_plans.append(u)
    write_json(nested_dir / "users_with_plans.json", users_with_plans, state, len(users_with_plans), "json_nested")

    items_by_session = group_by(flat["workout_history_items"], "history_session_id")
    history_by_session = []
    for session in flat["workout_history_sessions"]:
        s = dict(session)
        s["items"] = items_by_session.get(str(session.get("history_session_id")), [])
        history_by_session.append(s)
    write_json(nested_dir / "history_by_session.json", history_by_session, state, len(history_by_session), "json_nested")

    feedback_by_user_raw = group_by(flat["user_feedback"], "user_id")
    feedback_by_user = [{"user_id": u.get("user_id"), "feedback": feedback_by_user_raw.get(str(u.get("user_id")), [])} for u in flat["users"]]
    write_json(nested_dir / "feedback_by_user.json", feedback_by_user, state, len(feedback_by_user), "json_nested")


def sample_exercise_features(plan_items: list[dict[str, Any]], exercises_by_id: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    out = []
    for item in plan_items[:12]:
        ex = exercises_by_id.get(str(item.get("exercise_id")), {})
        out.append({
            "exercise_id": item.get("exercise_id"),
            "exercise_name": item.get("exercise_name_snapshot") or ex.get("exercise_name"),
            "equipment": ex.get("equipment"),
            "primary_muscles": ex.get("primary_muscles"),
            "recommended_goals": ex.get("recommended_goals"),
            "minimum_training_level": ex.get("minimum_training_level"),
        })
    return out


def export_ai_training(flat: dict[str, list[dict[str, Any]]], output_dir: Path, state: ExportState) -> None:
    ai_dir = output_dir / "json" / "ai_training"
    users_by_id = index_by(flat["users"], "user_id")
    exercises_by_id = index_by(flat["exercises"], "exercise_id")
    plan_items_by_plan = group_by(flat["workout_plan_items"], "plan_id")
    sessions_by_plan = group_by(flat["workout_history_sessions"], "plan_id")
    feedback_by_plan = group_by([f for f in flat["user_feedback"] if f.get("plan_id")], "plan_id")
    feedback_by_user = group_by(flat["user_feedback"], "user_id")
    history_items_by_user = group_by(flat["workout_history_items"], "user_id")

    rec_samples = []
    for plan in flat["workout_plans"][:1000]:
        items = plan_items_by_plan.get(str(plan.get("plan_id")), [])
        rec_samples.append({
            "task": "workout_recommendation",
            "input": {"user_profile": users_by_id.get(str(plan.get("user_id")), {}), "available_exercise_features": sample_exercise_features(items, exercises_by_id)},
            "output": {"workout_plan": plan, "plan_items": items},
            "metadata": {"user_id": plan.get("user_id"), "plan_id": plan.get("plan_id"), "source": "synthetic_master_dataset"},
        })
    write_jsonl(ai_dir / "workout_recommendation_samples.jsonl", rec_samples, state)

    adjustment_samples = []
    for plan in flat["workout_plans"][:1000]:
        pid = str(plan.get("plan_id"))
        recent_sessions = sessions_by_plan.get(pid, [])[-5:]
        recent_feedback = feedback_by_plan.get(pid, [])[-10:]
        action_counts = Counter(str(f.get("requested_action")) for f in recent_feedback if f.get("requested_action"))
        action = action_counts.most_common(1)[0][0] if action_counts else "Maintain"
        adjustment_samples.append({
            "task": "plan_adjustment",
            "input": {"user_profile": users_by_id.get(str(plan.get("user_id")), {}), "current_plan": plan, "recent_history_summary": recent_sessions, "recent_feedback": recent_feedback},
            "output": {"recommended_action": action, "reason": "Derived from recent history completion, pain and explicit feedback.", "target_changes": []},
            "metadata": {"user_id": plan.get("user_id"), "plan_id": plan.get("plan_id")},
        })
    write_jsonl(ai_dir / "plan_adjustment_samples.jsonl", adjustment_samples, state)

    pain_feedback = [f for f in flat["user_feedback"] if f.get("pain_feedback") in {"Pain", "Severe Pain", "Mild Discomfort"}]
    pain_items = [h for h in flat["workout_history_items"] if h.get("pain_during_exercise") == "Yes"]
    safety_samples = []
    for row in (pain_feedback[:700] + pain_items[:700])[:1000]:
        user_id = row.get("user_id")
        exercise_id = row.get("exercise_id")
        ex = exercises_by_id.get(str(exercise_id), {})
        safety_samples.append({
            "task": "safety_review",
            "input": {
                "user_injuries": users_by_id.get(str(user_id), {}).get("injuries_or_limitations"),
                "exercise_contraindications": ex.get("contraindications"),
                "pain_history": row.get("pain_areas"),
                "pain_feedback": row.get("pain_feedback") or row.get("pain_during_exercise"),
            },
            "output": {"safety_status": "review" if row.get("pain_feedback") == "Pain" else "monitor", "recommended_action": "Review Safety", "reason": "Pain or discomfort signal exists for this context."},
            "metadata": {"user_id": user_id, "exercise_id": exercise_id},
        })
    write_jsonl(ai_dir / "safety_review_samples.jsonl", safety_samples, state)

    preference_samples = []
    for user in flat["users"][:500]:
        uid = str(user.get("user_id"))
        fb = feedback_by_user.get(uid, [])[-30:]
        hist = history_items_by_user.get(uid, [])[-30:]
        preferred = sorted({f.get("exercise_id") for f in fb if f.get("sentiment") == "Positive" and f.get("exercise_id")})[:20]
        avoided = sorted({f.get("exercise_id") for f in fb if f.get("sentiment") == "Negative" and f.get("exercise_id")})[:20]
        tags = sorted({tag for f in fb for tag in (f.get("feedback_reason_tags") or []) if isinstance(f.get("feedback_reason_tags"), list)})[:30]
        preference_samples.append({
            "task": "preference_learning",
            "input": {"user_profile": user, "exercise_history": hist, "feedback": fb},
            "output": {"preferred_exercises": preferred, "avoided_exercises": avoided, "preference_tags": tags, "reason": "Aggregated from explicit feedback sentiment and exercise history."},
            "metadata": {"user_id": uid},
        })
    write_jsonl(ai_dir / "preference_learning_samples.jsonl", preference_samples, state)


def sql_type(column: str) -> str:
    if column in LIST_FIELDS:
        return "JSONB"
    if column in BOOL_FIELDS:
        return "BOOLEAN"
    if column in INT_FIELDS:
        return "INTEGER"
    if column in FLOAT_FIELDS:
        return "REAL"
    if column.endswith("_at") or column.endswith("_date") or column in {"scheduled_date", "plan_start_date", "plan_end_date", "last_reviewed_date"}:
        return "TIMESTAMP"
    return "TEXT"


def sql_literal(value: Any, column: str, state: ExportState) -> str:
    converted = convert_value(value, column, state)
    if converted is None:
        return "NULL"
    if isinstance(converted, bool):
        return "TRUE" if converted else "FALSE"
    if isinstance(converted, (int, float)):
        return str(converted)
    if isinstance(converted, (list, dict)):
        text = json.dumps(converted, ensure_ascii=False)
        return "'" + text.replace("'", "''") + "'::jsonb"
    return "'" + str(converted).replace("'", "''") + "'"


def export_sql(frames: dict[str, pd.DataFrame], output_dir: Path, state: ExportState) -> None:
    sql_dir = output_dir / "sql"
    sql_dir.mkdir(parents=True, exist_ok=True)
    fk_sql = {
        "workout_plans": [("user_id", "users", "user_id")],
        "workout_plan_items": [("plan_id", "workout_plans", "plan_id"), ("exercise_id", "exercises", "exercise_id")],
        "workout_history_sessions": [("user_id", "users", "user_id"), ("plan_id", "workout_plans", "plan_id")],
        "workout_history_items": [("history_session_id", "workout_history_sessions", "history_session_id"), ("user_id", "users", "user_id"), ("plan_id", "workout_plans", "plan_id"), ("plan_item_id", "workout_plan_items", "plan_item_id"), ("exercise_id", "exercises", "exercise_id")],
        "workout_history_summary": [("user_id", "users", "user_id"), ("plan_id", "workout_plans", "plan_id")],
        "user_feedback": [("user_id", "users", "user_id"), ("plan_id", "workout_plans", "plan_id"), ("history_session_id", "workout_history_sessions", "history_session_id"), ("history_item_id", "workout_history_items", "history_item_id"), ("plan_item_id", "workout_plan_items", "plan_item_id"), ("exercise_id", "exercises", "exercise_id")],
    }
    schema_lines = ["-- PostgreSQL schema for AI Fitness Dataset", "CREATE EXTENSION IF NOT EXISTS pgcrypto;", ""]
    for name in SQL_TABLE_ORDER:
        df = frames[name]
        pk = TABLES[name][2]
        cols = []
        for col in df.columns:
            definition = f'    "{col}" {sql_type(col)}'
            if col == pk:
                definition += " PRIMARY KEY"
            cols.append(definition)
        for col, tgt, tgt_col in fk_sql.get(name, []):
            if col in df.columns:
                cols.append(f'    FOREIGN KEY ("{col}") REFERENCES {tgt}("{tgt_col}")')
        schema_lines.append(f"CREATE TABLE IF NOT EXISTS {SQL_TABLE_NAMES[name]} (\n" + ",\n".join(cols) + "\n);")
        schema_lines.append("")
    schema_path = sql_dir / "schema.sql"
    schema_path.write_text("\n".join(schema_lines), encoding="utf-8")
    state.add_file(schema_path, "sql")

    indexes = [
        "CREATE INDEX IF NOT EXISTS idx_workout_plans_user_id ON workout_plans(user_id);",
        "CREATE INDEX IF NOT EXISTS idx_workout_plan_items_plan_id ON workout_plan_items(plan_id);",
        "CREATE INDEX IF NOT EXISTS idx_workout_plan_items_exercise_id ON workout_plan_items(exercise_id);",
        "CREATE INDEX IF NOT EXISTS idx_history_sessions_user_plan ON workout_history_sessions(user_id, plan_id);",
        "CREATE INDEX IF NOT EXISTS idx_history_sessions_date ON workout_history_sessions(scheduled_date);",
        "CREATE INDEX IF NOT EXISTS idx_history_items_session_id ON workout_history_items(history_session_id);",
        "CREATE INDEX IF NOT EXISTS idx_history_items_plan_item_id ON workout_history_items(plan_item_id);",
        "CREATE INDEX IF NOT EXISTS idx_history_items_exercise_id ON workout_history_items(exercise_id);",
        "CREATE INDEX IF NOT EXISTS idx_feedback_user_id ON user_feedback(user_id);",
        "CREATE INDEX IF NOT EXISTS idx_feedback_scope ON user_feedback(feedback_scope);",
        "CREATE INDEX IF NOT EXISTS idx_feedback_sentiment ON user_feedback(sentiment);",
        "CREATE INDEX IF NOT EXISTS idx_feedback_history_item_id ON user_feedback(history_item_id);",
        "CREATE INDEX IF NOT EXISTS idx_feedback_exercise_id ON user_feedback(exercise_id);",
    ]
    indexes_path = sql_dir / "indexes.sql"
    indexes_path.write_text("\n".join(indexes) + "\n", encoding="utf-8")
    state.add_file(indexes_path, "sql")

    inserts_path = sql_dir / "inserts.sql"
    with inserts_path.open("w", encoding="utf-8") as fh:
        fh.write("-- PostgreSQL inserts for AI Fitness Dataset\nBEGIN;\n")
        for name in SQL_TABLE_ORDER:
            df = frames[name]
            table = SQL_TABLE_NAMES[name]
            columns = list(df.columns)
            col_sql = ", ".join(f'"{c}"' for c in columns)
            for start in range(0, len(df), 500):
                chunk = df.iloc[start:start + 500]
                values = []
                for _, row in chunk.iterrows():
                    values.append("(" + ", ".join(sql_literal(row[c], c, state) for c in columns) + ")")
                fh.write(f"INSERT INTO {table} ({col_sql}) VALUES\n" + ",\n".join(values) + ";\n")
        fh.write("COMMIT;\n")
    state.add_file(inserts_path, "sql", sum(len(frames[n]) for n in SQL_TABLE_ORDER))

    readme = """# SQL Import

PostgreSQL style export.

```bash
psql "$DATABASE_URL" -f schema.sql
psql "$DATABASE_URL" -f inserts.sql
psql "$DATABASE_URL" -f indexes.sql
```

Insert order follows foreign-key dependencies.
"""
    readme_path = sql_dir / "README_sql_import.md"
    readme_path.write_text(readme, encoding="utf-8")
    state.add_file(readme_path, "md")


def export_mongodb(flat: dict[str, list[dict[str, Any]]], output_dir: Path, state: ExportState) -> None:
    mongo_dir = output_dir / "mongodb"
    mongo_dir.mkdir(parents=True, exist_ok=True)
    plan_items_by_plan = group_by(flat["workout_plan_items"], "plan_id")
    history_items_by_session = group_by(flat["workout_history_items"], "history_session_id")
    users = [{"user_id": u.get("user_id"), "profile": u, "created_at": u.get("created_at")} for u in flat["users"]]
    plans = [{"plan_id": p.get("plan_id"), "user_id": p.get("user_id"), "plan": p, "plan_items": plan_items_by_plan.get(str(p.get("plan_id")), [])} for p in flat["workout_plans"]]
    history = [{"history_session_id": s.get("history_session_id"), "user_id": s.get("user_id"), "plan_id": s.get("plan_id"), "session": s, "items": history_items_by_session.get(str(s.get("history_session_id")), [])} for s in flat["workout_history_sessions"]]
    write_json(mongo_dir / "users.json", users, state, len(users), "mongodb_json")
    write_json(mongo_dir / "exercises.json", flat["exercises"], state, len(flat["exercises"]), "mongodb_json")
    write_json(mongo_dir / "workout_plans.json", plans, state, len(plans), "mongodb_json")
    write_json(mongo_dir / "workout_history.json", history, state, len(history), "mongodb_json")
    write_json(mongo_dir / "user_feedback.json", flat["user_feedback"], state, len(flat["user_feedback"]), "mongodb_json")
    commands = """#!/usr/bin/env bash
mongoimport --db ai_fitness --collection users --file users.json --jsonArray
mongoimport --db ai_fitness --collection exercises --file exercises.json --jsonArray
mongoimport --db ai_fitness --collection workout_plans --file workout_plans.json --jsonArray
mongoimport --db ai_fitness --collection workout_history --file workout_history.json --jsonArray
mongoimport --db ai_fitness --collection user_feedback --file user_feedback.json --jsonArray
"""
    path = mongo_dir / "mongo_import_commands.sh"
    path.write_text(commands, encoding="utf-8")
    state.add_file(path, "sh")


def write_manifest_and_report(output_dir: Path, state: ExportState, export_status: str) -> None:
    generated_at = datetime.now().isoformat(timespec="seconds")
    manifest_path = output_dir / "export_manifest.json"
    report_path = output_dir / "export_report.txt"
    manifest_entry = {
        "path": str(manifest_path.relative_to(ROOT)).replace("\\", "/"),
        "format": "json",
        "rows": None,
        "size_bytes": manifest_path.stat().st_size if manifest_path.exists() else None,
        "status": "OK",
    }
    report_entry = {
        "path": str(report_path.relative_to(ROOT)).replace("\\", "/"),
        "format": "txt",
        "rows": None,
        "size_bytes": report_path.stat().st_size if report_path.exists() else None,
        "status": "OK",
    }
    manifest_files = [*state.files, manifest_entry, report_entry]
    manifest = {
        "generated_at": generated_at,
        "source_files": getattr(state, "source_files", {}),
        "validation_status": state.validation_status,
        "exported_files": manifest_files,
        "row_counts": state.row_counts,
        "warnings": state.warnings,
        "export_status": export_status,
        "ready_for_stage_5_statistics": export_status == "PASS",
    }
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    manifest_entry["size_bytes"] = manifest_path.stat().st_size

    def file_line(prefix: str) -> list[str]:
        return [f"- {f['path']}: {f.get('rows', '-')} rows, {f['size_bytes']} bytes" for f in manifest_files if f["path"].startswith(prefix)]

    lines = [
        "AI Fitness Dataset Export Report",
        "=" * 72,
        f"Generated at: {generated_at}",
        "",
        f"Export Status: {export_status}",
        f"Validation Status: {state.validation_status.get('overall_status')}",
        f"Stage 4 Ready: {'YES' if state.validation_status.get('stage_4_ready') else 'NO'}",
        "",
        "CSV Export:",
        *file_line("exports/csv/"),
        "",
        "JSON Export:",
        *file_line("exports/json/"),
        "",
        "SQL Export:",
        *file_line("exports/sql/"),
        "",
        "MongoDB Export:",
        *file_line("exports/mongodb/"),
        "",
        "Row Count Summary:",
        *[f"- {k}: {v}" for k, v in state.row_counts.items()],
        "",
        "Warnings:",
        *(state.warnings if state.warnings else ["- None"]),
        "",
        "Next Step:",
        "Proceed to Stage 5 Statistics" if export_status == "PASS" else "Fix export blockers before Stage 5.",
    ]
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    report_entry["size_bytes"] = report_path.stat().st_size
    manifest["exported_files"] = manifest_files
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    manifest_entry["size_bytes"] = manifest_path.stat().st_size
    manifest["exported_files"] = manifest_files
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    state.files = manifest_files


def write_readme(root: Path) -> None:
    text = """# README Export

## 1. Giai đoạn 4 dùng để làm gì
Export bộ master dataset đã PASS validator sang CSV, JSON flat, JSON nested, JSONL AI training, SQL PostgreSQL và MongoDB seed.

## 2. File input cần có
5 workbook trong `master/` và report Stage 3 trong `reports/stage_3_validation/`.

## 3. Cách chạy export_all.py
```bash
python export_all.py
```

## 4. Cách chạy từng exporter
```bash
python export_csv.py
python export_json.py
python export_sql.py
python export_mongodb.py
```

## 5. Output folder structure
Output nằm trong `exports/csv`, `exports/json`, `exports/sql`, `exports/mongodb`.

## 6. Cách import CSV
Dùng file trong `exports/csv/` với encoding `utf-8-sig`.

## 7. Cách import SQL
```bash
psql "$DATABASE_URL" -f exports/sql/schema.sql
psql "$DATABASE_URL" -f exports/sql/inserts.sql
psql "$DATABASE_URL" -f exports/sql/indexes.sql
```

## 8. Cách import MongoDB
```bash
cd exports/mongodb
bash mongo_import_commands.sh
```

## 9. Cách dùng JSON flat
Mỗi file trong `exports/json/flat` là một bảng dạng records.

## 10. Cách dùng JSON nested
`plans_with_items`, `users_with_plans`, `history_by_session`, `feedback_by_user` dùng cho API/RAG.

## 11. Cách dùng JSONL cho AI training
Mỗi dòng là một sample task trong `exports/json/ai_training`.

## 12. Điều kiện export PASS
Stage 3 PASS/PASS WITH WARNINGS, ERROR=0, export_ready=true, stage_4_ready=true.

## 13. Cách đọc export_manifest.json
Manifest ghi source files, validation status, file đã export, row counts, warnings và export_status.

## 14. Cách debug nếu export fail
Đọc `exports/export_report.txt`, kiểm tra readiness Stage 3 và warning trong manifest.
"""
    path = root / "README_export.md"
    path.write_text(text, encoding="utf-8")


def run_export(args: argparse.Namespace, only: str = "all") -> ExportState:
    output_dir = resolve(args.output_dir, DEFAULT_EXPORTS)
    state = ExportState()
    if not check_readiness(args, output_dir, state):
        write_manifest_and_report(output_dir, state, "BLOCKED")
        return state
    frames = read_workbooks(args, state)
    flat: dict[str, list[dict[str, Any]]] | None = None
    if only in {"all", "csv"}:
        export_csv(frames, output_dir, state)
    if only in {"all", "json", "mongodb"}:
        flat = export_json_flat(frames, output_dir, state)
    if only in {"all", "json"} and flat is not None:
        export_json_nested(flat, output_dir, state)
        export_ai_training(flat, output_dir, state)
    if only in {"all", "sql"}:
        export_sql(frames, output_dir, state)
    if only in {"all", "mongodb"}:
        if flat is None:
            flat = export_json_flat(frames, output_dir, state)
        export_mongodb(flat, output_dir, state)
    write_readme(ROOT)
    if only == "all":
        write_manifest_and_report(output_dir, state, "PASS" if not state.warnings else "PASS WITH WARNINGS")
    return state


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Stage 4 export pipeline for AI Fitness Dataset")
    p.add_argument("--exercise-master")
    p.add_argument("--user-master")
    p.add_argument("--plan-master")
    p.add_argument("--history-master")
    p.add_argument("--feedback-master")
    p.add_argument("--validation-report")
    p.add_argument("--readiness-report")
    p.add_argument("--output-dir")
    p.add_argument("--only", choices=["all", "csv", "json", "sql", "mongodb"], default="all")
    return p


def main() -> int:
    args = parser().parse_args()
    state = run_export(args, args.only)
    status = "PASS" if not state.warnings and state.validation_status.get("error_count") == 0 else "PASS WITH WARNINGS"
    if state.validation_status.get("ready_for_stage_4_export") is not True:
        status = "BLOCKED"
    print("=" * 72)
    print("AI FITNESS DATASET STAGE 4 EXPORT")
    print("=" * 72)
    print(f"Export Status : {status}")
    print(f"Files         : {len(state.files)}")
    print(f"Warnings      : {len(state.warnings)}")
    print(f"Output dir    : {resolve(args.output_dir, DEFAULT_EXPORTS)}")
    print("=" * 72)
    return 1 if status == "BLOCKED" else 0


if __name__ == "__main__":
    sys.exit(main())
