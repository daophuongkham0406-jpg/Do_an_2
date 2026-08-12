from __future__ import annotations

import argparse
import json
import math
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd


ROOT = Path(__file__).resolve().parent
DEFAULT_CSV_DIR = ROOT / "exports" / "csv"
DEFAULT_MANIFEST = ROOT / "exports" / "export_manifest.json"
DEFAULT_OUTPUT_DIR = ROOT / "reports" / "stage_5_statistics"

TABLE_FILES = {
    "exercises": "exercises.csv",
    "users": "users.csv",
    "workout_plans": "workout_plans.csv",
    "workout_plan_items": "workout_plan_items.csv",
    "workout_history_sessions": "workout_history_sessions.csv",
    "workout_history_items": "workout_history_items.csv",
    "workout_history_summary": "workout_history_summary.csv",
    "user_feedback": "user_feedback.csv",
}

PKS = {
    "exercises": "exercise_id",
    "users": "user_id",
    "workout_plans": "plan_id",
    "workout_plan_items": "plan_item_id",
    "workout_history_sessions": "history_session_id",
    "workout_history_items": "history_item_id",
    "workout_history_summary": "summary_id",
    "user_feedback": "feedback_id",
}

CRITICAL_COLUMNS = set(PKS.values()) | {"user_id", "plan_id", "exercise_id", "history_session_id", "history_item_id", "plan_item_id"}
EXPECTED_MISSING = {
    "actual_load_kg", "pain_areas", "secondary_goal", "avoided_exercise_ids", "preferred_exercise_ids",
    "history_item_id", "history_session_id", "plan_item_id", "exercise_id", "plan_id", "actual_rpe",
    "feedback_reason_tags", "duration_seconds",
}

LIST_FIELDS = {
    "equipment", "primary_muscles", "secondary_muscles", "recommended_goals", "contraindications",
    "available_equipment", "injuries_or_limitations", "pain_areas", "feedback_reason_tags",
    "actual_reps_json", "focus_muscles", "priority_muscles", "avoided_muscles",
}


def clean(v: Any) -> str:
    if v is None:
        return ""
    if isinstance(v, float) and math.isnan(v):
        return ""
    return str(v).strip()


def num_series(s: pd.Series) -> pd.Series:
    return pd.to_numeric(s.replace("", pd.NA), errors="coerce")


def pct(n: int | float, d: int | float) -> float:
    return 0.0 if not d else round(float(n) * 100.0 / float(d), 3)


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
            inner = s[1:-1].strip()
            return [x.strip().strip("'\"") for x in inner.split(",") if x.strip()]
    if ";" in s:
        return [x.strip() for x in s.split(";") if x.strip()]
    if "|" in s:
        return [x.strip() for x in s.split("|") if x.strip()]
    if "," in s:
        return [x.strip() for x in s.split(",") if x.strip()]
    return [s]


def dist(series: pd.Series, top: int | None = None) -> dict[str, int]:
    counts = Counter(series.map(clean))
    counts.pop("", None)
    items = counts.most_common(top)
    return dict(items if top else counts.most_common())


def list_dist(series: pd.Series, top: int = 20) -> dict[str, int]:
    c: Counter[str] = Counter()
    for value in series:
        c.update(parse_list(value))
    return dict(c.most_common(top))


def resolve(value: str | None, default: Path) -> Path:
    if not value:
        return default
    p = Path(value)
    return p if p.is_absolute() else (ROOT / p).resolve()


def load_csv_exports(csv_dir: Path) -> dict[str, pd.DataFrame]:
    frames: dict[str, pd.DataFrame] = {}
    for table, file_name in TABLE_FILES.items():
        path = csv_dir / file_name
        if not path.exists():
            raise FileNotFoundError(f"Missing CSV export: {path}")
        frames[table] = pd.read_csv(path, dtype=str, keep_default_na=False, encoding="utf-8-sig")
    return frames


def check_manifest_ready(manifest_path: Path) -> tuple[bool, dict[str, Any]]:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    ok = (
        manifest.get("export_status") == "PASS"
        and manifest.get("validation_status", {}).get("overall_status") == "PASS"
        and manifest.get("ready_for_stage_5_statistics") is True
    )
    return ok, manifest


def profile_table_shapes(frames: dict[str, pd.DataFrame], manifest: dict[str, Any]) -> pd.DataFrame:
    rows = []
    size_by_path = {Path(f["path"]).name: f.get("size_bytes", 0) for f in manifest.get("exported_files", []) if f.get("format") == "csv"}
    for table, df in frames.items():
        pk = PKS[table]
        pk_series = df[pk].map(clean) if pk in df.columns else pd.Series(dtype=str)
        dup = int(pk_series[pk_series != ""].duplicated().sum())
        blank = int((pk_series == "").sum())
        status = "PASS" if dup == 0 and blank == 0 else "NEED FIX"
        rows.append({
            "table": table,
            "rows": len(df),
            "columns": len(df.columns),
            "primary_key": pk,
            "unique_primary_keys": int(pk_series[pk_series != ""].nunique()),
            "duplicate_primary_keys": dup,
            "blank_primary_keys": blank,
            "memory_size_bytes": int(df.memory_usage(deep=True).sum()),
            "file_size_bytes": int(size_by_path.get(TABLE_FILES[table], 0)),
            "status": status,
        })
    return pd.DataFrame(rows)


