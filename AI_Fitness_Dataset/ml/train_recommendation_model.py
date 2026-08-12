from __future__ import annotations

from pathlib import Path
from typing import Any

from .train_all_models import train_task


def train_recommendation(input_dir: Path, model_dir: Path, output_dir: Path) -> dict[str, Any]:
    return train_task("recommendation", input_dir, model_dir, output_dir)
