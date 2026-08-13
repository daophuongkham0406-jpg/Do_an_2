import csv
import json
from datetime import datetime

from utils.path_utils import AI_FITNESS_DIR


class MLIntegrationService:
    def __init__(self):
        self.ai_dir = AI_FITNESS_DIR
        self.model_dir = AI_FITNESS_DIR / "models"
        self.csv_dir = AI_FITNESS_DIR / "exports" / "csv"
        self.output_dir = AI_FITNESS_DIR / "integration_outputs"

    def generate_plan(self, payload: dict) -> dict:
        result = self._dataset_plan(payload)
        result.setdefault("status", "OK")
        result.setdefault("generated_at", datetime.utcnow().isoformat())
        return result

    def _dataset_plan(self, payload: dict) -> dict:
        duration_days = self._safe_int(payload.get("duration_days") or payload.get("duration"), 7)
        duration_days = max(1, min(duration_days, 30))
        note = (
            "Lộ trình được tạo chỉ từ AI_Fitness_Dataset: exercises, workout_plans, "
            "workout_plan_items, users, workout_history, user_feedback và history_summary."
        )
        days = []
        dataset = self._load_dataset_context(payload)
        exercises_pool = dataset["exercises"]
        split = self._build_split(payload)
        training_weekdays = self._available_weekdays(payload) or self._training_weekdays(self._safe_int(payload.get("training_days_per_week"), 3))
        training_day_count = 0
        for day_number in range(1, duration_days + 1):
            weekday = ((day_number - 1) % 7) + 1
            is_rest = weekday not in training_weekdays
            workout = split[training_day_count % len(split)] if not is_rest else {"focus": "Nghỉ ngơi", "primary": [], "secondary": []}
            if not is_rest:
                training_day_count += 1
            selected = [] if is_rest else self._select_dataset_exercises(exercises_pool, workout, payload, dataset)
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
            "plan_name": "Lộ trình AI Fitness cá nhân hóa",
            "title": "Lộ trình AI Fitness cá nhân hóa",
            "summary": f"Lộ trình {duration_days} ngày dựa trên khảo sát hiện tại.",
            "duration_days": duration_days,
            "source_plan_id": "",
            "source_user_id": dataset["similar_user_id"],
            "daily_calories_workout": 2200,
            "daily_calories_rest": 1900,
            "daily_protein_workout": 150,
            "daily_protein_rest": 120,
            "safety_note": note,
            "days": days,
        }
        return {
            "status": "OK",
            "source": "ai_fitness_dataset_only",
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
                "decision_source": "ai_fitness_dataset_rule_engine",
                "was_overridden": False,
                "safety_status": "DatasetRules",
                "confidence": dataset["confidence"],
                "explanation": note,
                "dataset_context": {
                    "exercises": len(dataset["exercises"]),
                    "workout_plans": len(dataset["workout_plans"]),
                    "workout_plan_items": len(dataset["workout_plan_items"]),
                    "users": len(dataset["users"]),
                    "workout_history_sessions": len(dataset["history_sessions"]),
                    "workout_history_items": len(dataset["history_items"]),
                    "user_feedback": len(dataset["feedback"]),
                    "history_summary": len(dataset["history_summary"]),
                    "similar_user_id": dataset["similar_user_id"],
                    "rules": ["safety", "recommendation", "preference", "history/adherence/fatigue"],
                },
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

    def _load_csv(self, filename: str) -> list[dict]:
        path = self.csv_dir / filename
        if not path.exists():
            return []
        with path.open("r", encoding="utf-8-sig", newline="") as file:
            return list(csv.DictReader(file))

    def _load_dataset_context(self, payload: dict) -> dict:
        exercises = self._load_csv("exercises.csv")
        workout_plans = self._load_csv("workout_plans.csv")
        workout_plan_items = self._load_csv("workout_plan_items.csv")
        users = self._load_csv("users.csv")
        history_sessions = self._load_csv("workout_history_sessions.csv")
        history_items = self._load_csv("workout_history_items.csv")
        feedback = self._load_csv("user_feedback.csv")
        history_summary = self._load_csv("workout_history_summary.csv")
        similar_user = self._find_similar_user(users, payload)
        similar_user_id = similar_user.get("user_id", "")
        similar_plan_ids = {
            plan.get("plan_id")
            for plan in workout_plans
            if self._plan_matches_payload(plan, payload, similar_user_id)
        }
        if not similar_plan_ids and similar_user_id:
            similar_plan_ids = {
                plan.get("plan_id")
                for plan in workout_plans
                if plan.get("user_id") == similar_user_id
            }
        dataset = {
            "exercises": exercises,
            "workout_plans": workout_plans,
            "workout_plan_items": workout_plan_items,
            "users": users,
            "history_sessions": history_sessions,
            "history_items": history_items,
            "feedback": feedback,
            "history_summary": history_summary,
            "similar_user_id": similar_user_id,
            "similar_plan_ids": {plan_id for plan_id in similar_plan_ids if plan_id},
            "plan_item_scores": {},
            "preference_scores": {},
            "history_scores": {},
            "fatigue_penalties": {},
            "confidence": 0,
        }
        dataset["plan_item_scores"] = self._build_plan_item_scores(workout_plan_items, dataset["similar_plan_ids"])
        dataset["preference_scores"] = self._build_preference_scores(feedback)
        dataset["history_scores"] = self._build_history_scores(history_items)
        dataset["fatigue_penalties"] = self._build_fatigue_penalties(history_summary, workout_plan_items)
        dataset["confidence"] = min(95, 55 + min(len(dataset["similar_plan_ids"]), 10) * 3)
        return dataset

    def _find_similar_user(self, users: list[dict], payload: dict) -> dict:
        target_goal = self._map_goal(payload.get("goal"))
        target_level = self._map_level(payload.get("level"))
        target_days = self._safe_int(payload.get("training_days_per_week"), 3)
        target_minutes = self._safe_int(payload.get("session_duration_minutes"), 60)
        target_equipment = set(self._equipment_tokens(payload.get("equipment")))
        best_user = {}
        best_score = -1
        for user in users:
            score = 0
            if user.get("primary_goal") == target_goal:
                score += 4
            if user.get("training_level") == target_level:
                score += 3
            if self._safe_int(user.get("training_days_per_week"), 0) == target_days:
                score += 2
            if abs(self._safe_int(user.get("session_duration_minutes"), 0) - target_minutes) <= 15:
                score += 1
            user_equipment = set(self._json_values(user.get("available_equipment")))
            if target_equipment and target_equipment.intersection(user_equipment):
                score += 1
            if score > best_score:
                best_score = score
                best_user = user
        return best_user

    def _plan_matches_payload(self, plan: dict, payload: dict, similar_user_id: str) -> bool:
        goal = self._map_goal(payload.get("goal"))
        level = self._map_level(payload.get("level"))
        days = self._safe_int(payload.get("training_days_per_week"), 3)
        if similar_user_id and plan.get("user_id") == similar_user_id:
            return True
        if plan.get("primary_goal_snapshot") != goal:
            return False
        if plan.get("training_level_snapshot") != level:
            return False
        return abs(self._safe_int(plan.get("days_per_week"), days) - days) <= 1

    def _build_plan_item_scores(self, items: list[dict], plan_ids: set[str]) -> dict:
        scores = {}
        for item in items:
            if plan_ids and item.get("plan_id") not in plan_ids:
                continue
            exercise_id = item.get("exercise_id", "")
            if not exercise_id:
                continue
            priority = self._safe_int(item.get("priority_score"), 1)
            role = str(item.get("exercise_role", "")).lower()
            role_bonus = 2 if "primary" in role else 1 if "secondary" in role else 0
            scores[exercise_id] = scores.get(exercise_id, 0) + priority + role_bonus
        return scores

    def _build_preference_scores(self, feedback_rows: list[dict]) -> dict:
        scores = {}
        for row in feedback_rows:
            exercise_id = row.get("exercise_id", "")
            if not exercise_id:
                continue
            sentiment = str(row.get("sentiment", "")).lower()
            requested = str(row.get("requested_action", "")).lower()
            preference = str(row.get("exercise_preference", "")).lower()
            pain = str(row.get("pain_feedback", "")).lower()
            score = 0
            if "positive" in sentiment or "prefer" in preference:
                score += 2
            if "negative" in sentiment or "avoid" in requested or "replace" in requested:
                score -= 4
            if pain and pain not in {"none", "no", "nan"}:
                score -= 4
            scores[exercise_id] = scores.get(exercise_id, 0) + score
        return scores

    def _build_history_scores(self, history_items: list[dict]) -> dict:
        scores = {}
        for row in history_items:
            exercise_id = row.get("exercise_id", "")
            if not exercise_id:
                continue
            status = str(row.get("completion_status", "")).lower()
            enjoyment = self._safe_int(row.get("exercise_enjoyment"), 0)
            difficulty = self._safe_int(row.get("difficulty_rating"), 0)
            pain = str(row.get("pain_during_exercise", "")).lower()
            score = 0
            if "completed" in status:
                score += 1
            if enjoyment >= 4:
                score += 1
            if difficulty >= 5:
                score -= 1
            if pain in {"yes", "true", "1"}:
                score -= 4
            scores[exercise_id] = scores.get(exercise_id, 0) + score
        return scores

    def _build_fatigue_penalties(self, history_summary: list[dict], plan_items: list[dict]) -> dict:
        plan_penalties = {}
        for row in history_summary:
            if self._safe_int(row.get("fatigue_after"), 0) < 4 and str(row.get("recovery_flag", "")).lower() not in {"poor", "red"}:
                continue
            plan_id = row.get("plan_id")
            if not plan_id:
                continue
            plan_penalties[plan_id] = plan_penalties.get(plan_id, 0) + 1
        exercise_penalties = {}
        for item in plan_items:
            penalty = plan_penalties.get(item.get("plan_id"), 0)
            exercise_id = item.get("exercise_id", "")
            if penalty and exercise_id:
                exercise_penalties[exercise_id] = exercise_penalties.get(exercise_id, 0) + penalty
        return exercise_penalties

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

    def _available_weekdays(self, payload: dict) -> set[int]:
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
        for value in [payload.get("available_training_day_numbers"), payload.get("available_training_days")]:
            if value is None:
                continue
            items = value if isinstance(value, list) else str(value).replace(";", ",").split(",")
            for item in items:
                text = str(item).strip().lower()
                number = self._safe_int(text, 0)
                if 1 <= number <= 7:
                    weekdays.add(number)
                elif text in day_map:
                    weekdays.add(day_map[text])
        return weekdays

    def _select_dataset_exercises(self, pool: list[dict], workout: dict, payload: dict, dataset: dict) -> list[dict]:
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
            candidates.sort(key=lambda item: self._exercise_rank(item, payload, dataset))
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
        if equipment and not self._has_required_equipment(exercise, equipment):
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
                f"Fatigue score: {fatigue}. Bài được chọn từ AI_Fitness_Dataset theo nhóm cơ, thiết bị và mức mỏi.",
            ],
            "action": "Reduce Difficulty",
            "decision_source": "ai_fitness_dataset_rule_engine",
            "explanation": note,
        }

    def _exercise_rank(self, exercise: dict, payload: dict, dataset=None) -> tuple:
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
        exercise_id = exercise.get("exercise_id", "")
        dataset = dataset or {}
        template_bonus = dataset.get("plan_item_scores", {}).get(exercise_id, 0)
        preference_bonus = dataset.get("preference_scores", {}).get(exercise_id, 0)
        history_bonus = dataset.get("history_scores", {}).get(exercise_id, 0)
        fatigue_penalty = dataset.get("fatigue_penalties", {}).get(exercise_id, 0)
        dataset_score = template_bonus + preference_bonus + history_bonus - fatigue_penalty
        return (risk_penalty, -dataset_score, fatigue_rank, complexity, exercise.get("exercise_name", ""))

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
        if "gym" in text or "phòng gym" in text or "day du" in text or "đầy đủ" in text:
            return [
                "Barbell", "Bench", "Box", "Cable", "Dumbbell", "EZ Bar", "Exercise Ball",
                "Foam Roller", "Kettlebell", "Machine", "Mat", "Medicine Ball", "Pull-up Bar",
                "Resistance Band", "Smith Machine", "TRX", "Weight Plate", "Bodyweight",
            ]
        if "không tạ" in text or "bodyweight" in text or "ở nhà" in text or "tại nhà" in text:
            return ["Bodyweight", "Mat", "Resistance Band"]
        if "tạ đơn" in text or "dumbbell" in text:
            return ["Dumbbell", "Bodyweight", "Mat", "Resistance Band"]
        return []

    def _has_required_equipment(self, exercise: dict, available_equipment: list[str]) -> bool:
        allowed = {self._normalize_equipment(item) for item in available_equipment}
        required = {
            self._normalize_equipment(item)
            for item in self._json_values(exercise.get("equipment"))
            if self._normalize_equipment(item) not in {"", "none", "bodyweight"}
        }
        return required.issubset(allowed)

    def _normalize_equipment(self, value) -> str:
        text = str(value or "").strip().lower()
        aliases = {
            "barbell": "barbell",
            "bench": "bench",
            "box": "box",
            "cable": "cable",
            "dumbbell": "dumbbell",
            "ez bar": "ez bar",
            "exercise ball": "exercise ball",
            "foam roller": "foam roller",
            "kettlebell": "kettlebell",
            "machine": "machine",
            "mat": "mat",
            "medicine ball": "medicine ball",
            "pull-up bar": "pull-up bar",
            "resistance band": "resistance band",
            "smith machine": "smith machine",
            "trx": "trx",
            "weight plate": "weight plate",
            "bodyweight": "bodyweight",
        }
        return aliases.get(text, text)

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
