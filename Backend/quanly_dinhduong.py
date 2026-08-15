import json
import os
import re
from datetime import datetime

from flask import Blueprint, jsonify, request

from ketnoidb import db

try:
    import google.generativeai as genai
except ImportError:
    genai = None

nutrition_bp = Blueprint("nutrition", __name__)

FOOD_FALLBACKS = [
    {"keys": ["tom", "tôm", "shrimp"], "name": "Tôm", "protein_per_100g": 24, "calories_per_100g": 99, "carbs_per_100g": 0.2, "fat_per_100g": 0.3},
    {"keys": ["uc ga", "ức gà", "chicken breast"], "name": "Ức gà", "protein_per_100g": 31, "calories_per_100g": 165, "carbs_per_100g": 0, "fat_per_100g": 3.6},
    {"keys": ["ga luoc", "gà luộc", "thit ga", "thịt gà", "chicken"], "name": "Thịt gà", "protein_per_100g": 27, "calories_per_100g": 190, "carbs_per_100g": 0, "fat_per_100g": 8},
    {"keys": ["dui ga", "đùi gà", "chicken thigh"], "name": "Đùi gà", "protein_per_100g": 24, "calories_per_100g": 209, "carbs_per_100g": 0, "fat_per_100g": 11},
    {"keys": ["canh ga", "cánh gà", "chicken wing"], "name": "Cánh gà", "protein_per_100g": 23, "calories_per_100g": 203, "carbs_per_100g": 0, "fat_per_100g": 12},
    {"keys": ["chan ga", "chân gà", "chicken feet"], "name": "Chân gà", "protein_per_100g": 19, "calories_per_100g": 215, "carbs_per_100g": 0.2, "fat_per_100g": 15},
    {"keys": ["trung", "trứng", "egg"], "name": "Trứng", "protein_per_100g": 13, "calories_per_100g": 155, "carbs_per_100g": 1.1, "fat_per_100g": 11},
    {"keys": ["long trang", "lòng trắng", "egg white"], "name": "Lòng trắng trứng", "protein_per_100g": 11, "calories_per_100g": 52, "carbs_per_100g": 0.7, "fat_per_100g": 0.2},
    {"keys": ["bo", "bò", "beef"], "name": "Thịt bò nạc", "protein_per_100g": 26, "calories_per_100g": 217, "carbs_per_100g": 0, "fat_per_100g": 12},
    {"keys": ["heo nac", "heo nạc", "thit heo nac", "thịt heo nạc", "pork lean"], "name": "Thịt heo nạc", "protein_per_100g": 27, "calories_per_100g": 242, "carbs_per_100g": 0, "fat_per_100g": 14},
    {"keys": ["thit heo", "thịt heo", "thit lon", "thịt lợn", "pork"], "name": "Thịt heo", "protein_per_100g": 25, "calories_per_100g": 260, "carbs_per_100g": 0, "fat_per_100g": 17},
    {"keys": ["ba chi", "ba chỉ", "pork belly"], "name": "Thịt ba chỉ", "protein_per_100g": 9, "calories_per_100g": 518, "carbs_per_100g": 0, "fat_per_100g": 53},
    {"keys": ["duoi heo", "đuôi heo", "duoi lon", "đuôi lợn", "pork tail"], "name": "Đuôi heo", "protein_per_100g": 17, "calories_per_100g": 330, "carbs_per_100g": 0, "fat_per_100g": 29},
    {"keys": ["tai heo", "tai lợn", "tai lon", "pork ear"], "name": "Tai heo", "protein_per_100g": 22, "calories_per_100g": 234, "carbs_per_100g": 0, "fat_per_100g": 16},
    {"keys": ["mong gio", "móng giò", "chan gio", "chân giò", "gio heo", "giò heo", "pork hock"], "name": "Chân giò heo", "protein_per_100g": 18, "calories_per_100g": 260, "carbs_per_100g": 0, "fat_per_100g": 20},
    {"keys": ["ruot heo", "ruột heo", "long heo", "lòng heo", "pork intestine"], "name": "Ruột heo", "protein_per_100g": 14, "calories_per_100g": 200, "carbs_per_100g": 0, "fat_per_100g": 16},
    {"keys": ["gan heo", "gan lợn", "gan lon", "gan heo", "pork liver"], "name": "Gan heo", "protein_per_100g": 21, "calories_per_100g": 165, "carbs_per_100g": 4, "fat_per_100g": 5},
    {"keys": ["tim heo", "tim lợn", "tim lon", "pork heart"], "name": "Tim heo", "protein_per_100g": 17, "calories_per_100g": 118, "carbs_per_100g": 1, "fat_per_100g": 4},
    {"keys": ["suon", "sườn", "pork ribs"], "name": "Sườn heo", "protein_per_100g": 20, "calories_per_100g": 320, "carbs_per_100g": 0, "fat_per_100g": 26},
    {"keys": ["ca hoi", "cá hồi", "salmon"], "name": "Cá hồi", "protein_per_100g": 20, "calories_per_100g": 208, "carbs_per_100g": 0, "fat_per_100g": 13},
    {"keys": ["ca ngu", "cá ngừ", "tuna"], "name": "Cá ngừ", "protein_per_100g": 29, "calories_per_100g": 132, "carbs_per_100g": 0, "fat_per_100g": 1},
    {"keys": ["ca basa", "cá basa", "basa"], "name": "Cá basa", "protein_per_100g": 18, "calories_per_100g": 120, "carbs_per_100g": 0, "fat_per_100g": 5},
    {"keys": ["ca loc", "cá lóc"], "name": "Cá lóc", "protein_per_100g": 20, "calories_per_100g": 97, "carbs_per_100g": 0, "fat_per_100g": 2},
    {"keys": ["muc", "mực", "squid"], "name": "Mực", "protein_per_100g": 16, "calories_per_100g": 92, "carbs_per_100g": 3, "fat_per_100g": 1.4},
    {"keys": ["cua", "crab"], "name": "Cua", "protein_per_100g": 19, "calories_per_100g": 97, "carbs_per_100g": 0, "fat_per_100g": 1.5},
    {"keys": ["com", "cơm", "rice"], "name": "Cơm trắng", "protein_per_100g": 2.7, "calories_per_100g": 130, "carbs_per_100g": 28, "fat_per_100g": 0.3},
    {"keys": ["gao lut", "gạo lứt", "com gao lut", "cơm gạo lứt", "brown rice"], "name": "Cơm gạo lứt", "protein_per_100g": 2.6, "calories_per_100g": 111, "carbs_per_100g": 23, "fat_per_100g": 0.9},
    {"keys": ["bun", "bún"], "name": "Bún tươi", "protein_per_100g": 1.7, "calories_per_100g": 110, "carbs_per_100g": 25, "fat_per_100g": 0.2},
    {"keys": ["pho", "phở"], "name": "Bánh phở", "protein_per_100g": 3.2, "calories_per_100g": 143, "carbs_per_100g": 32, "fat_per_100g": 0.4},
    {"keys": ["mi", "mì", "noodle"], "name": "Mì", "protein_per_100g": 7, "calories_per_100g": 138, "carbs_per_100g": 25, "fat_per_100g": 2},
    {"keys": ["banh mi", "bánh mì", "bread"], "name": "Bánh mì", "protein_per_100g": 8, "calories_per_100g": 265, "carbs_per_100g": 49, "fat_per_100g": 3.2},
    {"keys": ["khoai lang", "sweet potato"], "name": "Khoai lang", "protein_per_100g": 1.6, "calories_per_100g": 86, "carbs_per_100g": 20, "fat_per_100g": 0.1},
    {"keys": ["khoai tay", "khoai tây", "potato"], "name": "Khoai tây", "protein_per_100g": 2, "calories_per_100g": 77, "carbs_per_100g": 17, "fat_per_100g": 0.1},
    {"keys": ["yến mạch", "yen mach", "oat"], "name": "Yến mạch", "protein_per_100g": 16.9, "calories_per_100g": 389, "carbs_per_100g": 66, "fat_per_100g": 6.9},
    {"keys": ["chuoi", "chuối", "banana"], "name": "Chuối", "protein_per_100g": 1.1, "calories_per_100g": 89, "carbs_per_100g": 23, "fat_per_100g": 0.3},
    {"keys": ["tao", "táo", "apple"], "name": "Táo", "protein_per_100g": 0.3, "calories_per_100g": 52, "carbs_per_100g": 14, "fat_per_100g": 0.2},
    {"keys": ["bo trai", "bơ trái", "avocado"], "name": "Bơ", "protein_per_100g": 2, "calories_per_100g": 160, "carbs_per_100g": 9, "fat_per_100g": 15},
    {"keys": ["sua tuoi", "sữa tươi", "milk"], "name": "Sữa tươi", "protein_per_100g": 3.2, "calories_per_100g": 60, "carbs_per_100g": 4.8, "fat_per_100g": 3.3},
    {"keys": ["sua chua", "sữa chua", "yogurt"], "name": "Sữa chua", "protein_per_100g": 3.5, "calories_per_100g": 61, "carbs_per_100g": 4.7, "fat_per_100g": 3.3},
    {"keys": ["dau hu", "đậu hũ", "tofu"], "name": "Đậu hũ", "protein_per_100g": 8, "calories_per_100g": 76, "carbs_per_100g": 1.9, "fat_per_100g": 4.8},
    {"keys": ["dau phong", "đậu phộng", "peanut"], "name": "Đậu phộng", "protein_per_100g": 26, "calories_per_100g": 567, "carbs_per_100g": 16, "fat_per_100g": 49},
    {"keys": ["rau", "vegetable"], "name": "Rau xanh", "protein_per_100g": 2, "calories_per_100g": 25, "carbs_per_100g": 5, "fat_per_100g": 0.2},
]

