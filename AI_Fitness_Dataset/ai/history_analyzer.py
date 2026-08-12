from __future__ import annotations

from collections import Counter
from typing import Any

try:
    from .utils import clean, parse_list, pct, to_float
except ImportError:  # pragma: no cover
    from utils import clean, parse_list, pct, to_float


def analyze_history(user_id: str, history_sessions: list[dict[str, Any]], history_items: list[dict[str, Any]]) -> dict[str, Any]:
    sessions = [s for s in history_sessions if clean(s.get("user_id")) == clean(user_id)]
    items = [i for i in history_items if clean(i.get("user_id")) == clean(user_id)]
    status = Counter(clean(s.get("completion_status")) for s in sessions)
    session_count = len(sessions)
    rpes = [to_float(s.get("session_rpe")) for s in sessions if clean(s.get("session_rpe"))]
    fatigue = [to_float(s.get("fatigue_after")) for s in sessions if clean(s.get("fatigue_after"))]
    pain_sessions = [s for s in sessions if clean(s.get("pain_reported")) == "Yes"]
    pain_areas = Counter()
    for s in pain_sessions:
        pain_areas.update(parse_list(s.get("pain_areas")))
    recent = sessions[-5:]
    first_half = sessions[: max(1, len(sessions) // 2)]
    last_half = sessions[max(0, len(sessions) // 2):]
    first_completion = sum(to_float(s.get("completion_pct")) for s in first_half) / max(1, len(first_half))
    last_completion = sum(to_float(s.get("completion_pct")) for s in last_half) / max(1, len(last_half))
    trend = "improving" if last_completion > first_completion + 3 else "declining" if last_completion < first_completion - 3 else "stable"
    risk_flags = []
    if pct(status.get("Skipped", 0), session_count) > 0.12:
        risk_flags.append("HIGH_SKIP_RATE")
    if pct(len(pain_sessions), session_count) > 0.05:
        risk_flags.append("PAIN_RATE_ELEVATED")
    if fatigue and sum(fatigue) / len(fatigue) >= 4:
        risk_flags.append("HIGH_FATIGUE")
    planned_sets = sum(to_float(i.get("planned_sets")) for i in items)
    actual_sets = sum(to_float(i.get("actual_sets_completed")) for i in items)
    return {
        "user_id": user_id,
        "session_count": session_count,
        "completion_rate": pct(status.get("Completed", 0), session_count),
        "set_completion_rate": pct(actual_sets, planned_sets),
        "skipped_rate": pct(status.get("Skipped", 0), session_count),
        "partial_rate": pct(status.get("Partial", 0), session_count),
        "average_rpe": round(sum(rpes) / len(rpes), 2) if rpes else 0.0,
        "average_fatigue": round(sum(fatigue) / len(fatigue), 2) if fatigue else 0.0,
        "pain_rate": pct(len(pain_sessions), session_count),
        "pain_areas": [k for k, _ in pain_areas.most_common(10)],
        "trend": trend,
        "risk_flags": risk_flags,
        "recent_sessions": recent,
        "summary": f"{session_count} sessions, completion {pct(status.get('Completed', 0), session_count):.2f}, trend {trend}.",
    }

