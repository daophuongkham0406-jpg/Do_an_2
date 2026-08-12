from __future__ import annotations

import argparse
import csv
import json
import math
import shutil
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd
from openpyxl import load_workbook


ROOT = Path(__file__).resolve().parent
MASTER = ROOT / "master"
REPORTS = ROOT / "reports" / "feedback_enrichment"

FEEDBACK_HEADERS = [
    "feedback_id", "user_id", "plan_id", "history_session_id", "history_item_id",
    "plan_item_id", "exercise_id", "feedback_scope", "feedback_type", "rating",
    "sentiment", "difficulty_feedback", "enjoyment_rating", "fatigue_feedback",
    "pain_feedback", "pain_areas", "duration_feedback", "exercise_preference",
    "progression_preference", "requested_action", "feedback_text",
    "feedback_reason_tags", "source_context", "feedback_status", "record_source",
    "is_synthetic", "created_at", "updated_at",
]


def clean(v: Any) -> str:
    if v is None:
        return ""
    if isinstance(v, float) and math.isnan(v):
        return ""
    return str(v).strip()


def parse_list(v: Any) -> list[str]:
    s = clean(v)
    if not s or s in {"[]", "null", "None"}:
        return []
    if s.startswith("[") and s.endswith("]"):
        try:
            data = json.loads(s)
            if isinstance(data, list):
                return [clean(x) for x in data if clean(x)]
        except Exception:
            inner = s[1:-1].strip()
            return [x.strip().strip("'\"") for x in inner.split(",") if x.strip()]
    if "," in s:
        return [x.strip() for x in s.split(",") if x.strip()]
    return [s]


def jarr(values: list[str]) -> str:
    return json.dumps([v for v in values if clean(v)], ensure_ascii=False)


def seed(text: Any) -> int:
    s = clean(text)
    h = 2166136261
    for ch in s:
        h ^= ord(ch)
        h = (h * 16777619) & 0xFFFFFFFF
    return h


def next_feedback_id(existing: pd.Series) -> int:
    max_id = 0
    for value in existing:
        s = clean(value)
        if s.startswith("FB"):
            try:
                max_id = max(max_id, int(s[2:]))
            except ValueError:
                pass
    return max_id + 1


def feedback_id(n: int) -> str:
    return f"FB{n:08d}"


