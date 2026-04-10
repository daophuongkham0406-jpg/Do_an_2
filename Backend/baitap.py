from flask import Blueprint, request, jsonify
from bson.objectid import ObjectId
from ketnoidb import db

baitap_bp = Blueprint('baitap', __name__)

# 1. LẤY DANH SÁCH BÀI TẬP (GET)
@baitap_bp.route('/', methods=['GET'])
def get_exercises():
    try:
        muscle = request.args.get('muscle')
        equip = request.args.get('equip')
        
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