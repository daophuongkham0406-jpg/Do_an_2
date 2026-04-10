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
        "role": 'user',
        "createdAt": datetime.now()
    }

    # 4. Lưu vào MongoDB
    db.user.insert_one(new_user)
    
    return jsonify({"message": "Đăng ký thành công"}), 201


# ==============================================================================
@auth_bp.route('/login', methods=['POST'])
def login():
    try:
        data = request.json
        email = data.get('email')
        password = data.get('password')

        # 1. Kiểm tra xem Frontend có gửi đủ thông tin không
        if not email or not password:
            return jsonify({"message": "Vui lòng nhập đầy đủ Email và Mật khẩu."}), 400

        # 2. Đi tìm User trong Database bằng Email
        user = db.user.find_one({"email": email})
        
        # Nếu không tìm thấy ai có email này
        if not user:
            return jsonify({"message": "Email hoặc mật khẩu không chính xác."}), 401

        # 3. So sánh mật khẩu (So sánh mk người dùng nhập với mk đã mã hóa trong DB)
        # Vì lúc đăng ký ta lưu dạng string, giờ phải chuyển lại thành byte để bcrypt kiểm tra
        is_password_correct = bcrypt.checkpw(
            password.encode('utf-8'), 
            user['passwordHash'].encode('utf-8')
        )

        if not is_password_correct:
            return jsonify({"message": "Email hoặc mật khẩu không chính xác."}), 401

        # 4. Đăng nhập thành công!
        # Tùy chọn: Ở đây bạn có thể tạo Token (JWT) hoặc Session để duy trì đăng nhập
        # Tạm thời ta chỉ trả về thông báo thành công và một số thông tin cơ bản (không trả về mật khẩu!)
        user_info = {
            "id": str(user['_id']),
            "fullName": user['fullName'],
            "username": user['username'],
            "isPremium": user['isPremium'],
            "role": user.get('role', 'user')
        }

        return jsonify({
            "message": "Đăng nhập thành công",
            "user": user_info
        }), 200

    except Exception as e:
        print(f"❌ Lỗi hệ thống nghiêm trọng (Login): {e}")
        return jsonify({"message": "Đã xảy ra lỗi máy chủ không xác định."}), 500