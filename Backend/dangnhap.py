import random
import re
from flask import Blueprint, request, jsonify, current_app
from flask_mail import Message
import bcrypt
from datetime import datetime, timedelta
from ketnoidb import db

# Tạo một Blueprint thay vì App
auth_bp = Blueprint('auth', __name__)


def normalize_login_premium(user):
    is_premium = bool(user.get("isPremium", False))
    expire_date = user.get("premiumExpire")
    if is_premium and (not expire_date or datetime.now() > expire_date):
        db.user.update_one(
            {"_id": user["_id"]},
            {"$set": {"isPremium": False, "premiumExpiredNotified": False}}
        )
        user["isPremium"] = False
        return False, True
    return is_premium, False

# ==============================================================================
# HÀM TIỆN ÍCH: GỬI MÃ OTP QUA EMAIL
# ==============================================================================
def generate_and_send_otp(email, otp_type):
    from flask_mail import Mail, Message
    from flask import current_app
    
    # Tạo mã 6 số ngẫu nhiên
    otp_code = str(random.randint(100000, 999999))
    # Đặt thời hạn 5 phút
    expires_at = datetime.now() + timedelta(minutes=5)
    
    # Lưu vào MongoDB (collection: otps), ghi đè nếu đã có mã cũ
    db.otps.update_one(
        {"email": email, "type": otp_type},
        {"$set": {"otp": otp_code, "expires_at": expires_at}},
        upsert=True
    )
    
    # Gửi email
    try:
        # 1. Khởi tạo Mail trực tiếp ngay trong ngữ cảnh hiện tại
        mail = Mail(current_app)
        
        # 2. Lấy email cấu hình làm người gửi
        sender = current_app.config.get('MAIL_USERNAME')
        
        # 3. Tạo nội dung thư
        msg = Message("Mã xác thực OTP FIT ME", sender=sender, recipients=[email])
        if otp_type == 'register':
            msg.body = f"Chào bạn,\n\nMã OTP để xác nhận đăng ký tài khoản của bạn là: {otp_code}\nMã này có hiệu lực trong 5 phút."
        else:
            msg.body = f"Chào bạn,\n\nMã OTP để khôi phục mật khẩu của bạn là: {otp_code}\nMã này có hiệu lực trong 5 phút."
            
        mail.send(msg)
        return True
    except Exception as e:
        print(f"❌ Chi tiết lỗi gửi email: {e}")
        return False

# ==============================================================================
# 1. ĐĂNG KÝ VÀ LƯU TẠM THỜI (CHƯA XÁC THỰC)
# ==============================================================================
@auth_bp.route('/register', methods=['POST'])
def register():
    data = request.json
    email = data.get('email')
    username = data.get('username')
    password_str = data.get('password')
    
    # Kiểm tra xem email hoặc username đã tồn tại chưa
    existing_user = db.user.find_one({"$or": [{"email": email}, {"username": username}]})
    
    if existing_user:
        if existing_user.get('isVerified'):
            return jsonify({"message": "Email hoặc Tên đăng nhập đã được sử dụng!"}), 400
        else:
            db.user.delete_one({"_id": existing_user["_id"]})
            
    # Kiểm tra mật khẩu mạnh ở phía Backend
    if not re.match(r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d).{8,}$", password_str):
        return jsonify({"message": "Mật khẩu phải từ 8 ký tự, gồm chữ hoa, chữ thường và số!"}), 400
    
    # Mã hóa mật khẩu
    password = password_str.encode('utf-8')
    hashed_password = bcrypt.hashpw(password, bcrypt.gensalt())

    # Tạo object user với trường isVerified = False
    new_user = {
        "fullName": data['fullName'],
        "age": data['age'],
        "gender": data['gender'],
        "username": username,
        "email": email,
        "passwordHash": hashed_password.decode('utf-8'),
        "isPremium": False,
        "role": 'user',
        "isVerified": False, 
        "createdAt": datetime.now()
    }

    # Lưu vào MongoDB
    db.user.insert_one(new_user)
    
    # Gọi hàm gửi OTP
    success = generate_and_send_otp(email, 'register')
    if not success:
        return jsonify({"message": "Lỗi cấu hình gửi Email. Vui lòng liên hệ Admin!"}), 500
        
    return jsonify({"message": "Mã OTP đã được gửi đến email"}), 201

