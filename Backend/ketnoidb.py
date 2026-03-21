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
    db = client["test_database"]
    collection = db["users"]
    collection.insert_one({"name": "Admin Web", "role": "Tester"})
    print("✅ Đã thêm dữ liệu từ Web vào database.")

except Exception as e:
    print("❌ KẾT NỐI THẤT BẠI:", e)