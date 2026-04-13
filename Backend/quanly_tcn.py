from flask import Blueprint, jsonify, request
from pymongo import MongoClient
from bson import ObjectId
import os
from dotenv import load_dotenv
from datetime import datetime, timedelta

load_dotenv()
tcn_bp = Blueprint('tcn', __name__)

try:
    client = MongoClient(os.getenv("MONGO_URI"))
    db = client["do_an_2"]
    user_col = db["user"]
    plan_col = db["plan"]
    history_col = db["history"]
    exercise_col = db["exercise"]
except Exception as e:
    print(f"❌ Lỗi DB Trang cá nhân: {e}")

MUSCLE_MAP = {
    "Ngực": ["ngực", "ngực trên", "ngực dưới"],
    "Lưng": ["lưng", "lưng xô", "lưng giữa", "xô"],
    "Chân": ["đùi", "đùi sau", "đùi sau & mông", "bắp chân", "chân/mông", "đùi sau/mông", "mông & đùi", "chân", "mông"],
    "Vai": ["vai", "vai giữa", "vai sau", "vai trước", "cầu vai"],
    "Tay": ["bắp tay trước", "tay sau", "tay trước", "cơ bắp", "cơ"],
    "Bụng": ["bụng", "bụng dưới", "liên sườn", "cơ lõi"]
}

def get_main_muscle_group(raw_muscle):
    if not raw_muscle: return None
    raw_lower = str(raw_muscle).lower().strip()
    for main_group, sub_groups in MUSCLE_MAP.items():
        if raw_lower in sub_groups:
            return main_group
    return None

def safe_float(val, default=0.0):
    try:
        if val is None or str(val).strip() == "": return float(default)
        return float(val)
    except (ValueError, TypeError):
        return float(default)

# Hàm lấy ngày tháng chuẩn từ CSDL
def get_date_from_val(val):
    if isinstance(val, datetime):
        return val.date()
    if isinstance(val, str):
        try:
            return datetime.strptime(val[:10], "%Y-%m-%d").date()
        except:
            pass
    return datetime.today().date()