def text_for(row: dict[str, Any], variant_key: str) -> str:
    scope = clean(row.get("feedback_scope"))
    sentiment = clean(row.get("sentiment"))
    action = clean(row.get("requested_action"))
    difficulty = clean(row.get("difficulty_feedback"))
    pain = clean(row.get("pain_feedback"))
    duration = clean(row.get("duration_feedback"))
    exercise = clean(row.get("exercise_name_snapshot")) or clean(row.get("exercise_id")) or "bài này"
    rating = clean(row.get("rating"))
    tags = ", ".join(parse_list(row.get("feedback_reason_tags"))[:2])
    areas = ", ".join(parse_list(row.get("pain_areas"))[:2])
    n = seed(clean(row.get("feedback_id")) + variant_key) % 12
    context_phrases = [
        "ở lần ghi nhận gần đây",
        "trong buổi tập này",
        "khi theo giáo án hiện tại",
        "sau vài set đầu",
        "ở phần cuối buổi",
        "khi so với khả năng hiện tại",
        "trong nhịp tập tuần này",
        "khi xét cảm giác phục hồi",
        "sau khi hoàn thành phần chính",
        "trong lần đánh giá hôm nay",
        "khi tập với mức hiện tại",
        "ở bối cảnh lịch tập này",
    ]
    suffix = f" Mức đánh giá {rating}/5, {context_phrases[n]}."

    if pain in {"Pain", "Severe Pain", "Mild Discomfort"}:
        templates = [
            f"Tôi cảm thấy {pain.lower()} ở {areas or 'vùng khớp'} khi tập {exercise}, nên muốn {action.lower()} trước buổi sau.",
            f"{exercise} tạo cảm giác không thật ổn ở {areas or 'cơ thể'}, tôi muốn kiểm tra kỹ thuật và điều chỉnh an toàn hơn.",
            f"Khi thực hiện {exercise}, vùng {areas or 'liên quan'} hơi khó chịu; nên ưu tiên phương án {action}.",
        ]
        return templates[n % len(templates)] + suffix
    if scope == "Exercise":
        if sentiment == "Positive" and action == "Increase Difficulty":
            templates = [
                f"{exercise} khá dễ kiểm soát, tôi hoàn thành tốt và muốn tăng thử thách nhẹ ở lần tới.",
                f"Tôi thấy {exercise} đang hơi nhẹ so với sức hiện tại, có thể tăng độ khó hoặc thêm volume vừa phải.",
                f"Bài {exercise} vào nhịp tốt, tôi muốn progression rõ hơn để tiếp tục tiến bộ.",
            ]
        elif sentiment == "Positive":
            templates = [
                f"Tôi thích {exercise}, cảm giác vào cơ tốt và muốn giữ bài này trong lịch.",
                f"{exercise} phù hợp với tôi, không gây khó chịu và giúp buổi tập có nhịp ổn.",
                f"Bài {exercise} dễ setup, cảm giác kiểm soát tốt nên tôi muốn tiếp tục duy trì.",
            ]
        elif sentiment == "Neutral":
            templates = [
                f"{exercise} ở mức chấp nhận được, tôi chưa có ưu tiên mạnh và muốn theo dõi thêm vài buổi.",
                f"Tôi thấy {exercise} bình thường, độ khó tương đối ổn nhưng chưa phải bài tôi thích nhất.",
                f"Bài {exercise} dùng được, hiện tại tôi muốn giữ lựa chọn mở thay vì đổi ngay.",
            ]
        else:
            templates = [
                f"{exercise} hơi quá sức hoặc khó giữ kỹ thuật, tôi muốn {action.lower()} để tập ổn hơn.",
                f"Tôi không hợp {exercise} lắm, cảm giác kiểm soát chưa tốt nên nên cân nhắc thay thế.",
                f"Bài {exercise} làm buổi tập nặng hơn dự kiến; tôi muốn giảm độ khó hoặc đổi biến thể.",
            ]
        return templates[n % len(templates)] + f" Lý do chính: {tags or difficulty}." + suffix
    if scope == "Session":
        if sentiment == "Positive":
            body = f"Buổi tập này vừa sức, tôi hoàn thành tốt phần lớn nội dung và muốn giữ nhịp hiện tại."
        elif sentiment == "Neutral":
            body = f"Buổi tập hôm nay ở mức ổn, có vài đoạn hơi đuối nhưng chưa cần thay đổi lớn."
        else:
            body = f"Buổi này hơi nặng hoặc {duration.lower() if duration else 'chưa vừa thời lượng'}, tôi muốn {action.lower()} cho lần tới."
        return body + suffix
    if scope == "Plan":
        if sentiment == "Positive":
            body = "Tổng thể giáo án hợp với lịch và mục tiêu của tôi, nên tôi muốn giữ cấu trúc này thêm vài tuần."
        elif sentiment == "Neutral":
            body = "Kế hoạch hiện tại dùng được, nhưng tôi muốn theo dõi thêm trước khi tăng hoặc giảm khối lượng."
        else:
            body = f"Kế hoạch này có vài điểm chưa hợp, tôi muốn {action.lower()} để dễ theo hơn."
        return body + suffix
    if sentiment == "Positive":
        body = "Tôi muốn tiếp tục với phong cách bài tập dễ theo dõi, ít mất thời gian setup và phù hợp mục tiêu."
    elif sentiment == "Neutral":
        body = "Tôi muốn hệ thống tiếp tục quan sát phản hồi của tôi trước khi thay đổi mạnh giáo án."
    else:
        body = "Tôi muốn lịch tập ưu tiên an toàn, dễ phục hồi và giảm các bài làm tôi khó chịu."
    return body + suffix


def tags_for(sentiment: str, difficulty: str, pain: str, preference: str, action: str) -> str:
    tags = [sentiment, difficulty, pain, preference, action]
    return jarr([x for x in tags if x and x != "Not Applicable"])


