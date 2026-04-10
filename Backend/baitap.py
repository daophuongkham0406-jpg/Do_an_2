from flask import Blueprint, request, jsonify
from bson.objectid import ObjectId
from ketnoidb import db

baitap_bp = Blueprint('baitap', __name__)

# Tương đương phương thức: +getByFilter(String muscle, String equip)
@baitap_bp.route('/', methods=['GET'])
def get_exercises_by_filter():
    try:
        # Lấy tham số bộ lọc từ Frontend gửi lên (ví dụ: ?muscle=Ngực&equip=Barbell)
        muscle = request.args.get('muscle')
        equip = request.args.get('equip')
        
        query = {}
        if muscle and muscle != 'all':
            query['muscleGroup'] = muscle
        if equip and equip != 'all':
            query['equipmentType'] = equip

        # Tìm trong DB
        exercises_cursor = db.exercise.find(query)
        exercises = []
        for ex in exercises_cursor:
            ex['_id'] = str(ex['_id']) # Ép kiểu ObjectId thành chuỗi
            exercises.append(ex)

        return jsonify(exercises), 200
    except Exception as e:
        return jsonify({"message": str(e)}), 500

# Tương đương phương thức: +getDetails()
@baitap_bp.route('/<ex_id>', methods=['GET'])
def get_details(ex_id):
    try:
        exercise = db.exercise.find_one({"_id": ObjectId(ex_id)})
        if not exercise:
            return jsonify({"message": "Không tìm thấy bài tập"}), 404
            
        exercise['_id'] = str(exercise['_id'])
        return jsonify(exercise), 200
    except Exception as e:
        return jsonify({"message": str(e)}), 500