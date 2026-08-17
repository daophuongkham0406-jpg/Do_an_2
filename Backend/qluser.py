from flask import Blueprint, jsonify, request
from bson.objectid import ObjectId
from ketnoidb import db
from email.utils import parsedate_to_datetime

user_bp = Blueprint('user', __name__)


def public_user(user):
    user = dict(user or {})
    user['id'] = str(user['_id'])
    del user['_id']
    user.pop('passwordHash', None)
    return user


def requester_id():
    return request.headers.get("X-User-Id") or request.args.get("requesterId")


def admin_sort_key(user):
    created_at = user.get("createdAt")
    if created_at:
        try:
            value = created_at.isoformat()
        except AttributeError:
            try:
                value = parsedate_to_datetime(str(created_at)).isoformat()
            except Exception:
                value = str(created_at)
        return (0, value, str(user.get("_id")))
    try:
        return (1, user["_id"].generation_time.isoformat(), str(user.get("_id")))
    except Exception:
        return (2, "", str(user.get("_id")))


def primary_admin():
    admins = list(db.user.find({"role": "admin"}))
    if not admins:
        return None
    return sorted(admins, key=admin_sort_key)[0]


def is_primary_admin(user_id):
    try:
        primary = primary_admin()
        return bool(primary and str(primary["_id"]) == str(user_id))
    except Exception:
        return False


def require_primary_admin():
    rid = requester_id()
    if not rid or not is_primary_admin(rid):
        return jsonify({
            "message": "Chỉ admin gốc mới có quyền quản lý tài khoản người dùng"
        }), 403
    return None

# 1. Lấy danh sách toàn bộ User
@user_bp.route('/', methods=['GET'])
def get_users():
    try:
        denied = require_primary_admin()
        if denied:
            return denied
        users_cursor = db.user.find()
        users = []
        for u in users_cursor:
            users.append(public_user(u))
        return jsonify(users), 200
    except Exception as e:
        return jsonify({"message": str(e)}), 500


@user_bp.route('/<user_id>', methods=['GET'])
def get_user(user_id):
    try:
        rid = requester_id()
        if rid and str(rid) != str(user_id) and not is_primary_admin(rid):
            return jsonify({"message": "Bạn không có quyền xem tài khoản này"}), 403
        user = db.user.find_one({"_id": ObjectId(user_id)})
        if not user:
            return jsonify({"message": "Không tìm thấy user"}), 404
        return jsonify(public_user(user)), 200
    except Exception as e:
        return jsonify({"message": str(e)}), 500


# 2. Cập nhật thông tin / quyền User theo ID
@user_bp.route('/<user_id>', methods=['PUT'])
def update_user(user_id):
    try:
        denied = require_primary_admin()
        if denied:
            return denied
        data = request.json or {}
        allowed_fields = {"role", "isPremium", "premiumPlan", "premiumExpire", "fullName", "age", "gender"}
        update_data = {key: value for key, value in data.items() if key in allowed_fields}

        if "role" in update_data:
            role = str(update_data["role"]).strip().lower()
            if role not in {"user", "admin", "premium"}:
                return jsonify({"message": "Vai trò tài khoản không hợp lệ"}), 400
            if is_primary_admin(user_id) and role != "admin":
                return jsonify({"message": "Không thể hạ quyền admin gốc"}), 400
            update_data["role"] = role

        if "isPremium" in update_data:
            update_data["isPremium"] = bool(update_data["isPremium"])

        if not update_data:
            return jsonify({"message": "Không có dữ liệu hợp lệ để cập nhật"}), 400

        result = db.user.update_one({"_id": ObjectId(user_id)}, {"$set": update_data})
        if result.matched_count != 1:
            return jsonify({"message": "Không tìm thấy user"}), 404

        updated = db.user.find_one({"_id": ObjectId(user_id)})
        return jsonify(public_user(updated)), 200
    except Exception as e:
        return jsonify({"message": str(e)}), 500


# 3. Xóa một User theo ID
@user_bp.route('/<user_id>', methods=['DELETE'])
def delete_user(user_id):
    try:
        denied = require_primary_admin()
        if denied:
            return denied
        if is_primary_admin(user_id):
            return jsonify({"message": "Không thể xóa admin gốc"}), 400
        result = db.user.delete_one({"_id": ObjectId(user_id)})
        if result.deleted_count == 1:
            return jsonify({"message": "Xóa user thành công"}), 200
        else:
            return jsonify({"message": "Không tìm thấy user"}), 404
    except Exception as e:
        return jsonify({"message": str(e)}), 500


@user_bp.route('/<user_id>/permissions', methods=['GET'])
def get_user_permissions(user_id):
    try:
        user = db.user.find_one({"_id": ObjectId(user_id)})
        if not user:
            return jsonify({"message": "Không tìm thấy user"}), 404
        is_admin = user.get("role") == "admin"
        can_manage_users = is_admin and is_primary_admin(user_id)
        return jsonify({
            "isAdmin": is_admin,
            "isPrimaryAdmin": can_manage_users,
            "canManageUsers": can_manage_users,
        }), 200
    except Exception as e:
        return jsonify({"message": str(e)}), 500
