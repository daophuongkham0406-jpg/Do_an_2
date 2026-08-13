from __future__ import annotations

import json
from datetime import datetime
from functools import lru_cache
from pathlib import Path
from typing import Any

from ml_integration.integration_pipeline import build_indexes, load_csv_data, run_for_user
from ml_integration.ml_predictor import MLPredictor
from ml_integration.model_loader import MLModelBundle
from ml_integration.schema import project_root


GOAL_MAP = {
    "tăng cơ": "Muscle Gain",
    "hypertrophy": "Muscle Gain",
    "tăng cân": "Muscle Gain",
    "giảm mỡ": "Fat Loss",
    "fat loss": "Fat Loss",
    "tăng sức mạnh": "Strength",
    "sức mạnh": "Strength",
    "strength": "Strength",
    "sức khỏe tổng quát": "General Fitness",
    "general fitness": "General Fitness",
    "sức bền": "Muscular Endurance",
}

LEVEL_MAP = {
    "người mới": "Beginner",
    "mới bắt đầu": "Beginner",
    "beginner": "Beginner",
    "trung bình": "Intermediate",
    "intermediate": "Intermediate",
    "kỳ cựu": "Advanced",
    "nâng cao": "Advanced",
    "advanced": "Advanced",
}

EQUIPMENT_MAP = {
    "phòng gym đầy đủ": ["Full Gym", "Dumbbell", "Chest Press Machine", "Lat Pulldown Machine", "Power Rack"],
    "gym": ["Full Gym", "Dumbbell", "Chest Press Machine", "Lat Pulldown Machine", "Power Rack"],
    "tại nhà không tạ": ["Bodyweight"],
    "ở nhà": ["Bodyweight"],
    "bodyweight": ["Bodyweight"],
    "chỉ có tạ đơn": ["Dumbbell"],
    "dumbbell": ["Dumbbell"],
}


@lru_cache(maxsize=1)
def _stage_6d_context() -> dict[str, Any]:
    root = project_root()
    csv_dir = root / "exports" / "csv"
    model_dir = root / "models"
    data = load_csv_data(csv_dir)
    indexes = build_indexes(data)
    bundle = MLModelBundle(model_dir)
    bundle.load_all()
    return {
        "root": root,
        "data": data,
        "indexes": indexes,
        "model_bundle": bundle,
        "predictor": MLPredictor(bundle),
    }


def generate_plan_from_web_payload(payload: dict) -> dict:
    context = _stage_6d_context()
    normalized = _normalize_payload(payload)
    user_id = _select_user_id(context["data"], normalized)
    decision, diagnostics = run_for_user(
        user_id,
        context["indexes"],
        context["model_bundle"],
        context["predictor"],
    )
    plan_data = _build_plan_data(context["indexes"], user_id, normalized, decision)
    ai_decision = _format_ai_decision(decision)
    _write_web_prediction_log(context["root"], payload, normalized, user_id, decision, diagnostics)

    return {
        "status": "OK",
        "source": "stage_6d_ai_integration",
        "generated_at": datetime.utcnow().isoformat(),
        "input": normalized,
        "selected_dataset_user_id": user_id,
        "plan": _format_api_plan(plan_data, ai_decision),
        "plan_data": plan_data,
        "ai_decision": ai_decision,
    }