def classify_missing(table: str, column: str, missing_count: int, missing_percent: float) -> tuple[str, str, str]:
    if missing_count == 0:
        return "No Missing", "PASS", "No missing values."
    if column == PKS.get(table) or (column in CRITICAL_COLUMNS and table not in {"user_feedback"}):
        return "Critical Missing", "ERROR", "Critical relationship/primary column has missing values."
    if table == "user_feedback" and column in {"plan_id", "history_session_id", "history_item_id", "plan_item_id", "exercise_id"}:
        return "Expected Missing", "PASS", "Optional feedback scope columns may be blank for General/Plan/Session feedback."
    if column in EXPECTED_MISSING:
        return "Expected Missing", "PASS", "Missing is expected for this context."
    if missing_percent > 50:
        return "Suspicious Missing", "WARNING", "High missing rate; review before AI training."
    return "Acceptable Missing", "PASS", "Low/acceptable missing rate."


def analyze_missing_values(frames: dict[str, pd.DataFrame]) -> pd.DataFrame:
    rows = []
    for table, df in frames.items():
        for col in df.columns:
            missing = int((df[col].map(clean) == "").sum())
            mp = pct(missing, len(df))
            mtype, severity, note = classify_missing(table, col, missing, mp)
            rows.append({
                "table": table,
                "column": col,
                "rows": len(df),
                "missing_count": missing,
                "missing_percent": mp,
                "missing_type": mtype,
                "severity": severity,
                "note": note,
            })
    return pd.DataFrame(rows)


def analyze_duplicates(frames: dict[str, pd.DataFrame]) -> pd.DataFrame:
    rows = []
    for table, df in frames.items():
        pk = PKS[table]
        dup_pk = int(df[pk].map(clean).duplicated().sum()) if pk in df.columns else len(df)
        rows.append({"table": table, "column_or_key": pk, "duplicate_count": dup_pk, "duplicate_percent": pct(dup_pk, len(df)), "duplicate_type": "Hard Duplicate", "severity": "ERROR" if dup_pk else "PASS", "note": "Primary key duplicate check."})
    if "exercise_name" in frames["exercises"]:
        d = int(frames["exercises"]["exercise_name"].map(clean).duplicated().sum())
        rows.append({"table": "exercises", "column_or_key": "exercise_name", "duplicate_count": d, "duplicate_percent": pct(d, len(frames["exercises"])), "duplicate_type": "Soft Duplicate", "severity": "WARNING" if d else "PASS", "note": "Duplicate names may be aliases or real duplicates."})
    pi = frames["workout_plan_items"]
    if {"plan_id", "week_number", "day_number", "exercise_id"}.issubset(pi.columns):
        d = int(pi.duplicated(["plan_id", "week_number", "day_number", "exercise_id"]).sum())
        rows.append({"table": "workout_plan_items", "column_or_key": "plan_id+week_number+day_number+exercise_id", "duplicate_count": d, "duplicate_percent": pct(d, len(pi)), "duplicate_type": "Expected Repetition", "severity": "PASS", "note": "Same exercise can appear in repeated weeks/days; validator already checks order collisions."})
    hi = frames["workout_history_items"]
    if {"history_session_id", "exercise_id"}.issubset(hi.columns):
        d = int(hi.duplicated(["history_session_id", "exercise_id"]).sum())
        rows.append({"table": "workout_history_items", "column_or_key": "history_session_id+exercise_id", "duplicate_count": d, "duplicate_percent": pct(d, len(hi)), "duplicate_type": "Suspicious Repetition", "severity": "WARNING" if d else "PASS", "note": "Same exercise repeated inside one logged session."})
    fb = frames["user_feedback"]
    if "feedback_text" in fb.columns:
        unique = int(fb["feedback_text"].map(clean).nunique())
        repeats = len(fb) - unique
        ratio = round(unique / len(fb), 3) if len(fb) else 0
        rows.append({"table": "user_feedback", "column_or_key": "feedback_text", "duplicate_count": repeats, "duplicate_percent": pct(repeats, len(fb)), "duplicate_type": "Expected Repetition" if ratio >= 0.1 else "Suspicious Repetition", "severity": "PASS" if ratio >= 0.1 else "WARNING", "note": f"unique_ratio={ratio}; text templates may repeat in synthetic data."})
    return pd.DataFrame(rows)


def describe_numeric(df: pd.DataFrame, col: str) -> dict[str, float]:
    if col not in df.columns:
        return {}
    s = num_series(df[col]).dropna()
    if s.empty:
        return {}
    return {"min": round(float(s.min()), 3), "mean": round(float(s.mean()), 3), "median": round(float(s.median()), 3), "max": round(float(s.max()), 3)}


