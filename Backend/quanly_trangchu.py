from flask import Blueprint, jsonify, request
from pymongo import MongoClient
from bson import ObjectId
import os
from dotenv import load_dotenv

load_dotenv()

# Tạo Blueprint cho trang chủ
trangchu_bp = Blueprint('trangchu', __name__)

# Kết nối Database
try:
    client = MongoClient(os.getenv("MONGO_URI"))
    db = client["do_an_2"]
    
    tips_collection = db["tips"]
    featured_collection = db["featured"]
    muscles_info_collection = db["muscles_info"]
    sample_workouts_collection = db["sample_workouts"]
except Exception as e:
    print(f"❌ Lỗi DB Trang chủ: {e}")

# ==========================================
# 1. API NỘI DUNG NỔI BẬT (CRUD HOÀN CHỈNH)
# ==========================================
@trangchu_bp.route('/api/featured', methods=['GET', 'POST'])
def api_featured():
    if request.method == 'GET':
        # Kiểm tra xem có phải Admin đang gọi API không
        is_admin = request.args.get('admin') == 'true'
        
        if is_admin:
            data = list(featured_collection.find().sort("order", 1))
        else:
            data = list(featured_collection.find({"is_hidden": {"$ne": True}}).sort("order", 1))
            
        for d in data: d['_id'] = str(d['_id'])
        return jsonify({"success": True, "data": data})
        
    elif request.method == 'POST':
        new_item = request.json
        if "order" not in new_item: new_item["order"] = 99
        featured_collection.insert_one(new_item)
        return jsonify({"success": True, "message": "Đã thêm nội dung nổi bật"})

@trangchu_bp.route('/api/featured/<item_id>', methods=['PUT', 'DELETE'])
def api_featured_detail(item_id):
    try:
        obj_id = ObjectId(item_id)
        if request.method == 'PUT':
            update_data = request.json
            featured_collection.update_one({"_id": obj_id}, {"$set": update_data})
            return jsonify({"success": True, "message": "Đã cập nhật"})
            
        elif request.method == 'DELETE':
            featured_collection.delete_one({"_id": obj_id})
            return jsonify({"success": True, "message": "Đã xóa"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400

# ==========================================
# 2. API NHÓM CƠ & BÀI TẬP (CRUD HOÀN CHỈNH)
# ==========================================
@trangchu_bp.route('/api/muscles-info', methods=['GET', 'POST'])
def api_muscles_info():
    if request.method == 'GET':
        is_admin = request.args.get('admin') == 'true'
        
        if is_admin:
            data = list(muscles_info_collection.find().sort("order", 1))
        else:
            data = list(muscles_info_collection.find({"is_hidden": {"$ne": True}}).sort("order", 1))
            
        for d in data: d['_id'] = str(d['_id'])
        return jsonify({"success": True, "data": data})
        
    elif request.method == 'POST':
        new_item = request.json
        if "order" not in new_item: new_item["order"] = 99
        muscles_info_collection.insert_one(new_item)
        return jsonify({"success": True, "message": "Đã thêm nhóm cơ"})

@trangchu_bp.route('/api/muscles-info/<item_id>', methods=['PUT', 'DELETE'])
def api_muscles_info_detail(item_id):
    try:
        obj_id = ObjectId(item_id)
        if request.method == 'PUT':
            update_data = request.json
            muscles_info_collection.update_one({"_id": obj_id}, {"$set": update_data})
            return jsonify({"success": True, "message": "Đã cập nhật"})
            
        elif request.method == 'DELETE':
            muscles_info_collection.delete_one({"_id": obj_id})
            return jsonify({"success": True, "message": "Đã xóa"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400

# ==========================================
# 3. API MẸO TẬP LUYỆN (CRUD HOÀN CHỈNH)
# ==========================================
@trangchu_bp.route('/api/tips', methods=['GET', 'POST'])
def api_tips():
    if request.method == 'GET':
        is_admin = request.args.get('admin') == 'true'
        
        if is_admin:
            data = list(tips_collection.find().sort("order", 1))
        else:
            data = list(tips_collection.find({"is_hidden": {"$ne": True}}).sort("order", 1))
            
        for d in data: d['_id'] = str(d['_id'])
        return jsonify({"success": True, "data": data})
        
    elif request.method == 'POST':
        new_tip = request.json
        if "order" not in new_tip: new_tip["order"] = 99 
        tips_collection.insert_one(new_tip)
        return jsonify({"success": True, "message": "Đã thêm mẹo mới"})

@trangchu_bp.route('/api/tips/<item_id>', methods=['PUT', 'DELETE'])
def api_tips_detail(item_id):
    try:
        obj_id = ObjectId(item_id)
        if request.method == 'PUT':
            update_data = request.json
            tips_collection.update_one({"_id": obj_id}, {"$set": update_data})
            return jsonify({"success": True, "message": "Đã cập nhật"})
            
        elif request.method == 'DELETE':
            tips_collection.delete_one({"_id": obj_id})
            return jsonify({"success": True, "message": "Đã xóa"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400

# ==========================================
# 4. API LỊCH TẬP MẪU (CRUD HOÀN CHỈNH)
# ==========================================
@trangchu_bp.route('/api/sample-workouts', methods=['GET', 'POST'])
def api_workouts():
    if request.method == 'GET':
        is_admin = request.args.get('admin') == 'true'
        
        # Sắp xếp theo Category trước, rồi đến Order
        if is_admin:
            data = list(sample_workouts_collection.find().sort([("category", 1), ("order", 1)]))
        else:
            data = list(sample_workouts_collection.find({"is_hidden": {"$ne": True}}).sort([("category", 1), ("order", 1)]))
            
        for d in data: d['_id'] = str(d['_id'])
        return jsonify({"success": True, "data": data})
        
    elif request.method == 'POST':
        new_item = request.json
        if "order" not in new_item: new_item["order"] = 99
        sample_workouts_collection.insert_one(new_item)
        return jsonify({"success": True, "message": "Đã thêm lịch tập"})

@trangchu_bp.route('/api/sample-workouts/<item_id>', methods=['PUT', 'DELETE'])
def api_workouts_detail(item_id):
    try:
        obj_id = ObjectId(item_id)
        if request.method == 'PUT':
            update_data = request.json
            sample_workouts_collection.update_one({"_id": obj_id}, {"$set": update_data})
            return jsonify({"success": True, "message": "Đã cập nhật"})
            
        elif request.method == 'DELETE':
            sample_workouts_collection.delete_one({"_id": obj_id})
            return jsonify({"success": True, "message": "Đã xóa"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400