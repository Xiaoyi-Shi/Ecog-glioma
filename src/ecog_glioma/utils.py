from __future__ import annotations

import json
import math
from collections.abc import Iterable
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def to_jsonable(value: Any) -> Any:
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        return None if math.isnan(float(value)) else float(value)
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, dict):
        return {str(key): to_jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [to_jsonable(item) for item in value]
    return value


def write_json(path: Path, payload: dict[str, Any]) -> None:
    ensure_parent(path)
    path.write_text(
        json.dumps(to_jsonable(payload), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def append_jsonl(path: Path, payload: dict[str, Any]) -> None:
    ensure_parent(path)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(to_jsonable(payload), ensure_ascii=False) + "\n")


def safe_float(value: Any) -> float | None:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return None
    return float(value)


def zscore_series(values: pd.Series) -> pd.Series:
    if len(values) <= 1:
        return pd.Series(np.zeros(len(values)), index=values.index, dtype=float)
    std = values.std(ddof=0)
    if std in (0, 0.0) or pd.isna(std):
        return pd.Series(np.zeros(len(values)), index=values.index, dtype=float)
    return (values - values.mean()) / std


def add_patient_zscore(
    frame: pd.DataFrame,
    feature_col: str = "feature_name",
    patient_col: str = "patient",
    value_col: str = "feature_value",
    output_col: str = "feature_z",
) -> pd.DataFrame:
    result = frame.copy()
    result[output_col] = (
        result.groupby([patient_col, feature_col], dropna=False)[value_col]
        .transform(zscore_series)
        .astype(float)
    )
    return result


def listify(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    return [value]


def write_dataframe(frame: pd.DataFrame, path: Path, index: bool = False) -> None:
    ensure_parent(path)
    frame.to_csv(path, index=index, encoding="utf-8")


def read_dataframe(path: Path, dtype: dict[str, str] | None = None) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path, dtype=dtype, keep_default_na=True)
