from flask import Blueprint, jsonify, request
from bson.objectid import ObjectId
from ketnoidb import db
from datetime import datetime
from services.ml_integration_service import MLIntegrationService

plan_bp = Blueprint('plan', __name__)
ml_refresh_service = MLIntegrationService()


def serialize_plan(plan):
    if not plan:
        return None
    plan = json_safe(plan)
    plan["id"] = str(plan["_id"])
    plan["_id"] = str(plan["_id"])
    return plan


def json_safe(value):
    if isinstance(value, ObjectId):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, list):
        return [json_safe(item) for item in value]
    if isinstance(value, dict):
        return {key: json_safe(item) for key, item in value.items()}
    return value


def build_daily_progress(plan_data):
    progress = []
    for day in plan_data.get("days", []):
        exercises = []
        for ex in day.get("exercises", []):
            exercises.append({
                "exercise_id": ex.get("exercise_id") or ex.get("id") or "",
                "name": ex.get("name") or ex.get("exercise_name") or "Bài tập",
                "name_vi": ex.get("name_vi") or "",
                "muscle": ex.get("muscle") or "",
                "muscle_keys": ex.get("muscle_keys") or "",
                "body_part": ex.get("body_part") or "",
                "goal": ex.get("goal") or "",
                "category": ex.get("category") or "",
                "met": ex.get("met"),
                "image": ex.get("image") or "",
                "images": ex.get("images") or [],
                "equipment": ex.get("equip") or ex.get("equipment") or "",
                "sets": ex.get("sets"),
                "reps": ex.get("reps"),
                "rest": ex.get("rest"),
                "difficulty": ex.get("diff") or ex.get("difficulty"),
                "action": ex.get("action"),
                "decision_source": ex.get("decision_source"),
                "explanation": ex.get("explanation"),
                "safety_status": ex.get("safety_status"),
                "steps": ex.get("steps") or [],
                "tips": ex.get("tips") or [],
                "completed": False,
                "completed_at": None,
            })
        progress.append({
            "day_number": day.get("day_number"),
            "day_name": day.get("day_name"),
            "is_rest": bool(day.get("is_rest")),
            "focus": day.get("focus"),
            "target_calories": day.get("target_calories"),
            "target_protein": day.get("target_protein"),
            "target_carbs": day.get("target_carbs"),
            "target_fat": day.get("target_fat"),
            "completed_exercises_count": 0,
            "total_exercises_count": len(exercises),
            "day_done": False,
            "is_locked": False,
            "updated_at": None,
            "exercises": exercises,
        })
    return progress


def refresh_plan_exercise_text(plan_data: dict) -> dict:
    plan_data = dict(plan_data or {})
    exercise_map = {row.get("id"): row for row in ml_refresh_service._load_exercises()}
    for day in plan_data.get("days", []):
        for ex in day.get("exercises", []):
            source = exercise_map.get(ex.get("exercise_id") or ex.get("id"))
            if not source:
                continue
            refreshed = ml_refresh_service._format_exercise(
                source,
                ml_refresh_service._map_goal((plan_data.get("input_snapshot") or {}).get("goal")),
                day.get("day_number") or 1,
                1,
                plan_data.get("plan_id") or "",
            )
            for key in ["name_vi", "steps", "tips", "goal", "category", "difficulty", "met", "body_part", "muscle", "muscle_keys", "image", "images"]:
                ex[key] = refreshed.get(key)
    return plan_data


def refresh_daily_progress_text(daily_progress: list, plan_data: dict) -> list:
    refreshed_by_day = {
        day.get("day_number"): {
            ex.get("exercise_id"): ex
            for ex in day.get("exercises", [])
            if ex.get("exercise_id")
        }
        for day in plan_data.get("days", [])
    }
    for day in daily_progress or []:
        day_source = refreshed_by_day.get(day.get("day_number"), {})
        day["target_calories"] = next(
            (src_day.get("target_calories") for src_day in plan_data.get("days", []) if src_day.get("day_number") == day.get("day_number")),
            day.get("target_calories"),
        )
        day["target_protein"] = next(
            (src_day.get("target_protein") for src_day in plan_data.get("days", []) if src_day.get("day_number") == day.get("day_number")),
            day.get("target_protein"),
        )
        day["target_carbs"] = next(
            (src_day.get("target_carbs") for src_day in plan_data.get("days", []) if src_day.get("day_number") == day.get("day_number")),
            day.get("target_carbs"),
        )
        day["target_fat"] = next(
            (src_day.get("target_fat") for src_day in plan_data.get("days", []) if src_day.get("day_number") == day.get("day_number")),
            day.get("target_fat"),
        )
        for ex in day.get("exercises", []):
            source = day_source.get(ex.get("exercise_id"))
            if not source:
                continue
            for key in ["name_vi", "steps", "tips", "goal", "category", "difficulty", "met", "body_part", "muscle", "muscle_keys", "image", "images"]:
                ex[key] = source.get(key)
    return daily_progress or []

