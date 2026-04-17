import os
import hmac
import hashlib
import time
import requests
from bson.objectid import ObjectId
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

MOMO_CONFIG = {
    "partnerCode": "MOMO",
    "accessKey": "M8brj9K6E22vXoDB",
    "secretKey": "nqQiVSgDMy809JoPF6OzP5OdPdBPcqeV",
    "endpoint": "https://test-payment.momo.vn/v2/gateway/api/create"
}

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

# ============================================================================
# TÍCH HỢP THANH TOÁN MOMO (PREMIUM)
# ============================================================================

@app.route('/api/payment/create', methods=['POST'])
def create_payment_url():
    try:
        MOMO_CONFIG = {
            "partnerCode": "MOMOBKUN20180529",
            "accessKey": "klm05TvNBzhg7h7j",
            "secretKey": "at67qH6mk8w5Y1nAyMoYKMWACiEi2bsa",
            "endpoint": "https://test-payment.momo.vn/v2/gateway/api/create"
        }

        data = request.json
        user_id = str(data.get('userId'))
        
        # 2. XỬ LÝ SỐ TIỀN CHUẨN (Chuỗi cho chữ ký, Số nguyên cho Body)
        amount_str = "50000"
        amount_int = 50000

        order_info = "Nang cap VIP FIT ME"
        order_id = f"FITME_{user_id}_{int(time.time())}"
        request_id = order_id
        
        return_url = "http://localhost:5173/Tcn.html" 
        notify_url = "http://localhost:5173/Tcn.html"

        # 3. TẠO CHỮ KÝ BẰNG CHUỖI (amount_str)
        raw_signature = f"accessKey={MOMO_CONFIG['accessKey']}&amount={amount_str}&extraData=&ipnUrl={notify_url}&orderId={order_id}&orderInfo={order_info}&partnerCode={MOMO_CONFIG['partnerCode']}&redirectUrl={return_url}&requestId={request_id}&requestType=captureWallet"
        
        signature = hmac.new(
            MOMO_CONFIG['secretKey'].encode('utf-8'),
            raw_signature.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()

        # 4. ĐÓNG GÓI DỮ LIỆU BẰNG SỐ NGUYÊN (amount_int)
        request_body = {
            "partnerCode": MOMO_CONFIG['partnerCode'],
            "partnerName": "FIT ME",
            "storeId": "MomoTestStore",
            "requestId": request_id,
            "amount": amount_int,  # BẮT BUỘC PHẢI LÀ SỐ NGUYÊN
            "orderId": order_id,
            "orderInfo": order_info,
            "redirectUrl": return_url,
            "ipnUrl": notify_url,
            "lang": "vi",
            "extraData": "",
            "requestType": "captureWallet",
            "signature": signature
        }

        # 5. GỌI API
        response = requests.post(MOMO_CONFIG['endpoint'], json=request_body)
        result = response.json()

        if "payUrl" in result:
            return jsonify({"payUrl": result["payUrl"]}), 200
        else:
            return jsonify({"message": "Loi tu MoMo", "error": result}), 400

    except Exception as e:
        return jsonify({"message": "Loi tao thanh toan", "error": str(e)}), 500

@app.route('/api/payment/callback', methods=['POST'])
def momo_callback():
    try:
        data = request.json
        order_id = data.get('orderId')
        result_code = data.get('resultCode')

        if result_code == 0: # Mã 0 là giao dịch thành công
            print(f"✅ Khách hàng đã thanh toán thành công đơn: {order_id}")
            
            user_id = order_id.split('_')[1] # Tách chuỗi để lấy ra ID người dùng

            # Cập nhật quyền Premium vào MongoDB
            db["users"].update_one(
                {'_id': ObjectId(user_id)}, 
                {'$set': {'isPremium': True}}
            )
            print(f"Đã nâng cấp tài khoản Premium cho User ID: {user_id}")
        else:
            print(f"❌ Giao dịch thất bại / Bị hủy. Mã lỗi: {result_code}")

        # BẮT BUỘC: Trả về HTTP 204 để báo cho MoMo biết là đã nhận được tin
        return '', 204 

    except Exception as e:
        print("Lỗi Webhook:", str(e))
        return jsonify({"message": "Lỗi xử lý callback"}), 500
    
# Chạy server ở cổng 5000
if __name__ == '__main__':
    print("🚀 Máy chủ Python đang chạy tại: http://127.0.0.1:5000")
    app.run(debug=True, port=5000)