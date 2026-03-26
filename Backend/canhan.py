from flask import Blueprint, request, jsonify
from datetime import datetime
from bson.objectid import ObjectId
from ketnoidb import db

# Tạo Blueprint cho Trang cá nhân
profile_bp = Blueprint('profile', __name__)

# 1. API Lấy thông tin người dùng & Lịch sử
@profile_bp.route('/get/<user_id>', methods=['GET'])
def get_profile(user_id):
    try:
        # Tìm user trong DB
        user = db.user.find_one({"_id": ObjectId(user_id)}, {"passwordHash": 0})
        if not user:
            return jsonify({"message": "Không tìm thấy người dùng"}), 404

        # Tìm lịch sử cập nhật cân nặng của user này
        history_cursor = db.history.find({"userId": user_id}).sort("date", 1)
        history = []
        for h in history_cursor:
            h['_id'] = str(h['_id'])
            history.append(h)

        # Chuyển ObjectId thành string để trả về JSON
        user['_id'] = str(user['_id'])
        
        return jsonify({
            "profile": user,
            "history": history
        }), 200

    except Exception as e:
        print(f"❌ Lỗi get_profile: {e}")
        return jsonify({"message": "Lỗi máy chủ"}), 500

# 2. API Chỉnh sửa thông tin cá nhân
@profile_bp.route('/update/<user_id>', methods=['PUT'])
def update_profile(user_id):
    try:
        data = request.json
        
        # Cập nhật vào bảng user
        update_data = {
            "fullName": data.get('fullName'),
            "age": data.get('age'),
            "gender": data.get('gender'),
            "weight": data.get('weight'),
            "height": data.get('height'),
            "goalWeight": data.get('goalWeight'),
            "level": data.get('level'),
            "goalType": data.get('goalType')
        }
        
        db.user.update_one({"_id": ObjectId(user_id)}, {"$set": update_data})
        return jsonify({"message": "Cập nhật thành công"}), 200

    except Exception as e:
        return jsonify({"message": str(e)}), 500

# 3. API Cập nhật nhật ký (Cân nặng, số đo)
@profile_bp.route('/log/<user_id>', methods=['POST'])
def log_stats(user_id):
    try:
        data = request.json
        today = datetime.now().strftime('%Y-%m-%d')
        
        log_entry = {
            "userId": user_id,
            "date": today,
            "weight": data.get('weight'),
            "fat": data.get('fat'),
            "waist": data.get('waist'),
            "note": data.get('note')
        }

        # Cập nhật hoặc thêm mới log cho ngày hôm nay (mỗi ngày chỉ 1 log)
        db.history.update_one(
            {"userId": user_id, "date": today},
            {"$set": log_entry},
            upsert=True # Nếu chưa có thì tạo mới
        )
        
        # Đồng thời cập nhật cân nặng hiện tại vào bảng user
        db.user.update_one({"_id": ObjectId(user_id)}, {"$set": {"weight": data.get('weight')}})

        return jsonify({"message": "Đã lưu nhật ký thành công"}), 200

    except Exception as e:
        return jsonify({"message": str(e)}), 500