DEFAULT_GRAMS_BY_KEYWORD = [
    (["bat", "chen"], 150),
    (["dia", "phan", "suat"], 250),
    (["hop"], 180),
    (["ly", "coc"], 240),
    (["qua", "trai"], 55),
    (["muong", "thia"], 15),
]


@nutrition_bp.route("/api/analyze-food", methods=["POST"])
def analyze_food():
    data = request.json or {}
    food_text = str(data.get("food_text") or data.get("foodText") or "").strip()
    if not food_text:
        return jsonify({"success": False, "error": "Thiếu mô tả món ăn"}), 400

    ai_result = analyze_food_with_gemini(food_text)
    result = ai_result or analyze_food_fallback(food_text) or unknown_food_response(food_text)
    return jsonify({"success": True, "data": result}), 200


@nutrition_bp.route("/api/save-nutrition", methods=["POST"])
def save_nutrition():
    data = request.json or {}
    user_id = data.get("userId") or data.get("user_id")
    date = data.get("date") or datetime.now().date().isoformat()
    if not user_id:
        return jsonify({"success": False, "error": "Thiếu userId"}), 400

    current = get_or_create_nutrition(user_id, date)
    if current.get("is_locked"):
        return jsonify({"success": False, "error": "Ngày dinh dưỡng này đã chốt sổ"}), 400

    entry = {
        "calories": safe_float(data.get("calories")),
        "protein": safe_float(data.get("protein")),
        "carbs": safe_float(data.get("carbs")),
        "fat": safe_float(data.get("fat")),
        "note": data.get("note", ""),
        "created_at": datetime.utcnow(),
    }
    db.nutrition_daily.update_one(
        {"user_id": user_id, "date": date},
        {
            "$inc": {
                "calories": entry["calories"],
                "protein": entry["protein"],
                "carbs": entry["carbs"],
                "fat": entry["fat"],
            },
            "$push": {"entries": entry},
            "$set": {"updated_at": datetime.utcnow()},
            "$setOnInsert": {"user_id": user_id, "date": date, "is_locked": False, "created_at": datetime.utcnow()},
        },
        upsert=True,
    )
    today = get_or_create_nutrition(user_id, date)
    return jsonify({"success": True, "today": serialize_nutrition(today)}), 200


