import os
from datetime import datetime

import requests
from bson.objectid import ObjectId
from flask import Blueprint, jsonify, request

from ketnoidb import db

try:
    import google.generativeai as genai
except ImportError:
    genai = None

coach_bp = Blueprint("coach", __name__)


@coach_bp.route("/api/coach/chat", methods=["POST"])
def coach_chat():
    data = request.json or {}
    user_id = data.get("userId") or data.get("user_id")
    message = str(data.get("message") or "").strip()
    current_day_number = safe_int(data.get("currentDayNumber") or data.get("current_day_number"), 0)

    if not message:
        return jsonify({"success": False, "error": "Thiếu nội dung câu hỏi"}), 400

    context = build_coach_context(user_id, current_day_number)
    intent = detect_intent(message)
    context["intent"] = intent
    reply = deterministic_context_reply(message, context)
    if not reply:
        reply = ask_gemini_coach(message, context, intent) or fallback_coach_reply(message, context)

    save_chat_log(user_id, message, reply, context)
    return jsonify({"success": True, "reply": reply, "context": public_context(context)}), 200


def build_coach_context(user_id: str, current_day_number: int = 0) -> dict:
    profile = None
    if user_id and user_id != "guest":
        try:
            profile = db.user.find_one({"_id": ObjectId(user_id)}, {"passwordHash": 0})
        except Exception:
            profile = db.user.find_one({"id": user_id}, {"passwordHash": 0})

    plan = db.plan.find_one({"user_id": user_id, "status": "active"}, sort=[("created_at", -1)]) if user_id else None
    plan_data = plan.get("plan_data", {}) if plan else {}
    progress = plan.get("daily_progress", []) if plan else []
    days = plan_data.get("days", [])

    selected_day = select_context_day(days, progress, current_day_number)
    today = datetime.now().date().isoformat()
    nutrition = db.nutrition_daily.find_one({"user_id": user_id, "date": today}) if user_id else None

    return {
        "user_id": user_id,
        "profile": summarize_profile(profile),
        "plan": summarize_plan(plan, plan_data),
        "today": summarize_day(selected_day),
        "progress": summarize_progress(progress),
        "nutrition": summarize_nutrition(nutrition, selected_day),
    }


def select_context_day(days: list, progress: list, current_day_number: int) -> dict:
    if not days:
        return {}
    day_number = current_day_number if current_day_number > 0 else next_unfinished_day(progress) or 1
    day = next((item for item in days if safe_int(item.get("day_number"), 0) == day_number), days[0])
    progress_day = next((item for item in progress if safe_int(item.get("day_number"), 0) == safe_int(day.get("day_number"), 0)), {})
    return {"plan_day": day, "progress_day": progress_day}


def next_unfinished_day(progress: list) -> int:
    for day in progress or []:
        if not day.get("day_done"):
            return safe_int(day.get("day_number"), 1)
    return 1


def summarize_profile(profile: dict | None) -> dict:
    if not profile:
        return {}
    return {
        "fullName": profile.get("fullName"),
        "age": profile.get("age"),
        "gender": profile.get("gender"),
        "height": profile.get("height"),
        "weight": profile.get("weight"),
        "goalType": profile.get("goalType"),
        "level": profile.get("level"),
    }


def summarize_plan(plan: dict | None, plan_data: dict) -> dict:
    if not plan:
        return {"has_active_plan": False}
    return {
        "has_active_plan": True,
        "plan_id": str(plan.get("_id")),
        "name": plan_data.get("plan_name") or plan_data.get("title"),
        "summary": plan_data.get("summary"),
        "duration_days": plan_data.get("duration_days") or len(plan_data.get("days", [])),
        "source": plan.get("source"),
        "safety_note": plan_data.get("safety_note"),
    }