def make_exercise_row(base: pd.Series, fid: str, created: str, ordinal: int) -> dict[str, Any]:
    pain = clean(base.get("pain_during_exercise"))
    item_status = clean(base.get("completion_status"))
    rpe = float(clean(base.get("actual_rpe")) or 0)
    enjoyment = int(float(clean(base.get("exercise_enjoyment")) or 3))
    if pain == "Yes":
        sentiment, rating, difficulty, preference, action = "Negative", 2, "Too Hard", "Dislike", "Review Safety"
        pain_feedback = "Mild Discomfort"
        pain_areas = clean(base.get("pain_areas")) or '["Joint discomfort"]'
        ftype = "Safety"
    elif item_status == "Skipped" or rpe >= 8.8 or enjoyment <= 2:
        sentiment, rating, difficulty, preference = "Negative", 2, "Too Hard", "Dislike"
        action = "Replace Exercise" if ordinal % 2 == 0 else "Reduce Difficulty"
        pain_feedback, pain_areas, ftype = "No Pain", "[]", "Difficulty"
    elif item_status == "Modified" or enjoyment == 3:
        sentiment, rating, difficulty, preference, action = "Neutral", 3, "Appropriate", "Neutral", "No Preference"
        pain_feedback, pain_areas, ftype = "No Pain", "[]", "Rating"
    elif ordinal % 5 == 0:
        sentiment, rating, difficulty, preference, action = "Positive", 5, "Too Easy", "Like", "Increase Difficulty"
        pain_feedback, pain_areas, ftype = "No Pain", "[]", "Progression"
    else:
        sentiment, rating, difficulty, preference, action = "Positive", 5 if ordinal % 3 else 4, "Appropriate", "Like", "Keep"
        pain_feedback, pain_areas, ftype = "No Pain", "[]", "Preference"
    row = {
        "feedback_id": fid,
        "user_id": clean(base.get("user_id")),
        "plan_id": clean(base.get("plan_id")),
        "history_session_id": clean(base.get("history_session_id")),
        "history_item_id": clean(base.get("history_item_id")),
        "plan_item_id": clean(base.get("plan_item_id")),
        "exercise_id": clean(base.get("exercise_id")),
        "exercise_name_snapshot": clean(base.get("exercise_name_snapshot")),
        "feedback_scope": "Exercise",
        "feedback_type": ftype,
        "rating": rating,
        "sentiment": sentiment,
        "difficulty_feedback": difficulty,
        "enjoyment_rating": max(1, min(5, enjoyment if sentiment != "Positive" else max(enjoyment, 4))),
        "fatigue_feedback": "Not Applicable",
        "pain_feedback": pain_feedback,
        "pain_areas": "[]" if pain_feedback == "No Pain" else pain_areas,
        "duration_feedback": "Not Applicable",
        "exercise_preference": preference,
        "progression_preference": "Increase Difficulty" if action == "Increase Difficulty" else "Reduce Difficulty" if action in {"Reduce Difficulty", "Replace Exercise"} else "Maintain",
        "requested_action": action,
        "feedback_reason_tags": tags_for(sentiment, difficulty, pain_feedback, preference, action),
        "source_context": "after_exercise",
        "feedback_status": "Active",
        "record_source": "Synthetic",
        "is_synthetic": "True",
        "created_at": created,
        "updated_at": created,
    }
    row["feedback_text"] = text_for(row, clean(base.get("history_item_id")))
    return {k: row.get(k, "") for k in FEEDBACK_HEADERS}


def make_session_row(session: pd.Series, fid: str, created: str, ordinal: int) -> dict[str, Any]:
    status = clean(session.get("completion_status"))
    pain = clean(session.get("pain_reported"))
    set_pct = float(clean(session.get("set_completion_pct")) or 0)
    if pain == "Yes":
        sentiment, rating, fatigue, action, pain_feedback, pain_areas = "Negative", 2, "High", "Review Safety", "Mild Discomfort", clean(session.get("pain_areas")) or '["Joint discomfort"]'
    elif status == "Skipped" or set_pct < 70:
        sentiment, rating, fatigue, action, pain_feedback, pain_areas = "Negative", 2, "High", "Reduce Volume", "No Pain", "[]"
    elif status == "Partial":
        sentiment, rating, fatigue, action, pain_feedback, pain_areas = "Neutral", 3, "Moderate", "No Preference", "No Pain", "[]"
    else:
        sentiment, rating, fatigue, action, pain_feedback, pain_areas = "Positive", 4 + (ordinal % 2), "Low", "Keep", "No Pain", "[]"
    row = {
        "feedback_id": fid,
        "user_id": clean(session.get("user_id")),
        "plan_id": clean(session.get("plan_id")),
        "history_session_id": clean(session.get("history_session_id")),
        "history_item_id": "",
        "plan_item_id": "",
        "exercise_id": "",
        "feedback_scope": "Session",
        "feedback_type": "Safety" if pain_feedback != "No Pain" else "Duration" if action == "Reduce Volume" else "Rating",
        "rating": rating,
        "sentiment": sentiment,
        "difficulty_feedback": "Not Applicable",
        "enjoyment_rating": rating,
        "fatigue_feedback": fatigue,
        "pain_feedback": pain_feedback,
        "pain_areas": pain_areas if pain_feedback != "No Pain" else "[]",
        "duration_feedback": "Too Long" if action == "Reduce Volume" else "Appropriate",
        "exercise_preference": "Not Applicable",
        "progression_preference": "Reduce Difficulty" if action == "Reduce Volume" else "Maintain",
        "requested_action": action,
        "source_context": "after_session",
        "feedback_status": "Active",
        "record_source": "Synthetic",
        "is_synthetic": "True",
        "created_at": created,
        "updated_at": created,
    }
    row["feedback_reason_tags"] = tags_for(sentiment, "Not Applicable", pain_feedback, "Not Applicable", action)
    row["feedback_text"] = text_for(row, clean(session.get("history_session_id")))
    return {k: row.get(k, "") for k in FEEDBACK_HEADERS}


