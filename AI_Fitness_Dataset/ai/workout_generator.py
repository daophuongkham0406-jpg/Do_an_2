from __future__ import annotations

from collections import defaultdict
from typing import Any

import pandas as pd

try:
    from .config import LEVEL_RANK, VOLUME_RULES
    from .safety_review_engine import review_safety
    from .utils import clean, parse_list
except ImportError:  # pragma: no cover
    from config import LEVEL_RANK, VOLUME_RULES
    from safety_review_engine import review_safety
    from utils import clean, parse_list


def equipment_ok(user_equipment: list[str], exercise_equipment: list[str]) -> bool:
    if not exercise_equipment:
        return True
    allowed = {x.lower() for x in user_equipment + ["Bodyweight", "None"]}
    return all(e.lower() in allowed or "bodyweight" in e.lower() for e in exercise_equipment)


def goal_ok(goal: str, recommended_goals: list[str]) -> bool:
    if not recommended_goals:
        return True
    g = goal.lower()
    return any(g in x.lower() or x.lower() in g for x in recommended_goals)


def _tokens(*values: Any) -> set[str]:
    out: set[str] = set()
    for value in values:
        for item in parse_list(value):
            low = item.lower()
            out.add(low)
            out.update(part for part in low.replace("-", " ").split() if part)
    return out


def infer_session_targets(split: str, day_number: int, days: int) -> list[str]:
    name = split.lower()
    if "push" in name and "pull" in name and "leg" in name:
        cycle = ["push", "pull", "legs"]
        target = cycle[(day_number - 1) % len(cycle)]
        if target == "push":
            return ["push", "horizontal push", "vertical push", "chest", "shoulder", "triceps"]
        if target == "pull":
            return ["pull", "horizontal pull", "vertical pull", "back", "rear delt", "biceps"]
        return ["legs", "squat", "lunge", "hinge", "quad", "hamstring", "glute", "calf", "core"]
    if "upper" in name or ("lower" in name and days >= 4):
        if day_number % 2 == 1:
            return ["upper", "horizontal push", "vertical push", "horizontal pull", "vertical pull", "shoulder", "arm", "core"]
        return ["lower", "squat", "lunge", "hinge", "quad", "hamstring", "glute", "calf", "core"]
    return ["lower", "push", "pull", "core", "accessory"]


def score_exercise_for_session(exercise: dict[str, Any], user_profile: dict[str, Any], session_targets: list[str]) -> float:
    target_tokens = {t.lower() for t in session_targets}
    ex_tokens = _tokens(
        exercise.get("movement_pattern"),
        exercise.get("primary_muscles"),
        exercise.get("secondary_muscles"),
        exercise.get("body_region"),
        exercise.get("force_type"),
        exercise.get("category"),
    )
    score = 0.0
    for target in target_tokens:
        if target in ex_tokens or any(target in tok or tok in target for tok in ex_tokens):
            score += 3.0
    priority = _tokens(user_profile.get("priority_muscles"))
    avoided = _tokens(user_profile.get("avoided_muscles"))
    if priority & ex_tokens:
        score += 1.0
    if avoided & ex_tokens:
        score -= 2.0
    if clean(exercise.get("safety_status")) == "Safe":
        score += 0.8
    elif clean(exercise.get("safety_status")) == "Monitor":
        score += 0.4
    elif clean(exercise.get("safety_status")) == "Review":
        score -= 1.0
    return score


def _role_for_exercise(exercise: dict[str, Any]) -> str:
    tokens = _tokens(
        exercise.get("movement_pattern"),
        exercise.get("primary_muscles"),
        exercise.get("secondary_muscles"),
        exercise.get("body_region"),
        exercise.get("force_type"),
    )
    if {"squat", "lunge", "hinge", "quad", "quadriceps", "hamstring", "glute", "calf", "lower"} & tokens:
        return "lower"
    if {"push", "chest", "pectoralis", "shoulder", "deltoid", "triceps"} & tokens:
        return "push"
    if {"pull", "back", "latissimus", "rhomboid", "trapezius", "biceps", "rear"} & tokens:
        return "pull"
    if {"core", "abdominis", "oblique", "anti", "plank"} & tokens:
        return "core"
    return "accessory"


def _is_repeatable_basic(exercise: dict[str, Any]) -> bool:
    tokens = _tokens(exercise.get("equipment"), exercise.get("primary_muscles"), exercise.get("movement_pattern"))
    return bool({"bodyweight", "core", "abdominis", "plank"} & tokens)