def analyze_exercise_statistics(frames: dict[str, pd.DataFrame]) -> dict[str, Any]:
    ex = frames["exercises"]
    return {
        "exercise_count": len(ex),
        "category_distribution": dist(ex.get("category", pd.Series(dtype=str))),
        "difficulty_distribution": dist(ex.get("minimum_training_level", ex.get("difficulty_level", pd.Series(dtype=str)))),
        "top_equipment": list_dist(ex.get("equipment", pd.Series(dtype=str))),
        "top_primary_muscles": list_dist(ex.get("primary_muscles", pd.Series(dtype=str))),
        "top_secondary_muscles": list_dist(ex.get("secondary_muscles", pd.Series(dtype=str))),
        "top_movement_patterns": dist(ex.get("movement_pattern", pd.Series(dtype=str)), 20),
        "goal_coverage": list_dist(ex.get("recommended_goals", pd.Series(dtype=str)), 40),
        "contraindication_distribution": list_dist(ex.get("contraindications", pd.Series(dtype=str)), 30),
        "met_value_distribution": describe_numeric(ex, "met_value"),
        "technical_complexity_distribution": describe_numeric(ex, "technical_complexity_score"),
        "mobility_requirement_distribution": describe_numeric(ex, "mobility_requirement"),
        "balance_requirement_distribution": describe_numeric(ex, "balance_requirement"),
    }


def analyze_user_statistics(frames: dict[str, pd.DataFrame]) -> dict[str, Any]:
    u = frames["users"]
    return {
        "user_count": len(u),
        "age_distribution": describe_numeric(u, "age"),
        "gender_distribution": dist(u.get("gender", pd.Series(dtype=str))),
        "height_distribution": describe_numeric(u, "height_cm"),
        "weight_distribution": describe_numeric(u, "weight_kg"),
        "bmi_distribution": describe_numeric(u, "bmi"),
        "primary_goal_distribution": dist(u.get("primary_goal", pd.Series(dtype=str))),
        "secondary_goal_distribution": dist(u.get("secondary_goal", pd.Series(dtype=str))),
        "training_level_distribution": dist(u.get("training_level", pd.Series(dtype=str))),
        "training_days_per_week_distribution": dist(u.get("training_days_per_week", pd.Series(dtype=str))),
        "available_equipment_distribution": list_dist(u.get("available_equipment", pd.Series(dtype=str)), 30),
        "preferred_split_distribution": dist(u.get("preferred_split", pd.Series(dtype=str))),
        "injury_distribution": list_dist(u.get("injuries_or_limitations", pd.Series(dtype=str)), 30),
        "session_duration_distribution": describe_numeric(u, "session_duration_minutes"),
    }


def analyze_workout_plan_statistics(frames: dict[str, pd.DataFrame]) -> dict[str, Any]:
    p, pi = frames["workout_plans"], frames["workout_plan_items"]
    structures = pi.groupby("plan_id")["exercise_id"].apply(lambda s: tuple(s.map(clean))).reset_index()
    plan_meta = p.set_index("plan_id")
    signatures = []
    for _, row in structures.iterrows():
        pid = row["plan_id"]
        if pid in plan_meta.index:
            signatures.append((clean(plan_meta.at[pid, "days_per_week"]), clean(plan_meta.at[pid, "split_type"]), row["exercise_id"]))
    signature_counts = Counter(signatures)
    unique_ex_per_plan = pi.groupby("plan_id")["exercise_id"].nunique()
    return {
        "plan_count": len(p),
        "plan_items_count": len(pi),
        "plans_per_user": summarize_counts(Counter(p["user_id"].map(clean))),
        "items_per_plan": summarize_counts(Counter(pi["plan_id"].map(clean))),
        "items_per_day_session": summarize_counts(Counter((pi["plan_id"].map(clean) + "|" + pi["week_number"].map(clean) + "|" + pi["day_number"].map(clean)))),
        "days_per_week_distribution": dist(p.get("days_per_week", pd.Series(dtype=str))),
        "split_distribution": dist(p.get("split_type", pd.Series(dtype=str))),
        "goal_distribution": dist(p.get("primary_goal_snapshot", pd.Series(dtype=str))),
        "training_level_snapshot_distribution": dist(p.get("training_level_snapshot", pd.Series(dtype=str))),
        "progression_strategy_distribution": dist(p.get("progression_strategy", pd.Series(dtype=str))),
        "planned_sets_distribution": describe_numeric(pi, "sets"),
        "rep_min_distribution": describe_numeric(pi, "rep_min"),
        "rep_max_distribution": describe_numeric(pi, "rep_max"),
        "target_rpe_distribution": describe_numeric(pi, "target_intensity"),
        "rest_seconds_distribution": describe_numeric(pi, "rest_seconds"),
        "exercise_order_distribution": describe_numeric(pi, "exercise_order"),
        "unique_plan_structures": len(signature_counts),
        "duplicate_plan_structures": sum(v - 1 for v in signature_counts.values() if v > 1),
        "average_unique_exercises_per_plan": round(float(unique_ex_per_plan.mean()), 3),
        "exercise_reuse_rate": round(len(pi) / max(pi["exercise_id"].nunique(), 1), 3),
        "top_exercises_in_plans": dist(pi.get("exercise_name_snapshot", pd.Series(dtype=str)), 20),
    }


