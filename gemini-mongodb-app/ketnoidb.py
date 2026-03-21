# File: test_db.py
from pymongo import MongoClient

try:
    # 1. Tạo kết nối đến MongoDB (địa chỉ mặc định)
    client = MongoClient("mongodb+srv://nguyentri01022005_db_user:XlaGz6YD6FI4Ueux@cluster0.abyajol.mongodb.net/?retryWrites=true&w=majority")
    
    # 2. Thử truy cập server để xem thông tin
    client.admin.command('ping')

    print("✅ KẾT NỐI THÀNH CÔNG! Python đã nhìn thấy MongoDB.")
    
    # 4. Thử thêm dữ liệu
    db = client["do_an_2"]
    collection = db["taikhoan"]
    # Tạo thử một tài khoản mẫu y như thật
    collection.insert_one({
            "tai_khoan": "chatbot_test", 
            "mat_khau": "123456", 
            "vai_tro": "quan_tri_vien"
    })
    print("✅ Đã thêm thành công một tài khoản mẫu vào database do_an_2!")

except Exception as e:
    print("❌ KẾT NỐI THẤT BẠI:", e)