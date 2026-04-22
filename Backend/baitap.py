from flask import Blueprint, request, jsonify
from bson.objectid import ObjectId
from ketnoidb import db
from collections import defaultdict  # ← THÊM DÒNG NÀY

baitap_bp = Blueprint('baitap', __name__)

LIMIT_PER_MUSCLE = 4  # ← THÊM DÒNG NÀY - Giới hạn 4 bài/nhóm cơ

# 1. LẤY DANH SÁCH BÀI TẬP (GET)
@baitap_bp.route('/', methods=['GET'])
def get_exercises():
    try:
        muscle = request.args.get('muscle')
        equip = request.args.get('equip')
        user_id = request.args.get('userId')  # ← THÊM DÒNG NÀY

          # ── THÊM ĐOẠN NÀY: Kiểm tra quyền Premium ──
        is_premium = False
        if user_id:
            try:
                user = db.user.find_one({"_id": ObjectId(user_id)})
                if user:
                    role = user.get("role", "user")
                    if role == "admin":
                        is_premium = True  # Admin xem tất cả
                    else:
                        is_premium = bool(user.get("isPremium", False))
            except Exception:
                pass  # userId lỗi → coi như chưa đăng nhập
        # ── KẾT THÚC ĐOẠN THÊM ──

        
        query = {}
        if muscle and muscle != 'all': query['muscle'] = muscle
        if equip and equip != 'all': query['equip'] = equip

        exercises_cursor = db.exercise.find(query)
        exercises = []
        for ex in exercises_cursor:
            # Đổi _id của MongoDB thành id để Frontend Admin dễ đọc
            ex['id'] = str(ex['_id'])
            del ex['_id']
            exercises.append(ex)

              # ── THÊM ĐOẠN NÀY: Giới hạn nếu không phải Premium ──
        if not is_premium:
            muscle_count = defaultdict(int)
            limited = []
            for ex in exercises:
                m = ex.get('muscle', '')
                if muscle_count[m] < LIMIT_PER_MUSCLE:
                    limited.append(ex)
                    muscle_count[m] += 1
            return jsonify({
                "data": limited,
                "isLimited": True,
                "limitPerMuscle": LIMIT_PER_MUSCLE
            }), 200
        # ── KẾT THÚC ĐOẠN THÊM ──

        return jsonify(exercises), 200
    except Exception as e:
        return jsonify({"message": str(e)}), 500

# 2. THÊM BÀI TẬP MỚI (POST)
@baitap_bp.route('/', methods=['POST'])
def add_exercise():
    try:
        data = request.json
        # Insert vào DB
        result = db.exercise.insert_one(data)
        # Lấy ID vừa tạo trả về cho Frontend
        data['id'] = str(result.inserted_id)
        del data['_id']
        return jsonify(data), 201
    except Exception as e:
        return jsonify({"message": str(e)}), 500

# 3. SỬA BÀI TẬP (PUT)
@baitap_bp.route('/<ex_id>', methods=['PUT'])
def update_exercise(ex_id):
    try:
        data = request.json
        # Update trong DB
        db.exercise.update_one({"_id": ObjectId(ex_id)}, {"$set": data})
        data['id'] = ex_id
        return jsonify(data), 200
    except Exception as e:
        return jsonify({"message": str(e)}), 500

# 4. XÓA BÀI TẬP (DELETE)
@baitap_bp.route('/<ex_id>', methods=['DELETE'])
def delete_exercise(ex_id):
    try:
        db.exercise.delete_one({"_id": ObjectId(ex_id)})
        return jsonify({"message": "Xóa thành công"}), 200
    except Exception as e:
        return jsonify({"message": str(e)}), 500