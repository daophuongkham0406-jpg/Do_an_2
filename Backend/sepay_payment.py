import os
import time
from flask import Blueprint, request, jsonify
from pymongo import MongoClient
from bson.objectid import ObjectId
from dotenv import load_dotenv
from datetime import datetime, timedelta

load_dotenv()

sepay_bp = Blueprint('sepay', __name__)

# ═══════════════════════════════════════════════════════
# CẤU HÌNH — điền vào file .env
# SEPAY_ACCOUNT=0325462768
# SEPAY_BANK_CODE=MB
# ═══════════════════════════════════════════════════════
SEPAY_CONFIG = {
    "account_number": os.getenv("SEPAY_ACCOUNT", "0325462768"),
    "bank_code":      os.getenv("SEPAY_BANK_CODE", "MB"),
}

# ── Kết nối MongoDB ──
_client     = MongoClient(os.getenv("MONGO_URI"))
_db         = _client["do_an_2"]
users_col   = _db["user"]
payment_col = _db["payments"]


def normalize_premium_status(user):
    is_premium = bool(user.get("isPremium", False))
    expired = False
    expire_date = user.get("premiumExpire")

    if is_premium and (not expire_date or datetime.now() > expire_date):
        users_col.update_one(
            {"_id": user["_id"]},
            {"$set": {"isPremium": False, "premiumExpiredNotified": False}}
        )
        is_premium = False
        expired = True

    expire_str = ""
    if expire_date:
        expire_str = expire_date.strftime('%d/%m/%Y')

    return is_premium, expired, expire_str


# ═══════════════════════════════════════════════════════
# HELPER: Tạo mã nội dung chuyển khoản duy nhất
# ═══════════════════════════════════════════════════════
def generate_transfer_content(user_id: str) -> str:
    uid_short = str(user_id)[-6:].upper().replace("-", "")
    ts_short  = str(int(time.time()))[-4:]
    return f"FITME{uid_short}{ts_short}"


# ═══════════════════════════════════════════════════════
# API 1: TẠO ĐƠN HÀNG
# POST /api/payment/create
# ═══════════════════════════════════════════════════════
@sepay_bp.route('/api/payment/create', methods=['POST'])
def create_payment():
    try:
        data      = request.json or {}
        user_id   = data.get('userId', '').strip()
        plan_type = data.get('planType', 'vip_1month')

        print(f"📥 Payment create — userId: {user_id}, plan: {plan_type}")

        if not user_id or user_id == 'guest':
            return jsonify({"success": False, "error": "Vui lòng đăng nhập để thanh toán"}), 400

        amount_map = {
            "vip_1month": 50000,
            "vip_3month": 120000,
        }
        amount = amount_map.get(plan_type, 50000)

        # Tái sử dụng đơn pending nếu có
        existing = payment_col.find_one({
            "user_id":   user_id,
            "plan_type": plan_type,
            "status":    "pending"
        })

        if existing:
            transfer_content = existing["transfer_content"]
            amount           = existing["amount"]
            print(f"♻️  Dùng lại đơn: {transfer_content}")
        else:
            transfer_content = generate_transfer_content(user_id)
            payment_col.insert_one({
                "user_id":          user_id,
                "plan_type":        plan_type,
                "amount":           amount,
                "transfer_content": transfer_content,
                "status":           "pending",
                "created_at":       datetime.now(),
                "paid_at":          None,
            })
            print(f"✅ Tạo đơn mới: {transfer_content}")

        bank_code      = SEPAY_CONFIG["bank_code"]
        account_number = SEPAY_CONFIG["account_number"]

        qr_url = (
            f"https://img.vietqr.io/image/{bank_code}-{account_number}-qr_only.png"
            f"?amount={amount}&addInfo={transfer_content}&accountName=FIT%20ME"
        )

        return jsonify({
            "success":          True,
            "transfer_content": transfer_content,
            "amount":           amount,
            "bank_code":        bank_code,
            "account_number":   account_number,
            "qr_url":           qr_url,
            "plan_type":        plan_type,
            "expire_minutes":   15,
        })

    except Exception as e:
        import traceback; traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500