def summarize_day(selected_day: dict) -> dict:
    plan_day = selected_day.get("plan_day") or {}
    progress_day = selected_day.get("progress_day") or {}
    progress_by_name = {item.get("name"): item for item in progress_day.get("exercises", [])}
    exercises = []
    for ex in plan_day.get("exercises", []):
        progress_ex = progress_by_name.get(ex.get("name"), {})
        exercises.append({
            "name": ex.get("name"),
            "muscle": ex.get("muscle"),
            "sets": ex.get("sets"),
            "reps": ex.get("reps"),
            "rest": ex.get("rest"),
            "equipment": ex.get("equip") or ex.get("equipment"),
            "completed": bool(progress_ex.get("completed")),
            "tips": ex.get("tips", [])[:3],
        })
    return {
        "day_number": plan_day.get("day_number"),
        "day_name": plan_day.get("day_name"),
        "is_rest": bool(plan_day.get("is_rest")),
        "focus": plan_day.get("focus"),
        "day_done": bool(progress_day.get("day_done")),
        "is_locked": bool(progress_day.get("is_locked")),
        "target_calories": progress_day.get("target_calories") or plan_day.get("target_calories"),
        "target_protein": progress_day.get("target_protein") or plan_day.get("target_protein"),
        "exercises": exercises,
    }


def summarize_progress(progress: list) -> dict:
    total_days = len(progress or [])
    done_days = sum(1 for day in progress or [] if day.get("day_done"))
    done_exercises = 0
    total_exercises = 0
    for day in progress or []:
        exercises = day.get("exercises", [])
        total_exercises += len(exercises)
        done_exercises += sum(1 for ex in exercises if ex.get("completed"))
    return {
        "done_days": done_days,
        "total_days": total_days,
        "done_exercises": done_exercises,
        "total_exercises": total_exercises,
    }


def summarize_nutrition(nutrition: dict | None, selected_day: dict) -> dict:
    day = summarize_day(selected_day)
    return {
        "calories": safe_float((nutrition or {}).get("calories")),
        "protein": safe_float((nutrition or {}).get("protein")),
        "carbs": safe_float((nutrition or {}).get("carbs")),
        "fat": safe_float((nutrition or {}).get("fat")),
        "is_locked": bool((nutrition or {}).get("is_locked")),
        "target_calories": safe_float(day.get("target_calories")),
        "target_protein": safe_float(day.get("target_protein")),
    }


def ask_gemini_coach(message: str, context: dict, intent: str) -> str | None:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return None
    prompt = build_coach_prompt(message, context, intent)
    return ask_gemini_sdk(api_key, prompt) or ask_gemini_rest(api_key, prompt)


def build_coach_prompt(message: str, context: dict, intent: str) -> str:
    context_text = compact_context_for_prompt(context, intent)
    return f"""
Bạn là AI Huấn Luyện Viên chuyên gia của FIT ME, nhưng vẫn có thể trả lời câu hỏi đời thường.
Ý định đã phân loại: {intent}

Luật trả lời:
- Trả lời trực tiếp đúng câu hỏi ngay câu đầu tiên. Không mở đầu bằng câu nhắc lại lộ trình.
- Nếu intent là plan: trả lời đúng trọng tâm câu hỏi về lộ trình hiện tại trước; chỉ nêu ngày, bài, tiến độ hoặc bước tiếp theo liên quan trực tiếp.
- Nếu intent là fitness, nutrition, recovery hoặc pain: dùng hồ sơ, lộ trình, tiến độ, dinh dưỡng trong ngữ cảnh để cá nhân hóa.
- Nếu intent là general: trả lời bằng kiến thức tổng quát như một trợ lý AI bình thường; chỉ nhắc FIT ME khi thật sự liên quan.
- Nếu người dùng nói "lỡ", "ăn dư", "tập thiếu", "quên", "trễ": trấn an trước, rồi đưa cách xử lý cụ thể trong hôm nay hoặc ngày mai.
- Không trả lời kiểu chung chung như "bạn hỏi cụ thể hơn" khi vẫn có thể đưa hướng xử lý an toàn.
- Không kê đơn y tế. Nếu có đau dữ dội, kéo dài, chóng mặt, đau ngực, khó thở, nôn ói, sốt hoặc ngất thì khuyên dừng tập và gặp chuyên gia y tế.
- Không tự xác nhận đã hoàn thành bài tập; nếu cần thì hướng dẫn người dùng bấm check-in.
- Giữ câu trả lời tự nhiên, 3-7 dòng, có gợi ý hành động rõ ràng.

NGỮ CẢNH:
{context_text}

CÂU HỎI:
{message}
""".strip()


