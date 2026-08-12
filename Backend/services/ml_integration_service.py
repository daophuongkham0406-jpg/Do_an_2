import csv
import json
import sys
from datetime import datetime

from utils.path_utils import AI_FITNESS_DIR, PROJECT_ROOT


if str(AI_FITNESS_DIR) not in sys.path:
    sys.path.append(str(AI_FITNESS_DIR))
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))


class MLIntegrationService:
    def __init__(self):
        self.ai_dir = AI_FITNESS_DIR
        self.model_dir = AI_FITNESS_DIR / "models"
        self.csv_dir = AI_FITNESS_DIR / "exports" / "csv"
        self.output_dir = AI_FITNESS_DIR / "integration_outputs"
        self._adapter = None

    def _load_adapter(self):
        if self._adapter is None:
            from ml_integration.web_adapter import generate_plan_from_web_payload

            self._adapter = generate_plan_from_web_payload
        return self._adapter

    def generate_plan(self, payload: dict) -> dict:
        try:
            adapter = self._load_adapter()
            result = adapter(payload)
        except Exception as exc:
            result = self._fallback_plan(payload, exc)
        result.setdefault("status", "OK")
        result.setdefault("generated_at", datetime.utcnow().isoformat())
        return result

    def _fallback_plan(self, payload: dict, exc: Exception) -> dict:
        duration_days = self._safe_int(payload.get("duration_days") or payload.get("duration"), 7)
        duration_days = max(1, min(duration_days, 14))
        note = (
            "Backend chưa gọi được Stage 6D thật, nên đang trả lộ trình dự phòng an toàn. "
            f"Lỗi kỹ thuật: {exc}"
        )
        days = []
        exercises_pool = self._load_exercise_pool()
        split = self._build_split(payload)
        training_weekdays = self._training_weekdays(self._safe_int(payload.get("training_days_per_week"), 3))
        training_day_count = 0
        for day_number in range(1, duration_days + 1):
            weekday = ((day_number - 1) % 7) + 1
            is_rest = weekday not in training_weekdays
            workout = split[training_day_count % len(split)] if not is_rest else {"focus": "Nghỉ ngơi", "primary": [], "secondary": []}
            if not is_rest:
                training_day_count += 1
            selected = [] if is_rest else self._select_fallback_exercises(exercises_pool, workout, payload)
            days.append({
                "day_number": day_number,
                "day_name": f"Ngày {day_number}",
                "is_rest": is_rest,
                "focus": "Nghỉ ngơi + giãn cơ nhẹ" if is_rest else workout["focus"],
                "target_calories": 1900 if is_rest else 2200,
                "target_protein": 120 if is_rest else 150,
                "exercises": [self._format_fallback_exercise(exercise, payload, note) for exercise in selected],
            })

        plan_data = {
            "plan_name": "Lộ trình AI dự phòng",
            "title": "Lộ trình AI dự phòng",
            "summary": f"Lộ trình {duration_days} ngày dựa trên khảo sát hiện tại.",
            "duration_days": duration_days,
            "source_plan_id": "",
            "source_user_id": "fallback",
            "daily_calories_workout": 2200,
            "daily_calories_rest": 1900,
            "daily_protein_workout": 150,
            "daily_protein_rest": 120,
            "safety_note": note,
            "days": days,
        }
        return {
            "status": "OK",
            "source": "backend_fallback_when_stage_6d_unavailable",
            "input": payload,
            "plan_data": plan_data,
            "plan": {
                "title": plan_data["title"],
                "summary": plan_data["summary"],
                "safety_note": note,
                "days": [{
                    "day": day["day_number"],
                    "focus": day["focus"],
                    "exercises": day["exercises"],
                } for day in days],
            },
            "ai_decision": {
                "final_action": "Reduce Difficulty",
                "decision_source": "backend_fallback",
                "was_overridden": False,
                "safety_status": "Fallback",
                "confidence": 0,
                "explanation": note,
            },
        }

    def _safe_int(self, value, default: int) -> int:
        try:
            return int(float(value))
        except (TypeError, ValueError):
            return default

    def _load_exercise_pool(self) -> list[dict]:
        path = self.csv_dir / "exercises.csv"
        if not path.exists():
            return []
        with path.open("r", encoding="utf-8-sig", newline="") as file:
            return list(csv.DictReader(file))

    def _build_split(self, payload: dict) -> list[dict]:
        training_days = self._safe_int(payload.get("training_days_per_week"), 3)
        priority = self._split_text(payload.get("priority_muscles"))
        core = ["Rectus Abdominis", "Obliques", "Core"]
        splits = {
            2: [
                {"focus": "Full Body A", "primary": ["Pectoralis Major", "Latissimus Dorsi", "Quadriceps"], "secondary": core},
                {"focus": "Full Body B", "primary": ["Gluteus Maximus", "Hamstrings", "Deltoids"], "secondary": core},
                {"focus": "Nghỉ ngơi", "primary": [], "secondary": []},
            ],
            3: [
                {"focus": "Ngực + tay sau", "primary": ["Pectoralis Major"], "secondary": ["Triceps Brachii"] + core[:1]},
                {"focus": "Lưng + tay trước", "primary": ["Latissimus Dorsi"], "secondary": ["Biceps Brachii", "Brachialis"] + core[:1]},
                {"focus": "Chân + core", "primary": ["Quadriceps", "Gluteus Maximus", "Hamstrings"], "secondary": core},
                {"focus": "Nghỉ ngơi", "primary": [], "secondary": []},
            ],
            4: [
                {"focus": "Đẩy: ngực + vai + tay sau", "primary": ["Pectoralis Major", "Deltoids"], "secondary": ["Triceps Brachii"]},
                {"focus": "Kéo: lưng + tay trước", "primary": ["Latissimus Dorsi", "Middle Back"], "secondary": ["Biceps Brachii", "Brachialis"]},
                {"focus": "Chân", "primary": ["Quadriceps", "Gluteus Maximus", "Hamstrings"], "secondary": ["Calves"]},
                {"focus": "Core + phục hồi chủ động", "primary": core, "secondary": ["Rotator Cuff", "Rear Deltoid"]},
                {"focus": "Nghỉ ngơi", "primary": [], "secondary": []},
            ],
        }
        split = splits[2] if training_days <= 2 else splits[4] if training_days >= 4 else splits[3]
        split = [item for item in split if item["focus"] != "Nghỉ ngơi"]
        if priority:
            split[0]["primary"] = priority + split[0]["primary"]
            split[0]["focus"] = "Ưu tiên " + ", ".join(priority[:2])
        return split

    def _training_weekdays(self, training_days: int) -> set[int]:
        schedules = {
            1: {1},
            2: {1, 4},
            3: {1, 3, 5},
            4: {1, 2, 4, 6},
            5: {1, 2, 3, 5, 6},
            6: {1, 2, 3, 4, 5, 6},
            7: {1, 2, 3, 4, 5, 6, 7},
        }
        return schedules.get(max(1, min(training_days, 7)), schedules[3])

    def _select_fallback_exercises(self, pool: list[dict], workout: dict, payload: dict) -> list[dict]:
        if not pool:
            return []
        session_minutes = self._safe_int(payload.get("session_duration_minutes"), 60)
        max_count = 4 if session_minutes <= 45 else 5 if session_minutes <= 70 else 6
        fatigue_budget = 18 if session_minutes <= 45 else 24 if session_minutes <= 70 else 30
        selected: list[dict] = []
        used_ids: set[str] = set()

        slots = []
        for muscle in workout.get("primary", [])[:4]:
            slots.extend([muscle, muscle] if muscle not in {"Biceps Brachii", "Triceps Brachii", "Brachialis", "Calves"} else [muscle])
        for muscle in workout.get("secondary", [])[:4]:
            slots.append(muscle)

        for muscle in slots:
            if len(selected) >= max_count:
                break
            current_fatigue = sum(self._fatigue_score(item) for item in selected)
            if current_fatigue >= fatigue_budget:
                break
            candidates = [
                item for item in pool
                if item.get("exercise_id") not in used_ids
                and self._matches_payload(item, payload)
                and self._matches_muscle(item, muscle)
            ]
            if not candidates:
                continue
            candidates.sort(key=lambda item: self._exercise_rank(item, payload))
            chosen = candidates[0]
            used_ids.add(chosen.get("exercise_id", ""))
            selected.append(chosen)
        return selected

    def _matches_payload(self, exercise: dict, payload: dict) -> bool:
        goal = self._map_goal(payload.get("goal"))
        level = self._map_level(payload.get("level"))
        equipment = self._equipment_tokens(payload.get("equipment"))
        avoid_text = " ".join([
            str(payload.get("avoid_notes", "")),
            str(payload.get("note", "")),
            str(payload.get("userInfo", "")),
        ]).lower()
        exercise_blob = " ".join(str(exercise.get(key, "")) for key in [
            "exercise_name", "equipment", "recommended_goals", "joint_stress_areas", "contraindications",
        ]).lower()
        if goal and goal not in self._json_values(exercise.get("recommended_goals")):
            return False
        if self._level_rank(exercise.get("minimum_training_level")) > self._level_rank(level):
            return False
        if equipment and not any(token.lower() in exercise_blob for token in equipment):
            return False
        primary_blob = " ".join([
            exercise.get("exercise_name", ""),
            exercise.get("primary_muscles", ""),
            exercise.get("movement_pattern", ""),
        ]).lower()
        if ("vai" in avoid_text or "shoulder" in avoid_text) and any(
            marker in primary_blob for marker in ["shoulder", "deltoid", "overhead", "lateral raise", "upright row"]
        ):
            return False
        if ("gối" in avoid_text or "knee" in avoid_text) and any(
            marker in primary_blob for marker in ["squat", "lunge", "knee", "quadriceps", "leg extension"]
        ):
            return False
        if ("lưng" in avoid_text or "back" in avoid_text) and any(
            marker in primary_blob for marker in ["deadlift", "hinge", "good morning", "lower back", "back extension"]
        ):
            return False
        return True

    def _format_fallback_exercise(self, exercise: dict, payload: dict, note: str) -> dict:
        goal = self._map_goal(payload.get("goal"))
        reps = "6-10" if goal == "Strength" else "12-15" if goal == "Fat Loss" else "8-12"
        fatigue = self._fatigue_score(exercise)
        rest = 105 if fatigue >= 7 else 75 if fatigue >= 5 else 60
        return {
            "name": exercise.get("exercise_name") or "Exercise",
            "muscle": self._first_json_value(exercise.get("primary_muscles")) or "Toàn thân",
            "sets": 2 if fatigue >= 8 else 3,
            "reps": reps,
            "rest": rest,
            "diff": self._level_code(exercise.get("minimum_training_level")),
            "equip": self._first_json_value(exercise.get("equipment")) or payload.get("equipment", "Dụng cụ"),
            "steps": self._json_values(exercise.get("execution_steps"))[:4] or [
                "Khởi động kỹ trước khi vào set chính",
                "Giữ kỹ thuật ổn định và tập trong biên độ không đau",
            ],
            "tips": self._json_values(exercise.get("cues"))[:3] or [
                f"Fatigue score: {fatigue}. Bài được chọn từ exercises.csv theo nhóm cơ, thiết bị và mức mỏi.",
            ],
            "action": "Reduce Difficulty",
            "decision_source": "dataset_rule_fallback",
            "explanation": note,
        }

    def _exercise_rank(self, exercise: dict, payload: dict) -> tuple:
        intensity = str(payload.get("intensity_preference", "")).lower()
        fatigue = self._fatigue_score(exercise)
        injury_risk = str(exercise.get("relative_injury_risk", "")).lower()
        risk_penalty = 2 if "high" in injury_risk else 1 if "moderate" in injury_risk else 0
        if "thử thách" in intensity:
            fatigue_rank = abs(fatigue - 6)
        elif "nhẹ" in intensity or "an toàn" in intensity:
            fatigue_rank = fatigue
        else:
            fatigue_rank = abs(fatigue - 4.5)
        complexity = self._safe_int(exercise.get("technical_complexity_score"), 3)
        return (risk_penalty, fatigue_rank, complexity, exercise.get("exercise_name", ""))

    def _matches_muscle(self, exercise: dict, muscle: str) -> bool:
        target = str(muscle).lower()
        blob = " ".join([
            exercise.get("primary_muscles", ""),
            exercise.get("secondary_muscles", ""),
            exercise.get("body_region", ""),
            exercise.get("movement_pattern", ""),
            exercise.get("exercise_name", ""),
        ]).lower()
        aliases = {
            "core": ["rectus abdominis", "obliques", "core", "abdom"],
            "middle back": ["trapezius", "rhomboids", "middle back", "latissimus"],
            "deltoids": ["deltoid", "shoulder"],
            "calves": ["calf", "gastrocnemius", "soleus"],
        }
        return target in blob or any(alias in blob for alias in aliases.get(target, []))

    def _fatigue_score(self, exercise: dict) -> int:
        return self._safe_int(exercise.get("systemic_fatigue_score"), 3) + self._safe_int(exercise.get("local_fatigue_score"), 3)

    def _map_goal(self, value) -> str:
        text = str(value or "").lower()
        if "giảm" in text or "fat" in text:
            return "Fat Loss"
        if "sức mạnh" in text or "strength" in text:
            return "Strength"
        if "sức bền" in text or "endurance" in text:
            return "Muscular Endurance"
        return "Muscle Gain"

    def _map_level(self, value) -> str:
        text = str(value or "").lower()
        if "mới" in text or "beginner" in text:
            return "Beginner"
        if "kỳ cựu" in text or "nâng cao" in text or "advanced" in text:
            return "Advanced"
        return "Intermediate"

    def _equipment_tokens(self, value) -> list[str]:
        text = str(value or "").lower()
        if "không tạ" in text or "bodyweight" in text or "ở nhà" in text or "tại nhà" in text:
            return ["Bodyweight", "Mat", "Resistance Band"]
        if "tạ đơn" in text or "dumbbell" in text:
            return ["Dumbbell", "Bodyweight", "Mat"]
        return []

    def _level_rank(self, level) -> int:
        text = str(level or "").lower()
        if "advanced" in text:
            return 3
        if "intermediate" in text:
            return 2
        return 1

    def _level_code(self, level) -> str:
        rank = self._level_rank(level)
        return "A" if rank == 3 else "I" if rank == 2 else "B"

    def _split_text(self, value) -> list[str]:
        muscle_map = {
            "ngực": "Pectoralis Major",
            "lưng": "Latissimus Dorsi",
            "vai": "Deltoids",
            "tay sau": "Triceps Brachii",
            "tay trước": "Biceps Brachii",
            "mông": "Gluteus Maximus",
            "đùi": "Quadriceps",
            "chân": "Quadriceps",
            "core": "Core",
            "bụng": "Core",
        }
        text = str(value or "").lower().replace(";", ",")
        result = []
        for raw in text.split(","):
            raw = raw.strip()
            for key, mapped in muscle_map.items():
                if key in raw and mapped not in result:
                    result.append(mapped)
        return result

    def _json_values(self, value) -> list[str]:
        if isinstance(value, list):
            return [str(item) for item in value]
        try:
            parsed = json.loads(str(value or "[]"))
            return [str(item) for item in parsed] if isinstance(parsed, list) else []
        except json.JSONDecodeError:
            return [str(value)] if value else []

    def _first_json_value(self, value) -> str:
        values = self._json_values(value)
        return values[0] if values else ""