# ═══════════════════════════════════════════════════════
# API 2: WEBHOOK — SePay gọi về khi có tiền vào
# POST /api/payment/webhook
# Không cần xác thực (khớp cài đặt SePay "Không cần chứng thực")
#
# SePay gửi JSON dạng:
# {
#   "id": 1234,
#   "gateway": "MBBank",
#   "transactionDate": "2024-01-15 10:30:00",
#   "accountNumber": "0325462768",
#   "code": "FITME...",
#   "content": "FITME...",
#   "transferType": "in",
#   "transferAmount": 50000,
#   "referenceCode": "FT24...",
# }
# ═══════════════════════════════════════════════════════
@sepay_bp.route('/api/payment/webhook', methods=['POST'])
def payment_webhook():
    try:
        data = request.json or {}
        print(f"\n📨 ═══ WEBHOOK SEPAY ═══")
        print(f"📦 Raw data: {data}")

        # SePay gửi nội dung ở nhiều field khác nhau tuỳ phiên bản
        transfer_content = (
            str(data.get('content') or '')
            or str(data.get('code') or '')
            or str(data.get('description') or '')
        ).strip()

        amount_received = int(
            data.get('transferAmount', 0)
            or data.get('amount', 0)
            or 0
        )

        transaction_id = str(
            data.get('referenceCode', '')
            or data.get('id', '')
            or ''
        )

        transfer_type = str(data.get('transferType', 'in')).lower()

        print(f"💰 Số tiền: {amount_received}đ")
        print(f"📝 Nội dung: '{transfer_content}'")
        print(f"🔖 Mã GD: {transaction_id}")
        print(f"↕️  Loại: {transfer_type}")

        # Chỉ xử lý giao dịch TIỀN VÀO
        if transfer_type not in ('in', 'credit', ''):
            print("⏭️  Bỏ qua — không phải tiền vào")
            return jsonify({"success": True, "message": "Bỏ qua tiền ra"}), 200

        if not transfer_content or amount_received <= 0:
            print("⚠️  Thiếu dữ liệu cần thiết")
            return jsonify({"success": True, "message": "Thiếu dữ liệu"}), 200

        # ── Tìm đơn hàng khớp nội dung ──
        payment = None

        # 1. Tìm chính xác
        payment = payment_col.find_one({
            "transfer_content": transfer_content,
            "status": "pending"
        })

        # 2. Tìm không phân biệt hoa thường
        if not payment:
            payment = payment_col.find_one({
                "transfer_content": {"$regex": f"^{transfer_content}$", "$options": "i"},
                "status": "pending"
            })

        # 3. Tìm linh hoạt — nội dung CK chứa mã đơn
        if not payment:
            all_pending   = list(payment_col.find({"status": "pending"}))
            content_upper = transfer_content.upper()
            for p in all_pending:
                code = p.get("transfer_content", "").upper()
                if code and (code in content_upper or content_upper in code):
                    payment = p
                    print(f"🔍 Khớp fuzzy: '{code}' trong '{content_upper}'")
                    break

        if not payment:
            print(f"⚠️  Không khớp đơn hàng! Content='{transfer_content}'")
            all_p = list(payment_col.find({"status": "pending"}, {"transfer_content": 1}))
            print(f"📋 Đơn pending: {[p.get('transfer_content') for p in all_p]}")
            return jsonify({"success": True, "message": "Không tìm thấy đơn"}), 200

        # Kiểm tra số tiền
        if amount_received < payment["amount"]:
            print(f"⚠️  Tiền chưa đủ: nhận {amount_received}, cần {payment['amount']}")
            return jsonify({"success": True, "message": "Số tiền chưa đủ"}), 200

        # ── Cập nhật đơn hàng → paid ──
        payment_col.update_one(
            {"_id": payment["_id"]},
            {"$set": {
                "status":          "paid",
                "paid_at":         datetime.now(),
                "transaction_id":  transaction_id,
                "amount_received": amount_received,
            }}
        )
        print(f"✅ Đơn {payment['transfer_content']} → PAID")

        # ── Nâng cấp tài khoản ──
        user_id     = payment["user_id"]
        plan_type   = payment["plan_type"]
        expire_days = 90 if "3month" in plan_type else 30
        expire_date = datetime.now() + timedelta(days=expire_days)

        result = users_col.update_one(
            {"_id": ObjectId(user_id)},
            {"$set": {
                "isPremium":     True,
                "premiumPlan":   plan_type,
                "premiumExpire": expire_date,
                "upgradedAt":    datetime.now(),
            }}
        )

        if result.modified_count > 0:
            print(f"🎉 VIP thành công! userId={user_id} | Gói={plan_type} | HH={expire_date.strftime('%d/%m/%Y')}")
        else:
            print(f"❌ Không tìm thấy user {user_id}!")

        return jsonify({"success": True}), 200

    except Exception as e:
        import traceback; traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500