def make_plan_row(plan: pd.Series, fid: str, created: str, ordinal: int) -> dict[str, Any]:
    sentiment = "Positive" if ordinal % 10 < 6 else "Neutral" if ordinal % 10 < 8 else "Negative"
    action = "Keep" if sentiment == "Positive" else "No Preference" if sentiment == "Neutral" else "Change Split"
    rating = 5 if sentiment == "Positive" and ordinal % 2 else 4 if sentiment == "Positive" else 3 if sentiment == "Neutral" else 2
    row = {
        "feedback_id": fid,
        "user_id": clean(plan.get("user_id")),
        "plan_id": clean(plan.get("plan_id")),
        "history_session_id": "",
        "history_item_id": "",
        "plan_item_id": "",
        "exercise_id": "",
        "feedback_scope": "Plan",
        "feedback_type": "Progression",
        "rating": rating,
        "sentiment": sentiment,
        "difficulty_feedback": "Not Applicable",
        "enjoyment_rating": rating,
        "fatigue_feedback": "Moderate" if sentiment != "Positive" else "Low",
        "pain_feedback": "No Pain",
        "pain_areas": "[]",
        "duration_feedback": "Not Applicable",
        "exercise_preference": "Not Applicable",
        "progression_preference": "Maintain" if sentiment != "Negative" else "Reduce Difficulty",
        "requested_action": action,
        "feedback_reason_tags": tags_for(sentiment, "Not Applicable", "No Pain", "Not Applicable", action),
        "source_context": "after_plan",
        "feedback_status": "Active",
        "record_source": "Synthetic",
        "is_synthetic": "True",
        "created_at": created,
        "updated_at": created,
    }
    row["feedback_text"] = text_for(row, clean(plan.get("plan_id")))
    return {k: row.get(k, "") for k in FEEDBACK_HEADERS}


def make_general_row(user: pd.Series, fid: str, created: str, ordinal: int) -> dict[str, Any]:
    sentiment = "Positive" if ordinal % 4 != 0 else "Neutral"
    rating = 4 if sentiment == "Positive" else 3
    row = {
        "feedback_id": fid,
        "user_id": clean(user.get("user_id")),
        "plan_id": "",
        "history_session_id": "",
        "history_item_id": "",
        "plan_item_id": "",
        "exercise_id": "",
        "feedback_scope": "General",
        "feedback_type": "Free Text",
        "rating": rating,
        "sentiment": sentiment,
        "difficulty_feedback": "Not Applicable",
        "enjoyment_rating": rating,
        "fatigue_feedback": "Not Applicable",
        "pain_feedback": "Not Applicable",
        "pain_areas": "[]",
        "duration_feedback": "Not Applicable",
        "exercise_preference": "Not Applicable",
        "progression_preference": "Not Applicable",
        "requested_action": "No Preference",
        "feedback_reason_tags": tags_for(sentiment, "Not Applicable", "No Pain", "Not Applicable", "No Preference"),
        "source_context": "weekly_checkin",
        "feedback_status": "Active",
        "record_source": "Synthetic",
        "is_synthetic": "True",
        "created_at": created,
        "updated_at": created,
    }
    row["feedback_text"] = text_for(row, clean(user.get("user_id")))
    return {k: row.get(k, "") for k in FEEDBACK_HEADERS}


