import os
from dotenv import load_dotenv
from pymongo import MongoClient

# 1. Kích hoạt và lấy đường link bí mật từ file .env
load_dotenv()
MONGO_URI = os.getenv("MONGO_URI")

try:
    # 2. Tạo kết nối bằng biến MONGO_URI (không lộ link thật)
    client = MongoClient(MONGO_URI)
    
    # 3. Thử ping xem có thông mạng không
    client.admin.command('ping')
    print("✅ KẾT NỐI THÀNH CÔNG! Trang Web đã nhìn thấy MongoDB trên mây.")
    
    # 4. Thử thêm dữ liệu
    db = client["do_an_2"]
    collection = db["taikhoan"]
    # Tạo thử một tài khoản mẫu y như thật
    collection.insert_one({
            "tai_khoan": "admin_test", 
            "mat_khau": "123456", 
            "vai_tro": "quan_tri_vien"
    })
    print("✅ Đã thêm thành công một tài khoản mẫu vào database do_an_2!")

except Exception as e:
    print("❌ KẾT NỐI THẤT BẠI:", e)