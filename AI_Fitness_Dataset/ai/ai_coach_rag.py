from __future__ import annotations

from typing import Any


def _pct(value: float) -> str:
    return f"{round(float(value) * 100, 1)}%"


def answer_user_question(question: str, context: dict[str, Any]) -> dict[str, Any]:
    q = question.lower()
    recommendation = context.get("recommendation", {})
    safety = context.get("safety_review", {})
    history = context.get("history_analysis", {})
    action = recommendation.get("recommended_action", "Keep")
    reason_codes = recommendation.get("reason_codes", []) or []
    safety_status = safety.get("safety_status", "Safe")
    risk_flags = safety.get("risk_flags", []) or []
    completion = history.get("completion_rate", 0)
    avg_rpe = history.get("average_rpe", 0)
    fatigue = history.get("average_fatigue", 0)
    pain_rate = history.get("pain_rate", 0)
    if safety.get("safety_status") in {"Avoid", "Review"} or "đau" in q or "pain" in q:
        flags = ", ".join(risk_flags) if risk_flags else "pain/safety signal"
        answer = (
            f"Có tín hiệu cần chú ý an toàn ({flags}), nên không cố tập nặng hôm nay. "
            f"Pain rate hiện là {_pct(pain_rate)}, safety status {safety_status}; hãy giảm tải, kiểm tra kỹ thuật hoặc đổi bài. "
            "Nếu đau rõ hoặc kéo dài, nên hỏi chuyên gia y tế/huấn luyện viên."
        )
    elif "mệt" in q or "tired" in q:
        if action == "Keep":
            answer = (
                f"Dữ liệu gần đây cho thấy bạn vẫn theo được lịch: completion {_pct(completion)}, RPE trung bình {avg_rpe}, fatigue {fatigue}. "
                "Hôm nay có thể giữ buổi tập như kế hoạch, nhưng giữ RPE trong vùng mục tiêu và không cần đẩy thêm."
            )
        elif action == "Reduce Difficulty":
            answer = (
                f"Vì fatigue/RPE hoặc pain signal đang cao hơn mong muốn (RPE {avg_rpe}, fatigue {fatigue}, pain {_pct(pain_rate)}), "
                "hôm nay nên giảm độ khó: giảm tải, giảm RPE mục tiêu hoặc chọn biến thể dễ kiểm soát hơn."
            )
        elif action == "Review Safety":
            answer = (
                f"Recommendation hiện là Review Safety với reason codes {reason_codes}. "
                "Hôm nay nên giảm tải rõ rệt hoặc đổi bài, không tăng độ khó cho tới khi kiểm tra lại kỹ thuật và vùng đau."
            )
        else:
            answer = (
                f"Recommendation hiện là {action}. Completion {_pct(completion)}, RPE {avg_rpe}, fatigue {fatigue}; "
                "hãy điều chỉnh buổi hôm nay theo action này thay vì cố vượt kế hoạch."
            )
    elif "đổi bài" in q or "replace" in q:
        answer = (
            f"Có thể đổi bài nếu action là {action} hoặc reason codes có tín hiệu không hợp bài: {reason_codes}. "
            f"Bài thay thế vẫn cần safety status Safe/Monitor, khớp mục tiêu và thiết bị hiện có."
        )
    else:
        answer = (
            f"Khuyến nghị hiện tại là {action}. Dữ liệu chính: completion {_pct(completion)}, RPE trung bình {avg_rpe}, "
            f"fatigue {fatigue}, pain rate {_pct(pain_rate)}, safety status {safety_status}, reason codes {reason_codes}."
        )
    return {
        "answer": answer,
        "recommendation": recommendation,
        "safety_notes": safety.get("risk_flags", []),
        "data_used": ["User Profile", "Workout Plan", "Workout History", "User Feedback", "Exercise Master", "Safety Review"],
        "confidence": recommendation.get("confidence", 0.7),
        "disclaimer": "Thông tin này chỉ hỗ trợ tập luyện, không thay thế tư vấn y tế hoặc chẩn đoán chuyên môn.",
    }