@nutrition_bp.route("/api/get-nutrition", methods=["GET"])
def get_nutrition():
    user_id = request.args.get("userId") or request.args.get("user_id")
    date = request.args.get("date") or datetime.now().date().isoformat()
    if not user_id:
        return jsonify(default_nutrition(date)), 200
    return jsonify(serialize_nutrition(get_or_create_nutrition(user_id, date))), 200


@nutrition_bp.route("/api/lock-nutrition", methods=["POST"])
def lock_nutrition():
    data = request.json or {}
    user_id = data.get("userId") or data.get("user_id")
    date = data.get("date") or datetime.now().date().isoformat()
    if not user_id:
        return jsonify({"success": False, "error": "Thiếu userId"}), 400
    db.nutrition_daily.update_one(
        {"user_id": user_id, "date": date},
        {
            "$set": {"is_locked": True, "locked_at": datetime.utcnow(), "updated_at": datetime.utcnow()},
            "$setOnInsert": {"calories": 0, "protein": 0, "carbs": 0, "fat": 0, "entries": [], "created_at": datetime.utcnow()},
        },
        upsert=True,
    )
    return jsonify({"success": True, "message": "Đã chốt sổ dinh dưỡng hôm nay"}), 200


def analyze_food_with_gemini(food_text: str):
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key or genai is None:
        return None
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("gemini-1.5-flash")
        prompt = f"""
Bạn là chuyên gia dinh dưỡng thể hình tại Việt Nam. Phân tích dinh dưỡng ước tính cho món ăn/nguyên liệu sau: {food_text}

Yêu cầu:
- Hiểu cả món Việt, nguyên liệu đơn giản và nội tạng/da/xương như ruột heo, lòng heo, chân gà, cánh gà, đùi gà.
- Nếu người dùng ghi khối lượng như 300g, 0.3kg, 1 bát, 1 chén, 1 quả thì quy đổi hợp lý.
- Với món có xương/da như chân gà, ước tính theo phần ăn được phổ biến; ghi rõ trong summary là ước tính.
- Trả về số gần đúng, không để calories/protein/carbs/fat bằng 0 nếu thực phẩm có dữ liệu dinh dưỡng.
- Chỉ trả về JSON hợp lệ, không markdown:
{{
  "summary": "mô tả ngắn",
  "items": [{{"name":"tên món","amount":"khối lượng","calories":0,"protein":0,"carbs":0,"fat":0}}],
  "total": {{"calories":0,"protein":0,"carbs":0,"fat":0}}
}}
"""
        response = model.generate_content(prompt)
        text = (response.text or "").strip()
        text = re.sub(r"^```json|```$", "", text, flags=re.IGNORECASE).strip()
        parsed = json.loads(text)
        return normalize_analysis(parsed)
    except Exception:
        return None


