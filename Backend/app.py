import os
from flask import Flask, request, jsonify
from flask_cors import CORS
import google.generativeai as genai
from pymongo import MongoClient
from dotenv import load_dotenv
from datetime import datetime
from dangnhap import auth_bp

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