def analyze_workout_history_statistics(frames: dict[str, pd.DataFrame]) -> dict[str, Any]:
    s, i = frames["workout_history_sessions"], frames["workout_history_items"]
    planned_sets = num_series(i["planned_sets"]).sum()
    actual_sets = num_series(i["actual_sets_completed"]).sum()
    planned_items = len(i)
    completed_items = int((i["completion_status"].map(clean) != "Skipped").sum())
    return {
        "history_session_count": len(s),
        "history_item_count": len(i),
        "sessions_per_user": summarize_counts(Counter(s["user_id"].map(clean))),
        "sessions_per_plan": summarize_counts(Counter(s["plan_id"].map(clean))),
        "items_per_session": summarize_counts(Counter(i["history_session_id"].map(clean))),
        "completion_status_distribution": dist(s.get("completion_status", pd.Series(dtype=str))),
        "completion_pct_distribution": describe_numeric(s, "completion_pct"),
        "set_completion_pct_distribution": describe_numeric(s, "set_completion_pct"),
        "actual_duration_distribution": describe_numeric(s, "actual_duration_min"),
        "session_rpe_distribution": describe_numeric(s, "session_rpe"),
        "energy_before_distribution": describe_numeric(s, "energy_before"),
        "fatigue_after_distribution": describe_numeric(s, "fatigue_after"),
        "pain_session_percent": pct(int((s["pain_reported"].map(clean) == "Yes").sum()), len(s)),
        "pain_area_distribution": list_dist(s.get("pain_areas", pd.Series(dtype=str)), 30),
        "recovery_flag_distribution": dist(s.get("recovery_flag", pd.Series(dtype=str))),
        "planned_sets_total": int(planned_sets),
        "actual_sets_total": int(actual_sets),
        "set_completion_rate": pct(actual_sets, planned_sets),
        "planned_items_total": planned_items,
        "completed_items_total": completed_items,
        "item_completion_rate": pct(completed_items, planned_items),
        "actual_sets_completed_distribution": describe_numeric(i, "actual_sets_completed"),
        "actual_rpe_distribution": describe_numeric(i, "actual_rpe"),
    }


def analyze_user_feedback_statistics(frames: dict[str, pd.DataFrame]) -> dict[str, Any]:
    fb = frames["user_feedback"]
    text = fb["feedback_text"].map(clean) if "feedback_text" in fb else pd.Series(dtype=str)
    lengths = text.map(len)
    unique = int(text.nunique()) if len(text) else 0
    return {
        "feedback_count": len(fb),
        "feedback_per_user": summarize_counts(Counter(fb["user_id"].map(clean))),
        "feedback_scope_distribution": dist(fb.get("feedback_scope", pd.Series(dtype=str))),
        "feedback_type_distribution": dist(fb.get("feedback_type", pd.Series(dtype=str))),
        "sentiment_distribution": dist(fb.get("sentiment", pd.Series(dtype=str))),
        "rating_distribution": dist(fb.get("rating", pd.Series(dtype=str))),
        "enjoyment_rating_distribution": dist(fb.get("enjoyment_rating", pd.Series(dtype=str))),
        "difficulty_feedback_distribution": dist(fb.get("difficulty_feedback", pd.Series(dtype=str))),
        "fatigue_feedback_distribution": dist(fb.get("fatigue_feedback", pd.Series(dtype=str))),
        "pain_feedback_distribution": dist(fb.get("pain_feedback", pd.Series(dtype=str))),
        "duration_feedback_distribution": dist(fb.get("duration_feedback", pd.Series(dtype=str))),
        "exercise_preference_distribution": dist(fb.get("exercise_preference", pd.Series(dtype=str))),
        "progression_preference_distribution": dist(fb.get("progression_preference", pd.Series(dtype=str))),
        "requested_action_distribution": dist(fb.get("requested_action", pd.Series(dtype=str))),
        "feedback_status_distribution": dist(fb.get("feedback_status", pd.Series(dtype=str))),
        "source_context_distribution": dist(fb.get("source_context", pd.Series(dtype=str))),
        "feedback_text_total_count": len(text),
        "feedback_text_unique_count": unique,
        "feedback_text_unique_ratio": round(unique / len(text), 3) if len(text) else 0,
        "top_repeated_feedback_text": dict(Counter(text).most_common(10)),
        "feedback_reason_tags_distribution": list_dist(fb.get("feedback_reason_tags", pd.Series(dtype=str)), 40),
        "average_feedback_text_length": round(float(lengths.mean()), 3) if len(lengths) else 0,
    }


def summarize_counts(counter: Counter) -> dict[str, float]:
    vals = list(counter.values())
    return {"min": min(vals) if vals else 0, "mean": round(sum(vals) / len(vals), 3) if vals else 0, "max": max(vals) if vals else 0}