def _build_selected(exercise: dict[str, Any], rules: dict[str, int], goal: str, reason: str) -> dict[str, Any]:
    return {
        "exercise_id": clean(exercise.get("exercise_id")),
        "exercise_name": clean(exercise.get("exercise_name")),
        "sets": rules["sets"],
        "rep_min": 8 if goal != "Strength" else 4,
        "rep_max": 12 if goal != "Strength" else 8,
        "target_rpe": rules["rpe"],
        "rest_seconds": rules["rest"],
        "reason": reason,
    }


def generate_workout_plan(user_profile: dict[str, Any], exercises: pd.DataFrame) -> dict[str, Any]:
    level = clean(user_profile.get("training_level")) or "Beginner"
    rules = VOLUME_RULES.get(level, VOLUME_RULES["Beginner"])
    days = int(float(clean(user_profile.get("training_days_per_week")) or clean(user_profile.get("available_days")) or 3))
    days = max(1, min(6, days))
    split = clean(user_profile.get("preferred_split")) or ("Full Body" if days <= 3 else "Upper Lower")
    goal = clean(user_profile.get("primary_goal")) or "General Fitness"
    equipment = parse_list(user_profile.get("available_equipment"))
    user_rank = LEVEL_RANK.get(level, 1)
    candidates = []
    review_candidates = []
    safety_notes = []
    for _, row in exercises.iterrows():
        ex = row.to_dict()
        ex_rank = LEVEL_RANK.get(clean(ex.get("minimum_training_level")), 1)
        if ex_rank > user_rank + 1:
            continue
        if not equipment_ok(equipment, parse_list(ex.get("equipment"))):
            continue
        if not goal_ok(goal, parse_list(ex.get("recommended_goals"))):
            continue
        safety = review_safety(user_profile, ex)
        if safety["safety_status"] == "Avoid":
            safety_notes.append({"exercise_id": ex.get("exercise_id"), "reason": safety["risk_flags"]})
            continue
        ex["safety_status"] = safety["safety_status"]
        ex["risk_flags"] = safety["risk_flags"]
        if safety["safety_status"] == "Review":
            review_candidates.append(ex)
            continue
        candidates.append(ex)
    if not candidates:
        candidates = review_candidates or exercises.head(20).to_dict(orient="records")
    sessions = []
    repeat_counts: dict[str, int] = defaultdict(int)
    for day in range(1, days + 1):
        max_ex = rules["max_exercises"]
        selected = []
        selected_ids: set[str] = set()
        targets = infer_session_targets(split, day, days)
        target_queue = targets[:max_ex]
        ranked = sorted(
            candidates,
            key=lambda ex: score_exercise_for_session(ex, user_profile, targets),
            reverse=True,
        )
        for target in target_queue:
            if len(selected) >= max_ex:
                break
            target_ranked = sorted(
                ranked,
                key=lambda ex, t=target: (
                    score_exercise_for_session(ex, user_profile, [t]),
                    score_exercise_for_session(ex, user_profile, targets),
                ),
                reverse=True,
            )
            for ex in target_ranked:
                eid = clean(ex.get("exercise_id"))
                if not eid or eid in selected_ids:
                    continue
                if repeat_counts[eid] >= 2 and not _is_repeatable_basic(ex):
                    continue
                role = _role_for_exercise(ex)
                if role in {_role_for_exercise(s) for s in selected} and len(selected) < min(4, max_ex):
                    continue
                selected.append(ex)
                selected_ids.add(eid)
                repeat_counts[eid] += 1
                break
        if len(selected) < rules["min_exercises"]:
            for ex in ranked + review_candidates:
                eid = clean(ex.get("exercise_id"))
                if not eid or eid in selected_ids:
                    continue
                if repeat_counts[eid] >= 2 and not _is_repeatable_basic(ex):
                    continue
                if clean(ex.get("safety_status")) == "Review":
                    safety_notes.append({"exercise_id": eid, "reason": "Review candidate used because safe choices were insufficient."})
                selected.append(ex)
                selected_ids.add(eid)
                repeat_counts[eid] += 1
                if len(selected) >= rules["min_exercises"]:
                    break
        selected_items = [
            _build_selected(ex, rules, goal, "Matched session target balance, goal, level, equipment and safety filters.")
            for ex in selected
        ]
        focus = sorted({_role_for_exercise(ex) for ex in selected})
        sessions.append({"day_number": day, "session_name": f"{split} Day {day}", "focus_muscles": focus, "session_targets": targets, "exercises": selected_items})
    return {
        "plan_name": f"{level} {goal} {days}-Day Plan",
        "user_id": clean(user_profile.get("user_id")),
        "days_per_week": days,
        "split_type": split,
        "sessions": sessions,
        "safety_notes": safety_notes[:20],
        "generation_summary": {"candidate_count": len(candidates), "review_candidate_count": len(review_candidates), "safety_exclusions": len(safety_notes)},
    }
