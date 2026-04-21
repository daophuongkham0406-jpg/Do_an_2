from flask import Blueprint, request, jsonify
from bson.objectid import ObjectId

# BẮT BUỘC: Import biến db từ file ketnoidb.py của bạn
from ketnoidb import db 

# Khởi tạo Blueprint thay vì dùng app
avatar_bp = Blueprint('avatar', __name__)

# Chú ý: Dùng @avatar_bp thay vì @app
@avatar_bp.route('/update-avatar', methods=['POST'])
def update_avatar():
    try:
        data = request.json
        user_id = data.get('userId')
        avatar_base64 = data.get('avatar')

        if not user_id or not avatar_base64:
            return jsonify({"success": False, "error": "Thiếu dữ liệu"}), 400

        # Cập nhật ảnh vào trong thông tin user
        db.users.update_one(
            {"_id": ObjectId(user_id)}, 
            {"$set": {"avatar": avatar_base64}}
        )

        return jsonify({"success": True, "message": "Đã lưu ảnh"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500