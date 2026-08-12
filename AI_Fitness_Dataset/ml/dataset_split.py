from __future__ import annotations

import random
from typing import Iterable

import pandas as pd

from .feature_engineering import clean
from .ml_schema import RANDOM_SEED


def assign_user_splits(user_ids: Iterable[str], seed: int = RANDOM_SEED) -> dict[str, str]:
    unique_users = sorted({clean(user_id) for user_id in user_ids if clean(user_id)})
    rng = random.Random(seed)
    rng.shuffle(unique_users)
    total = len(unique_users)
    train_cut = int(total * 0.70)
    validation_cut = train_cut + int(total * 0.15)
    assignments: dict[str, str] = {}
    for idx, user_id in enumerate(unique_users):
        if idx < train_cut:
            split = "train"
        elif idx < validation_cut:
            split = "validation"
        else:
            split = "test"
        assignments[user_id] = split
    return assignments


def split_dataframe(df: pd.DataFrame, user_splits: dict[str, str]) -> dict[str, pd.DataFrame]:
    if df.empty or "user_id" not in df.columns:
        return {
            "train": df.iloc[0:0].copy(),
            "validation": df.iloc[0:0].copy(),
            "test": df.iloc[0:0].copy(),
        }
    with_split = df.copy()
    with_split["split"] = with_split["user_id"].map(lambda value: user_splits.get(clean(value), "train"))
    return {
        "train": with_split[with_split["split"] == "train"].drop(columns=["split"]),
        "validation": with_split[with_split["split"] == "validation"].drop(columns=["split"]),
        "test": with_split[with_split["split"] == "test"].drop(columns=["split"]),
    }


def user_overlap_count(split_frames: dict[str, pd.DataFrame]) -> int:
    user_sets = {
        name: set(frame["user_id"].map(clean)) if "user_id" in frame.columns else set()
        for name, frame in split_frames.items()
    }
    return len(user_sets["train"] & user_sets["validation"]) + len(user_sets["train"] & user_sets["test"]) + len(user_sets["validation"] & user_sets["test"])
