from flask import Blueprint, abort, jsonify, request, send_from_directory

from services.ml_integration_service import MLIntegrationService
from utils.path_utils import AI_DIR


ml_bp = Blueprint("ml_bp", __name__, url_prefix="/api/ml")
ml_service = MLIntegrationService()


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


@ml_bp.route("/exercise-image/<path:filename>", methods=["GET"])
def exercise_image(filename):
    image_dir = AI_DIR / "image" / "flat"
    target = image_dir / filename
    if not target.is_file() or target.parent.resolve() != image_dir.resolve():
        abort(404)
    return send_from_directory(image_dir, filename)