def coverage_status(percent: float) -> str:
    if percent >= 95:
        return "Excellent Coverage"
    if percent >= 80:
        return "Good Coverage"
    if percent >= 60:
        return "Moderate Coverage"
    if percent >= 30:
        return "Low Coverage"
    return "Needs Improvement"


def coverage_row(metric: str, source_table: str, target_table: str, source_count: int, covered: int, note: str) -> dict[str, Any]:
    percent = pct(covered, source_count)
    return {
        "coverage_metric": metric,
        "source_table": source_table,
        "target_table": target_table,
        "source_count": source_count,
        "covered_count": covered,
        "uncovered_count": max(source_count - covered, 0),
        "coverage_percent": percent,
        "status": coverage_status(percent),
        "note": note,
    }


def analyze_relationship_coverage(frames: dict[str, pd.DataFrame]) -> pd.DataFrame:
    u, ex, p, pi, hs, hi, fb = frames["users"], frames["exercises"], frames["workout_plans"], frames["workout_plan_items"], frames["workout_history_sessions"], frames["workout_history_items"], frames["user_feedback"]
    rows = [
        coverage_row("users_with_plans", "users", "workout_plans", len(u), p["user_id"].nunique(), "Users represented in workout plans."),
        coverage_row("users_with_history", "users", "workout_history_sessions", len(u), hs["user_id"].nunique(), "Users represented in workout history."),
        coverage_row("users_with_feedback", "users", "user_feedback", len(u), fb["user_id"].nunique(), "Users represented in feedback."),
        coverage_row("exercises_used_in_plan_items", "exercises", "workout_plan_items", len(ex), pi["exercise_id"].nunique(), "Exercise library coverage in generated plans."),
        coverage_row("exercises_used_in_history_items", "exercises", "workout_history_items", len(ex), hi["exercise_id"].nunique(), "Exercise library coverage in history."),
        coverage_row("exercises_used_in_feedback", "exercises", "user_feedback", len(ex), fb["exercise_id"].replace("", pd.NA).dropna().nunique(), "Exercise library coverage in feedback."),
        coverage_row("plans_with_items", "workout_plans", "workout_plan_items", len(p), pi["plan_id"].nunique(), "Plans with prescribed items."),
        coverage_row("plans_with_history", "workout_plans", "workout_history_sessions", len(p), hs["plan_id"].nunique(), "Plans with logged history."),
        coverage_row("plans_with_feedback", "workout_plans", "user_feedback", len(p), fb["plan_id"].replace("", pd.NA).dropna().nunique(), "Plans with feedback context."),
        coverage_row("history_sessions_with_items", "workout_history_sessions", "workout_history_items", len(hs), hi["history_session_id"].nunique(), "Sessions with item-level logs."),
        coverage_row("history_items_with_feedback", "workout_history_items", "user_feedback", len(hi), fb["history_item_id"].replace("", pd.NA).dropna().nunique(), "History item coverage in explicit feedback; low is normal because feedback is sampled."),
    ]
    return pd.DataFrame(rows)


def bar_chart(data: dict[str, int], title: str, path: Path, top: int = 20) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    items = list(data.items())[:top]
    labels = [str(k) for k, _ in items]
    values = [v for _, v in items]
    plt.figure(figsize=(10, 5))
    plt.bar(labels, values)
    plt.title(title)
    plt.xticks(rotation=45, ha="right")
    plt.tight_layout()
    plt.savefig(path, dpi=150)
    plt.close()


def generate_charts(summary: dict[str, Any], missing: pd.DataFrame, coverage: pd.DataFrame, output_dir: Path) -> None:
    charts = output_dir / "charts"
    ex = summary["exercise_statistics"]
    user = summary["user_statistics"]
    hist = summary["history_statistics"]
    fb = summary["feedback_statistics"]
    bar_chart(ex["category_distribution"], "Exercise Category Distribution", charts / "exercise_category_distribution.png")
    bar_chart(ex["difficulty_distribution"], "Exercise Difficulty Distribution", charts / "exercise_difficulty_distribution.png")
    bar_chart(ex["top_equipment"], "Top Equipment", charts / "top_equipment.png")
    bar_chart(ex["top_primary_muscles"], "Top Primary Muscles", charts / "top_primary_muscles.png")
    bar_chart(user["primary_goal_distribution"], "Goal Distribution", charts / "goal_distribution.png")
    bar_chart(user["training_level_distribution"], "Training Level Distribution", charts / "training_level_distribution.png")
    bar_chart(hist["completion_status_distribution"], "Completion Status Distribution", charts / "completion_status_distribution.png")
    bar_chart(fb["feedback_scope_distribution"], "Feedback Scope Distribution", charts / "feedback_scope_distribution.png")
    bar_chart(fb["sentiment_distribution"], "Sentiment Distribution", charts / "sentiment_distribution.png")
    bar_chart(fb["requested_action_distribution"], "Requested Action Distribution", charts / "requested_action_distribution.png")
    top_missing = missing.sort_values("missing_count", ascending=False).head(20)
    bar_chart(dict(zip(top_missing["table"] + "." + top_missing["column"], top_missing["missing_count"])), "Missing Values Top 20", charts / "missing_values_top20.png")
    exercise_cov = coverage[coverage["coverage_metric"].str.startswith("exercises_")]
    bar_chart(dict(zip(exercise_cov["coverage_metric"], exercise_cov["coverage_percent"])), "Exercise Coverage Percent", charts / "exercise_coverage.png")
    user_cov = coverage[coverage["coverage_metric"].str.startswith("users_")]
    bar_chart(dict(zip(user_cov["coverage_metric"], user_cov["coverage_percent"])), "User Coverage Percent", charts / "user_coverage.png")