def _normalize_payload(payload: dict) -> dict:
    goal = _map_text(payload.get("goal"), GOAL_MAP, "Muscle Gain")
    level = _map_text(payload.get("level"), LEVEL_MAP, "Intermediate")
    equipment = _map_text_list(payload.get("equipment"), EQUIPMENT_MAP, ["Full Gym"])
    note = payload.get("note", payload.get("userInfo", "")) or ""
    return {
        "primary_goal": goal,
        "training_level": level,
        "gender": payload.get("gender", "Prefer not to say"),
        "height_cm": _safe_int(payload.get("height"), 170),
        "weight_kg": _safe_float(payload.get("weight"), 65),
        "age": _safe_int(payload.get("age"), 24),
        "available_equipment": equipment,
        "training_days_per_week": _safe_int(payload.get("training_days_per_week"), 3),
        "available_training_day_numbers": _normalize_weekday_numbers(
            payload.get("available_training_day_numbers"),
            payload.get("available_training_days"),
        ),
        "session_duration_minutes": _safe_int(payload.get("session_duration_minutes"), 60),
        "intensity_preference": payload.get("intensity_preference", "Vừa phải"),
        "priority_muscles": _split_notes(payload.get("priority_muscles")),
        "avoid_notes": payload.get("avoid_notes", ""),
        "duration_days": max(1, min(_safe_int(payload.get("duration_days", payload.get("duration")), 7), 30)),
        "injuries_or_limitations": _extract_limitations(note),
        "note": note,
    }


def _select_user_id(data: dict[str, Any], normalized: dict[str, Any]) -> str:
    users = data["users"]
    matches = users[
        (users["primary_goal"].str.lower() == normalized["primary_goal"].lower())
        & (users["training_level"].str.lower() == normalized["training_level"].lower())
    ]
    if matches.empty:
        matches = users[users["primary_goal"].str.lower() == normalized["primary_goal"].lower()]
    if matches.empty:
        return "U000001"
    return str(matches.iloc[0]["user_id"])


def _build_plan_data(indexes: dict[str, Any], user_id: str, normalized: dict[str, Any], decision: dict[str, Any]) -> dict[str, Any]:
    source_plan = indexes["plans_by_user"].get(user_id, {})
    plan_id = str(source_plan.get("plan_id") or "")
    source_items = indexes["plan_items_by_plan"].get(plan_id, [])
    days = []
    by_day: dict[int, list[dict[str, Any]]] = {}
    for item in source_items:
        day_number = _safe_int(item.get("day_number"), 1)
        by_day.setdefault(day_number, []).append(item)

    requested_days = normalized["duration_days"]
    template_days = sorted(by_day) or [1]
    training_weekdays = set(normalized.get("available_training_day_numbers") or []) or _training_weekdays(normalized.get("training_days_per_week", 3))
    training_day_count = 0
    for day_number in range(1, requested_days + 1):
        weekday = ((day_number - 1) % 7) + 1
        is_rest = weekday not in training_weekdays
        if is_rest:
            exercises = []
        else:
            template_day = template_days[training_day_count % len(template_days)]
            training_day_count += 1
            items = sorted(by_day.get(template_day, []), key=lambda row: _safe_int(row.get("exercise_order"), 0))
            exercises = [_format_exercise(item, indexes, decision) for item in items[:8]]
            is_rest = not exercises
        days.append({
            "day_number": day_number,
            "day_name": f"Ngày {day_number}",
            "is_rest": is_rest,
            "focus": _day_focus(exercises, source_plan),
            "target_calories": 1900 if is_rest else 2200,
            "target_protein": 120 if is_rest else 150,
            "exercises": exercises,
        })

    return {
        "plan_name": "Lộ trình AI cá nhân hóa",
        "title": "Lộ trình AI cá nhân hóa",
        "summary": f"Lộ trình {requested_days} ngày cho mục tiêu {normalized['primary_goal']}, cấp độ {normalized['training_level']}, {len(training_weekdays)} buổi/tuần.",
        "duration_days": requested_days,
        "source_plan_id": plan_id,
        "source_user_id": user_id,
        "daily_calories_workout": 2200,
        "daily_calories_rest": 1900,
        "daily_protein_workout": 150,
        "daily_protein_rest": 120,
        "safety_note": _safety_note(decision),
        "days": days,
    }


