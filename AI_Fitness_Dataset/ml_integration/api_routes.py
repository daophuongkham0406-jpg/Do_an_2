from __future__ import annotations

from pathlib import Path
from typing import Any


try:
    from flask import Blueprint, jsonify, request
except Exception:  # pragma: no cover
    Blueprint = None
    jsonify = None
    request = None


def recommend_action_ml(payload: dict[str, Any]) -> dict[str, Any]:
    return {"status": "NOT_CONNECTED", "message": "Use integration_pipeline.py or wire this mock to your app service."}


def check_safety_ml(payload: dict[str, Any]) -> dict[str, Any]:
    return {"status": "NOT_CONNECTED", "message": "Safety ML is auxiliary; Rule-Based Safety Lock remains final."}


def predict_preference_ml(payload: dict[str, Any]) -> dict[str, Any]:
    return {"status": "NOT_CONNECTED", "message": "Preference model requires feedback-like features for reliable use."}


def final_decision_ml(payload: dict[str, Any]) -> dict[str, Any]:
    return {"status": "NOT_CONNECTED", "message": "Call ml_integration.integration_pipeline.run_for_user in backend service."}


def integration_test_ml(payload: dict[str, Any]) -> dict[str, Any]:
    return {"status": "NOT_CONNECTED", "message": "Run python ml_integration/integration_pipeline.py --sample-size 100."}


if Blueprint is not None:
    ml_bp = Blueprint("ml_integration", __name__)

    @ml_bp.route("/api/ml/recommend-action", methods=["POST"])
    def recommend_action_route():
        return jsonify(recommend_action_ml(request.get_json(silent=True) or {}))

    @ml_bp.route("/api/ml/check-safety", methods=["POST"])
    def check_safety_route():
        return jsonify(check_safety_ml(request.get_json(silent=True) or {}))

    @ml_bp.route("/api/ml/predict-preference", methods=["POST"])
    def predict_preference_route():
        return jsonify(predict_preference_ml(request.get_json(silent=True) or {}))

    @ml_bp.route("/api/ml/final-decision", methods=["POST"])
    def final_decision_route():
        return jsonify(final_decision_ml(request.get_json(silent=True) or {}))

    @ml_bp.route("/api/ml/integration-test", methods=["POST"])
    def integration_test_route():
        return jsonify(integration_test_ml(request.get_json(silent=True) or {}))
else:
    ml_bp = None
