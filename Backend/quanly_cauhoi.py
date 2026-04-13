from flask import Blueprint, jsonify, request
from pymongo import MongoClient
from bson import ObjectId
import os
from dotenv import load_dotenv

load_dotenv()

# Tạo Blueprint cho Quản lý FAQ
cauhoi_bp = Blueprint('cauhoi', __name__)

# Kết nối Database
try:
    client = MongoClient(os.getenv("MONGO_URI"))
    db = client["do_an_2"]
    faq_collection = db["faq"] # Bảng chứa Câu hỏi thường gặp
    about_features_collection = db["about_features"] # Bảng Đặc điểm nổi bật
    contacts_collection = db["contacts"] # Bảng Liên hệ
    hero_stats_collection = db["hero_stats"] # Bảng Thống kê Nền tảng
except Exception as e:
    print(f"❌ Lỗi DB Quản lý Câu hỏi: {e}")

# ==========================================
# 1. API CÂU HỎI THƯỜNG GẶP (FAQ)
# ==========================================
@cauhoi_bp.route('/api/faq', methods=['GET', 'POST'])
def api_faq():
    if request.method == 'GET':
        # Kiểm tra xem có phải Admin đang gọi API không
        is_admin = request.args.get('admin') == 'true'
        
        if is_admin:
            data = list(faq_collection.find().sort("cat", 1))
        else:
            data = list(faq_collection.find({"is_hidden": {"$ne": True}}).sort("cat", 1))
            
        for d in data: d['_id'] = str(d['_id'])
        return jsonify({"success": True, "data": data})
        
    elif request.method == 'POST':
        new_item = request.json
        faq_collection.insert_one(new_item)
        return jsonify({"success": True, "message": "Đã thêm câu hỏi mới"})

@cauhoi_bp.route('/api/faq/<item_id>', methods=['PUT', 'DELETE'])
def api_faq_detail(item_id):
    try:
        obj_id = ObjectId(item_id)
        if request.method == 'PUT':
            update_data = request.json
            faq_collection.update_one({"_id": obj_id}, {"$set": update_data})
            return jsonify({"success": True, "message": "Đã cập nhật câu hỏi"})
            
        elif request.method == 'DELETE':
            faq_collection.delete_one({"_id": obj_id})
            return jsonify({"success": True, "message": "Đã xóa câu hỏi"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400

# ==========================================
# 2. API VÌ SAO CHỌN FIT ME (ABOUT FEATURES)
# ==========================================
@cauhoi_bp.route('/api/about-features', methods=['GET', 'POST'])
def api_about_features():
    if request.method == 'GET':
        is_admin = request.args.get('admin') == 'true'
        
        if is_admin:
            data = list(about_features_collection.find().sort("order", 1))
        else:
            data = list(about_features_collection.find({"is_hidden": {"$ne": True}}).sort("order", 1))
            
        for d in data: d['_id'] = str(d['_id'])
        return jsonify({"success": True, "data": data})
        
    elif request.method == 'POST':
        new_item = request.json
        if "order" not in new_item: new_item["order"] = 99
        about_features_collection.insert_one(new_item)
        return jsonify({"success": True, "message": "Đã thêm đặc điểm"})

@cauhoi_bp.route('/api/about-features/<item_id>', methods=['PUT', 'DELETE'])
def api_about_features_detail(item_id):
    try:
        obj_id = ObjectId(item_id)
        if request.method == 'PUT':
            update_data = request.json
            about_features_collection.update_one({"_id": obj_id}, {"$set": update_data})
            return jsonify({"success": True, "message": "Đã cập nhật đặc điểm"})
            
        elif request.method == 'DELETE':
            about_features_collection.delete_one({"_id": obj_id})
            return jsonify({"success": True, "message": "Đã xóa đặc điểm"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400

# ==========================================
# 3. API THÔNG TIN LIÊN HỆ (CONTACTS)
# ==========================================
@cauhoi_bp.route('/api/contacts', methods=['GET', 'POST'])
def api_contacts():
    if request.method == 'GET':
        is_admin = request.args.get('admin') == 'true'
        
        if is_admin:
            data = list(contacts_collection.find().sort("order", 1))
        else:
            data = list(contacts_collection.find({"is_hidden": {"$ne": True}}).sort("order", 1))
            
        for d in data: d['_id'] = str(d['_id'])
        return jsonify({"success": True, "data": data})
        
    elif request.method == 'POST':
        new_item = request.json
        if "order" not in new_item: new_item["order"] = 99
        contacts_collection.insert_one(new_item)
        return jsonify({"success": True, "message": "Đã thêm liên hệ mới"})

@cauhoi_bp.route('/api/contacts/<item_id>', methods=['PUT', 'DELETE'])
def api_contacts_detail(item_id):
    try:
        obj_id = ObjectId(item_id)
        if request.method == 'PUT':
            update_data = request.json
            contacts_collection.update_one({"_id": obj_id}, {"$set": update_data})
            return jsonify({"success": True, "message": "Đã cập nhật liên hệ"})
            
        elif request.method == 'DELETE':
            contacts_collection.delete_one({"_id": obj_id})
            return jsonify({"success": True, "message": "Đã xóa liên hệ"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400
    
# ==========================================
# 4. API THỐNG KÊ NỀN TẢNG (HERO STATS)
# ==========================================
@cauhoi_bp.route('/api/hero-stats', methods=['GET', 'POST'])
def api_hero_stats():
    if request.method == 'GET':
        is_admin = request.args.get('admin') == 'true'
        
        if is_admin:
            data = list(hero_stats_collection.find().sort("order", 1))
        else:
            data = list(hero_stats_collection.find({"is_hidden": {"$ne": True}}).sort("order", 1))
            
        for d in data: d['_id'] = str(d['_id'])
        return jsonify({"success": True, "data": data})
        
    elif request.method == 'POST':
        new_item = request.json
        if "order" not in new_item: new_item["order"] = 99
        hero_stats_collection.insert_one(new_item)
        return jsonify({"success": True, "message": "Đã thêm thống kê"})

@cauhoi_bp.route('/api/hero-stats/<item_id>', methods=['PUT', 'DELETE'])
def api_hero_stats_detail(item_id):
    try:
        obj_id = ObjectId(item_id)
        if request.method == 'PUT':
            update_data = request.json
            hero_stats_collection.update_one({"_id": obj_id}, {"$set": update_data})
            return jsonify({"success": True, "message": "Đã cập nhật thống kê"})
            
        elif request.method == 'DELETE':
            hero_stats_collection.delete_one({"_id": obj_id})
            return jsonify({"success": True, "message": "Đã xóa thống kê"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400