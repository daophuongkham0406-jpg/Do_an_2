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
    {"keys": ["trung", "trứng", "egg"], "name": "Trứng", "protein_per_100g": 13, "calories_per_100g": 155, "carbs_per_100g": 1.1, "fat_per_100g": 11},
    {"keys": ["bo", "bò", "beef"], "name": "Thịt bò nạc", "protein_per_100g": 26, "calories_per_100g": 217, "carbs_per_100g": 0, "fat_per_100g": 12},
    {"keys": ["ca hoi", "cá hồi", "salmon"], "name": "Cá hồi", "protein_per_100g": 20, "calories_per_100g": 208, "carbs_per_100g": 0, "fat_per_100g": 13},
    {"keys": ["com", "cơm", "rice"], "name": "Cơm trắng", "protein_per_100g": 2.7, "calories_per_100g": 130, "carbs_per_100g": 28, "fat_per_100g": 0.3},
]


@nutrition_bp.route("/api/analyze-food", methods=["POST"])
def analyze_food():
    data = request.json or {}
    food_text = str(data.get("food_text") or data.get("foodText") or "").strip()
    if not food_text:
        return jsonify({"success": False, "error": "Thiếu mô tả món ăn"}), 400

    ai_result = analyze_food_with_gemini(food_text)
    result = ai_result or analyze_food_fallback(food_text)
    if not result:
        return jsonify({"success": False, "error": "Chưa phân tích được món ăn này"}), 400
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
Phân tích dinh dưỡng cho món ăn sau bằng tiếng Việt: {food_text}
Chỉ trả về JSON hợp lệ, không markdown:
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
    lowered = food_text.lower()
    grams = extract_grams(lowered)
    matches = [food for food in FOOD_FALLBACKS if any(key in lowered for key in food["keys"])]
    if not matches:
        return None

    items = []
    total = {"calories": 0, "protein": 0, "carbs": 0, "fat": 0}
    for food in matches:
        factor = grams / 100
        item = {
            "name": food["name"],
            "amount": f"{grams:g}g",
            "calories": round(food["calories_per_100g"] * factor, 1),
            "protein": round(food["protein_per_100g"] * factor, 1),
            "carbs": round(food["carbs_per_100g"] * factor, 1),
            "fat": round(food["fat_per_100g"] * factor, 1),
        }
        items.append(item)
        for key in total:
            total[key] += item[key]
    total = {key: round(value, 1) for key, value in total.items()}
    return {
        "summary": f"Ước tính theo dữ liệu dinh dưỡng phổ biến cho {food_text}.",
        "items": items,
        "total": total,
    }


def extract_grams(text: str) -> float:
    kg_match = re.search(r"(\d+(?:[.,]\d+)?)\s*kg", text)
    if kg_match:
        return float(kg_match.group(1).replace(",", ".")) * 1000
    gram_match = re.search(r"(\d+(?:[.,]\d+)?)\s*g", text)
    if gram_match:
        return float(gram_match.group(1).replace(",", "."))
    return 100


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
