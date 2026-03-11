# File: test_db.py
from pymongo import MongoClient

try:
    # 1. Tạo kết nối đến MongoDB (địa chỉ mặc định)
    client = MongoClient("mongodb://localhost:27017/")
    
    # 2. Thử truy cập server để xem thông tin
    client.admin.command('ping')
    
    print("✅ KẾT NỐI THÀNH CÔNG! Python đã nhìn thấy MongoDB.")
    
    # 3. Tạo thử một database và thêm dữ liệu mẫu
    db = client["test_database"]  # Tên database
    collection = db["users"]      # Tên bảng (collection)
    
    # Thêm một dòng dữ liệu vào
    collection.insert_one({"name": "Admin", "role": "Tester"})
    print("✅ Đã thêm thử dữ liệu vào database 'test_database'.")

except Exception as e:
    print("❌ KẾT NỐI THẤT BẠI:", e)