from flask import Flask, request, jsonify
from flask_cors import CORS
import google.generativeai as genai

# Khởi tạo ứng dụng web
app = Flask(__name__)
CORS(app) # Cho phép Frontend gọi tới Backend

# 2. Cấu hình Gemini API (Tuyệt đối không hardcode key thật ở đây, nên dùng file .env như trước)
API_KEY = "API_KEY_MỚI_CỦA_BẠN_ĐIỀN_VÀO_ĐÂY" 
genai.configure(api_key=API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

@app.route('/api/generate-plan', methods=['POST'])
def generate_plan():
    try:
        # 1. Lấy dữ liệu từ Frontend gửi lên
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'Không nhận được dữ liệu.'}), 400

        goal = data.get('goal', '')
        level = data.get('level', '')
        equipment = data.get('equipment', '')
        user_info = data.get('userInfo', '')

        # 3. Xây dựng Prompt (Câu lệnh cho AI)
        prompt = f"""Bạn là một huấn luyện viên thể hình chuyên nghiệp. Hãy tạo một lộ trình tập luyện trong 3 ngày dựa trên thông tin sau:
- Mục tiêu: {goal}
- Kinh nghiệm: {level}
- Thiết bị sẵn có: {equipment}
- Tình trạng cá nhân / Lưu ý thêm: {user_info}

YÊU CẦU QUAN TRỌNG: Bạn CHỈ ĐƯỢC PHÉP trả về mã HTML (không dùng markdown ```html), không kèm bất kỳ câu chữ nào khác. Hãy dùng chính xác cấu trúc HTML sau cho mỗi ngày:

<div class='day-card'>
    <div class='day-header'><span>Thứ [X]</span><span>[Tên nhóm cơ / Phục hồi]</span></div>
    <div class='day-body'>
        <div class='routine-item'>
            <img src='[Tìm một link ảnh unsplash minh họa bài tập, ví dụ: [https://images.unsplash.com/photo-1581009146145-b5ef050c2e1e?w=400&q=80](https://images.unsplash.com/photo-1581009146145-b5ef050c2e1e?w=400&q=80)]' alt='[Tên bài]'>
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
</div>"""

        # 4 & 5. Gửi Request tới Gemini AI
        response = model.generate_content(prompt)
        
        # 6. Xử lý kết quả trả về
        ai_html = response.text
        # Loại bỏ markdown (nếu AI ngoan cố thêm vào)
        ai_html = ai_html.replace('```html', '').replace('```', '').strip()
        
        return jsonify({'html': ai_html})

    except Exception as e:
        return jsonify({'error': f'Lỗi kết nối API: {str(e)}'}), 500

if __name__ == '__main__':
    print("🚀 Máy chủ Python đang chạy tại: [http://127.0.0.1:5000](http://127.0.0.1:5000)")
    app.run(debug=True, port=5000)