# ==============================================================================
# 2. XÁC NHẬN MÃ OTP ĐỂ HOÀN TẤT ĐĂNG KÝ
# ==============================================================================
@auth_bp.route('/verify-registration', methods=['POST'])
def verify_registration():
    data = request.json
    email = data.get('email')
    otp_input = data.get('otp')
    
    # Tìm mã OTP trong database
    otp_record = db.otps.find_one({"email": email, "type": "register"})
    
    if not otp_record:
        return jsonify({"message": "Không tìm thấy yêu cầu xác thực cho email này!"}), 400
        
    # Kiểm tra hạn của mã OTP
    if datetime.now() > otp_record['expires_at']:
        return jsonify({"message": "Mã OTP đã hết hạn, vui lòng yêu cầu gửi lại mã!"}), 400
        
    # So sánh mã OTP
    if otp_record['otp'] != otp_input:
        return jsonify({"message": "Mã OTP không chính xác!"}), 400
        
    # Cập nhật trạng thái user thành đã xác thực
    db.user.update_one({"email": email}, {"$set": {"isVerified": True}})
    
    # Xóa mã OTP sau khi dùng xong
    db.otps.delete_one({"_id": otp_record['_id']})
    
    return jsonify({"message": "Xác thực tài khoản thành công!"}), 200

# ==============================================================================
# 3. ĐĂNG NHẬP (CHẶN NẾU CHƯA XÁC THỰC)
# ==============================================================================
@auth_bp.route('/login', methods=['POST'])
def login():
    try:
        data = request.json
        email = data.get('email')
        password = data.get('password')

        if not email or not password:
            return jsonify({"message": "Vui lòng nhập đầy đủ Email và Mật khẩu."}), 400

        user = db.user.find_one({"email": email})
        
        if not user:
            return jsonify({"message": "Email hoặc mật khẩu không chính xác."}), 401

        if not user.get('isVerified', True):
            return jsonify({"message": "Tài khoản của bạn chưa được xác thực Email!"}), 403

        is_password_correct = bcrypt.checkpw(
            password.encode('utf-8'), 
            user['passwordHash'].encode('utf-8')
        )

        if not is_password_correct:
            return jsonify({"message": "Email hoặc mật khẩu không chính xác."}), 401

        is_premium, premium_expired = normalize_login_premium(user)

        user_info = {
            "id": str(user['_id']),
            "fullName": user['fullName'],
            "username": user['username'],
            "isPremium": is_premium,
            "role": user.get('role', 'user'),
            "premiumExpired": premium_expired,
        }

        return jsonify({
            "message": "Đăng nhập thành công",
            "user": user_info
        }), 200

    except Exception as e:
        print(f"❌ Lỗi hệ thống nghiêm trọng (Login): {e}")
        return jsonify({"message": "Đã xảy ra lỗi máy chủ không xác định."}), 500

# ==============================================================================
# 4. YÊU CẦU QUÊN MẬT KHẨU (GỬI OTP)
# ==============================================================================
@auth_bp.route('/forgot-password', methods=['POST'])
def forgot_password():
    email = request.json.get('email')
    
    user = db.user.find_one({"email": email, "isVerified": True})
    
    if not user:
        return jsonify({"message": "Email này không tồn tại hoặc chưa được xác thực!"}), 404
        
    success = generate_and_send_otp(email, 'reset_password')
    if not success:
        return jsonify({"message": "Lỗi khi gửi email OTP!"}), 500
        
    return jsonify({"message": "Đã gửi mã OTP đến email!"}), 200

# ==============================================================================
# 5. XÁC NHẬN OTP VÀ CẬP NHẬT MẬT KHẨU MỚI
# ==============================================================================
@auth_bp.route('/reset-password', methods=['POST'])
def reset_password():
    data = request.json
    email = data.get('email')
    otp_input = data.get('otp')
    new_password = data.get('newPassword')
    
    otp_record = db.otps.find_one({"email": email, "type": "reset_password"})
    
    if not otp_record or datetime.now() > otp_record['expires_at']:
        return jsonify({"message": "Mã OTP không hợp lệ hoặc đã hết hạn!"}), 400
        
    if otp_record['otp'] != otp_input:
        return jsonify({"message": "Mã OTP không chính xác!"}), 400
        
    # Kiểm tra mật khẩu mạnh ở phía Backend
    if not re.match(r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d).{8,}$", new_password):
        return jsonify({"message": "Mật khẩu mới không đủ mạnh!"}), 400
        
    # Mã hóa mật khẩu mới và lưu vào DB
    hashed_password = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt())
    db.user.update_one(
        {"email": email}, 
        {"$set": {"passwordHash": hashed_password.decode('utf-8')}}
    )
    
    # Xóa OTP sau khi đổi thành công
    db.otps.delete_one({"_id": otp_record['_id']})
    
    return jsonify({"message": "Mật khẩu của bạn đã được cập nhật!"}), 200
