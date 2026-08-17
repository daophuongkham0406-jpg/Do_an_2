import base64
import csv
import re
import unicodedata
from datetime import datetime

from flask import Blueprint, abort, jsonify, request, send_from_directory

from services.ml_integration_service import MLIntegrationService
from utils.path_utils import AI_DIR


ml_bp = Blueprint("ml_bp", __name__, url_prefix="/api/ml")
ml_service = MLIntegrationService()

EXERCISE_FIELDS = [
    "id", "name_en", "name_de", "name_es", "category", "force_type", "mechanic",
    "difficulty", "equipment", "body_part", "primary_muscles", "secondary_muscles",
    "goals", "tags", "met", "is_unilateral", "is_bodyweight", "description_en",
    "instructions_en", "image_flat_start", "image_flat_peak", "image_flat_main",
    "instructions_vi",
]

MUSCLE_TO_KEYS = {
    "Ngực": ("chest", "pectoralis_major"),
    "Lưng": ("back", "latissimus_dorsi"),
    "Vai": ("shoulders", "deltoids"),
    "Tay trước": ("upper_arms", "biceps_brachii"),
    "Tay sau": ("upper_arms", "triceps_brachii"),
    "Chân": ("upper_legs", "quadriceps"),
    "Mông": ("upper_legs", "gluteus_maximus"),
    "Bụng": ("core", "rectus_abdominis"),
    "Core": ("core", "rectus_abdominis"),
    "Toàn thân": ("full_body", "full_body"),
}

DIFFICULTY_TO_KEY = {"B": "beginner", "I": "intermediate", "A": "advanced"}


def slugify(value):
    text = unicodedata.normalize("NFKD", str(value or "").strip().lower())
    text = "".join(char for char in text if not unicodedata.combining(char))
    text = text.replace("đ", "d")
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-") or f"exercise-{datetime.now().strftime('%Y%m%d%H%M%S')}"


def unique_exercise_id(name, existing_rows):
    existing = {row.get("id") for row in existing_rows}
    base = slugify(name)
    candidate = base
    index = 2
    while candidate in existing:
        candidate = f"{base}-{index}"
        index += 1
    return candidate


def save_uploaded_image(image_data, exercise_id):
    if not image_data or not str(image_data).startswith("data:image/"):
        return ""
    header, encoded = image_data.split(",", 1)
    match = re.search(r"data:image/([a-zA-Z0-9+.-]+);base64", header)
    ext = (match.group(1) if match else "webp").lower().replace("jpeg", "jpg")
    if ext not in {"jpg", "png", "webp"}:
        ext = "webp"
    image_dir = AI_DIR / "image" / "flat"
    image_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{exercise_id}-admin.{ext}"
    (image_dir / filename).write_bytes(base64.b64decode(encoded))
    return f"images/flat/{filename}"


def step_to_text(step):
    if isinstance(step, dict):
        return str(step.get("d") or step.get("description") or step.get("t") or "").strip()
    return str(step or "").strip()


@ml_bp.route("/health", methods=["GET"])
def health():
    return jsonify({
        "status": "OK",
        "message": "ML API is running",
        "source": "ai_exercises_csv_rule_engine",
    }), 200


@ml_bp.route("/generate-plan", methods=["POST"])
def generate_plan():
    data = request.get_json() or {}
    required_fields = ["goal", "level", "height", "weight", "age"]
    missing = [field for field in required_fields if data.get(field) in [None, ""]]

    if missing:
        return jsonify({
            "status": "ERROR",
            "message": "Missing required fields",
            "missing_fields": missing,
        }), 400

    try:
        return jsonify(ml_service.generate_plan(data)), 200
    except Exception as exc:
        return jsonify({
            "status": "ERROR",
            "message": str(exc),
        }), 500


@ml_bp.route("/exercises", methods=["GET"])
def exercises():
    try:
        items = [
            ml_service._format_exercise(row, "hypertrophy", 1, index + 1, "LIBRARY")
            for index, row in enumerate(ml_service._load_exercises())
        ]
        return jsonify({
            "success": True,
            "source": "AI/exercises.csv",
            "data": items,
            "total": len(items),
        }), 200
    except Exception as exc:
        return jsonify({"success": False, "message": str(exc)}), 500


@ml_bp.route("/exercises", methods=["POST"])
def add_exercise():
    data = request.get_json() or {}
    name = str(data.get("name") or data.get("name_en") or "").strip()
    muscle_label = str(data.get("muscle") or "").strip()
    difficulty_key = str(data.get("diff") or data.get("difficulty") or "").strip()
    category = str(data.get("category") or data.get("equip") or "").strip()
    goals = data.get("goals") or data.get("goal") or []
    secondary = data.get("secondary_muscles") or data.get("sec") or []
    steps = data.get("steps") or []

    if not name or not muscle_label or not difficulty_key or not category or not goals:
        return jsonify({
            "success": False,
            "message": "Thiếu tên bài, nhóm cơ, độ khó, loại bài hoặc mục tiêu.",
        }), 400

    if isinstance(goals, str):
        goals = [item.strip() for item in goals.replace(";", "|").split("|") if item.strip()]
    if isinstance(secondary, str):
        secondary = [item.strip() for item in secondary.replace(";", "|").split("|") if item.strip()]

    try:
        existing_rows = ml_service._load_exercises()
        exercise_id = unique_exercise_id(name, existing_rows)
        body_part, primary_muscle = MUSCLE_TO_KEYS.get(muscle_label, (slugify(muscle_label), slugify(muscle_label)))
        image_path = save_uploaded_image(data.get("image"), exercise_id)
        instructions_vi = " | ".join(text for text in (step_to_text(step) for step in steps) if text)

        row = {field: "" for field in EXERCISE_FIELDS}
        row.update({
            "id": exercise_id,
            "name_en": name,
            "category": category,
            "force_type": data.get("force_type") or "",
            "mechanic": data.get("mechanic") or "compound",
            "difficulty": DIFFICULTY_TO_KEY.get(difficulty_key, difficulty_key),
            "equipment": "",
            "body_part": body_part,
            "primary_muscles": primary_muscle,
            "secondary_muscles": "|".join(slugify(item).replace("-", "_") for item in secondary),
            "goals": "|".join(goals),
            "tags": data.get("tags") or "admin_added",
            "met": data.get("met") or "5.0",
            "is_unilateral": "False",
            "is_bodyweight": "False",
            "description_en": data.get("description") or "",
            "instructions_en": "",
            "image_flat_start": image_path,
            "image_flat_peak": "",
            "image_flat_main": "",
            "instructions_vi": instructions_vi,
        })

        file_exists = ml_service.exercise_path.exists()
        with ml_service.exercise_path.open("a", encoding="utf-8-sig", newline="") as file:
            writer = csv.DictWriter(file, fieldnames=EXERCISE_FIELDS)
            if not file_exists or ml_service.exercise_path.stat().st_size == 0:
                writer.writeheader()
            writer.writerow(row)

        formatted = ml_service._format_exercise(row, "hypertrophy", 1, len(existing_rows) + 1, "LIBRARY")
        return jsonify({"success": True, "data": formatted, "total": len(existing_rows) + 1}), 201
    except Exception as exc:
        return jsonify({"success": False, "message": str(exc)}), 500


@ml_bp.route("/exercise-image/<path:filename>", methods=["GET"])
def exercise_image(filename):
    image_dir = AI_DIR / "image" / "flat"
    target = image_dir / filename
    if not target.is_file() or target.parent.resolve() != image_dir.resolve():
        abort(404)
    return send_from_directory(image_dir, filename)