def metrics(df: pd.DataFrame, exercises_total: int = 350) -> dict[str, Any]:
    texts = df["feedback_text"].map(clean)
    ex_used = set(df["exercise_id"].map(clean)) - {""}
    return {
        "feedback_count": len(df),
        "feedback_text_unique_count": int(texts.nunique()),
        "feedback_text_unique_ratio": round(texts.nunique() / len(df), 4) if len(df) else 0,
        "exercises_with_feedback": len(ex_used),
        "exercise_feedback_coverage_percent": round(len(ex_used) * 100 / exercises_total, 3),
        "scope_distribution": dict(Counter(df["feedback_scope"].map(clean))),
        "sentiment_distribution": dict(Counter(df["sentiment"].map(clean))),
    }


def enrich(args: argparse.Namespace) -> dict[str, Any]:
    REPORTS.mkdir(parents=True, exist_ok=True)
    source = Path(args.feedback_master or MASTER / "user_feedback_master.xlsx")
    history_path = Path(args.history_master or MASTER / "workout_history_master.xlsx")
    user_path = Path(args.user_master or MASTER / "user_master.xlsx")
    plan_path = Path(args.plan_master or MASTER / "workout_plan_master.xlsx")
    exercise_path = Path(args.exercise_master or MASTER / "exercise_master.xlsx")
    out_path = Path(args.output or MASTER / "user_feedback_master_enriched.xlsx")
    created = datetime.now().isoformat(timespec="seconds")

    feedback = pd.read_excel(source, sheet_name="User_Feedback", dtype=str, engine="openpyxl").fillna("")
    history_items = pd.read_excel(history_path, sheet_name="Workout_History_Items", dtype=str, engine="openpyxl").fillna("")
    sessions = pd.read_excel(history_path, sheet_name="Workout_History_Sessions", dtype=str, engine="openpyxl").fillna("")
    plans = pd.read_excel(plan_path, sheet_name="Workout_Plan", dtype=str, engine="openpyxl").fillna("")
    users = pd.read_excel(user_path, sheet_name="User_Profile", dtype=str, engine="openpyxl").fillna("")
    exercises = pd.read_excel(exercise_path, sheet_name="gym_exercise_dataset", dtype=str, engine="openpyxl").fillna("")

    before = metrics(feedback, len(exercises))
    history_exercises = set(history_items["exercise_id"].map(clean)) - {""}
    feedback_exercises = set(feedback["exercise_id"].map(clean)) - {""}
    missing_exercises = sorted(history_exercises - feedback_exercises)
    used_history_items = set(feedback["history_item_id"].map(clean)) - {""}
    next_id = next_feedback_id(feedback["feedback_id"])

    enriched = feedback.copy()
    history_item_map = {
        clean(row.get("history_item_id")): row.to_dict()
        for _, row in history_items.iterrows()
        if clean(row.get("history_item_id"))
    }
    # Rewrite old text deterministically while preserving every structured field.
    for idx in enriched.index:
        row = enriched.loc[idx].to_dict()
        if clean(row.get("feedback_scope")) == "Exercise":
            hi = history_item_map.get(clean(row.get("history_item_id")))
            if hi:
                row["exercise_name_snapshot"] = clean(hi.get("exercise_name_snapshot"))
        enriched.at[idx, "feedback_text"] = text_for(row, f"old-{idx}")
        enriched.at[idx, "updated_at"] = created

    new_rows: list[dict[str, Any]] = []
    # Add 3000 exercise feedback rows, prioritizing exercises missing feedback coverage.
    candidate_items = history_items[~history_items["history_item_id"].map(clean).isin(used_history_items)].copy()
    chosen_indices: list[int] = []
    candidate_groups = {k: g for k, g in candidate_items.groupby(candidate_items["exercise_id"].map(clean))}
    for ex_id in missing_exercises:
        ex_items = candidate_groups.get(ex_id)
        if ex_items is not None and not ex_items.empty:
            chosen_indices.append(int(ex_items.index[seed(ex_id) % len(ex_items)]))
    remaining = candidate_items.drop(index=chosen_indices, errors="ignore")
    remaining = remaining.sort_values(["exercise_id", "history_item_id"], key=lambda s: s.map(lambda x: seed(x)))
    chosen_indices.extend([int(i) for i in remaining.index[: max(0, 3000 - len(chosen_indices))]])
    for ordinal, idx in enumerate(chosen_indices[:3000]):
        new_rows.append(make_exercise_row(history_items.loc[idx], feedback_id(next_id), created, ordinal))
        next_id += 1

    used_sessions = set(feedback["history_session_id"].map(clean)) - {""}
    session_candidates = sessions[~sessions["history_session_id"].map(clean).isin(used_sessions)]
    for ordinal, (_, session) in enumerate(session_candidates.head(1100).iterrows()):
        new_rows.append(make_session_row(session, feedback_id(next_id), created, ordinal))
        next_id += 1

    used_plan_scope = set(feedback.loc[feedback["feedback_scope"].map(clean) == "Plan", "plan_id"].map(clean)) - {""}
    plan_candidates = plans[~plans["plan_id"].map(clean).isin(used_plan_scope)].sample(frac=1, random_state=42).head(200)
    for ordinal, (_, plan) in enumerate(plan_candidates.iterrows()):
        new_rows.append(make_plan_row(plan, feedback_id(next_id), created, ordinal))
        next_id += 1

    used_general_users = set(feedback.loc[feedback["feedback_scope"].map(clean) == "General", "user_id"].map(clean)) - {""}
    user_candidates = users[~users["user_id"].map(clean).isin(used_general_users)].sample(frac=1, random_state=7).head(200)
    for ordinal, (_, user) in enumerate(user_candidates.iterrows()):
        new_rows.append(make_general_row(user, feedback_id(next_id), created, ordinal))
        next_id += 1

    enriched = pd.concat([enriched[FEEDBACK_HEADERS], pd.DataFrame(new_rows, columns=FEEDBACK_HEADERS)], ignore_index=True)
    after = metrics(enriched, len(exercises))

    duplicate_ids = int(enriched["feedback_id"].duplicated().sum())
    fk_missing = 0
    cross_mismatch = 0
    hi_map = history_item_map
    for _, row in enriched[enriched["feedback_scope"] == "Exercise"].iterrows():
        hid = clean(row.get("history_item_id"))
        target = hi_map.get(hid)
        if target is None:
            fk_missing += 1
            continue
        for col in ["user_id", "plan_id", "plan_item_id", "exercise_id", "history_session_id"]:
            if clean(row.get(col)) != clean(target.get(col)):
                cross_mismatch += 1

    # Preserve workbook sheets and append enrichment sheets.
    tmp_path = out_path
    with pd.ExcelWriter(tmp_path, engine="openpyxl") as writer:
        sheets = pd.read_excel(source, sheet_name=None, dtype=str, engine="openpyxl")
        for name, df in sheets.items():
            if name == "User_Feedback":
                enriched.to_excel(writer, sheet_name=name, index=False)
            else:
                df.fillna("").to_excel(writer, sheet_name=name, index=False)
        pd.DataFrame([
            {"metric": "before_feedback_count", "value": before["feedback_count"]},
            {"metric": "after_feedback_count", "value": after["feedback_count"]},
            {"metric": "new_feedback_rows_added", "value": len(new_rows)},
            {"metric": "old_feedback_rows_rewritten", "value": len(feedback)},
            {"metric": "before_feedback_text_unique_ratio", "value": before["feedback_text_unique_ratio"]},
            {"metric": "after_feedback_text_unique_ratio", "value": after["feedback_text_unique_ratio"]},
            {"metric": "before_exercises_with_feedback", "value": before["exercises_with_feedback"]},
            {"metric": "after_exercises_with_feedback", "value": after["exercises_with_feedback"]},
            {"metric": "duplicate_feedback_id_count", "value": duplicate_ids},
            {"metric": "fk_missing_count", "value": fk_missing},
            {"metric": "cross_consistency_mismatch_count", "value": cross_mismatch},
        ]).to_excel(writer, sheet_name="Enrichment_Summary", index=False)
        text_counts = Counter(enriched["feedback_text"].map(clean))
        pd.DataFrame([
            {"feedback_text": k, "count": v, "percent": round(v * 100 / len(enriched), 4)}
            for k, v in text_counts.most_common(200)
        ]).to_excel(writer, sheet_name="Text_Diversity_Report", index=False)
        cov_rows = [
            {"metric": "exercises_total", "value": len(exercises)},
            {"metric": "history_exercises", "value": len(history_exercises)},
            {"metric": "before_feedback_exercises", "value": before["exercises_with_feedback"]},
            {"metric": "after_feedback_exercises", "value": after["exercises_with_feedback"]},
            {"metric": "after_coverage_percent", "value": after["exercise_feedback_coverage_percent"]},
        ]
        pd.DataFrame(cov_rows).to_excel(writer, sheet_name="Coverage_Report", index=False)

    status = "PASS" if after["feedback_text_unique_ratio"] >= 0.2 and after["exercises_with_feedback"] >= 210 and duplicate_ids == 0 and fk_missing == 0 and cross_mismatch == 0 else "PASS WITH NOTES"
    summary = {
        "generated_at": created,
        "status": status,
        "output": str(out_path),
        "before": before,
        "after": after,
        "new_feedback_rows_added": len(new_rows),
        "old_feedback_rows_rewritten": len(feedback),
        "duplicate_feedback_id_count": duplicate_ids,
        "fk_missing_count": fk_missing,
        "cross_consistency_mismatch_count": cross_mismatch,
    }
    (REPORTS / "feedback_enrichment_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    report = [
        "# Feedback Enrichment Report",
        "",
        f"Status: **{status}**",
        f"Generated at: {created}",
        "",
        "## Before / After",
        f"- Feedback count: {before['feedback_count']} -> {after['feedback_count']}",
        f"- Text unique count: {before['feedback_text_unique_count']} -> {after['feedback_text_unique_count']}",
        f"- Text unique ratio: {before['feedback_text_unique_ratio']} -> {after['feedback_text_unique_ratio']}",
        f"- Exercises with feedback: {before['exercises_with_feedback']} -> {after['exercises_with_feedback']}",
        f"- Exercise feedback coverage: {before['exercise_feedback_coverage_percent']}% -> {after['exercise_feedback_coverage_percent']}%",
        f"- New rows added: {len(new_rows)}",
        f"- Old rows rewritten: {len(feedback)}",
        "",
        "## Integrity",
        f"- Duplicate feedback_id count: {duplicate_ids}",
        f"- FK missing count: {fk_missing}",
        f"- Cross-consistency mismatch count: {cross_mismatch}",
    ]
    (REPORTS / "feedback_enrichment_report.md").write_text("\n".join(report) + "\n", encoding="utf-8")
    pd.DataFrame([{"issue": "", "severity": "", "note": "No enrichment issues" if status == "PASS" else "Review summary thresholds"}]).to_csv(REPORTS / "feedback_enrichment_issues.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame([{"metric": k, "before": before.get(k), "after": after.get(k)} for k in sorted(set(before) | set(after))]).to_csv(REPORTS / "feedback_coverage_report.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame([{"feedback_text": k, "count": v, "percent": round(v * 100 / len(enriched), 4)} for k, v in Counter(enriched["feedback_text"].map(clean)).most_common()]).to_csv(REPORTS / "feedback_text_diversity_report.csv", index=False, encoding="utf-8-sig")
    return summary


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Enrich user_feedback_master with diverse text and better exercise coverage")
    p.add_argument("--feedback-master")
    p.add_argument("--history-master")
    p.add_argument("--user-master")
    p.add_argument("--plan-master")
    p.add_argument("--exercise-master")
    p.add_argument("--output")
    return p


def main() -> int:
    summary = enrich(parser().parse_args())
    print("=" * 72)
    print("USER FEEDBACK ENRICHMENT")
    print("=" * 72)
    print(f"Status                  : {summary['status']}")
    print(f"Output                  : {summary['output']}")
    print(f"Rows                    : {summary['before']['feedback_count']} -> {summary['after']['feedback_count']}")
    print(f"Text unique ratio       : {summary['before']['feedback_text_unique_ratio']} -> {summary['after']['feedback_text_unique_ratio']}")
    print(f"Exercises with feedback : {summary['before']['exercises_with_feedback']} -> {summary['after']['exercises_with_feedback']}")
    print(f"FK missing              : {summary['fk_missing_count']}")
    print(f"Cross mismatch          : {summary['cross_consistency_mismatch_count']}")
    print("=" * 72)
    return 0 if summary["duplicate_feedback_id_count"] == 0 and summary["fk_missing_count"] == 0 and summary["cross_consistency_mismatch_count"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