def ask_gemini_sdk(api_key: str, prompt: str) -> str | None:
    if genai is None:
        return None
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("gemini-1.5-flash")
        response = model.generate_content(prompt)
        return (response.text or "").strip() or None
    except Exception:
        return None


def ask_gemini_rest(api_key: str, prompt: str) -> str | None:
    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
        response = requests.post(
            url,
            json={"contents": [{"parts": [{"text": prompt}]}]},
            timeout=20,
        )
        if response.status_code >= 400:
            return None
        data = response.json()
        candidates = data.get("candidates") or []
        parts = ((candidates[0] or {}).get("content") or {}).get("parts") or [] if candidates else []
        return "\n".join(part.get("text", "") for part in parts).strip() or None
    except Exception:
        return None


def compact_context_for_prompt(context: dict, intent: str) -> dict:
    if intent == "general":
        return {
            "note": "Câu hỏi không liên quan trực tiếp tới tập luyện; chỉ dùng hồ sơ FIT ME nếu thật sự cần.",
            "profile": context.get("profile", {}),
        }
    return {
        "profile": context.get("profile", {}),
        "plan": context.get("plan", {}),
        "today": context.get("today", {}),
        "progress": context.get("progress", {}),
        "nutrition": context.get("nutrition", {}),
    }


def deterministic_context_reply(message: str, context: dict) -> str | None:
    intent = context.get("intent") or detect_intent(message)
    plan = context.get("plan", {})
    if intent != "plan":
        return None
    if not plan.get("has_active_plan"):
        return "Bạn chưa có lộ trình đang áp dụng. Hãy tạo lộ trình trước, sau đó mình mới theo dõi được ngày tập, bài đã hoàn thành và bước tiếp theo cho bạn."
    return plan_reply(message, context)


def fallback_coach_reply(message: str, context: dict) -> str:
    plan = context.get("plan", {})
    today = context.get("today", {})
    nutrition = context.get("nutrition", {})
    lowered = message.lower()
    intent = context.get("intent") or detect_intent(message)

    if not plan.get("has_active_plan"):
        if intent == "general":
            return general_fallback_reply(message)
        return "Hiện bạn chưa có lộ trình đang chạy nên mình chưa thể cá nhân hóa theo tiến độ tập. Nhưng bạn vẫn có thể hỏi về kỹ thuật, dinh dưỡng hoặc sức khỏe, mình sẽ tư vấn theo nguyên tắc an toàn."

    pain_reply = pain_or_health_reply(lowered, today)
    if pain_reply:
        return pain_reply

    if intent == "technique":
        return technique_reply(today)

    if intent == "plan":
        return plan_reply(message, context)

    if intent == "nutrition":
        return nutrition_reply(lowered, nutrition, today)

    if intent == "general":
        return general_fallback_reply(message)

    return answer_from_current_day(message, today, context.get("progress", {}))


def detect_intent(message: str) -> str:
    lowered = message.lower()
    if any(key in lowered for key in ["đau", "dau", "mỏi", "moi", "chóng mặt", "choang", "buồn nôn", "nôn", "khó thở", "kho tho", "đau ngực", "dau nguc", "chuột rút", "cramp", "chấn thương"]):
        return "pain"
    if any(key in lowered for key in ["ngày nghỉ", "ngay nghi", "có nghỉ", "co nghi", "nghỉ không", "nghi khong", "hôm nay tập", "hom nay tap", "tập gì", "tap gi", "bài gì", "bai gi", "bài tiếp", "bai tiep", "tiếp theo", "tiep theo", "tập tiếp", "tap tiep", "lịch tập", "lich tap", "lộ trình", "tiến độ"]):
        return "plan"
    if any(key in lowered for key in ["protein", "calo", "calories", "kcal", "ăn ", " an ", "dinh dưỡng", "bữa", "đói", "carb", "fat", "tôm", "gà", "trứng", "cơm", "lỡ ăn", "ăn dư", "ăn thiếu", "uống"]):
        return "nutrition"
    if any(key in lowered for key in ["lưu ý", "ky thuat", "kỹ thuật", "form", "đúng cách", "sai cách", "tư thế", "bài đầu"]):
        return "technique"
    if any(key in lowered for key in ["hôm nay", "tap gi", "tập gì", "bài gì", "bai gi", "bài tiếp", "bai tiep", "tiếp theo", "tiep theo", "tập tiếp", "tap tiep", "lich", "lịch", "lộ trình", "ngày mấy", "tiến độ"]):
        return "plan"
    if any(key in lowered for key in ["tập", "workout", "gym", "sets", "reps", "cơ", "ngực", "vai", "lưng", "chân", "bụng"]):
        return "fitness"
    return "general"


