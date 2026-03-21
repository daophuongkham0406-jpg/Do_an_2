import os
import datetime
from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv()
client = MongoClient(os.getenv("MONGO_URI"))
db = client["do_an_2"]

# Lấy 3 bảng
users_col = db["user"]
plans_col = db["plan"]
admins_col = db["admin"]

# 1. TẠO USER
new_user = {
    "fullName": "Nguyễn Minh Trí",
    "email": "tri@gmail.com",
    "passwordHash": "mat_khau_da_ma_hoa_123",
    "isPremium": False,
    "targetCalories": 2500,
    "streakDays": 3,
    "savedExercises": [],
    "createdAt": datetime.datetime.now()
}
user_result = users_col.insert_one(new_user)
user_id = user_result.inserted_id # LẤY ID CỦA USER VỪA TẠO
print(f"✅ Đã tạo User thành công! ID: {user_id}")

# 2. TẠO PLAN VÀ GẮN VÀO USER TRÊN
new_plan = {
    "userId": user_id, # DÙNG ID VỪA LẤY ĐƯỢC NHÉT VÀO ĐÂY
    "goal": "Tăng cơ giảm mỡ",
    "experienceLevel": "Beginner",
    "equipmentAvailable": "Dumbbell, Mat",
    "isActive": True,
    "createdAt": datetime.datetime.now()
}
plans_col.insert_one(new_plan)
print("✅ Đã tạo Plan và liên kết với User thành công!")

# 3. TẠO ADMIN (Gộp chung thuộc tính User và Admin)
new_admin = {
    "fullName": "Quản trị viên 1",
    "email": "admin1@gmail.com",
    "passwordHash": "admin_hash_pass",
    "isPremium": True,
    "targetCalories": 2200,
    "streakDays": 10,
    "savedExercises": [],
    "createdAt": datetime.datetime.now(),
    "adminLevel": 1 # Cột riêng của Admin
}
admins_col.insert_one(new_admin)
print("✅ Đã tạo Admin thành công!")