def _format_exercise(item: dict[str, Any], indexes: dict[str, Any], decision: dict[str, Any]) -> dict[str, Any]:
    exercise = indexes["exercises"].get(str(item.get("exercise_id") or ""), {})
    rep_min = item.get("rep_min") or ""
    rep_max = item.get("rep_max") or ""
    reps = f"{rep_min}-{rep_max}" if rep_min and rep_max else rep_min or rep_max or "8-12"
    return {
        "name": item.get("exercise_name_snapshot") or exercise.get("exercise_name") or "Exercise",
        "muscle": _first_json_value(item.get("primary_muscles_snapshot")) or _first_json_value(exercise.get("primary_muscles")) or "Toàn thân",
        "sets": _safe_int(item.get("sets"), 3),
        "reps": reps,
        "rest": _safe_int(item.get("rest_seconds"), 75),
        "diff": _level_code(item.get("exercise_min_level_snapshot") or exercise.get("minimum_training_level")),
        "equip": _first_json_value(item.get("exercise_equipment_snapshot")) or _first_json_value(exercise.get("equipment")) or "Dụng cụ",
        "steps": _json_list(exercise.get("execution_steps")),
        "tips": _json_list(exercise.get("cues")) or [item.get("coaching_note") or decision.get("explanation") or ""],
        "action": decision.get("final_action", "Keep"),
        "decision_source": decision.get("decision_source", ""),
        "explanation": decision.get("explanation", ""),
    }


def _format_ai_decision(decision: dict[str, Any]) -> dict[str, Any]:
    safety = decision.get("rule_safety_review", {})
    lock = decision.get("safety_lock", {})
    return {
        "final_action": decision.get("final_action", "Keep"),
        "decision_source": decision.get("decision_source", ""),
        "was_overridden": bool(lock.get("was_overridden", decision.get("was_overridden", False))),
        "safety_status": safety.get("safety_status", "Unknown"),
        "confidence": decision.get("final_confidence", 0),
        "explanation": decision.get("explanation", ""),
    }


def _format_api_plan(plan_data: dict[str, Any], ai_decision: dict[str, Any]) -> dict[str, Any]:
    return {
        "title": plan_data["title"],
        "summary": plan_data["summary"],
        "safety_note": plan_data["safety_note"],
        "days": [
            {
                "day": day["day_number"],
                "focus": day["focus"],
                "exercises": [
                    {
                        "name": ex["name"],
                        "sets": ex["sets"],
                        "reps": ex["reps"],
                        "action": ex["action"],
                        "decision_source": ex["decision_source"],
                        "explanation": ex["explanation"],
                    }
                    for ex in day["exercises"]
                ],
            }
            for day in plan_data["days"]
        ],
    }


def _write_web_prediction_log(root: Path, payload: dict, normalized: dict, user_id: str, decision: dict[str, Any], diagnostics: dict[str, Any]) -> None:
    output_dir = root / "integration_outputs"
    output_dir.mkdir(parents=True, exist_ok=True)
    safety = decision.get("rule_safety_review", {})
    lock = decision.get("safety_lock", {})
    log_row = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "user_id": user_id,
        "payload": payload,
        "normalized_payload": normalized,
        "plan_id": diagnostics.get("plan_id", ""),
        "exercise_id": diagnostics.get("exercise_id", ""),
        "final_action": decision.get("final_action", ""),
        "decision_source": decision.get("decision_source", ""),
        "was_overridden": bool(lock.get("was_overridden", decision.get("was_overridden", False))),
        "safety_status": safety.get("safety_status", ""),
        "confidence": decision.get("final_confidence", 0),
        "feedback_after_action": "",
        "ground_truth_note": "Prediction log chưa phải ground truth cho đến khi user gửi feedback sau buổi tập.",
    }
    with (output_dir / "web_prediction_logs.jsonl").open("a", encoding="utf-8") as file:
        file.write(json.dumps(log_row, ensure_ascii=False) + "\n")


def _map_text(value: Any, mapping: dict[str, Any], default: str) -> str:
    text = str(value or "").strip().lower()
    for key, mapped in mapping.items():
        if key in text:
            return mapped
    return default


