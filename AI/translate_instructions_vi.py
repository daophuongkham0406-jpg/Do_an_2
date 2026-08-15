import csv
import json
import os
import re
import time
import urllib.error
import urllib.request
from pathlib import Path

from vietnamese_exercise_text import translate_steps
from vietnamese_normalizer import normalize_text


ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = ROOT.parent
CSV_PATH = ROOT / "exercises.csv"
BACKUP_PATH = ROOT / "exercises_before_vi_translation.csv"
REPORT_PATH = ROOT / "vietnamese_steps_audit.json"
MODEL = "gemini-1.5-flash"


def load_env(path: Path) -> dict:
    values = {}
    if not path.exists():
        return values
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def gemini_translate(api_key: str, name: str, steps: list[str], retries: int = 2) -> list[str] | None:
    prompt = {
        "contents": [{
            "parts": [{
                "text": (
                    "Dịch hướng dẫn bài tập gym sau sang tiếng Việt tự nhiên, rõ kỹ thuật, dễ hiểu cho người tập.\n"
                    "Giữ đúng số bước và đúng ý gốc. Không thêm cảnh báo chung chung nếu câu gốc không có.\n"
                    "Không để sót tiếng Anh trong phần hướng dẫn, trừ tên riêng rất phổ biến nếu không dịch được.\n"
                    "Chỉ trả về JSON hợp lệ dạng {\"steps\":[\"...\",\"...\"]}.\n\n"
                    f"Bài tập: {name}\n"
                    f"Hướng dẫn gốc: {json.dumps(steps, ensure_ascii=False)}"
                )
            }]
        }],
        "generationConfig": {
            "temperature": 0.2,
            "responseMimeType": "application/json",
        },
    }
    body = json.dumps(prompt).encode("utf-8")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent?key={api_key}"
    request = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"}, method="POST")
    for attempt in range(retries + 1):
        try:
            with urllib.request.urlopen(request, timeout=45) as response:
                data = json.loads(response.read().decode("utf-8"))
            text = data["candidates"][0]["content"]["parts"][0]["text"].strip()
            text = re.sub(r"^```json|```$", "", text, flags=re.IGNORECASE).strip()
            parsed = json.loads(text)
            translated = parsed.get("steps")
            if isinstance(translated, list) and len(translated) == len(steps):
                clean = [str(step).strip() for step in translated]
                if all(clean):
                    return clean
        except (urllib.error.URLError, urllib.error.HTTPError, KeyError, json.JSONDecodeError, TimeoutError):
            if attempt >= retries:
                return None
            time.sleep(1.5 * (attempt + 1))
    return None


def split_steps(value: str) -> list[str]:
    return [part.strip() for part in str(value or "").split("|") if part.strip()]


def audit_rows(rows: list[dict]) -> dict:
    english_terms = re.compile(
        r"\b(grip|hold|pull|push|press|lower|raise|place|sit|stand|lie|step|drive|loop|repeat|switch|continue|anchor|drop|"
        r"barbell|dumbbell|cable|machine|bench|kettlebell|with|your|and|for the|palms|feet|hands|elbows|knees|hips|torso|"
        r"chest|shoulder|floor|position|control|starting|straight|toward|under|over|body|arms|legs)\b",
        re.IGNORECASE,
    )
    generic_markers = [
        "giu ky thuat on dinh trong buoc nay",
        "chuan bi dung tu the",
        "thuc hien pha chinh dut khoat",
        "nam hoac giu chac diem tua",
        "day len co kiem soat",
        "keo co kiem soat",
        "nang len cham rai trong bien do",
        "ha hoac dua co the ve vi tri ban dau",
        "giu tu the trong thoi gian duoc chi dinh",
    ]
    issues = []
    for row in rows:
        steps = split_steps(row.get("instructions_vi", ""))
        for index, step in enumerate(steps, 1):
            found = []
            if english_terms.search(step):
                found.append("english_residue")
            if any(marker in normalize_text(step) for marker in generic_markers):
                found.append("generic_fallback")
            if found:
                issues.append({
                    "id": row.get("id"),
                    "name_en": row.get("name_en"),
                    "step": index,
                    "issue": found,
                    "translated_vi": step,
                })
    return {
        "summary": {
            "rows": len(rows),
            "steps": sum(len(split_steps(row.get("instructions_vi", ""))) for row in rows),
            "issues": len(issues),
            "affected_exercises": len({item["id"] for item in issues}),
        },
        "issues": issues,
    }


def main():
    env = {**load_env(PROJECT_ROOT / "Backend" / ".env"), **os.environ}
    api_key = env.get("GEMINI_API_KEY", "")
    with CSV_PATH.open("r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        rows = list(reader)
        fieldnames = list(reader.fieldnames or [])
    if "instructions_vi" not in fieldnames:
        fieldnames.append("instructions_vi")
    if not BACKUP_PATH.exists():
        BACKUP_PATH.write_text(CSV_PATH.read_text(encoding="utf-8-sig"), encoding="utf-8")

    translated_count = 0
    fallback_count = 0
    for row in rows:
        source_steps = split_steps(row.get("instructions_en", ""))
        if not source_steps:
            row["instructions_vi"] = ""
            continue
        use_gemini = os.getenv("USE_GEMINI_TRANSLATION", "0") == "1"
        translated = gemini_translate(api_key, row.get("name_en", ""), source_steps) if api_key and use_gemini else None
        if translated:
            translated_count += 1
        else:
            translated = translate_steps(row.get("instructions_en", ""), row.get("name_en", ""))
            fallback_count += 1
        row["instructions_vi"] = " | ".join(translated)
        print(f"{row.get('id')}: {'gemini' if translated_count + fallback_count and translated_count >= fallback_count else 'done'}")
        time.sleep(0.05)

    with CSV_PATH.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    report = audit_rows(rows)
    report["translation"] = {"gemini_rows": translated_count, "fallback_rows": fallback_count}
    REPORT_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))
    print(json.dumps(report["translation"], ensure_ascii=False, indent=2))
    print(f"report={REPORT_PATH}")


if __name__ == "__main__":
    main()
