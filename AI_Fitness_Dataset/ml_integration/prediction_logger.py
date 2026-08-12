from __future__ import annotations

from datetime import datetime
from typing import Any

import pandas as pd

from .schema import LOG_COLUMNS


def build_log_row(prediction_id: str, decision: dict[str, Any], plan_id: str) -> dict[str, Any]:
    ml_rec = decision.get("ml_recommendation", {})
    ml_pref = decision.get("ml_preference", {})
    ml_safe = decision.get("ml_safety", {})
    rule_rec = decision.get("rule_based_recommendation", {})
    rule_safe = decision.get("rule_safety_review", {})
    lock = decision.get("safety_lock", {})
    return {
        "prediction_id": prediction_id,
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "user_id": decision.get("user_id", ""),
        "plan_id": plan_id,
        "exercise_id": decision.get("exercise_id", ""),
        "raw_ml_recommendation": ml_rec.get("raw_prediction", ""),
        "ml_recommendation_confidence": ml_rec.get("confidence", 0),
        "ml_preference_prediction": ml_pref.get("raw_prediction", ""),
        "ml_preference_confidence": ml_pref.get("confidence", 0),
        "ml_safety_prediction": ml_safe.get("raw_prediction", ""),
        "ml_safety_confidence": ml_safe.get("confidence", 0),
        "rule_based_action": rule_rec.get("recommended_action", ""),
        "rule_safety_status": rule_safe.get("safety_status", ""),
        "risk_score": rule_safe.get("risk_score", 0),
        "final_action": decision.get("final_action", ""),
        "was_overridden": lock.get("was_overridden", False),
        "override_reason": lock.get("override_reason", ""),
        "decision_source": decision.get("decision_source", ""),
        "user_feedback_after_action": "",
    }


def write_prediction_log(rows: list[dict[str, Any]], path: str) -> None:
    pd.DataFrame(rows, columns=LOG_COLUMNS).to_csv(path, index=False, encoding="utf-8-sig")
