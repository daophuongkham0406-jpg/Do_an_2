import os
from flask import Flask, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
from dangnhap import auth_bp
from ketnoidb import db  # Import kết nối từ file ketnoidb.py của bạn

# 1. Tải cấu hình từ file .env (Folder Backend)
load_dotenv()

# 2. Khởi tạo Flask App
app = Flask(__name__)

# 3. Cấu hình CORS (Rất quan trọng để Frontend gọi vào Backend không bị chặn)
CORS(app, resources={r"/*": {"origins": "*"}})

# 4. Đăng ký Blueprint cho phần Đăng nhập/Đăng ký
# Tất cả các link trong dangnhap.py sẽ có tiền tố /api/auth
# Ví dụ: http://127.0.0.1:5000/api/auth/register
app.register_blueprint(auth_bp, url_prefix='/api/auth')

# 5. Route kiểm tra Server
@app.route('/')
def home():
    return jsonify({
        "status": "Server Chinh dang chay",
        "port": 5000,
        "database": "Connected" if db is not None else "Error"
    })

# 6. Chạy Server Chính
if __name__ == '__main__':
    print("--------------------------------------------------")
    print(" SERVER CHÍNH (ĐĂNG NHẬP) ĐANG CHẠY TẠI:")
    print(" http://127.0.0.1:5000")
    print("--------------------------------------------------")
    # Chạy ở cổng 5000
    app.run(debug=True, port=5000)