def analyze_food_fallback(food_text: str):
    lowered = strip_vietnamese_accents(food_text.lower())
    matches = find_food_matches(lowered)
    if not matches:
        return None

    items = []
    total = {"calories": 0, "protein": 0, "carbs": 0, "fat": 0}
    for food, match_pos in matches:
        grams = extract_item_grams(lowered, match_pos)
        factor = grams / 100
        cooking = cooking_adjustment(lowered, match_pos)
        item = {
            "name": apply_cooking_name(food["name"], cooking),
            "amount": f"{grams:g}g",
            "calories": round((food["calories_per_100g"] + cooking["extra_calories_per_100g"]) * cooking["calorie_multiplier"] * factor, 1),
            "protein": round(food["protein_per_100g"] * factor, 1),
            "carbs": round(food["carbs_per_100g"] * factor, 1),
            "fat": round((food["fat_per_100g"] + cooking["extra_fat_per_100g"]) * cooking["fat_multiplier"] * factor, 1),
        }
        items.append(item)
        for key in total:
            total[key] += item[key]
    total = {key: round(value, 1) for key, value in total.items()}
    return {
        "summary": f"Ước tính theo dữ liệu dinh dưỡng phổ biến cho {food_text}. Cách chế biến như chiên/rán có thể làm calories và fat cao hơn.",
        "items": items,
        "total": total,
    }