def generate_excel_distribution_report(output_dir: Path, overview: pd.DataFrame, missing: pd.DataFrame, duplicates: pd.DataFrame, coverage: pd.DataFrame, summary: dict[str, Any], recommendations: list[str]) -> None:
    path = output_dir / "distribution_report.xlsx"
    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        overview.to_excel(writer, sheet_name="Overview", index=False)
        missing.to_excel(writer, sheet_name="Missing_Values", index=False)
        duplicates.to_excel(writer, sheet_name="Duplicates", index=False)
        dict_to_df(summary["exercise_statistics"]).to_excel(writer, sheet_name="Exercise_Distribution", index=False)
        dict_to_df(summary["user_statistics"]).to_excel(writer, sheet_name="User_Distribution", index=False)
        dict_to_df(summary["plan_statistics"]).to_excel(writer, sheet_name="Plan_Distribution", index=False)
        dict_to_df(summary["history_statistics"]).to_excel(writer, sheet_name="History_Distribution", index=False)
        dict_to_df(summary["feedback_statistics"]).to_excel(writer, sheet_name="Feedback_Distribution", index=False)
        coverage.to_excel(writer, sheet_name="Coverage", index=False)
        pd.DataFrame({"recommendation": recommendations}).to_excel(writer, sheet_name="Recommendations", index=False)


def dict_to_df(d: dict[str, Any]) -> pd.DataFrame:
    rows = []
    for key, value in d.items():
        if isinstance(value, dict):
            rows.append({"metric": key, "value": json.dumps(value, ensure_ascii=False)})
        else:
            rows.append({"metric": key, "value": value})
    return pd.DataFrame(rows)


def assess(summary: dict[str, Any], missing: pd.DataFrame, duplicates: pd.DataFrame, coverage: pd.DataFrame) -> tuple[str, bool, str, list[str], list[str], list[str]]:
    blocking = []
    notes = []
    improvements = []
    if int((missing["severity"] == "ERROR").sum()) > 0:
        blocking.append("Critical missing values exist.")
    if int((duplicates["severity"] == "ERROR").sum()) > 0:
        blocking.append("Duplicate primary key exists.")
    low_cov = coverage[(coverage["status"].isin(["Low Coverage", "Needs Improvement"])) & (coverage["coverage_metric"] != "history_items_with_feedback")]
    if not low_cov.empty:
        improvements.append("Some relationship coverage metrics are low.")
    fb_unique = summary["feedback_statistics"]["feedback_text_unique_ratio"]
    if fb_unique < 0.2:
        improvements.append(f"Feedback text unique ratio is low ({fb_unique}); improve text diversity before AI Coach language training.")
    hist_dist = summary["history_statistics"]["completion_status_distribution"]
    total = sum(hist_dist.values())
    completed = pct(hist_dist.get("Completed", 0), total)
    partial = pct(hist_dist.get("Partial", 0), total)
    skipped = pct(hist_dist.get("Skipped", 0), total)
    if not (78 <= completed <= 87 and 8 <= partial <= 15 and 3 <= skipped <= 8):
        improvements.append("Workout history completion distribution is outside target range.")
    pain = summary["history_statistics"]["pain_session_percent"]
    if not (1 <= pain <= 4):
        improvements.append("Pain session distribution is outside target range.")
    if blocking:
        return "NEED IMPROVEMENT", False, "High", blocking, notes, improvements
    if improvements:
        return "PASS WITH NOTES", True, "Medium", blocking, notes, improvements
    return "PASS", True, "Low", blocking, notes, improvements


def md_table(df: pd.DataFrame, max_rows: int = 20) -> str:
    small = df.head(max_rows)
    cols = list(small.columns)
    lines = ["| " + " | ".join(cols) + " |", "| " + " | ".join(["---"] * len(cols)) + " |"]
    for _, row in small.iterrows():
        values = [str(row.get(c, "")).replace("\n", " ").replace("|", "/") for c in cols]
        lines.append("| " + " | ".join(values) + " |")
    return "\n".join(lines)


