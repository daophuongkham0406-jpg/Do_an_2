import os
import hmac
import hashlib
import time
import requests
from bson.objectid import ObjectId
from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_mail import Mail  
from pymongo import MongoClient
from dotenv import load_dotenv
from datetime import datetime
from avatar import avatar_bp

# --- Import các Blueprint hiện có ---
from dangnhap import auth_bp
from canhan import profile_bp
from baitap import baitap_bp
from qluser import user_bp
from quanly_plan import plan_bp
from quanly_trangchu import trangchu_bp
from quanly_cauhoi import cauhoi_bp
from quanly_tcn import tcn_bp
from quanly_dinhduong import nutrition_bp
from quanly_coach import coach_bp
from routes.ml_routes import ml_bp

# --- IMPORT SEPAY ---
from sepay_payment import sepay_bp

# 1. Tải cấu hình từ file .env
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
MONGO_URI = os.getenv("MONGO_URI")

app = Flask(__name__)

# Cấu hình CORS
CORS(app, resources={r"/*": {"origins": "*"}})

# ============================================================================
# 2. CẤU HÌNH GỬI EMAIL (FLASK-MAIL)
# ============================================================================
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USE_SSL'] = False
app.config['MAIL_DEFAULT_SENDER'] = os.getenv('MAIL_USERNAME')

mail = Mail(app)

# ============================================================================
# ĐĂNG KÝ CÁC BLUEPRINT
# ============================================================================
app.register_blueprint(auth_bp,    url_prefix='/api/auth')
app.register_blueprint(profile_bp, url_prefix='/api/profile')
app.register_blueprint(baitap_bp,  url_prefix='/api/exercises')
app.register_blueprint(user_bp,    url_prefix='/api/users')
app.register_blueprint(plan_bp,    url_prefix='/api/plans')
app.register_blueprint(avatar_bp, url_prefix='/api/profile')
app.register_blueprint(trangchu_bp)
app.register_blueprint(cauhoi_bp)
app.register_blueprint(tcn_bp)
app.register_blueprint(nutrition_bp)
app.register_blueprint(coach_bp)
app.register_blueprint(ml_bp)

# --- ĐĂNG KÝ SEPAY BLUEPRINT (KHÔNG có url_prefix để khớp /api/payment/...) ---
app.register_blueprint(sepay_bp)


@app.route("/")
def home():
    return jsonify({
        "status": "OK",
        "message": "AI Fitness Backend is running",
    })

# ============================================================================
# 3. Kết nối MongoDB
# ============================================================================
try:
    client = MongoClient(MONGO_URI)
    db = client["do_an_2"]
    workout_collection = db["workout_plan"]
    print("✅ Kết nối MongoDB thành công!")
except Exception as e:
    print(f"❌ Lỗi kết nối MongoDB: {e}")

print("\n=== ROUTES ===")
print(app.url_map)
print("=================")
# ============================================================================
# Chạy server ở cổng 5000
# ============================================================================
if __name__ == '__main__':
    print("🚀 Máy chủ Python đang chạy tại: http://0.0.0.0:5000")
    app.run(host='0.0.0.0', debug=True, port=5000)