# 1. Lấy Lộ trình đang "active" của một User
@plan_bp.route('/active/<user_id>', methods=['GET'])
def get_active_plan(user_id):
    try:
        # Tìm plan có user_id tương ứng và status là "active"
        plan = db.plan.find_one({"user_id": user_id, "status": "active"}, sort=[("created_at", -1)])
        
        if plan:
            return jsonify(serialize_plan(plan)), 200
        else:
            return jsonify({"message": "Không có lộ trình nào đang diễn ra"}), 404
            
    except Exception as e:
        return jsonify({"message": str(e)}), 500


@plan_bp.route('/save-ai-plan', methods=['POST'])
def save_ai_plan():
    try:
        data = request.json or {}
        user_id = data.get("userId") or data.get("user_id")
        plan_data = data.get("plan_data")
        if not user_id or not plan_data:
            return jsonify({"success": False, "error": "Thiếu userId hoặc plan_data"}), 400

        now = datetime.utcnow()
        db.plan.update_many(
            {"user_id": user_id, "status": "active"},
            {"$set": {"status": "cancelled", "cancelled_at": now, "updated_at": now}},
        )

        doc = {
            "user_id": user_id,
            "status": "active",
            "source": data.get("source", "ai_exercises_csv_rule_engine"),
            "generation_source": data.get("source", "ai_exercises_csv_rule_engine"),
            "input_snapshot": data.get("input_snapshot") or {},
            "ai_decision": data.get("ai_decision") or {},
            "plan_data": plan_data,
            "daily_progress": build_daily_progress(plan_data),
            "created_at": now,
            "updated_at": now,
        }
        result = db.plan.insert_one(doc)
        return jsonify({
            "success": True,
            "message": "Đã lưu lộ trình AI vào MongoDB",
            "plan_id": str(result.inserted_id),
            "plan": serialize_plan(db.plan.find_one({"_id": result.inserted_id})),
        }), 201
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@plan_bp.route('/get-active-plan', methods=['GET'])
def get_active_plan_query():
    user_id = request.args.get("userId") or request.args.get("user_id")
    if not user_id:
        return jsonify({"plan": None, "message": "Thiếu userId"}), 400
    plan = db.plan.find_one({"user_id": user_id, "status": "active"}, sort=[("created_at", -1)])
    return jsonify({"plan": serialize_plan(plan) if plan else None}), 200


@plan_bp.route('/refresh-ai-plan-text/<plan_id>', methods=['POST'])
def refresh_ai_plan_text(plan_id):
    try:
        plan = db.plan.find_one({"_id": ObjectId(plan_id)})
        if not plan:
            return jsonify({"success": False, "error": "Không tìm thấy lộ trình"}), 404
        plan_data = refresh_plan_exercise_text(plan.get("plan_data") or {})
        daily_progress = refresh_daily_progress_text(plan.get("daily_progress") or [], plan_data)
        now = datetime.utcnow()
        db.plan.update_one(
            {"_id": ObjectId(plan_id)},
            {"$set": {"plan_data": plan_data, "daily_progress": daily_progress, "updated_at": now}},
        )
        refreshed = db.plan.find_one({"_id": ObjectId(plan_id)})
        return jsonify({"success": True, "plan": serialize_plan(refreshed)}), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@plan_bp.route('/cancel-active/<user_id>', methods=['DELETE'])
def cancel_active_plan(user_id):
    now = datetime.utcnow()
    db.plan.update_many(
        {"user_id": user_id, "status": "active"},
        {"$set": {"status": "cancelled", "cancelled_at": now, "updated_at": now}},
    )
    return jsonify({"success": True, "message": "Đã hủy lộ trình đang tập"}), 200