def pain_or_health_reply(lowered: str, today: dict) -> str | None:
    health_keys = ["đau", "dau", "mỏi", "moi", "chóng mặt", "choang", "buồn nôn", "nôn", "khó thở", "kho tho", "đau ngực", "dau nguc", "chuột rút", "cramp"]
    if not any(key in lowered for key in health_keys):
        return None

    if any(key in lowered for key in ["bụng", "bung", "dạ dày", "da day", "stomach"]):
        return (
            "Nếu bạn đang đau bụng thì hôm nay không nên cố tập nặng. Hãy dừng các bài gây gồng bụng mạnh, ngồi nghỉ 10-15 phút, uống từng ngụm nước nhỏ và theo dõi cảm giác.\n"
            f"Với lộ trình hôm nay của bạn là Ngày {today.get('day_number')} - {today.get('focus')}, mình khuyên chuyển sang nghỉ/phục hồi nếu đau còn rõ. "
            "Nếu đau dữ dội, đau tăng dần, buồn nôn, sốt, tiêu chảy nặng hoặc đau kéo dài thì nên đi khám."
        )

    if any(key in lowered for key in ["ngực", "nguc", "tim", "khó thở", "kho tho", "chóng mặt", "choang"]):
        return (
            "Bạn nên dừng tập ngay lúc này. Đau ngực, khó thở hoặc chóng mặt khi tập là dấu hiệu cần ưu tiên an toàn, không cố hoàn thành lộ trình.\n"
            "Hãy ngồi nghỉ, hít thở chậm, báo người bên cạnh nếu có, và đi khám/cấp cứu nếu triệu chứng không giảm nhanh hoặc lặp lại."
        )

    if any(key in lowered for key in ["vai", "shoulder", "gối", "goi", "lưng", "lung", "cổ tay", "co tay", "khớp", "khop"]):
        return (
            "Nếu đau ở khớp hoặc đau nhói khi thực hiện động tác, bạn nên dừng bài đó thay vì cố tập tiếp. Giảm tải, kiểm tra lại kỹ thuật và tránh các động tác làm đau tăng.\n"
            f"Hôm nay lộ trình đang là Ngày {today.get('day_number')} - {today.get('focus')}. Bạn có thể bỏ bài gây đau và chỉ tập bài không đau, hoặc chuyển sang nghỉ phục hồi. "
            "Nếu đau kéo dài qua 24-48 giờ hoặc sưng/nóng/giới hạn vận động, nên gặp chuyên gia."
        )

    return (
        "Nếu bạn đang đau hoặc khó chịu khi tập, hãy giảm cường độ ngay và đừng cố hoàn thành buổi tập bằng mọi giá.\n"
        f"Với Ngày {today.get('day_number')} - {today.get('focus')}, bạn có thể nghỉ 5-10 phút, thử lại nhẹ hơn; nếu cảm giác đau vẫn còn thì chuyển sang nghỉ/phục hồi. "
        "Đau dữ dội, kéo dài hoặc kèm chóng mặt/khó thở thì nên đi khám."
    )


