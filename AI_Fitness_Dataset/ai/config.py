from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CSV_DIR = ROOT / "exports" / "csv"
OUTPUT_DIR = ROOT / "ai_outputs"

VALID_ACTIONS = {
    "Keep", "Increase Difficulty", "Reduce Difficulty", "Increase Volume",
    "Reduce Volume", "Replace Exercise", "Change Split", "Review Safety",
}

LEVEL_RANK = {"Beginner": 1, "Intermediate": 2, "Advanced": 3}

VOLUME_RULES = {
    "Beginner": {"sets": 2, "min_exercises": 2, "max_exercises": 4, "rpe": 6, "rest": 90},
    "Intermediate": {"sets": 3, "min_exercises": 3, "max_exercises": 5, "rpe": 7, "rest": 120},
    "Advanced": {"sets": 4, "min_exercises": 4, "max_exercises": 6, "rpe": 8, "rest": 150},
}

