import csv
import hashlib
import json
import math
import os
import re
import sys
from datetime import datetime
from pathlib import Path

from utils.path_utils import AI_DIR

if str(AI_DIR) not in sys.path:
    sys.path.insert(0, str(AI_DIR))

from vietnamese_normalizer import (  # noqa: E402
    display_label,
    display_pipe_values,
    normalize_text,
    normalize_avoid_terms,
    safety_tag_for_avoid_key,
)
from vietnamese_exercise_text import translate_steps, vietnamese_exercise_name  # noqa: E402

try:
    import google.generativeai as genai
except ImportError:
    genai = None


class MLIntegrationService:
    def __init__(self):
        self.ai_dir = AI_DIR
        self.exercise_path = AI_DIR / "exercises.csv"
        self._translation_cache = {}

    def generate_plan(self, payload: dict) -> dict:
        exercises = self._load_exercises()
        if not exercises:
            raise ValueError("Không tìm thấy dữ liệu bài tập tại AI/exercises.csv")

        duration_days = max(1, min(self._safe_int(payload.get("duration_days") or payload.get("duration"), 7), 30))
        training_days = max(1, min(self._safe_int(payload.get("training_days_per_week"), 3), 7))
        goal = self._map_goal(payload.get("goal"))
        level = self._map_level(payload.get("level"))
        avoid = normalize_avoid_terms(self._avoid_text(payload))
        bmi = self._bmi(payload)
        nutrition = self._nutrition_targets(payload, goal, training_days, exercises)
        plan_id = self._make_id("PLAN", payload, duration_days)

        split = self._build_split(goal, training_days, payload)
        training_weekdays = self._available_weekdays(payload) or self._training_weekdays(training_days)
        weekly_training_weekdays = self._weekly_available_weekdays(payload)
        days = []
        training_index = 0

        for day_number in range(1, duration_days + 1):
            weekday = ((day_number - 1) % 7) + 1
            week_index = (day_number - 1) // 7
            active_weekdays = (
                weekly_training_weekdays[min(week_index, len(weekly_training_weekdays) - 1)]
                if weekly_training_weekdays
                else training_weekdays
            )
            is_rest = weekday not in active_weekdays
            if is_rest:
                days.append(self._rest_day(day_number, nutrition))
                continue

            focus = split[training_index % len(split)]
            training_index += 1
            selected = self._select_exercises(exercises, focus, goal, level, avoid, payload)
            day_items = [
                self._format_exercise(item, goal, day_number, order_index + 1, plan_id)
                for order_index, item in enumerate(selected)
            ]
            days.append({
                "day_number": day_number,
                "day_name": f"Ngày {day_number}",
                "is_rest": False,
                "focus": focus["name"],
                "target_calories": nutrition["workout"]["calories"],
                "target_protein": nutrition["workout"]["protein"],
                "target_carbs": nutrition["workout"]["carbs"],
                "target_fat": nutrition["workout"]["fat"],
                "exercises": day_items,
            })

        plan_data = {
            "plan_id": plan_id,
            "plan_name": "Lộ trình FIT ME theo luật cá nhân hóa",
            "title": "Lộ trình FIT ME theo luật cá nhân hóa",
            "summary": self._summary(goal, level, duration_days, training_days, bmi),
            "duration_days": duration_days,
            "source_plan_id": plan_id,
            "source_user_id": str(payload.get("user_id") or payload.get("userId") or ""),
            "daily_calories_workout": nutrition["workout"]["calories"],
            "daily_calories_rest": nutrition["rest"]["calories"],
            "daily_protein_workout": nutrition["workout"]["protein"],
            "daily_protein_rest": nutrition["rest"]["protein"],
            "nutrition_note": nutrition["note"],
            "safety_note": self._safety_note(avoid),
            "bmi": bmi,
            "days": days,
        }
        return {
            "status": "OK",
            "source": "ai_exercises_csv_rule_engine",
            "input": payload,
            "plan_data": plan_data,
            "plan": {
                "title": plan_data["title"],
                "summary": plan_data["summary"],
                "safety_note": plan_data["safety_note"],
                "days": [{"day": day["day_number"], "focus": day["focus"], "exercises": day["exercises"]} for day in days],
            },
            "ai_decision": {
                "final_action": "Generate Rule-Based Plan",
                "decision_source": "AI/exercises.csv",
                "was_overridden": False,
                "safety_status": "VietnameseAvoidTermsApplied",
                "confidence": 82,
                "explanation": "Lộ trình được sinh từ AI/exercises.csv, luật gym, chuẩn hóa tiếng Việt và công thức dinh dưỡng.",
                "dataset_context": {
                    "exercises": len(exercises),
                    "rules": ["goal", "level", "muscle_balance", "injury_avoidance", "sets_reps_rest", "nutrition_formula"],
                    "avoid_keys": avoid["avoid_keys"],
                    "unknown_avoid_terms": avoid["unknown_terms"],
                },
            },
        }

    def _load_exercises(self) -> list[dict]:
        with self.exercise_path.open("r", encoding="utf-8-sig", newline="") as file:
            return list(csv.DictReader(file))

    def _select_exercises(self, exercises, focus, goal, level, avoid, payload):
        session_minutes = self._safe_int(payload.get("session_duration_minutes"), 60)
        target_count = 4 if session_minutes <= 45 else 5 if session_minutes <= 70 else 6
        selected = []
        used_ids = set()
        muscle_counts = {}
        candidates = [
            item for item in exercises
            if self._level_rank(item.get("difficulty")) <= self._level_rank(level)
            and self._goal_matches(item, goal)
            and self._is_safe(item, avoid)
        ]

        for slot in focus["slots"]:
            pool = [item for item in candidates if item["id"] not in used_ids and self._matches_slot(item, slot)]
            if not pool:
                pool = [item for item in candidates if item["id"] not in used_ids]
            pool.sort(key=lambda item: self._rank_exercise(item, goal, level, focus, muscle_counts, payload))
            if not pool:
                continue
            chosen = pool[0]
            selected.append(chosen)
            used_ids.add(chosen["id"])
            primary = self._tokens(chosen.get("primary_muscles"))
            for muscle in primary:
                muscle_counts[muscle] = muscle_counts.get(muscle, 0) + 1
            if len(selected) >= target_count:
                break
        return selected

    def _is_safe(self, exercise, avoid):
        tags = set(self._tokens(exercise.get("tags")))
        muscles = set(self._tokens(exercise.get("primary_muscles")) + self._tokens(exercise.get("secondary_muscles")))
        body_part = str(exercise.get("body_part") or "")
        category = str(exercise.get("category") or "")
        name = str(exercise.get("name_en") or "").lower()
        knee_sensitive = {"quadriceps", "hamstrings", "gluteus_maximus", "gluteus_medius", "adductors", "abductors", "gastrocnemius", "soleus"}
        shoulder_sensitive = {"anterior_deltoid", "lateral_deltoid", "posterior_deltoid", "trapezius", "serratus_anterior", "pectoralis_major"}
        lower_back_sensitive = {"erector_spinae", "quadratus_lumborum", "gluteus_maximus", "hamstrings", "latissimus_dorsi"}
        for key in avoid["avoid_keys"]:
            safety_tag = safety_tag_for_avoid_key(key)
            if safety_tag and safety_tag not in tags:
                return False
            if key == "knee" and (body_part in {"upper_legs", "lower_legs"} or muscles.intersection(knee_sensitive)):
                return False
            if key == "shoulder" and (body_part in {"shoulders", "chest"} or muscles.intersection(shoulder_sensitive) or "overhead" in name):
                return False
            if key == "lower_back" and (body_part == "back" or muscles.intersection(lower_back_sensitive) or any(word in name for word in ["deadlift", "good morning", "back extension"])):
                return False
            if key in muscles or key == body_part:
                return False
            if key in {"elbow", "wrist"} and body_part in {"upper_arms", "lower_arms"}:
                return False
            if key == "neck" and (body_part in {"back", "shoulders"} or "neck" in name):
                return False
        if category == "olympic" and any(key in avoid["avoid_keys"] for key in {"knee", "shoulder", "lower_back", "wrist"}):
            return False
        return True

    def _goal_matches(self, exercise, goal):
        goals = set(self._tokens(exercise.get("goals")))
        category = str(exercise.get("category") or "")
        met = self._safe_float(exercise.get("met"), 5)
        if goal == "fat_loss":
            return category in {"cardio", "plyometrics", "strength", "strongman"} or met >= 6
        if goal == "muscle_gain":
            return "hypertrophy" in goals or category == "strength"
        if goal == "strength":
            return "strength" in goals or "power" in goals
        if goal == "endurance":
            return "endurance" in goals or category in {"cardio", "plyometrics"}
        if goal == "mobility":
            return "mobility" in goals or category == "stretching"
        if goal == "rehabilitation":
            return "rehabilitation" in goals or "mobility" in goals or category == "stretching"
        return True

    def _rank_exercise(self, exercise, goal, level, focus, muscle_counts, payload):
        met = self._safe_float(exercise.get("met"), 5)
        mechanic = str(exercise.get("mechanic") or "")
        primary = self._tokens(exercise.get("primary_muscles"))
        overused_penalty = sum(muscle_counts.get(muscle, 0) for muscle in primary)
        intensity = normalize_text(str(payload.get("intensity_preference") or "vua phai"))
        intensity_score = abs(met - 5.5)
        if "nhe" in intensity or "an toan" in intensity:
            intensity_score = met
        elif "thu thach" in intensity:
            intensity_score = -met
        goal_bonus = 0
        if goal == "fat_loss":
            goal_bonus -= met
            if exercise.get("body_part") == "full_body":
                goal_bonus -= 2
            if mechanic == "compound":
                goal_bonus -= 1
        elif mechanic == "compound" and goal in {"strength", "muscle_gain"}:
            goal_bonus -= 1
        slot_bonus = -2 if any(self._matches_slot(exercise, slot) for slot in focus["slots"][:3]) else 0
        level_penalty = abs(self._level_rank(exercise.get("difficulty")) - self._level_rank(level))
        return (overused_penalty, slot_bonus, goal_bonus, intensity_score, level_penalty, exercise.get("name_en", ""))

    def _matches_slot(self, exercise, slot):
        slot = str(slot or "")
        values = set(self._tokens(exercise.get("primary_muscles")) + self._tokens(exercise.get("secondary_muscles")))
        values.add(str(exercise.get("body_part") or ""))
        values.add(str(exercise.get("force_type") or ""))
        values.add(str(exercise.get("category") or ""))
        return slot in values

    def _format_exercise(self, exercise, goal, day_number, order_index, plan_id):
        prescription = self._prescription(goal, exercise)
        muscles = exercise.get("primary_muscles")
        images = self._exercise_images(exercise)
        return {
            "plan_item_id": f"WPI{day_number:02d}{order_index:02d}{exercise.get('id', '')[:6].upper()}",
            "plan_id": plan_id,
            "exercise_id": exercise.get("id", ""),
            "name": exercise.get("name_en", "Exercise"),
            "name_vi": vietnamese_exercise_name(exercise.get("name_en", "")),
            "muscle": display_pipe_values(muscles),
            "muscle_keys": muscles,
            "body_part": display_label(exercise.get("body_part", ""), "body_part"),
            "goal": display_pipe_values(exercise.get("goals"), "goal"),
            "category": display_label(exercise.get("category", ""), "category"),
            "difficulty": display_label(exercise.get("difficulty", ""), "difficulty"),
            "sets": prescription["sets"],
            "reps": prescription["reps"],
            "rest": prescription["rest"],
            "met": self._safe_float(exercise.get("met"), 0),
            "image": images[0]["url"] if images else "",
            "images": images,
            "steps": self._steps_vi(exercise)[:5],
            "tips": [
                f"Mục tiêu: {display_pipe_values(exercise.get('goals'), 'goal')}",
                f"Nhóm cơ chính: {display_pipe_values(muscles)}",
            ],
            "action": "Recommend",
            "decision_source": "AI/exercises.csv rule engine",
            "explanation": "Bài được chọn theo mục tiêu, trình độ, nhóm cơ và luật tránh chấn thương.",
        }

    def _exercise_images(self, exercise):
        labels = {
            "image_flat_start": "Tư thế bắt đầu",
            "image_flat_peak": "Tư thế chính",
            "image_flat_main": "Minh họa",
        }
        images = []
        seen = set()
        for key in ("image_flat_start", "image_flat_peak", "image_flat_main"):
            value = str(exercise.get(key) or "").strip().replace("\\", "/")
            if not value:
                continue
            filename = Path(value).name
            if not filename or filename in seen:
                continue
            seen.add(filename)
            images.append({
                "label": labels[key],
                "path": value,
                "filename": filename,
                "url": f"/api/ml/exercise-image/{filename}",
            })
        return images

    def _prescription(self, goal, exercise):
        category = exercise.get("category")
        if goal == "strength":
            return {"sets": 4, "reps": "3-6", "rest": 150}
        if goal == "endurance" or goal == "fat_loss":
            if category == "cardio":
                return {"sets": 3, "reps": "30-60 giây", "rest": 45}
            return {"sets": 3, "reps": "12-20", "rest": 45}
        if goal in {"mobility", "rehabilitation"} or category == "stretching":
            return {"sets": 2, "reps": "20-45 giây", "rest": 30}
        return {"sets": 3, "reps": "8-12", "rest": 75}

    def _nutrition_targets(self, payload, goal, training_days, exercises):
        weight = self._safe_float(payload.get("weight"), 70)
        height = self._safe_float(payload.get("height"), 170)
        age = self._safe_float(payload.get("age"), 25)
        gender = str(payload.get("gender") or payload.get("sex") or "").lower()
        male = gender not in {"female", "nu", "nữ"}
        bmr = 10 * weight + 6.25 * height - 5 * age + (5 if male else -161)
        activity_factor = 1.2 + min(training_days, 6) * 0.055
        tdee = bmr * activity_factor
        avg_met = sum(self._safe_float(item.get("met"), 5) for item in exercises) / max(len(exercises), 1)
        workout_bonus = min(350, max(120, avg_met * weight * 0.35))
        adjustment = {
            "fat_loss": -350,
            "muscle_gain": 250,
            "strength": 150,
            "endurance": 100,
            "mobility": 0,
            "rehabilitation": 0,
        }.get(goal, 0)
        workout_cal = round((tdee + adjustment + workout_bonus) / 10) * 10
        rest_cal = round((tdee + adjustment - 120) / 10) * 10
        protein_factor = 2.0 if goal in {"muscle_gain", "strength"} else 1.8 if goal == "fat_loss" else 1.6
        protein = round(weight * protein_factor)

        def macros(calories):
            protein_cal = protein * 4
            fat = round((calories * 0.25) / 9)
            carbs = round(max(0, calories - protein_cal - fat * 9) / 4)
            return {"calories": int(calories), "protein": protein, "carbs": carbs, "fat": fat}

        return {
            "workout": macros(workout_cal),
            "rest": macros(rest_cal),
            "note": "Calo/protein được tính từ BMR, TDEE ước tính, mục tiêu và cường độ bài tập; Gemini có thể dùng thêm để diễn giải thực đơn, không thay thế công thức nền.",
        }

    def _build_split(self, goal, training_days, payload=None):
        if goal in {"fat_loss", "endurance"}:
            base = [
                {"name": "Toàn thân + tim mạch", "slots": ["full_body", "cardio", "upper_legs", "core", "push", "pull"]},
                {"name": "Chân + core đốt năng lượng", "slots": ["upper_legs", "lower_legs", "core", "plyometrics", "full_body"]},
                {"name": "Thân trên + cardio", "slots": ["chest", "back", "shoulders", "upper_arms", "cardio"]},
            ]
        elif goal == "mobility" or goal == "rehabilitation":
            base = [
                {"name": "Mobility toàn thân", "slots": ["stretching", "core", "back", "shoulders", "upper_legs"]},
                {"name": "Phục hồi thân dưới", "slots": ["stretching", "upper_legs", "lower_legs", "core"]},
                {"name": "Phục hồi thân trên", "slots": ["stretching", "back", "chest", "shoulders"]},
            ]
        else:
            base = [
                {"name": "Push: ngực + vai + tay sau", "slots": ["chest", "shoulders", "triceps_brachii", "push", "core"]},
                {"name": "Pull: lưng + tay trước", "slots": ["back", "latissimus_dorsi", "biceps_brachii", "pull", "core"]},
                {"name": "Legs: đùi + mông + bắp chân", "slots": ["upper_legs", "quadriceps", "hamstrings", "gluteus_maximus", "lower_legs"]},
                {"name": "Upper/Full Body bổ trợ", "slots": ["chest", "back", "shoulders", "core", "full_body"]},
            ]
        result = base[:max(1, min(training_days, len(base)))] or base
        priority = normalize_avoid_terms((payload or {}).get("priority_muscles", "")).get("avoid_keys", [])
        if priority:
            result[0] = {
                **result[0],
                "name": "Ưu tiên " + ", ".join(self._display_slot(slot) for slot in priority[:3]),
                "slots": priority + result[0]["slots"],
            }
        return result

    def _rest_day(self, day_number, nutrition):
        return {
            "day_number": day_number,
            "day_name": f"Ngày {day_number}",
            "is_rest": True,
            "focus": "Nghỉ ngơi + phục hồi",
            "target_calories": nutrition["rest"]["calories"],
            "target_protein": nutrition["rest"]["protein"],
            "target_carbs": nutrition["rest"]["carbs"],
            "target_fat": nutrition["rest"]["fat"],
            "exercises": [],
        }

    def _training_weekdays(self, training_days):
        schedules = {
            1: {1},
            2: {1, 4},
            3: {1, 3, 5},
            4: {1, 2, 4, 6},
            5: {1, 2, 3, 5, 6},
            6: {1, 2, 3, 4, 5, 6},
            7: {1, 2, 3, 4, 5, 6, 7},
        }
        return schedules.get(training_days, schedules[3])

    def _available_weekdays(self, payload):
        values = payload.get("available_training_day_numbers")
        if not values:
            return set()
        if not isinstance(values, list):
            values = str(values).replace(";", ",").split(",")
        weekdays = {self._safe_int(value, 0) for value in values}
        return {day for day in weekdays if 1 <= day <= 7}

    def _weekly_available_weekdays(self, payload):
        values = payload.get("weekly_available_training_day_numbers") or []
        if not isinstance(values, list):
            return []
        weeks = []
        for week in values:
            if not isinstance(week, list):
                week = str(week).replace(";", ",").split(",")
            weekdays = {self._safe_int(value, 0) for value in week}
            valid = {day for day in weekdays if 1 <= day <= 7}
            if valid:
                weeks.append(valid)
        return weeks

    def _avoid_text(self, payload):
        return " ".join(str(payload.get(key, "")) for key in ["avoid_notes", "note", "userInfo", "injuries", "health_notes"])

    def _map_goal(self, value):
        text = normalize_text(str(value or ""))
        if "giam" in text or "fat" in text or "weight" in text:
            return "fat_loss"
        if "suc manh" in text or "strength" in text:
            return "strength"
        if "suc ben" in text or "endurance" in text:
            return "endurance"
        if "linh hoat" in text or "mobility" in text:
            return "mobility"
        if "phuc hoi" in text or "rehab" in text:
            return "rehabilitation"
        return "muscle_gain"

    def _map_level(self, value):
        text = normalize_text(str(value or ""))
        if "moi" in text or "beginner" in text:
            return "beginner"
        if "nang cao" in text or "advanced" in text:
            return "advanced"
        return "intermediate"

    def _level_rank(self, level):
        text = str(level or "").lower()
        if text == "advanced":
            return 3
        if text == "intermediate":
            return 2
        return 1

    def _bmi(self, payload):
        height_m = self._safe_float(payload.get("height"), 0) / 100
        weight = self._safe_float(payload.get("weight"), 0)
        if height_m <= 0 or weight <= 0:
            return None
        return round(weight / (height_m * height_m), 1)

    def _summary(self, goal, level, duration_days, training_days, bmi):
        goal_vi = {
            "fat_loss": "giảm cân/giảm mỡ",
            "muscle_gain": "tăng cơ",
            "strength": "tăng sức mạnh",
            "endurance": "tăng sức bền",
            "mobility": "tăng linh hoạt",
            "rehabilitation": "phục hồi",
        }.get(goal, goal)
        bmi_text = f" BMI hiện tại {bmi}." if bmi else ""
        return f"Lộ trình {duration_days} ngày, {training_days} buổi/tuần cho mục tiêu {goal_vi}, trình độ {display_label(level, 'difficulty')}.{bmi_text}"

    def _safety_note(self, avoid):
        if not avoid["avoid_keys"]:
            return "Không ghi nhận nhóm cơ hoặc vùng chấn thương cần tránh."
        injury_labels = {
            "knee": "gối",
            "lower_back": "lưng dưới",
            "shoulder": "vai",
            "elbow": "khuỷu tay",
            "wrist": "cổ tay",
            "neck": "cổ/gáy",
        }
        labels = [
            injury_labels.get(key) or (
                display_label(key, "muscle")
                if display_label(key, "muscle") != key
                else display_label(key, "body_part")
            )
            for key in avoid["avoid_keys"]
        ]
        unknown = f" Chưa nhận diện: {', '.join(avoid['unknown_terms'])}." if avoid["unknown_terms"] else ""
        return "Đã áp dụng luật tránh/giảm tải cho: " + ", ".join(labels) + "." + unknown

    def _display_slot(self, value):
        return display_label(value, "muscle") if display_label(value, "muscle") != value else display_label(value, "body_part")

    def _split_steps(self, value):
        return [part.strip() for part in str(value or "").split("|") if part.strip()]

    def _steps_vi(self, exercise):
        key = exercise.get("id") or exercise.get("name_en") or ""
        if key in self._translation_cache:
            return self._translation_cache[key]
        if exercise.get("instructions_vi"):
            steps = self._split_steps(exercise.get("instructions_vi"))
            if steps:
                self._translation_cache[key] = steps
                return steps
        source_steps = self._split_steps(exercise.get("instructions_en"))
        translated = self._translate_steps_with_gemini(exercise.get("name_en", ""), source_steps)
        if not translated:
            translated = translate_steps(exercise.get("instructions_en"), exercise.get("name_en", ""))
        self._translation_cache[key] = translated
        return translated

    def _translate_steps_with_gemini(self, exercise_name, source_steps):
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key or genai is None or not source_steps:
            return None
        try:
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel("gemini-1.5-flash")
            prompt = f"""
Dịch hướng dẫn bài tập gym sau sang tiếng Việt tự nhiên, dễ hiểu, đúng kỹ thuật.
Không thêm kiến thức ngoài nội dung gốc. Không dùng markdown. Chỉ trả về JSON hợp lệ dạng:
{{"steps":["...","..."]}}

Bài tập: {exercise_name}
Hướng dẫn gốc:
{json.dumps(source_steps, ensure_ascii=False)}
"""
            response = model.generate_content(prompt)
            text = (response.text or "").strip()
            text = re.sub(r"^```json|```$", "", text, flags=re.IGNORECASE).strip()
            data = json.loads(text)
            steps = data.get("steps") if isinstance(data, dict) else None
            if not isinstance(steps, list):
                return None
            clean_steps = [str(step).strip() for step in steps if str(step).strip()]
            return clean_steps if clean_steps else None
        except Exception:
            return None

    def _tokens(self, value):
        return [part.strip() for part in str(value or "").split("|") if part.strip() and part.strip().lower() != "nan"]

    def _make_id(self, prefix, payload, duration_days):
        seed = "|".join(str(payload.get(key, "")) for key in ["user_id", "userId", "goal", "level", "height", "weight", "age"])
        seed += f"|{duration_days}|{datetime.utcnow().isoformat()}"
        digest = hashlib.sha1(seed.encode("utf-8")).hexdigest()[:8].upper()
        return f"{prefix}{digest}"

    def _safe_int(self, value, default):
        try:
            return int(float(value))
        except (TypeError, ValueError):
            return default

    def _safe_float(self, value, default=0):
        try:
            number = float(value)
            return number if math.isfinite(number) else default
        except (TypeError, ValueError):
            return default