def nutrition_reply(lowered: str, nutrition: dict, today: dict) -> str:
    calories = nutrition.get("calories", 0)
    protein = nutrition.get("protein", 0)
    target_calories = nutrition.get("target_calories", 0)
    target_protein = nutrition.get("target_protein", 0)
    missing_protein = max(0, target_protein - protein)
    missing_cal = max(0, target_calories - calories)
    over_cal = max(0, calories - target_calories)
    over_protein = max(0, protein - target_protein)

    if any(key in lowered for key in ["lỡ", "lo", "ăn dư", "du calo", "dư calo", "quá calo", "ăn quá", "ăn nhiều"]):
        if over_cal > 0:
            return (
                f"Không sao, hôm nay bạn đang dư khoảng {over_cal:.0f} kcal so với mục tiêu. Một ngày dư nhẹ không phá lộ trình, quan trọng là tổng cả tuần.\n"
                "Bữa còn lại hãy ăn nhẹ hơn: ưu tiên rau, đạm nạc, uống nước; hạn chế đồ ngọt/dầu mỡ thêm. "
                f"Nếu vẫn tập Ngày {today.get('day_number')} - {today.get('focus')}, cứ tập đúng sức, không cần cardio phạt bản thân."
            )
        return (
            f"Bạn chưa bị dư theo dữ liệu hiện tại: mới khoảng {calories:.0f}/{target_calories:.0f} kcal. "
            "Nếu cảm giác đã ăn hơi nhiều, bữa sau chỉ cần chọn món nhẹ, nhiều rau và đạm nạc; không cần nhịn đói để bù."
        )

    if any(key in lowered for key in ["thiếu", "cần ăn thêm", "ăn thêm", "bao nhiêu calo", "bao nhiêu protein", "còn thiếu"]):
        return (
            f"Hôm nay bạn còn thiếu khoảng {missing_cal:.0f} kcal và {missing_protein:.0f}g protein. "
            "Gợi ý gọn: 200g ức gà hoặc tôm + 1 bát cơm + rau là khá hợp. "
            "Nếu gần giờ ngủ, ưu tiên protein dễ tiêu và đừng nạp quá no."
        )

    if any(key in lowered for key in ["protein"]):
        status = "đạt mục tiêu" if missing_protein <= 0 else f"còn thiếu khoảng {missing_protein:.0f}g"
        return (
            f"Protein hôm nay của bạn là {protein:.0f}/{target_protein:.0f}g, tức là {status}. "
            "Nếu cần bổ sung, chọn tôm, ức gà, cá, trứng, sữa chua Hy Lạp hoặc whey tùy bạn có gì sẵn."
        )

    if over_protein > 0 and over_cal == 0:
        return (
            f"Bạn đang vượt protein khoảng {over_protein:.0f}g nhưng calories vẫn chưa vượt mục tiêu. Thường không đáng lo nếu thận khỏe và bạn uống đủ nước. "
            "Bữa sau chỉ cần cân bằng thêm rau, carb vừa phải và không cần ép thêm đạm."
        )

    return (
        f"Dinh dưỡng hôm nay: {calories:.0f}/{target_calories:.0f} kcal và {protein:.0f}/{target_protein:.0f}g protein. "
        f"Còn thiếu khoảng {missing_cal:.0f} kcal, {missing_protein:.0f}g protein. "
        "Mục tiêu là đủ năng lượng để tập nhưng không ăn quá no sát buổi tập."
    )


def general_fallback_reply(message: str) -> str:
    lowered = message.lower()
    if any(key in lowered for key in ["xin chào", "hello", "hi", "chào"]):
        return "Chào bạn, mình đây. Bạn có thể hỏi mình về buổi tập, dinh dưỡng, phục hồi, hoặc cả câu hỏi ngoài tập luyện cũng được."
    if any(key in lowered for key in ["cảm ơn", "cam on", "thanks"]):
        return "Không có gì. Cứ hỏi tiếp khi bạn cần, mình sẽ trả lời sát tình huống nhất có thể."
    return (
        "Mình có thể trả lời câu hỏi này, nhưng hiện backend chưa kết nối được AI tổng quát nên mình chỉ trả lời chắc chắn trong phạm vi FIT ME: tập luyện, dinh dưỡng, phục hồi và lộ trình cá nhân. "
        "Khi cấu hình Gemini/API ngoài hoạt động, phần này sẽ trả lời rộng hơn như một trợ lý AI bình thường."
    )


