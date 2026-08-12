from __future__ import annotations

from typing import Any

import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from .model_schema import ID_COLUMNS


def _one_hot_encoder() -> OneHotEncoder:
    try:
        return OneHotEncoder(handle_unknown="ignore", sparse_output=False)
    except TypeError:  # pragma: no cover
        return OneHotEncoder(handle_unknown="ignore", sparse=False)


def infer_feature_columns(df: pd.DataFrame, label_column: str) -> dict[str, list[str]]:
    excluded = sorted([col for col in ID_COLUMNS | {label_column} if col in df.columns])
    candidates = [col for col in df.columns if col not in excluded]
    numeric_features: list[str] = []
    categorical_features: list[str] = []
    for column in candidates:
        converted = pd.to_numeric(df[column], errors="coerce")
        if converted.notna().mean() >= 0.95:
            numeric_features.append(column)
        else:
            categorical_features.append(column)
    return {
        "label": [label_column],
        "numeric_features": numeric_features,
        "categorical_features": categorical_features,
        "excluded_columns": excluded,
    }


def build_preprocessor(numeric_features: list[str], categorical_features: list[str]) -> ColumnTransformer:
    numeric_pipe = Pipeline([
        ("imputer", SimpleImputer(strategy="median")),
        ("scaler", StandardScaler()),
    ])
    categorical_pipe = Pipeline([
        ("imputer", SimpleImputer(strategy="constant", fill_value="Unknown")),
        ("onehot", _one_hot_encoder()),
    ])
    return ColumnTransformer([
        ("numeric", numeric_pipe, numeric_features),
        ("categorical", categorical_pipe, categorical_features),
    ], remainder="drop")


def prepare_xy(df: pd.DataFrame, label_column: str, feature_spec: dict[str, Any]) -> tuple[pd.DataFrame, pd.Series]:
    features = feature_spec["numeric_features"] + feature_spec["categorical_features"]
    x = df[features].copy()
    y = df[label_column].astype(str).str.strip()
    return x, y


def transformed_feature_names(preprocessor: ColumnTransformer) -> list[str]:
    try:
        return [str(name) for name in preprocessor.get_feature_names_out()]
    except Exception:
        names: list[str] = []
        for name, _, columns in preprocessor.transformers_:
            if name == "remainder":
                continue
            names.extend([f"{name}__{column}" for column in columns])
        return names
