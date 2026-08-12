from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any

try:
    from .utils import clean, parse_list
except ImportError:  # pragma: no cover
    from utils import clean, parse_list


def analyze_feedback(user_id: str, feedback: list[dict[str, Any]]) -> dict[str, Any]:
    rows = [f for f in feedback if clean(f.get("user_id")) == clean(user_id)]
    sentiments = Counter(clean(f.get("sentiment")) for f in rows)
    actions = Counter(clean(f.get("requested_action")) for f in rows)
    tags = Counter()
    liked, disliked, too_easy, too_hard, pain_related = [], [], [], [], []
    for f in rows:
        ex = clean(f.get("exercise_id"))
        if ex and clean(f.get("exercise_preference")) == "Like":
            liked.append(ex)
        if ex and clean(f.get("exercise_preference")) == "Dislike":
            disliked.append(ex)
        if ex and clean(f.get("difficulty_feedback")) == "Too Easy":
            too_easy.append(ex)
        if ex and clean(f.get("difficulty_feedback")) == "Too Hard":
            too_hard.append(ex)
        if ex and clean(f.get("pain_feedback")) in {"Mild Discomfort", "Pain", "Severe Pain"}:
            pain_related.append(ex)
        tags.update(parse_list(f.get("feedback_reason_tags")))
    return {
        "user_id": user_id,
        "feedback_count": len(rows),
        "sentiment_summary": dict(sentiments),
        "liked_exercises": sorted(set(liked)),
        "disliked_exercises": sorted(set(disliked)),
        "too_easy_exercises": sorted(set(too_easy)),
        "too_hard_exercises": sorted(set(too_hard)),
        "pain_related_exercises": sorted(set(pain_related)),
        "preferred_actions": dict(actions),
        "preference_tags": [k for k, _ in tags.most_common(20)],
        "recent_feedback": rows[-15:],
        "summary": f"{len(rows)} feedback rows; top sentiment/action: {sentiments.most_common(1)}, {actions.most_common(1)}.",
    }