def _map_text_list(value: Any, mapping: dict[str, list[str]], default: list[str]) -> list[str]:
    text = str(value or "").strip().lower()
    for key, mapped in mapping.items():
        if key in text:
            return mapped
    return default


def _extract_limitations(note: str) -> list[str]:
    lowered = note.lower()
    limitations = []
    if "lưng" in lowered or "back" in lowered:
        limitations.append("lower back pain")
    if "vai" in lowered or "shoulder" in lowered:
        limitations.append("shoulder pain")
    if "gối" in lowered or "knee" in lowered:
        limitations.append("knee pain")
    return limitations


def _split_notes(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    return [item.strip() for item in str(value or "").replace(";", ",").split(",") if item.strip()]


def _normalize_weekday_numbers(numbers_value: Any, names_value: Any = None) -> list[int]:
    day_map = {
        "mon": 1, "monday": 1, "thu 2": 1, "thứ 2": 1, "t2": 1,
        "tue": 2, "tuesday": 2, "thu 3": 2, "thứ 3": 2, "t3": 2,
        "wed": 3, "wednesday": 3, "thu 4": 3, "thứ 4": 3, "t4": 3,
        "thu": 4, "thursday": 4, "thu 5": 4, "thứ 5": 4, "t5": 4,
        "fri": 5, "friday": 5, "thu 6": 5, "thứ 6": 5, "t6": 5,
        "sat": 6, "saturday": 6, "thu 7": 6, "thứ 7": 6, "t7": 6,
        "sun": 7, "sunday": 7, "chu nhat": 7, "chủ nhật": 7, "cn": 7,
    }
    weekdays: set[int] = set()
    for value in [numbers_value, names_value]:
        if value is None:
            continue
        items = value if isinstance(value, list) else str(value).replace(";", ",").split(",")
        for item in items:
            text = str(item).strip().lower()
            number = _safe_int(text, 0)
            if 1 <= number <= 7:
                weekdays.add(number)
            elif text in day_map:
                weekdays.add(day_map[text])
    return sorted(weekdays)


def _training_weekdays(training_days: int) -> set[int]:
    schedules = {
        1: {1},
        2: {1, 4},
        3: {1, 3, 5},
        4: {1, 2, 4, 6},
        5: {1, 2, 3, 5, 6},
        6: {1, 2, 3, 4, 5, 6},
        7: {1, 2, 3, 4, 5, 6, 7},
    }
    return schedules.get(max(1, min(_safe_int(training_days, 3), 7)), schedules[3])


def _day_focus(exercises: list[dict[str, Any]], source_plan: dict[str, Any]) -> str:
    if not exercises:
        return "Nghỉ ngơi"
    muscles = [ex["muscle"] for ex in exercises[:3] if ex.get("muscle")]
    return " + ".join(dict.fromkeys(muscles)) or source_plan.get("split_type") or "Buổi tập"


def _safety_note(decision: dict[str, Any]) -> str:
    safety = decision.get("rule_safety_review", {})
    status = safety.get("safety_status", "Unknown")
    return f"Safety lock Stage 6D: {status}. ML chỉ gợi ý; rule-based safety là lớp kiểm duyệt cuối."


def _json_list(value: Any) -> list[str]:
    if not value:
        return []
    if isinstance(value, list):
        return [str(item) for item in value if str(item)]
    try:
        parsed = json.loads(str(value))
        if isinstance(parsed, list):
            return [str(item) for item in parsed if str(item)]
    except json.JSONDecodeError:
        pass
    text = str(value).strip()
    return [text] if text else []


def _first_json_value(value: Any) -> str:
    values = _json_list(value)
    return values[0] if values else ""


def _level_code(level: Any) -> str:
    level_text = str(level or "").lower()
    if "advanced" in level_text:
        return "A"
    if "beginner" in level_text:
        return "B"
    return "I"


def _safe_int(value: Any, default: int) -> int:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def _safe_float(value: Any, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default
