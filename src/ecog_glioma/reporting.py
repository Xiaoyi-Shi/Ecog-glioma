from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class ReportingCohort:
    name: str
    analysis_role: str
    flag_column: str | None


REPORTING_COHORTS = (
    ReportingCohort("main", "primary", "patient_main_included"),
    ReportingCohort("sensitivity", "exploratory", "patient_sensitivity_included"),
    ReportingCohort("full_modelable", "exploratory", None),
)

COHORT_BY_NAME = {cohort.name: cohort for cohort in REPORTING_COHORTS}


def filter_frame_for_cohort(
    frame: pd.DataFrame,
    cohort_name: str,
    *,
    patient_col: str = "patient",
) -> pd.DataFrame:
    if frame.empty:
        return frame.copy()
    cohort = COHORT_BY_NAME[cohort_name]
    result = frame.copy()
    if patient_col in result.columns:
        result = result[result[patient_col].notna()].copy()
    if cohort.flag_column is None:
        return result
    if cohort.flag_column not in result.columns:
        return result.iloc[0:0].copy()
    mask = result[cohort.flag_column].fillna(False).astype(bool)
    return result.loc[mask].copy()


def cohort_patient_sets(
    frame: pd.DataFrame,
    *,
    patient_col: str = "patient",
) -> dict[str, set[str]]:
    result: dict[str, set[str]] = {}
    for cohort in REPORTING_COHORTS:
        subset = filter_frame_for_cohort(frame, cohort.name, patient_col=patient_col)
        if patient_col not in subset.columns or subset.empty:
            result[cohort.name] = set()
            continue
        result[cohort.name] = {
            str(value)
            for value in subset[patient_col].dropna().astype(str).unique().tolist()
        }
    return result


def subset_by_patient_set(
    frame: pd.DataFrame,
    patients: set[str],
    *,
    patient_col: str = "patient",
) -> pd.DataFrame:
    if frame.empty:
        return frame.copy()
    if not patients:
        return frame.iloc[0:0].copy()
    if patient_col not in frame.columns:
        return frame.iloc[0:0].copy()
    normalized = frame.copy()
    normalized[patient_col] = normalized[patient_col].astype(str)
    return normalized.loc[normalized[patient_col].isin(patients)].copy()


def build_cohort_manifest(
    frame: pd.DataFrame,
    *,
    patient_col: str = "patient",
    interval_col: str = "interval_id",
) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for cohort in REPORTING_COHORTS:
        subset = filter_frame_for_cohort(frame, cohort.name, patient_col=patient_col)
        interval_count = 0
        if interval_col in subset.columns and patient_col in subset.columns and not subset.empty:
            interval_count = int(
                subset[[patient_col, interval_col]]
                .dropna()
                .drop_duplicates()
                .shape[0]
            )
        patient_count = (
            int(subset[patient_col].dropna().astype(str).nunique())
            if patient_col in subset.columns and not subset.empty
            else 0
        )
        rows.append(
            {
                "cohort": cohort.name,
                "analysis_role": cohort.analysis_role,
                "patient_count": patient_count,
                "interval_count": interval_count,
                "row_count": int(len(subset)),
            }
        )
    return pd.DataFrame(rows)