# ==========================================
# 1. API LẤY TỔNG QUAN, TẦN SUẤT & STREAK
# ==========================================
@tcn_bp.route('/api/tcn/overview', methods=['GET'])
def get_tcn_overview():
    try:
        user_id = request.args.get('userId')
        if not user_id: return jsonify({"success": False, "error": "Thiếu userId"})

        query = {"_id": ObjectId(user_id)} if len(str(user_id)) == 24 else {"_id": user_id}
        user = user_col.find_one(query)
        if not user: return jsonify({"success": False, "error": "Không tìm thấy User"})

        weight = safe_float(user.get("weight", 0))
        height_cm = safe_float(user.get("height", 0)) 
        age = safe_float(user.get("age", 25))
        gender = str(user.get("gender", "nam")).lower()
        is_male = 1 if gender in ['nam', 'male'] else 0

        bmi = round(weight / ((height_cm/100)**2), 1) if height_cm > 0 else 0
        weight_change = round(abs(weight - safe_float(user.get("initialWeight", weight))), 1)

        plans = list(plan_col.find({"user_id": user_id}).sort("created_at", 1))
        routines_completed = 0
        workouts_completed = 0
        all_workouts = []
        all_days_status = [] 
        
        # Biến mới để lưu các ngày thực tế có tập (dùng để tính Streak)
        workout_dates_set = set()

        today = datetime.today().date()
        current_monday = today - timedelta(days=today.weekday())
        freq_data = [0] * 8 

        for plan in plans:
            if plan.get("status") == "completed":
                routines_completed += 1
            
            start_date = get_date_from_val(plan.get("created_at"))
                
            for i, day in enumerate(plan.get("daily_progress", [])):
                exercises = day.get("exercises", [])
                completed_exs = [ex for ex in exercises if ex.get("completed") == True]
                
                is_done = 1 if len(completed_exs) > 0 else 0
                all_days_status.append(is_done)

                if is_done:
                    workouts_completed += 1
                    day_num = int(day.get('day_number', i + 1))
                    workout_date = start_date + timedelta(days=day_num - 1)
                    
                    # Thêm ngày tập vào danh sách để tính Streak
                    workout_dates_set.add(workout_date)
                    
                    days_ago = (current_monday - workout_date).days
                    
                    if -7 < days_ago <= 0: freq_data[7] += 1
                    elif 0 < days_ago <= 49:
                        week_idx = 7 - ((days_ago - 1) // 7 + 1)
                        if 0 <= week_idx < 8: freq_data[week_idx] += 1

                    all_workouts.append({
                        "name": f"Ngày {day_num} - {day.get('focus', 'Tập luyện')}",
                        "time": "Hoàn thành",
                        "vol": f"{len(completed_exs)}/{len(exercises)} bài",
                        "date": workout_date.strftime("%d/%m/%Y") 
                    })

        # =========================================================
        # --- LOGIC TÍNH NGÀY STREAK (CHUỖI LIÊN TIẾP) ---
        # =========================================================
        current_streak = 0
        sorted_dates = sorted(list(workout_dates_set), reverse=True) # Sắp xếp từ mới nhất về cũ nhất
        yesterday = today - timedelta(days=1)

        if sorted_dates:
            # Nếu ngày tập gần nhất là hôm nay hoặc hôm qua thì Streak đang "sống"
            if sorted_dates[0] == today:
                current_streak = 1
                check_date = today
            elif sorted_dates[0] == yesterday:
                current_streak = 1
                check_date = yesterday
            else:
                check_date = None # Đã đứt chuỗi vì ngày tập cuối cùng cách đây > 2 ngày

            # Lùi về quá khứ xem các ngày liên tiếp
            if current_streak > 0:
                for i in range(1, len(sorted_dates)):
                    if sorted_dates[i] == check_date - timedelta(days=1):
                        current_streak += 1
                        check_date = sorted_dates[i]
                    else:
                        break # Đứt chuỗi

        # --- LOGIC ƯỚC TÍNH CƠ BẮP ---
        muscle_pct = 0
        if bmi > 0:
            base_muscle = 36.0
            if is_male:
                if bmi < 18.5: base_muscle = 32.5
                elif bmi >= 25: base_muscle = 33.0
                else: base_muscle = 36.0
            else:
                if bmi < 18.5: base_muscle = 23.5
                elif bmi >= 25: base_muscle = 24.0
                else: base_muscle = 27.0

            workout_bonus = (workouts_completed ** 0.6) * 0.5 if workouts_completed > 0 else 0
            max_limit = 55.0 if is_male else 45.0
            muscle_pct = round(min(base_muscle + workout_bonus, max_limit), 1)

        all_workouts = all_workouts[::-1]
        recent_workouts = all_workouts[:5]
        freq_data = [0] * (8 - len(freq_data)) + freq_data if len(freq_data) < 8 else freq_data[-8:]

        data = {
            "fullName": user.get("fullName", "User"),
            "age": user.get("age", "--"),
            "weight": weight,
            "height": height_cm, 
            "bmi": bmi,
            "musclePct": muscle_pct, 
            "workoutsCompleted": workouts_completed,
            "routinesCompleted": routines_completed,
            "weightChange": weight_change,
            "currentStreak": current_streak, # BIẾN STREAK TRUYỀN XUỐNG JS
            "recentWorkouts": recent_workouts,
            "allWorkouts": all_workouts,
            "freqData": freq_data
        }
        return jsonify({"success": True, "data": data})
    except Exception as e:
        print(f"❌ Lỗi API Overview: {e}")
        return jsonify({"success": False, "error": str(e)})


# ==========================================
# 2. API BIỂU ĐỒ MẠNG NHỆN (CHỈ SỐ THỰC TẾ = 0)
# ==========================================
@tcn_bp.route('/api/tcn/radar', methods=['GET'])
def get_tcn_radar():
    try:
        user_id = request.args.get('userId')
        
        # Tất cả nhóm cơ bắt đầu từ 0
        exercise_counts = { "Ngực": 0, "Lưng": 0, "Chân": 0, "Vai": 0, "Tay": 0, "Bụng": 0 }
        
        # Hệ số điểm mỗi bài tập theo chuẩn: 10đ = Thay đổi rõ rệt
        multipliers = {
            "Ngực": 0.20,  # ~50 bài = 10đ
            "Lưng": 0.167, # ~60 bài = 10đ (Cơ rộng nhất, cần nhiều bài nhất)
            "Chân": 0.20,  # ~50 bài = 10đ
            "Vai":  0.25,  # ~40 bài = 10đ
            "Tay":  0.333, # ~30 bài = 10đ (Cơ nhỏ, nhanh rõ)
            "Bụng": 0.25   # ~40 bài = 10đ
        }

        # Quét lịch sử
        plans = list(plan_col.find({"user_id": user_id}))
        completed_exercise_names = []
        
        for plan in plans:
            for day in plan.get("daily_progress", []):
                for ex in day.get("exercises", []):
                    if ex.get("completed") == True:
                        completed_exercise_names.append(ex.get("name"))

        if completed_exercise_names:
            ex_details = list(exercise_col.find({"name": {"$in": completed_exercise_names}}))
            for ex in ex_details:
                raw_muscle = ex.get("muscle", "")
                main_branch = get_main_muscle_group(raw_muscle)
                if main_branch:
                    exercise_counts[main_branch] += 1

        # Nhân hệ số và làm tròn 1 chữ số thập phân (VD: 4.2 điểm)
        radar_array = []
        for branch in ["Ngực", "Lưng", "Chân", "Vai", "Tay", "Bụng"]:
            score = exercise_counts[branch] * multipliers[branch]
            radar_array.append(round(score, 1))
        return jsonify({"success": True, "data": radar_array})
    except Exception as e:
        print(f"❌ Lỗi API Radar: {e}")
        return jsonify({"success": False, "error": str(e)})

# ==========================================
# 3. API BIỂU ĐỒ CÂN NẶNG
# ==========================================
@tcn_bp.route('/api/tcn/weight-chart', methods=['GET'])
def get_tcn_weight_chart():
    try:
        user_id = request.args.get('userId')
        
        query_conds = [{"user_id": user_id}, {"userId": user_id}]
        if len(str(user_id)) == 24:
            query_conds.extend([{"user_id": ObjectId(user_id)}, {"userId": ObjectId(user_id)}])
            
        histories = list(history_col.find({"$or": query_conds}).sort("date", 1))
        
        labels = []
        weights = []
        for h in histories:
            labels.append(h.get("date", ""))
            weights.append(safe_float(h.get("weight", 0)))

        query = {"_id": ObjectId(user_id)} if len(str(user_id)) == 24 else {"_id": user_id}
        user = user_col.find_one(query)
        goal_weight = safe_float(user.get("goalWeight", 0)) if user else 0

        return jsonify({
            "success": True, 
            "data": { "labels": labels, "weights": weights, "goal_weight": goal_weight }
        })
    except Exception as e:
        print(f"❌ Lỗi API Weight Chart: {e}")
        return jsonify({"success": False, "error": str(e)})
    # ==========================================
# 4. API LẤY VÀ PHÂN TÍCH MỨC TẠ ĐỀ XUẤT
# ==========================================
@tcn_bp.route('/api/tcn/weights', methods=['GET'])
def get_tcn_weights():
    try:
        user_id = request.args.get('userId')
        query = {"_id": ObjectId(user_id)} if len(str(user_id)) == 24 else {"_id": user_id}
        user = user_col.find_one(query)
        if not user: return jsonify({"success": False, "error": "User not found"})

        # 1. TÍNH TOÁN HỆ SỐ THỂ TRẠNG (Dựa vào BMI & Giới tính)
        weight = safe_float(user.get("weight", 0))
        height_cm = safe_float(user.get("height", 0))
        bmi = round(weight / ((height_cm/100)**2), 1) if height_cm > 0 else 0
        gender = str(user.get("gender", "")).lower()

        factor = 1.0 # Mức chuẩn xanh lá
        if bmi < 18.5: factor = 0.6       # Thiếu cân -> Yếu
        elif bmi >= 25: factor = 0.7      # Thừa cân/Béo phì -> Thể lực kém
        
        if gender in ['nữ', 'female']: factor *= 0.6 # Nữ mặc định tạ nhẹ hơn nam
        
        # Mốc tạ tối đa cho người Bình thường (Factor = 1.0)
        base_weights = {
            "Ngực": round(15 * factor),
            "Lưng": round(20 * factor),
            "Chân": round(30 * factor),
            "Vai": round(10 * factor),
            "Tay": round(8 * factor),
            "Bụng": round(5 * factor) # Tính bằng tạ ôm hoặc kg tạ đòn
        }
        # Đảm bảo mức tạ tối thiểu là 1kg
        for k in base_weights: base_weights[k] = max(1, base_weights[k])

        # 2. LẤY MỨC TẠ LƯU TRONG CSDL CỦA NGƯỜI DÙNG (Nếu họ đã từng chỉnh sửa)
        saved_weights = user.get("muscle_weights") or {}
        current_weights = {k: saved_weights.get(k, base_weights[k]) for k in base_weights}
        # 3. QUÉT LỊCH SỬ ĐỂ ĐẾM SỐ BÀI TẬP ĐÃ HOÀN THÀNH
        exercise_counts = { "Ngực": 0, "Lưng": 0, "Chân": 0, "Vai": 0, "Tay": 0, "Bụng": 0 }
        plans = list(plan_col.find({"user_id": user_id}))
        completed_exs = []
        for plan in plans:
            for day in plan.get("daily_progress", []):
                for ex in day.get("exercises", []):
                    if ex.get("completed") == True: completed_exs.append(ex.get("name"))
        
        if completed_exs:
            ex_details = list(exercise_col.find({"name": {"$in": completed_exs}}))
            for ex in ex_details:
                main_branch = get_main_muscle_group(ex.get("muscle", ""))
                if main_branch: exercise_counts[main_branch] += 1

        # 4. THUẬT TOÁN BÌNH LUẬN (CẢNH BÁO PROGRESSIVE OVERLOAD)
        # Ngưỡng số bài tập cần đạt để tăng tạ (Dựa vào ảnh 2)
        thresholds = { "Ngực": 10, "Lưng": 12, "Chân": 8, "Vai": 10, "Tay": 8, "Bụng": 8 }
        
        results = []
        for muscle in ["Ngực", "Lưng", "Chân", "Vai", "Tay", "Bụng"]:
            count = exercise_counts[muscle]
            thresh = thresholds[muscle]
            weight_val = current_weights[muscle]
            
            is_upgrade = False
            if count >= thresh:
                comment = f"🔥 Bạn đã tích lũy {count} bài tập. Cơ bắp đã quen, hãy thử tăng thêm 2-5kg nhé!"
                is_upgrade = True
            elif count > 0:
                comment = f"Đang trong giai đoạn làm quen ({count}/{thresh} bài). Hãy duy trì mức {weight_val}kg để chuẩn form."
            else:
                if factor < 0.8: comment = f"Mức tạ khởi điểm thấp do BMI của bạn chưa ở mức lý tưởng. Hãy tập từ từ."
                else: comment = "Mức tạ khởi điểm tiêu chuẩn cho thể trạng của bạn."

            results.append({
                "muscle": muscle,
                "weight": weight_val,
                "comment": comment,
                "is_upgrade": is_upgrade
            })

        return jsonify({"success": True, "data": results})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

# ==========================================
# 5. API LƯU MỨC TẠ KHI NGƯỜI DÙNG BẤM [+] [-]
# ==========================================
@tcn_bp.route('/api/tcn/weights/update', methods=['POST'])
def update_tcn_weights():
    try:
        data = request.json
        user_id = data.get('userId')
        muscle = data.get('muscle')
        new_weight = safe_float(data.get('weight'))

        query = {"_id": ObjectId(user_id)} if len(str(user_id)) == 24 else {"_id": user_id}
        # Update cụ thể một field trong object muscle_weights
        user_col.update_one(query, {"$set": {f"muscle_weights.{muscle}": new_weight}})
        
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})