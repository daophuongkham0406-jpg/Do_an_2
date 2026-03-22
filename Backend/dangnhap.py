from flask import Blueprint, request, jsonify
from flask_cors import CORS
import bcrypt
from datetime import datetime
from ketnoidb import db

# Tạo một Blueprint thay vì App
auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/register', methods=['POST'])
def register():
    data = request.json
    
    # 1. Kiểm tra username tồn tại
    if db.user.find_one({"username": data['username']}):
        return jsonify({"message": "Tên đăng nhập đã tồn tại!"}), 400
    
    # 2. Mã hóa mật khẩu
    password = data['password'].encode('utf-8')
    hashed_password = bcrypt.hashpw(password, bcrypt.gensalt())

    # 3. Tạo object
    new_user = {
        "fullName": data['fullName'],
        "age": data['age'],
        "gender": data['gender'],
        "username": data['username'],
        "email": data['email'],
        "passwordHash": hashed_password.decode('utf-8'),
        "isPremium": False,
        "createdAt": datetime.now()
    }

    # 4. Lưu vào MongoDB
    db.user.insert_one(new_user)
    
    return jsonify({"message": "Đăng ký thành công"}), 201