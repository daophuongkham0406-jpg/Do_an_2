import os
from flask import Flask, request, jsonify
from flask_cors import CORS
import google.generativeai as genai
from pymongo import MongoClient
from dotenv import load_dotenv
from datetime import datetime
from dangnhap import auth_bp
from canhan import profile_bp
from baitap import baitap_bp
from qluser import user_bp
from quanly_plan import plan_bp
from quanly_trangchu import trangchu_bp

# 1. Tải cấu hình từ file .env
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
MONGO_URI = os.getenv("MONGO_URI")

# Đăng ký Blueprint cho phần đăng nhập
app = Flask(__name__)

# Cấu hình đầy đủ để trình duyệt không chặn nữa
CORS(app, resources={r"/*": {"origins": "*"}})

# Tất cả đường dẫn trong auth_bp sẽ bắt đầu bằng /api/auth
app.register_blueprint(auth_bp, url_prefix='/api/auth') 

# Tất cả đường dẫn trong profile_bp sẽ bắt đầu bằng /api/profile
app.register_blueprint(profile_bp, url_prefix='/api/profile')
# Tất cả đường dẫn trong baitap_bp sẽ bắt đầu bằng /api/exercises
app.register_blueprint(baitap_bp, url_prefix='/api/exercises')
# Tất cả đường dẫn trong user_bp sẽ bắt đầu bằng /api/users
app.register_blueprint(user_bp, url_prefix='/api/users')
# Thêm dòng này ở chỗ đăng ký Blueprint:
app.register_blueprint(plan_bp, url_prefix='/api/plans')
# Thêm dòng này ở chỗ đăng ký Blueprint:
app.register_blueprint(trangchu_bp)

# 3. Kết nối MongoDB
try:
    client = MongoClient(MONGO_URI)
    db = client["do_an_2"]
    workout_collection = db["workout_plans"]
    print("✅ Kết nối MongoDB thành công!")
except Exception as e:
    print(f"❌ Lỗi kết nối MongoDB: {e}")

# Chạy server ở cổng 5000
if __name__ == '__main__':
    print("🚀 Máy chủ Python đang chạy tại: http://127.0.0.1:5000")
    app.run(debug=True, port=5000)