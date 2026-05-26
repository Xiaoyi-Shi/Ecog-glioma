from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import pandas as pd

from .config import DEFAULT_SESSION_FILTER
from .paths import as_repo_path


INTERVAL_COLUMN_PATTERN = re.compile(r"^\d+_\d+$")
A_LABEL_PATTERN = re.compile(r"^a\d+$", re.IGNORECASE)
B_DISTANCE_PATTERN = re.compile(
    r"^b\d+\[(?P<distance>-?\d+(?:\.\d+)?)\]$",
    re.IGNORECASE,
)
B_NO_DISTANCE_PATTERN = re.compile(r"^b\d+$", re.IGNORECASE)


def normalize_subject(value: Any) -> str:
    subject = str(value).strip()
    if subject.lower().startswith("sub-"):
        subject = subject[4:]
    return subject


def interval_columns(columns: list[str]) -> list[str]:
    return [column for column in columns if INTERVAL_COLUMN_PATTERN.match(str(column))]


def distance_to_region(distance_mm: float) -> int:
    if distance_mm <= 1.0:
        return 2
    if distance_mm <= 3.0:
        return 3
    return 4


def parse_interval_label(raw_value: Any) -> dict[str, Any]:
    if raw_value is None or (isinstance(raw_value, float) and pd.isna(raw_value)):
        return {
            "normalized_label": None,
            "label_valid": False,
            "parse_status": "blank",
            "distance_mm": None,
            "region": None,
            "is_boundary_interface": 0,
        }

    raw_label = str(raw_value).strip()
    normalized = raw_label.lower()
    if not raw_label:
        return {
            "normalized_label": None,
            "label_valid": False,
            "parse_status": "blank",
            "distance_mm": None,
            "region": None,
            "is_boundary_interface": 0,
        }
    if raw_label == "用不了":
        return {
            "normalized_label": normalized,
            "label_valid": False,
            "parse_status": "marked_unusable",
            "distance_mm": None,
            "region": None,
            "is_boundary_interface": 0,
        }
    if A_LABEL_PATTERN.match(normalized):
        return {
            "normalized_label": normalized,
            "label_valid": True,
            "parse_status": "tumor_internal",
            "distance_mm": None,
            "region": 1,
            "is_boundary_interface": 0,
        }
    match = B_DISTANCE_PATTERN.match(normalized)
    if match:
        distance_mm = float(match.group("distance"))
        return {
            "normalized_label": normalized,
            "label_valid": True,
            "parse_status": "tumor_external",
            "distance_mm": distance_mm,
            "region": distance_to_region(distance_mm),
            "is_boundary_interface": int(distance_mm == 0.0),
        }
    if B_NO_DISTANCE_PATTERN.match(normalized):
        return {
            "normalized_label": normalized,
            "label_valid": False,
            "parse_status": "missing_distance",
            "distance_mm": None,
            "region": None,
            "is_boundary_interface": 0,
        }
    return {
        "normalized_label": normalized,
        "label_valid": False,
        "parse_status": "unparsed_label",
        "distance_mm": None,
        "region": None,
        "is_boundary_interface": 0,
    }


def build_label_manifest(
    metadata_xlsx: Path,
    session_filter: str = DEFAULT_SESSION_FILTER,
) -> pd.DataFrame:
    workbook = pd.read_excel(as_repo_path(metadata_xlsx), sheet_name=0)
    interval_cols = interval_columns(workbook.columns.astype(str).tolist())
    rows: list[dict[str, Any]] = []

    for row_number, row in workbook.iterrows():
        session = row.get("sesion")
        if pd.isna(session) or str(session).strip() != session_filter:
            continue
        patient_id_value = row.get("patient_id")
        if pd.isna(patient_id_value):
            continue
        patient_id = str(int(patient_id_value)) if isinstance(patient_id_value, (int, float)) else str(patient_id_value).strip()
        subject = normalize_subject(row.get("Sub-ID"))
        patient_name = None if pd.isna(row.get("姓名")) else str(row.get("姓名")).strip()
        for interval_col in interval_cols:
            contact_a, contact_b = [int(part) for part in interval_col.split("_")]
            parsed = parse_interval_label(row.get(interval_col))
            rows.append(
                {
                    "metadata_row": int(row_number) + 2,
                    "patient_id": patient_id,
                    "subject": subject,
                    "session": session_filter,
                    "patient_name": patient_name,
                    "interval_id": interval_col,
                    "interval_index": contact_a,
                    "contact_a": contact_a,
                    "contact_b": contact_b,
                    "raw_label": row.get(interval_col),
                    **parsed,
                }
            )

    manifest = pd.DataFrame(rows)
    if manifest.empty:
        return manifest

    manifest = manifest.sort_values(
        ["subject", "interval_index"],
        kind="stable",
    ).reset_index(drop=True)
    return manifest