def technique_reply(today: dict) -> str:
    exercises = today.get("exercises", [])
    if today.get("is_rest"):
        return "Hôm nay là ngày nghỉ, ưu tiên đi bộ nhẹ, giãn cơ và ngủ đủ. Nếu bạn muốn vận động, giữ ở mức rất nhẹ để cơ phục hồi."
    if not exercises:
        return "Mình chưa thấy bài tập cụ thể trong ngày hiện tại, nên chưa thể hướng dẫn kỹ thuật sát bài."
    ex = next((item for item in exercises if not item.get("completed")), exercises[0])
    tips = ex.get("tips") or []
    lines = [
        f"Bài nên chú ý trước là {ex.get('name')}. Hãy làm đúng kỹ thuật trước khi tăng reps.",
        f"- Mức tập: {ex.get('sets')} sets x {ex.get('reps')} reps, nghỉ {ex.get('rest')}s.",
    ]
    if tips:
        lines.extend(f"- {tip}" for tip in tips[:3])
    else:
        lines.extend([
            "- Giữ thân người ổn định, không vội ở pha hạ người.",
            "- Dừng lại nếu thấy đau nhói ở khớp hoặc khó kiểm soát động tác.",
        ])
    return "\n".join(lines)


def plan_reply(message: str, context: dict) -> str:
    lowered = message.lower()
    today = context.get("today", {})
    progress = context.get("progress", {})
    exercises = today.get("exercises", [])
    unfinished = [ex for ex in exercises if not ex.get("completed")]
    completed = [ex for ex in exercises if ex.get("completed")]

    if any(key in lowered for key in ["tiến độ", "tien do", "hoàn thành", "hoan thanh", "xong bao nhiêu", "xong bao nhieu"]):
        return (
            f"Tiến độ hiện tại của bạn: đã hoàn thành {progress.get('done_days', 0)}/{progress.get('total_days', 0)} ngày "
            f"và {progress.get('done_exercises', 0)}/{progress.get('total_exercises', 0)} bài tập.\n"
            f"Riêng Ngày {today.get('day_number')}: {len(completed)}/{len(exercises)} bài đã xong. "
            f"Bài tiếp theo là {unfinished[0].get('name') if unfinished else 'không còn bài nào trong ngày'}."
        )

    if any(key in lowered for key in ["bài tiếp", "bai tiep", "tiếp theo", "tiep theo", "tập tiếp", "tap tiep", "nên tập bài nào", "nen tap bai nao"]):
        if today.get("is_rest"):
            return f"Hôm nay là Ngày {today.get('day_number')} - ngày nghỉ/phục hồi, nên không có bài chính cần tập. Bạn chỉ nên đi bộ nhẹ hoặc giãn cơ 10-15 phút."
        if not unfinished:
            return f"Ngày {today.get('day_number')} đã hoàn thành hết bài. Bạn không cần tập thêm bài chính; ưu tiên giãn cơ, ăn đủ protein và phục hồi."
        ex = unfinished[0]
        return (
            f"Bài tiếp theo của bạn là {ex.get('name')}: {ex.get('sets')} sets x {ex.get('reps')} reps, nghỉ {ex.get('rest')}s.\n"
            f"Dụng cụ: {ex.get('equipment') or 'không cần dụng cụ'}. Nhóm cơ chính: {ex.get('muscle') or today.get('focus')}. "
            "Tập xong thì bấm hoàn thành để mình cập nhật tiến độ."
        )

    if any(key in lowered for key in ["hôm nay", "hom nay", "tập gì", "tap gi", "bài gì", "bai gi", "lịch hôm nay", "lich hom nay"]):
        return describe_today_training(today, progress)

    if any(key in lowered for key in ["ngày nghỉ", "ngay nghi", "có nghỉ", "co nghi", "nghỉ không", "nghi khong"]):
        if today.get("is_rest"):
            return f"Có, hôm nay là Ngày {today.get('day_number')} - ngày nghỉ/phục hồi. Mục tiêu chính là hồi phục, ngủ đủ và giữ dinh dưỡng."
        return f"Không, hôm nay là Ngày {today.get('day_number')} - {today.get('focus')}. Bạn còn {len(unfinished)} bài chưa hoàn thành trong buổi này."

    if any(key in lowered for key in ["đổi bài", "doi bai", "thay bài", "thay bai", "không tập được", "khong tap duoc"]):
        if not unfinished:
            return "Hôm nay bạn đã hoàn thành hết bài nên chưa cần đổi bài. Nếu có bài gây đau ở buổi sau, hãy nói tên bài hoặc vị trí đau để mình gợi ý thay thế an toàn."
        ex = unfinished[0]
        return (
            f"Nếu bạn không tập được {ex.get('name')}, đừng cố làm sai kỹ thuật. "
            "Hiện mình cần bạn nói rõ lý do: thiếu dụng cụ, đau ở đâu, hay bài quá khó. "
            "Sau đó mình sẽ gợi ý bài thay thế cùng nhóm cơ và an toàn hơn."
        )

    return describe_today_training(today, progress)


