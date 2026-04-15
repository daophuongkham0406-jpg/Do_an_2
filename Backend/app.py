import os
from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_mail import Mail  # Thư viện dùng để gửi thư
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
from quanly_cauhoi import cauhoi_bp
from quanly_tcn import tcn_bp

# 1. Tải cấu hình từ file .env
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
MONGO_URI = os.getenv("MONGO_URI")

app = Flask(__name__)

# Cấu hình đầy đủ để trình duyệt không chặn nữa
CORS(app, resources={r"/*": {"origins": "*"}})

# ============================================================================
# 2. CẤU HÌNH GỬI EMAIL (FLASK-MAIL) 
# ============================================================================
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587                     # Dùng cổng 587 (TLS) để tránh bị nhà mạng chặn
app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USE_SSL'] = False
app.config['MAIL_DEFAULT_SENDER'] = os.getenv('MAIL_USERNAME')

# Khởi tạo đối tượng mail
mail = Mail(app)

# Tất cả đường dẫn Blueprint
app.register_blueprint(auth_bp, url_prefix='/api/auth') 
app.register_blueprint(profile_bp, url_prefix='/api/profile')
app.register_blueprint(baitap_bp, url_prefix='/api/exercises')
app.register_blueprint(user_bp, url_prefix='/api/users')
app.register_blueprint(plan_bp, url_prefix='/api/plans')
app.register_blueprint(trangchu_bp)
app.register_blueprint(cauhoi_bp)
app.register_blueprint(tcn_bp)

# 3. Kết nối MongoDB
try:
    client = MongoClient(MONGO_URI)
    db = client["do_an_2"]
    workout_collection = db["workout_plan"]
    print("✅ Kết nối MongoDB thành công!")
except Exception as e:
    print(f"❌ Lỗi kết nối MongoDB: {e}")

# Chạy server ở cổng 5000
if __name__ == '__main__':
    print("🚀 Máy chủ Python đang chạy tại: http://127.0.0.1:5000")
    app.run(debug=True, port=5000)