def cooking_adjustment(text: str, match_pos: int) -> dict:
    segment, _ = food_segment(text, match_pos)
    if any(word in segment for word in ["chien", "ran", "xao"]):
        return {
            "label": "chiên",
            "calorie_multiplier": 1.0,
            "fat_multiplier": 1.0,
            "extra_calories_per_100g": 70,
            "extra_fat_per_100g": 8,
        }
    if any(word in segment for word in ["nuong", "ap chao"]):
        return {
            "label": "nướng",
            "calorie_multiplier": 1.08,
            "fat_multiplier": 1.05,
            "extra_calories_per_100g": 0,
            "extra_fat_per_100g": 0,
        }
    return {"label": "", "calorie_multiplier": 1.0, "fat_multiplier": 1.0, "extra_calories_per_100g": 0, "extra_fat_per_100g": 0}


def apply_cooking_name(name: str, cooking: dict) -> str:
    label = cooking.get("label")
    return f"{name} {label}" if label and label not in strip_vietnamese_accents(name.lower()) else name


def find_food_matches(text: str) -> list[tuple[dict, int]]:
    matches = []
    occupied = []
    foods = sorted(
        FOOD_FALLBACKS,
        key=lambda item: max(len(strip_vietnamese_accents(key.lower())) for key in item["keys"]),
        reverse=True,
    )
    for food in foods:
        key_hits = []
        for key in food["keys"]:
            normalized_key = strip_vietnamese_accents(key.lower())
            hit = re.search(rf"(?<!\w){re.escape(normalized_key)}(?!\w)", text)
            if hit:
                key_hits.append(hit.start())
        if not key_hits:
            continue
        pos = min(key_hits)
        if any(abs(pos - used) < 3 for used in occupied):
            continue
        occupied.append(pos)
        matches.append((food, pos))
    return sorted(matches, key=lambda item: item[1])


def extract_item_grams(text: str, match_pos: int) -> float:
    segment, local_match_pos = food_segment(text, match_pos)
    grams = extract_nearest_grams(segment, local_match_pos)
    if grams:
        return grams
    return default_serving_grams(segment)


def food_segment(text: str, match_pos: int) -> tuple[str, int]:
    delimiters = [",", ";", "\n", " va ", " voi ", " cung ", " kem "]
    start = 0
    end = len(text)
    for delimiter in delimiters:
        left = text.rfind(delimiter, 0, match_pos)
        if left != -1:
            start = max(start, left + len(delimiter))
        right = text.find(delimiter, match_pos)
        if right != -1:
            end = min(end, right)
    segment = text[start:end].strip()
    return segment, max(0, match_pos - start)


def extract_nearest_grams(text: str, match_pos: int) -> float | None:
    candidates = []
    patterns = [
        (r"(\d+(?:[.,]\d+)?)\s*kg", 1000),
        (r"(\d+(?:[.,]\d+)?)\s*(?:g|gram|gam)", 1),
        (r"(\d+(?:[.,]\d+)?)\s*(?:bat|chen|chén|bát)", 150),
        (r"(\d+(?:[.,]\d+)?)\s*(?:ly|coc|cốc)", 240),
        (r"(\d+(?:[.,]\d+)?)\s*(?:qua|quả|trai|trái)", 55),
        (r"(\d+(?:[.,]\d+)?)\s*(?:hop|hộp)", 180),
        (r"(\d+(?:[.,]\d+)?)\s*(?:muong|muỗng|thia|thìa)", 15),
    ]
    for pattern, multiplier in patterns:
        for match in re.finditer(pattern, text):
            amount = float(match.group(1).replace(",", ".")) * multiplier
            candidates.append((abs(match.start() - match_pos), amount))
    if not candidates:
        return None
    return min(candidates, key=lambda item: item[0])[1]