def answer_from_current_day(message: str, today: dict, progress: dict) -> str:
    exercises = today.get("exercises", [])
    if today.get("is_rest"):
        return (
            f"Mình hiểu câu hỏi của bạn. Vì hôm nay là Ngày {today.get('day_number')} - ngày nghỉ/phục hồi, "
            "ưu tiên phục hồi trước: đi bộ nhẹ, giãn cơ, ngủ đủ và ăn đủ protein. Nếu câu hỏi liên quan đau/mệt, đừng cố tập nặng hôm nay."
        )
    next_ex = next((ex for ex in exercises if not ex.get("completed")), exercises[0] if exercises else {})
    if next_ex:
        return (
            f"Mình hiểu ý bạn. Dựa trên lộ trình hiện tại, hôm nay bạn đang ở Ngày {today.get('day_number')} - {today.get('focus')}. "
            f"Bài tiếp theo nên ưu tiên là {next_ex.get('name')}: {next_ex.get('sets')} sets x {next_ex.get('reps')} reps, nghỉ {next_ex.get('rest')}s.\n"
            "Nếu câu hỏi của bạn là về đau, mệt hoặc kỹ thuật, hãy nói rõ vị trí/cảm giác để mình điều chỉnh sát hơn."
        )
    return describe_today_training(today, progress)


def describe_today_training(today: dict, progress: dict) -> str:
    if today.get("is_rest"):
        return f"Hôm nay là Ngày {today.get('day_number')} - ngày nghỉ/phục hồi. Bạn nên đi bộ nhẹ, giãn cơ 10-15 phút, ngủ đủ và giữ protein theo mục tiêu."
    exercises = today.get("exercises", [])
    if not exercises:
        return "Hôm nay chưa có bài tập trong lộ trình. Bạn có thể kiểm tra lại lộ trình hoặc tạo lại plan."
    lines = [
        f"Hôm nay là Ngày {today.get('day_number')}, trọng tâm {today.get('focus')}.",
        f"Tiến độ toàn lộ trình: {progress.get('done_days', 0)}/{progress.get('total_days', 0)} ngày hoàn thành.",
        "Các bài hôm nay:",
    ]
    for ex in exercises:
        status = "đã xong" if ex.get("completed") else "chưa xong"
        lines.append(f"- {ex.get('name')}: {ex.get('sets')} sets x {ex.get('reps')} reps, nghỉ {ex.get('rest')}s ({status}).")
    return "\n".join(lines)


def save_chat_log(user_id: str, message: str, reply: str, context: dict) -> None:
    try:
        db.coach_chat_logs.insert_one({
            "user_id": user_id,
            "message": message,
            "reply": reply,
            "plan_id": context.get("plan", {}).get("plan_id"),
            "day_number": context.get("today", {}).get("day_number"),
            "created_at": datetime.utcnow(),
        })
    except Exception:
        pass


def public_context(context: dict) -> dict:
    return {
        "has_active_plan": context.get("plan", {}).get("has_active_plan", False),
        "day_number": context.get("today", {}).get("day_number"),
        "focus": context.get("today", {}).get("focus"),
    }


def safe_int(value, default: int = 0) -> int:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def safe_float(value, default: float = 0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default
