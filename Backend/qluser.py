from flask import Blueprint, jsonify
from bson.objectid import ObjectId
from ketnoidb import db

user_bp = Blueprint('user', __name__)

# 1. Lấy danh sách toàn bộ User
@user_bp.route('/', methods=['GET'])
def get_users():
    try:
        users_cursor = db.user.find()
        users = []
        for u in users_cursor:
            u['id'] = str(u['_id'])
            del u['_id']
            # Cắt bớt thông tin nhạy cảm trước khi gửi về Admin nếu cần
            # del u['passwordHash'] 
            users.append(u)
        return jsonify(users), 200
    except Exception as e:
        return jsonify({"message": str(e)}), 500

# 2. Xóa một User theo ID
@user_bp.route('/<user_id>', methods=['DELETE'])
def delete_user(user_id):
    try:
        result = db.user.delete_one({"_id": ObjectId(user_id)})
        if result.deleted_count == 1:
            return jsonify({"message": "Xóa user thành công"}), 200
        else:
            return jsonify({"message": "Không tìm thấy user"}), 404
    except Exception as e:
        return jsonify({"message": str(e)}), 500