# ═══════════════════════════════════════════════════════
# API 3: POLLING — Frontend gọi mỗi 3 giây
# GET /api/payment/check?transfer_content=FITME...&userId=...
# ═══════════════════════════════════════════════════════
@sepay_bp.route('/api/payment/check', methods=['GET'])
def check_payment():
    try:
        transfer_content = request.args.get('transfer_content', '').strip()
        user_id          = request.args.get('userId', '').strip()

        if not transfer_content:
            return jsonify({"success": False, "error": "Thiếu transfer_content"}), 400

        payment = payment_col.find_one({
            "transfer_content": transfer_content,
            "user_id":          user_id,
        })

        if not payment:
            return jsonify({"success": False, "status": "not_found"}), 404

        if payment["status"] == "paid":
            try:
                user       = users_col.find_one({"_id": ObjectId(user_id)})
                expire_str = ""
                if user and user.get("premiumExpire"):
                    expire_str = user["premiumExpire"].strftime('%d/%m/%Y')
            except Exception:
                expire_str = ""

            return jsonify({
                "success":   True,
                "status":    "paid",
                "isPremium": True,
                "plan_type": payment["plan_type"],
                "expire":    expire_str,
            })

        return jsonify({"success": True, "status": "pending"})

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# ═══════════════════════════════════════════════════════
# API 4: KIỂM TRA PREMIUM STATUS
# GET /api/payment/status/<user_id>
# ═══════════════════════════════════════════════════════
@sepay_bp.route('/api/payment/status/<user_id>', methods=['GET'])
def get_premium_status(user_id):
    try:
        user = users_col.find_one({"_id": ObjectId(user_id)})
        if not user:
            return jsonify({"isPremium": False}), 404

        is_premium, expired, expire_str = normalize_premium_status(user)

        return jsonify({
            "isPremium":  is_premium,
            "plan":       user.get("premiumPlan", ""),
            "expireDate": expire_str,
            "expired":    expired,
            "message":    "Gói Premium của bạn đã hết hạn. Trạng thái Premium đã được khóa." if expired else "",
        })

    except Exception as e:
        return jsonify({"isPremium": False, "error": str(e)}), 500


# ═══════════════════════════════════════════════════════
# API 5: TEST THỦ CÔNG — Kích hoạt VIP không qua chuyển khoản
# POST /api/payment/test-activate
# Body: { "transfer_content": "FITME..." }
# ⚠️  XÓA API NÀY TRƯỚC KHI DEPLOY THẬT
# ═══════════════════════════════════════════════════════
@sepay_bp.route('/api/payment/test-activate', methods=['POST'])
def test_activate():
    try:
        data             = request.json or {}
        transfer_content = data.get('transfer_content', '').strip()

        if not transfer_content:
            return jsonify({"success": False, "error": "Thiếu transfer_content"}), 400

        payment = payment_col.find_one({
            "transfer_content": transfer_content,
            "status": "pending"
        })

        if not payment:
            all_p = list(payment_col.find({}, {"transfer_content": 1, "status": 1}))
            return jsonify({
                "success":      False,
                "error":        f"Không tìm thấy đơn '{transfer_content}'",
                "all_payments": [
                    {"content": p.get("transfer_content"), "status": p.get("status")}
                    for p in all_p
                ]
            }), 404

        plan_type   = payment["plan_type"]
        expire_days = 90 if "3month" in plan_type else 30
        expire_date = datetime.now() + timedelta(days=expire_days)

        payment_col.update_one(
            {"_id": payment["_id"]},
            {"$set": {
                "status":         "paid",
                "paid_at":        datetime.now(),
                "transaction_id": "TEST_MANUAL",
                "amount_received": payment["amount"],
            }}
        )

        users_col.update_one(
            {"_id": ObjectId(payment["user_id"])},
            {"$set": {
                "isPremium":     True,
                "premiumPlan":   plan_type,
                "premiumExpire": expire_date,
                "upgradedAt":    datetime.now(),
            }}
        )

        return jsonify({
            "success": True,
            "message": f"✅ Đã kích hoạt VIP cho user {payment['user_id']}",
            "plan":    plan_type,
            "expires": expire_date.strftime('%d/%m/%Y'),
        })

    except Exception as e:
        import traceback; traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500