@plan_bp.route('/checkin-exercise', methods=['POST'])
def checkin_exercise():
    try:
        data = request.json or {}
        plan_id = data.get("planId") or data.get("plan_id")
        day_number = int(data.get("dayNumber") or data.get("day_number"))
        exercise_name = data.get("exerciseName") or data.get("exercise_name")
        completed = bool(data.get("completed"))
        if not plan_id or not exercise_name:
            return jsonify({"success": False, "error": "Thiếu planId hoặc exerciseName"}), 400

        plan = db.plan.find_one({"_id": ObjectId(plan_id)})
        if not plan:
            return jsonify({"success": False, "error": "Không tìm thấy lộ trình"}), 404

        progress = plan.get("daily_progress", [])
        target_day = None
        for day in progress:
            if int(day.get("day_number") or 0) == day_number:
                target_day = day
                break
        if not target_day:
            return jsonify({"success": False, "error": "Không tìm thấy ngày tập"}), 404
        if target_day.get("is_locked"):
            return jsonify({"success": False, "error": "Ngày này đã chốt sổ"}), 400

        now = datetime.utcnow()
        if exercise_name == "RestDay" or target_day.get("is_rest"):
            if target_day.get("day_done") and not completed:
                return jsonify({"success": False, "error": "Ngày nghỉ đã hoàn thành, không thể hoàn tác"}), 400
            target_day["day_done"] = completed
        else:
            target_exercise = None
            for ex in target_day.get("exercises", []):
                if ex.get("name") == exercise_name:
                    target_exercise = ex
                    break
            if not target_exercise:
                return jsonify({"success": False, "error": "Không tìm thấy bài tập"}), 404
            if target_exercise.get("completed"):
                return jsonify({"success": False, "error": "Bài tập đã hoàn thành, không thể hoàn tác"}), 400
            if not completed:
                return jsonify({"success": False, "error": "Không thể bỏ hoàn thành bài tập"}), 400
            target_exercise["completed"] = True
            target_exercise["completed_at"] = now
            exercises = target_day.get("exercises", [])
            target_day["day_done"] = bool(exercises) and all(bool(ex.get("completed")) for ex in exercises)
        exercises = target_day.get("exercises", [])
        target_day["completed_exercises_count"] = sum(1 for ex in exercises if ex.get("completed"))
        target_day["total_exercises_count"] = len(exercises)
        target_day["updated_at"] = now

        db.plan.update_one(
            {"_id": ObjectId(plan_id)},
            {"$set": {"daily_progress": progress, "updated_at": now}},
        )
        return jsonify({
            "success": True,
            "daily_progress": json_safe(progress),
            "day_progress": json_safe(target_day),
        }), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@plan_bp.route('/lock-day', methods=['POST'])
def lock_day():
    try:
        data = request.json or {}
        plan_id = data.get("planId") or data.get("plan_id")
        day_number = int(data.get("dayNumber") or data.get("day_number"))
        plan = db.plan.find_one({"_id": ObjectId(plan_id)})
        if not plan:
            return jsonify({"success": False, "error": "Không tìm thấy lộ trình"}), 404

        progress = plan.get("daily_progress", [])
        now = datetime.utcnow()
        for day in progress:
            if int(day.get("day_number") or 0) == day_number:
                day["is_locked"] = True
                day["day_done"] = True
                day["locked_at"] = now
                day["updated_at"] = now
                break
        db.plan.update_one(
            {"_id": ObjectId(plan_id)},
            {"$set": {"daily_progress": progress, "updated_at": now}},
        )
        return jsonify({"success": True, "message": "Đã chốt sổ ngày tập"}), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

# 2. Cập nhật tiến độ (Đánh dấu hoàn thành ngày tập)
@plan_bp.route('/update_progress/<plan_id>', methods=['POST'])
def update_progress(plan_id):
    try:
        data = request.json
        day_index = data.get('day_index') # Ngày số mấy (0 đến 6)
        is_completed = data.get('is_completed') # True hoặc False
        
        # Cập nhật trạng thái của ngày đó trong mảng daily_progress
        update_query = {
            f"daily_progress.{day_index}.completed": is_completed,
            f"daily_progress.{day_index}.updated_at": datetime.utcnow()
        }
        
        result = db.plan.update_one(
            {"_id": ObjectId(plan_id)},
            {"$set": update_query}
        )
        
        if result.modified_count == 1:
            return jsonify({"message": "Cập nhật tiến độ thành công!"}), 200
        else:
            return jsonify({"message": "Không tìm thấy plan hoặc không có thay đổi"}), 400
            
    except Exception as e:
        return jsonify({"message": str(e)}), 500
