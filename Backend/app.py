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
    "partnerCode": "MOMOBKUN20220314",
    "accessKey": "klm05ndA7YtS6p82",
    "secretKey": "at67qH6v0vnB5oaA78w9H6nS7v7uA7uY",
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
        data = request.json
        user_id = data.get('userId')  # Lấy ID user từ Frontend
        amount = str(data.get('amount'))   # Số tiền cần thanh toán

        order_info = "Nang cap tai khoan FIT ME Premium"
        order_id = f"FITME_{user_id}_{int(time.time())}" # Tạo mã đơn hàng duy nhất chứa userId
        request_id = order_id
        
        return_url = "http://localhost:3000/payment-success" # Nơi chuyển về sau khi quét QR xong
        notify_url = "https://your-ngrok-domain.com/api/payment/callback" # Link để MoMo báo kết quả ngầm (cần dùng Ngrok)

        # 1. Tạo chuỗi dữ liệu chuẩn MoMo
        raw_signature = f"accessKey={MOMO_CONFIG['accessKey']}&amount={amount}&extraData=&ipnUrl={notify_url}&orderId={order_id}&orderInfo={order_info}&partnerCode={MOMO_CONFIG['partnerCode']}&redirectUrl={return_url}&requestId={request_id}&requestType=captureWallet"
        
        # 2. Mã hóa chữ ký bảo mật SHA256
        signature = hmac.new(
            MOMO_CONFIG['secretKey'].encode('utf-8'),
            raw_signature.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()

        # 3. Đóng gói dữ liệu gửi đi
        request_body = {
            "partnerCode": str(MOMO_CONFIG['partnerCode']),
            "partnerName": "FIT ME",
            "storeId": "FitMeStore",
            "requestId": str(request_id),
            "amount": str(amount),
            "orderId": str(order_id),
            "orderInfo": str(order_info),
            "redirectUrl": str(return_url),
            "ipnUrl": str(notify_url),
            "extraData": "",
            "requestType": "captureWallet",
            "signature": str(signature),
            "lang": "vi"
        }

        # 4. Gửi request lấy link thanh toán
        response = requests.post(MOMO_CONFIG['endpoint'], json=request_body)
        result = response.json()

        # 5. Trả link mã QR về cho Frontend
        if "payUrl" in result:
            return jsonify({"payUrl": result["payUrl"]}), 200
        else:
            return jsonify({"message": "Lỗi từ MoMo", "error": result}), 400

    except Exception as e:
        return jsonify({"message": "Lỗi tạo thanh toán", "error": str(e)}), 500

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