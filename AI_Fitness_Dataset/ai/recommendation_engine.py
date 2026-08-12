from __future__ import annotations

from collections import Counter
from typing import Any

try:
    from .utils import clean, to_float
except ImportError:  # pragma: no cover
    from utils import clean, to_float


def _pct(value: float) -> str:
    return f"{round(value * 100, 1)}%"


def build_recommendation_explanation(
    action: str,
    reason_codes: list[str],
    history: dict[str, Any],
    recent_feedback: list[dict[str, Any]],
    safety: dict[str, Any],
) -> str:
    completion = float(history.get("completion_rate", 0))
    avg_rpe = float(history.get("average_rpe", 0))
    fatigue = float(history.get("average_fatigue", 0))
    pain_rate = float(history.get("pain_rate", 0))
    sentiments = Counter(clean(f.get("sentiment")) for f in recent_feedback)
    difficulty = Counter(clean(f.get("difficulty_feedback")) for f in recent_feedback)
    risk_flags = safety.get("risk_flags", []) or []
    codes = ", ".join(reason_codes) if reason_codes else "NO_MAJOR_SIGNAL"

    if action == "Review Safety":
        flags = ", ".join(risk_flags) if risk_flags else codes
        return (
            f"Cần review an toàn vì phát hiện {flags}. Completion hiện tại là {_pct(completion)}, "
            f"pain rate {_pct(pain_rate)}, RPE trung bình {avg_rpe}. Không nên tăng độ khó cho đến khi kiểm tra kỹ thuật hoặc đổi bài phù hợp hơn."
        )
    if action == "Reduce Difficulty":
        return (
            f"Khuyến nghị giảm độ khó vì có tín hiệu {codes}. Completion hiện tại là {_pct(completion)}, "
            f"RPE trung bình {avg_rpe}, fatigue trung bình {fatigue}, pain rate {_pct(pain_rate)}."
        )
    if action == "Increase Difficulty":
        return (
            f"Có thể tăng độ khó nhẹ vì user hoàn thành tốt với completion {_pct(completion)}, RPE trung bình {avg_rpe}, "
            f"fatigue {fatigue}, và có {difficulty.get('Too Easy', 0)} feedback báo bài hơi dễ."
        )
    if action == "Reduce Volume":
        return (
            f"Khuyến nghị giảm volume vì {codes}. Completion {_pct(completion)}, skipped rate {_pct(float(history.get('skipped_rate', 0)))}, "
            f"fatigue trung bình {fatigue}."
        )
    if action == "Replace Exercise":
        return (
            f"Khuyến nghị thay bài vì feedback tiêu cực hoặc yêu cầu đổi bài xuất hiện. Positive={sentiments.get('Positive', 0)}, "
            f"Neutral={sentiments.get('Neutral', 0)}, Negative={sentiments.get('Negative', 0)}; reason codes: {codes}."
        )
    if action == "Keep":
        return (
            f"Khuyến nghị giữ nguyên vì adherence ổn: completion {_pct(completion)}, RPE trung bình {avg_rpe}, "
            f"fatigue {fatigue}, positive feedback {sentiments.get('Positive', 0)} so với negative {sentiments.get('Negative', 0)}."
        )
    return f"Khuyến nghị {action} dựa trên reason codes {codes}, completion {_pct(completion)}, RPE {avg_rpe}, fatigue {fatigue}."


def recommend_action(payload: dict[str, Any]) -> dict[str, Any]:
    history = payload.get("history_summary", {}) or {}
    recent_feedback = payload.get("recent_feedback", []) or []
    safety = payload.get("safety_review", {}) or {}
    reason_codes: list[str] = []
    safety_flags = list(safety.get("risk_flags", []))
    sentiments = Counter(clean(f.get("sentiment")) for f in recent_feedback)
    difficulty = Counter(clean(f.get("difficulty_feedback")) for f in recent_feedback)
    actions = Counter(clean(f.get("requested_action")) for f in recent_feedback)
    pain_feedback = [clean(f.get("pain_feedback")) for f in recent_feedback]
    completion = float(history.get("completion_rate", 0))
    skipped = float(history.get("skipped_rate", 0))
    avg_rpe = float(history.get("average_rpe", 0))
    fatigue = float(history.get("average_fatigue", 0))
    pain_rate = float(history.get("pain_rate", 0))

    if safety.get("safety_status") in {"Avoid", "Review"} or any(p in {"Pain", "Severe Pain"} for p in pain_feedback):
        action = "Review Safety"
        reason_codes += ["PAIN_REPORTED", *safety_flags]
        confidence = 0.95
    elif "Mild Discomfort" in pain_feedback or pain_rate > 0.05:
        action = "Reduce Difficulty"
        reason_codes += ["MILD_DISCOMFORT", "PAIN_RATE_ELEVATED"]
        confidence = 0.84
    elif difficulty.get("Too Easy", 0) > 0 and completion >= 0.9 and avg_rpe <= 7.5 and fatigue <= 3:
        action = "Increase Difficulty"
        reason_codes += ["TOO_EASY", "GOOD_ADHERENCE", "LOW_RPE"]
        confidence = 0.82
    elif difficulty.get("Too Hard", 0) > 0 or avg_rpe >= 8.5 or fatigue >= 4:
        action = "Reduce Difficulty"
        reason_codes += ["TOO_HARD", "HIGH_RPE" if avg_rpe >= 8.5 else "HIGH_FATIGUE"]
        confidence = 0.8
    elif actions.get("Replace Exercise", 0) > 0 or sentiments.get("Negative", 0) > sentiments.get("Positive", 0):
        action = "Replace Exercise"
        reason_codes += ["USER_DISLIKES_EXERCISE", "NEGATIVE_FEEDBACK"]
        confidence = 0.74
    elif skipped > 0.12 or actions.get("Reduce Session Duration", 0) > 0:
        action = "Reduce Volume"
        reason_codes += ["LOW_COMPLETION", "DURATION_TOO_LONG"]
        confidence = 0.72
    elif completion >= 0.8 and 6 <= avg_rpe <= 8 and sentiments.get("Positive", 0) >= sentiments.get("Negative", 0):
        action = "Keep"
        reason_codes += ["GOOD_ADHERENCE", "POSITIVE_FEEDBACK"]
        confidence = 0.78
    else:
        action = "Keep"
        reason_codes += ["INSUFFICIENT_RISK_SIGNAL"]
        confidence = 0.62

    reason_codes = sorted(set(reason_codes))
    return {
        "recommended_action": action,
        "confidence": round(confidence, 2),
        "reason_codes": reason_codes,
        "explanation": build_recommendation_explanation(action, reason_codes, history, recent_feedback, safety),
        "safety_flags": sorted(set(safety_flags)),
        "target_changes": [{"action": action, "scope": "exercise_or_plan", "reason": ",".join(reason_codes)}],
    }