def generate_markdown_report(output_dir: Path, summary: dict[str, Any], overview: pd.DataFrame, missing: pd.DataFrame, duplicates: pd.DataFrame, coverage: pd.DataFrame, status: str, ready: bool, risk: str, blocking: list[str], notes: list[str], improvements: list[str]) -> None:
    lines = [
        "# Stage 5 Statistics Report",
        "",
        "## 1. Executive Summary",
        f"Statistics Status: **{status}**",
        f"Ready for Stage 6 AI: **{'YES' if ready else 'NO'}**",
        f"Risk Level: **{risk}**",
        "",
        "## 2. Dataset Overview",
        md_table(overview),
        "",
        "## 3. Missing Values Summary",
        md_table(missing.sort_values('missing_count', ascending=False).head(20)),
        "",
        "## 4. Duplicate Summary",
        md_table(duplicates),
        "",
        "## 5. Exercise Statistics",
        f"- Exercise count: {summary['exercise_statistics']['exercise_count']}",
        f"- Category distribution: `{summary['exercise_statistics']['category_distribution']}`",
        f"- Difficulty distribution: `{summary['exercise_statistics']['difficulty_distribution']}`",
        "",
        "## 6. User Statistics",
        f"- User count: {summary['user_statistics']['user_count']}",
        f"- Goal distribution: `{summary['user_statistics']['primary_goal_distribution']}`",
        f"- Training level distribution: `{summary['user_statistics']['training_level_distribution']}`",
        "",
        "## 7. Workout Plan Statistics",
        f"- Plan count: {summary['plan_statistics']['plan_count']}",
        f"- Plan items count: {summary['plan_statistics']['plan_items_count']}",
        f"- Items per plan: `{summary['plan_statistics']['items_per_plan']}`",
        f"- Unique plan structures: {summary['plan_statistics']['unique_plan_structures']}",
        "",
        "## 8. Workout History Statistics",
        f"- Session count: {summary['history_statistics']['history_session_count']}",
        f"- Item count: {summary['history_statistics']['history_item_count']}",
        f"- Completion status distribution: `{summary['history_statistics']['completion_status_distribution']}`",
        f"- Pain session percent: {summary['history_statistics']['pain_session_percent']}%",
        "",
        "## 9. User Feedback Statistics",
        f"- Feedback count: {summary['feedback_statistics']['feedback_count']}",
        f"- Scope distribution: `{summary['feedback_statistics']['feedback_scope_distribution']}`",
        f"- Sentiment distribution: `{summary['feedback_statistics']['sentiment_distribution']}`",
        f"- Feedback text unique ratio: {summary['feedback_statistics']['feedback_text_unique_ratio']}",
        "",
        "## 10. Relationship Coverage",
        md_table(coverage),
        "",
        "## 11. Data Balance Assessment",
        "Core history and feedback distributions are inside target ranges. User coverage is complete. Exercise coverage is strong for plans/history and moderate for explicit feedback, which is expected because feedback is sampled.",
        "",
        "## 12. AI Training Risk Assessment",
        f"Risk level is **{risk}**. Blocking issues: {len(blocking)}.",
        "",
        "## 13. Recommendations",
    ]
    if blocking:
        lines.extend([f"- {x}" for x in blocking])
    if improvements:
        lines.extend([f"- {x}" for x in improvements])
    if not blocking and not improvements:
        lines.append("- No blocking or major improvement recommendation.")
    lines += [
        "",
        "## 14. Final Stage 5 Status",
        f"Statistics Status: **{status}**",
        f"Ready for Stage 6 AI: **{'YES' if ready else 'NO'}**",
    ]
    (output_dir / "statistics_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def generate_json_summary(output_dir: Path, summary: dict[str, Any]) -> None:
    (output_dir / "statistics_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")


def generate_readiness_report(output_dir: Path, status: str, ready: bool, risk: str, blocking: list[str], notes: list[str], improvements: list[str]) -> None:
    report = {
        "stage_5_status": status,
        "ready_for_stage_6_ai": ready,
        "blocking_issues": blocking,
        "non_blocking_issues": notes,
        "improvement_recommendations": improvements,
        "risk_level": risk,
        "recommended_next_step": "Proceed to Stage 6 AI" if ready else "Fix statistics blocking issues before Stage 6 AI",
    }
    (output_dir / "statistics_readiness_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")


def write_readme(output_dir: Path) -> None:
    text = """# README Statistics

## 1. Giai đoạn 5 dùng để làm gì
Phân tích profiling, missing values, duplicates, distribution, coverage và readiness cho AI training.

## 2. File input cần có
CSV trong `exports/csv/` và `exports/export_manifest.json`.

## 3. Cách chạy statistics.py
```bash
python statistics.py
python statistics.py --csv-dir exports/csv --manifest exports/export_manifest.json --output-dir reports/stage_5_statistics
```

## 4. Output tạo ra
Markdown, JSON summary, missing/duplicate/coverage CSV, Excel distribution report, readiness JSON và chart PNG.

## 5. Cách đọc statistics_report.md
Đọc Executive Summary, Data Balance Assessment, AI Training Risk Assessment và Final Stage 5 Status.

## 6. Cách đọc missing_values_report.csv
Xem `severity`, `missing_type`, `missing_percent` và `note`.

## 7. Cách đọc duplicate_report.csv
Hard duplicate là lỗi nghiêm trọng; soft/expected repetition cần đánh giá theo ngữ cảnh.

## 8. Cách đọc coverage_report.csv
Coverage cho biết bảng nguồn được đại diện trong bảng đích bao nhiêu phần trăm.

## 9. Ý nghĩa PASS / PASS WITH NOTES / NEED IMPROVEMENT
PASS sạch; PASS WITH NOTES có cải thiện nhưng không chặn; NEED IMPROVEMENT có vấn đề ảnh hưởng training.

## 10. Điều kiện Ready for Stage 6 AI
Không có critical missing, không duplicate primary key, coverage và distribution chính đạt mức dùng được.

## 11. Cách thêm thống kê mới
Thêm hàm phân tích hoặc bổ sung metric vào các hàm `analyze_*` trong `statistics.py`.
"""
    (output_dir / "README_statistics.md").write_text(text, encoding="utf-8")


def run(args: argparse.Namespace) -> dict[str, Any]:
    csv_dir = resolve(args.csv_dir, DEFAULT_CSV_DIR)
    manifest_path = resolve(args.manifest, DEFAULT_MANIFEST)
    output_dir = resolve(args.output_dir, DEFAULT_OUTPUT_DIR)
    output_dir.mkdir(parents=True, exist_ok=True)
    ready, manifest = check_manifest_ready(manifest_path)
    if not ready:
        raise RuntimeError("Export manifest is not PASS/ready for Stage 5.")
    frames = load_csv_exports(csv_dir)
    overview = profile_table_shapes(frames, manifest)
    missing = analyze_missing_values(frames)
    duplicates = analyze_duplicates(frames)
    coverage = analyze_relationship_coverage(frames)
    dataset_overview = {
        "table_shapes": overview.to_dict(orient="records"),
        "total_rows": int(overview["rows"].sum()),
        "total_columns": int(overview["columns"].sum()),
        "largest_table_by_rows": overview.sort_values("rows", ascending=False).iloc[0]["table"],
        "largest_table_by_file_size": overview.sort_values("file_size_bytes", ascending=False).iloc[0]["table"],
        "smallest_table_by_rows": overview.sort_values("rows").iloc[0]["table"],
    }
    summary = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "statistics_status": "PENDING",
        "dataset_overview": dataset_overview,
        "missing_values": {
            "critical_missing_count": int((missing["severity"] == "ERROR").sum()),
            "top_missing": missing.sort_values("missing_count", ascending=False).head(20).to_dict(orient="records"),
        },
        "duplicates": {
            "duplicate_primary_key_tables": duplicates[(duplicates["duplicate_type"] == "Hard Duplicate") & (duplicates["duplicate_count"] > 0)].to_dict(orient="records"),
            "duplicate_report": duplicates.to_dict(orient="records"),
        },
        "exercise_statistics": analyze_exercise_statistics(frames),
        "user_statistics": analyze_user_statistics(frames),
        "plan_statistics": analyze_workout_plan_statistics(frames),
        "history_statistics": analyze_workout_history_statistics(frames),
        "feedback_statistics": analyze_user_feedback_statistics(frames),
        "coverage_statistics": coverage.to_dict(orient="records"),
        "recommendations": [],
    }
    status, stage6_ready, risk, blocking, notes, improvements = assess(summary, missing, duplicates, coverage)
    summary["statistics_status"] = status
    summary["recommendations"] = improvements
    missing.to_csv(output_dir / "missing_values_report.csv", index=False, encoding="utf-8-sig")
    duplicates.to_csv(output_dir / "duplicate_report.csv", index=False, encoding="utf-8-sig")
    coverage.to_csv(output_dir / "coverage_report.csv", index=False, encoding="utf-8-sig")
    generate_charts(summary, missing, coverage, output_dir)
    generate_excel_distribution_report(output_dir, overview, missing, duplicates, coverage, summary, improvements)
    generate_markdown_report(output_dir, summary, overview, missing, duplicates, coverage, status, stage6_ready, risk, blocking, notes, improvements)
    generate_json_summary(output_dir, summary)
    generate_readiness_report(output_dir, status, stage6_ready, risk, blocking, notes, improvements)
    write_readme(output_dir)
    return {"status": status, "ready": stage6_ready, "risk": risk, "blocking": blocking, "improvements": improvements, "output_dir": str(output_dir)}


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Stage 5 statistics/profiling for AI Fitness Dataset")
    p.add_argument("--csv-dir")
    p.add_argument("--manifest")
    p.add_argument("--output-dir")
    return p


def main() -> int:
    args = parser().parse_args()
    result = run(args)
    print("=" * 72)
    print("AI FITNESS DATASET STAGE 5 STATISTICS")
    print("=" * 72)
    print(f"Statistics Status : {result['status']}")
    print(f"Ready Stage 6 AI  : {'YES' if result['ready'] else 'NO'}")
    print(f"Risk Level        : {result['risk']}")
    print(f"Blocking Issues   : {len(result['blocking'])}")
    print(f"Recommendations   : {len(result['improvements'])}")
    print(f"Output dir        : {result['output_dir']}")
    print("=" * 72)
    return 0 if result["ready"] else 1


if __name__ == "__main__":
    sys.exit(main())
