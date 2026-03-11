import os
from flask import Flask, request, jsonify
from flask_cors import CORS
import google.generativeai as genai
from pymongo import MongoClient
from dotenv import load_dotenv
from datetime import datetime

# 1. Tải cấu hình từ file .env
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
MONGO_URI = os.getenv("MONGO_URI")

# 2. Khởi tạo ứng dụng web Flask
app = Flask(__name__)
CORS(app) # Cho phép file HTML gửi dữ liệu đến Python

# 3. Kết nối MongoDB
try:
    client = MongoClient(MONGO_URI)
    db = client["pumpd_database"]
    workout_collection = db["workout_plans"]
    print("✅ Kết nối MongoDB thành công!")
except Exception as e:
    print(f"❌ Lỗi kết nối MongoDB: {e}")

# 4. Cấu hình AI Gemini
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

# 5. Tạo đường dẫn (API) để nhận dữ liệu từ web
@app.route('/api/generate-plan', methods=['POST'])
def generate_plan():
    try:
        # Lấy dữ liệu người dùng nhập từ form
        data = request.json
        goal = data.get('goal', '')
        level = data.get('level', '')
        equipment = data.get('equipment', '')
        user_info = data.get('userInfo', '')

        # Tạo câu lệnh (Prompt) ép AI trả về đúng mã HTML của bạn
        prompt = f"""
        Bạn là một huấn luyện viên thể hình chuyên nghiệp. Hãy tạo một lộ trình tập luyện trong 3 ngày dựa trên thông tin sau:
        - Mục tiêu: {goal}
        - Kinh nghiệm: {level}
        - Thiết bị sẵn có: {equipment}
        - Thông tin thêm: {user_info}

        YÊU CẦU QUAN TRỌNG: Bạn CHỈ ĐƯỢC PHÉP trả về mã HTML. Không dùng markdown, không kèm bất kỳ câu chữ nào khác.
        Dùng chính xác cấu trúc HTML sau cho mỗi ngày:
        <div class='day-card'>
            <div class='day-header'><span>Thứ [X]</span><span>[Tên nhóm cơ / Phục hồi]</span></div>
            <div class='day-body'>
                <div class='routine-item'>
                    <img src='[Tìm một link ảnh unsplash minh họa bài tập, ví dụ: https://images.unsplash.com/photo-1581009146145-b5ef050c2e1e?w=400&q=80]' alt='[Tên bài]'>
                    <div class='routine-item-info'>
                        <h4>[Tên bài tập]</h4>
                        <span class='tag tag-muscle'>[Nhóm cơ]</span>
                    </div>
                </div>
            </div>
        </div>
        Nếu là ngày nghỉ, dùng cấu trúc:
        <div class='day-card'>
            <div class='day-header'><span>Thứ [X]</span><span>Phục hồi</span></div>
            <div class='rest-day'>Nghỉ ngơi và bổ sung dinh dưỡng.</div>
        </div>
        """

        # Gửi cho AI và nhận kết quả
        response = model.generate_content(prompt)
        ai_html = response.text.replace('```html', '').replace('```', '').strip()

        # Lưu lại vào MongoDB để làm lịch sử
        plan_document = {
            "user_inputs": data,
            "ai_generated_html": ai_html,
            "timestamp": datetime.now()
        }
        workout_collection.insert_one(plan_document)

        # Trả kết quả HTML về cho web
        return jsonify({"html": ai_html})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Chạy server ở cổng 5000
if __name__ == '__main__':
    print("🚀 Máy chủ Python đang chạy tại: http://127.0.0.1:5000")
    app.run(debug=True, port=5000)