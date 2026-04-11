from flask import Blueprint, jsonify, request
from bson.objectid import ObjectId
from ketnoidb import db
from datetime import datetime

plan_bp = Blueprint('plan', __name__)

# 1. Lấy Lộ trình đang "active" của một User
@plan_bp.route('/active/<user_id>', methods=['GET'])
def get_active_plan(user_id):
    try:
        # Tìm plan có user_id tương ứng và status là "active"
        plan = db.plan.find_one({"user_id": user_id, "status": "active"})
        
        if plan:
            plan['id'] = str(plan['_id'])
            del plan['_id']
            return jsonify(plan), 200
        else:
            return jsonify({"message": "Không có lộ trình nào đang diễn ra"}), 404
            
    except Exception as e:
        return jsonify({"message": str(e)}), 500

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