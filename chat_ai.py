import os
import google.generativeai as genai
from pymongo import MongoClient
from dotenv import load_dotenv
from datetime import datetime

# 1. Tải thông tin bảo mật từ file .env
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
MONGO_URI = os.getenv("MONGO_URI")

# 2. Kết nối với MongoDB
try:
    client = MongoClient(MONGO_URI)
    # Tạo (hoặc chọn) Database có tên là "ai_chatbot"
    db = client["ai_chatbot"] 
    # Tạo (hoặc chọn) Collection (bảng) có tên là "chat_history"
    collection = db["chat_history"] 
    print("✅ Đã kết nối MongoDB thành công!")
except Exception as e:
    print(f"❌ Lỗi kết nối Database: {e}")
    exit()

# 3. Cấu hình AI Gemini
try:
    genai.configure(api_key=GEMINI_API_KEY)
    # Sử dụng model gemini-1.5-flash cho tốc độ phản hồi nhanh và thông minh
    model = genai.GenerativeModel('gemini-3.1-flash-lite')
    print("✅ Đã kết nối AI Gemini thành công!\n")
except Exception as e:
    print(f"❌ Lỗi kết nối AI: {e}")
    exit()

# 4. Chương trình Chat
print("="*50)
print("🤖 TRỢ LÝ ẢO GEMINI ĐÃ SẴN SÀNG!")
print("💡 Gõ 'thoat' hoặc 'quit' để dừng cuộc trò chuyện.")
print("="*50)

while True:
    # Nhập câu hỏi từ bàn phím
    user_message = input("\n🧑 Bạn: ")
    
    # Kiểm tra nếu muốn thoát
    if user_message.lower() in ['thoat', 'quit', 'exit']:
        print("👋 Tạm biệt! Hẹn gặp lại nhé.")
        break
        
    if not user_message.strip():
        continue
        
    print("⏳ AI đang suy nghĩ...")
    
    try:
        # Gửi câu hỏi cho Gemini và nhận câu trả lời
        response = model.generate_content(user_message)
        ai_message = response.text
        
        # In câu trả lời ra màn hình
        print(f"🤖 Gemini: {ai_message}")
        
        # 5. Lưu toàn bộ lịch sử vào MongoDB
        chat_data = {
            "nguoi_dung": user_message,
            "ai_tra_loi": ai_message,
            "thoi_gian": datetime.now()
        }
        collection.insert_one(chat_data)
        
    except Exception as e:
        print(f"❌ Có lỗi xảy ra trong quá trình chat: {e}")