def extract_grams(text: str, default: float | None = 100) -> float | None:
    kg_match = re.search(r"(\d+(?:[.,]\d+)?)\s*kg", text)
    if kg_match:
        return float(kg_match.group(1).replace(",", ".")) * 1000
    gram_match = re.search(r"(\d+(?:[.,]\d+)?)\s*(?:g|gram|gam)", text)
    if gram_match:
        return float(gram_match.group(1).replace(",", "."))
    bowl_match = re.search(r"(\d+(?:[.,]\d+)?)\s*(?:bat|chen|chén|bát)", text)
    if bowl_match:
        return float(bowl_match.group(1).replace(",", ".")) * 150
    egg_match = re.search(r"(\d+(?:[.,]\d+)?)\s*(?:qua|quả|trai|trái)", text)
    if egg_match:
        return float(egg_match.group(1).replace(",", ".")) * 55
    return default


def default_serving_grams(text: str) -> float:
    for keys, grams in DEFAULT_GRAMS_BY_KEYWORD:
        if any(key in text for key in keys):
            number_match = re.search(r"(\d+(?:[.,]\d+)?)", text)
            if number_match:
                return float(number_match.group(1).replace(",", ".")) * grams
            return grams
    return 100


def unknown_food_response(food_text: str) -> dict:
    return {
        "summary": (
            "Chưa có đủ dữ liệu để ước tính món này một cách đáng tin. "
            "Bạn có thể nhập tay 4 chỉ số hoặc nhập rõ hơn theo dạng: 200g tên món, 1 bát cơm, 2 quả trứng."
        ),
        "items": [{
            "name": food_text,
            "amount": "",
            "calories": 0,
            "protein": 0,
            "carbs": 0,
            "fat": 0,
            "needs_manual_input": True,
        }],
        "total": {"calories": 0, "protein": 0, "carbs": 0, "fat": 0},
        "needs_manual_input": True,
    }


def strip_vietnamese_accents(text: str) -> str:
    source = "àáạảãâầấậẩẫăằắặẳẵèéẹẻẽêềếệểễìíịỉĩòóọỏõôồốộổỗơờớợởỡùúụủũưừứựửữỳýỵỷỹđ"
    target = "aaaaaaaaaaaaaaaaaeeeeeeeeeeeiiiiiooooooooooooooooouuuuuuuuuuuyyyyyd"
    table = str.maketrans(source + source.upper(), target + target.upper())
    return text.translate(table)


def normalize_analysis(data: dict) -> dict:
    items = data.get("items") or []
    safe_items = []
    total = {"calories": 0, "protein": 0, "carbs": 0, "fat": 0}
    for item in items:
        safe_item = {
            "name": str(item.get("name") or "Món ăn"),
            "amount": str(item.get("amount") or ""),
            "calories": safe_float(item.get("calories")),
            "protein": safe_float(item.get("protein")),
            "carbs": safe_float(item.get("carbs")),
            "fat": safe_float(item.get("fat")),
        }
        safe_items.append(safe_item)
        for key in total:
            total[key] += safe_item[key]
    provided_total = data.get("total") or {}
    for key in total:
        total[key] = round(safe_float(provided_total.get(key), total[key]), 1)
    return {"summary": data.get("summary", ""), "items": safe_items, "total": total}


def get_or_create_nutrition(user_id: str, date: str) -> dict:
    doc = db.nutrition_daily.find_one({"user_id": user_id, "date": date})
    return doc or default_nutrition(date, user_id)


def default_nutrition(date: str, user_id: str = "") -> dict:
    return {"user_id": user_id, "date": date, "calories": 0, "protein": 0, "carbs": 0, "fat": 0, "entries": [], "is_locked": False}


def serialize_nutrition(doc: dict) -> dict:
    doc = dict(doc or {})
    doc.pop("_id", None)
    for key in ["calories", "protein", "carbs", "fat"]:
        doc[key] = safe_float(doc.get(key))
    doc.setdefault("is_locked", False)
    doc.setdefault("entries", [])
    return doc


def safe_float(value, default: float = 0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default
