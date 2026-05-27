from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from .config import DEFAULT_MAIN_MIN_INTERVALS, DEFAULT_SENSITIVITY_MIN_INTERVALS
from .dynamic import compute_average_controllability, compute_column_fragility
from .reporting import REPORTING_COHORTS, filter_frame_for_cohort, subset_by_patient_set
from .run_context import RunContext
from .utils import read_dataframe, write_dataframe

INCLUSION_THRESHOLD_GRID = (8, 10, 12, 14, 16, 18)
DISTANCE_THRESHOLD_GRID = (1.0, 1.5, 2.0, 2.5)
PRIMARY_DISTANCE_THRESHOLD_MM = 1.5
STRUCTURAL_NULL_REPLICATES = 32
PERMUTATION_REPLICATES = 128
PAIR_PERMUTATION_REPLICATES = 256
STRUCTURAL_MATRIX_SCALE = 0.12
STRUCTURAL_SPECTRAL_RADIUS_CAP = 0.95
MIN_CORRELATION_PAIRS = 4
MIN_PAIRED_PATIENTS = 4
REFERENCE_THRESHOLD_BY_COHORT = {
    "main": DEFAULT_MAIN_MIN_INTERVALS,
    "sensitivity": DEFAULT_SENSITIVITY_MIN_INTERVALS,
    "full_modelable": None,
}
CONTRAST_AC_METRIC_FAMILY = "average_controllability_p90"
CONTRAST_FRAGILITY_METRIC_FAMILY = "fragility_mean"
CONTRAST_VALUE_COLUMN = "feature_z"

DECOMPOSITION_COLUMNS = [
    "run_dir",
    "cohort",
    "analysis_role",
    "aggregation_level",
    "value_scale",
    "decomposition_view",
    "grouping_stratum",
    "observed_rho",
    "n_pairs",
    "patient_count",
    "interval_count",
    "status",
    "insufficient_reason",
]
NULL_COMPARISON_COLUMNS = [
    "run_dir",
    "cohort",
    "analysis_role",
    "aggregation_level",
    "value_scale",
    "decomposition_view",
    "grouping_stratum",
    "observed_rho",
    "observed_n_pairs",
    "observed_status",
    "structural_rho_mean",
    "structural_rho_median",
    "structural_rho_min",
    "structural_rho_max",
    "structural_replicates",
    "structural_seed",
    "permutation_rho_mean",
    "permutation_rho_median",
    "permutation_rho_min",
    "permutation_rho_max",
    "permutation_abs_ge_rate",
    "permutation_replicates",
    "permutation_seed",
    "permutation_stratification",
]
INCLUSION_SCAN_COLUMNS = [
    "run_dir",
    "threshold_kind",
    "threshold_value",
    "eligible_patient_count",
    "eligible_interval_count",
    "finding_id",
    "finding_label",
    "finding_kind",
    "expected_direction",
    "observed_value",
    "p_value",
    "paired_patient_count",
    "boundary_interval_count",
    "remote_interval_count",
    "status",
    "insufficient_reason",
]
DISTANCE_SCAN_COLUMNS = [
    "run_dir",
    "cohort",
    "analysis_role",
    "threshold_kind",
    "threshold_value",
    "eligible_patient_count",
    "eligible_interval_count",
    "excluded_missing_distance_count",
    "finding_id",
    "finding_label",
    "finding_kind",
    "expected_direction",
    "observed_value",
    "p_value",
    "paired_patient_count",
    "boundary_interval_count",
    "remote_interval_count",
    "status",
    "insufficient_reason",
]
STABILITY_MATRIX_COLUMNS = [
    "run_dir",
    "cohort",
    "analysis_role",
    "finding_id",
    "finding_label",
    "inclusion_reference_threshold",
    "inclusion_direction_status",
    "inclusion_significance_status",
    "inclusion_unstable_thresholds",
    "inclusion_insufficient_thresholds",
    "distance_reference_threshold",
    "distance_direction_status",
    "distance_significance_status",
    "distance_unstable_thresholds",
    "distance_insufficient_thresholds",
    "overall_stability_status",
]
ROBUSTNESS_SUMMARY_COLUMNS = [
    "run_dir",
    "cohort",
    "analysis_role",
    "finding_id",
    "finding_label",
    "finding_kind",
    "expected_direction",
    "reference_threshold",
    "reference_distance_threshold_mm",
    "observed_value",
    "observed_p_value",
    "observed_status",
    "observed_n_pairs",
    "structural_rho_median",
    "structural_gap",
    "permutation_abs_ge_rate",
    "inclusion_direction_status",
    "inclusion_significance_status",
    "distance_direction_status",
    "distance_significance_status",
    "robustness_status",
    "source_artifact",
]
QC_SUMMARY_COLUMNS = [
    "run_dir",
    "cohort",
    "analysis_role",
    "patient_count",
    "interval_count",
    "patient_interval_gini",
    "region_1_interval_count",
    "region_2_interval_count",
    "region_3_interval_count",
]


@dataclass(frozen=True)
class ScaleSpec:
    name: str
    ac_column: str
    fragility_column: str


@dataclass
class DecompositionDescriptor:
    run_dir: str
    cohort: str
    analysis_role: str
    aggregation_level: str
    value_scale: str
    decomposition_view: str
    grouping_stratum: str
    frame: pd.DataFrame
    ac_column: str
    fragility_column: str
    status: str
    insufficient_reason: str | None
    observed_rho: float | None
    n_pairs: int
    patient_count: int
    interval_count: int
    permutation_stratification: str

    @property
    def key(self) -> tuple[str, str, str, str, str, str]:
        return (
            self.cohort,
            self.aggregation_level,
            self.value_scale,
            self.decomposition_view,
            self.grouping_stratum,
            self.analysis_role,
        )


SCALE_SPECS = (
    ScaleSpec("raw", "raw_average_controllability", "raw_fragility"),
    ScaleSpec("feature_z", "feature_z_average_controllability", "feature_z_fragility"),
    ScaleSpec(
        "feature_z_within_band",
        "feature_z_within_band_average_controllability",
        "feature_z_within_band_fragility",
    ),
)


@dataclass(frozen=True)
class HeadlineFinding:
    finding_id: str
    finding_label: str
    finding_kind: str
    expected_direction: str
    distance_scan_finding_id: str | None = None


HEADLINE_FINDINGS = (
    HeadlineFinding(
        "overall_coupling",
        "Overall AC-NF coupling",
        "coupling",
        "negative",
        None,
    ),
    HeadlineFinding(
        "region2_coupling",
        "Region 2 AC-NF coupling",
        "coupling",
        "negative",
        "distance_boundary_coupling",
    ),
    HeadlineFinding(
        "region2_ac_elevation",
        "Region 2 minus Region 1 average controllability",
        "contrast",
        "positive",
        "distance_boundary_minus_remote_average_controllability",
    ),
    HeadlineFinding(
        "region2_fragility_reduction",
        "Region 2 minus Region 1 fragility",
        "contrast",
        "negative",
        "distance_boundary_minus_remote_fragility",
    ),
)
HEADLINE_FINDING_BY_ID = {finding.finding_id: finding for finding in HEADLINE_FINDINGS}


def _load_csv(path: Path, dtype: dict[str, str] | None = None) -> pd.DataFrame:
    return read_dataframe(path, dtype=dtype)


def _zscore(series: pd.Series) -> pd.Series:
    if len(series) <= 1:
        return pd.Series(np.zeros(len(series)), index=series.index, dtype=float)
    std = float(series.std(ddof=0))
    if std == 0.0 or pd.isna(std):
        return pd.Series(np.zeros(len(series)), index=series.index, dtype=float)
    return ((series - float(series.mean())) / std).astype(float)


def _safe_spearman(
    frame: pd.DataFrame,
    x_col: str,
    y_col: str,
) -> dict[str, Any]:
    subset = frame[[x_col, y_col]].dropna()
    n_pairs = int(len(subset))
    if n_pairs < MIN_CORRELATION_PAIRS:
        return {
            "rho": None,
            "n_pairs": n_pairs,
            "status": "insufficient",
            "reason": "too_few_pairs",
        }
    if subset[x_col].nunique() < 2 or subset[y_col].nunique() < 2:
        return {
            "rho": None,
            "n_pairs": n_pairs,
            "status": "insufficient",
            "reason": "zero_variance",
        }
    rho = subset[x_col].rank(method="average").corr(subset[y_col].rank(method="average"))
    if pd.isna(rho):
        return {
            "rho": None,
            "n_pairs": n_pairs,
            "status": "insufficient",
            "reason": "correlation_nan",
        }
    return {
        "rho": float(rho),
        "n_pairs": n_pairs,
        "status": "complete",
        "reason": None,
    }


def _format_grouping_value(value: Any) -> str:
    if value is None:
        return "all"
    if isinstance(value, float) and pd.isna(value):
        return "all"
    return str(value)


def _unique_interval_count(frame: pd.DataFrame) -> int:
    if frame.empty or not {"patient", "interval_id"}.issubset(frame.columns):
        return 0
    return int(frame[["patient", "interval_id"]].dropna().drop_duplicates().shape[0])


def _patient_count(frame: pd.DataFrame) -> int:
    if frame.empty or "patient" not in frame.columns:
        return 0
    return int(frame["patient"].dropna().astype(str).nunique())


def _normalize_pair_frame(frame: pd.DataFrame) -> pd.DataFrame:
    if frame.empty:
        return frame.copy()
    result = frame.copy()
    for column in ["patient", "session", "run", "interval_id", "band", "cohort", "analysis_role"]:
        if column in result.columns:
            result[column] = result[column].astype(str)
    if "region" in result.columns:
        result["region"] = pd.to_numeric(result["region"], errors="coerce")
    if "distance_mm" in result.columns:
        result["distance_mm"] = pd.to_numeric(result["distance_mm"], errors="coerce")
    if "interval_index" in result.columns:
        result["interval_index"] = pd.to_numeric(result["interval_index"], errors="coerce")
    return result


def _normalize_metric_frame(frame: pd.DataFrame) -> pd.DataFrame:
    if frame.empty:
        return frame.copy()
    result = frame.copy()
    for column in ["patient", "session", "run", "band", "interval_id", "metric_family"]:
        if column in result.columns:
            result[column] = result[column].astype(str)
    for column in ["region", "distance_mm", "interval_index"]:
        if column in result.columns:
            result[column] = pd.to_numeric(result[column], errors="coerce")
    return result


def _prepare_contrast_frames_by_cohort(model_band_metric: pd.DataFrame) -> dict[str, dict[str, pd.DataFrame]]:
    frames_by_cohort: dict[str, dict[str, pd.DataFrame]] = {}
    for cohort in REPORTING_COHORTS:
        cohort_frame = filter_frame_for_cohort(model_band_metric, cohort.name, patient_col="patient")
        frames_by_cohort[cohort.name] = {
            "average_controllability": cohort_frame.loc[
                cohort_frame["metric_family"] == CONTRAST_AC_METRIC_FAMILY
            ].copy(),
            "fragility": cohort_frame.loc[
                cohort_frame["metric_family"] == CONTRAST_FRAGILITY_METRIC_FAMILY
            ].copy(),
        }
    return frames_by_cohort


def _center_within_group(
    frame: pd.DataFrame,
    group_col: str,
    x_col: str,
    y_col: str,
) -> pd.DataFrame:
    centered = frame.copy()
    centered[x_col] = centered.groupby(group_col, dropna=False)[x_col].transform(lambda values: values - values.mean())
    centered[y_col] = centered.groupby(group_col, dropna=False)[y_col].transform(lambda values: values - values.mean())
    return centered


def _permutation_stratification(view: str, frame: pd.DataFrame) -> str:
    if view == "between_patient":
        return "global"
    if "patient" not in frame.columns or frame.empty:
        return "global"
    group_sizes = frame.groupby("patient", dropna=False).size()
    if (group_sizes >= 2).any():
        return "within_patient"
    return "global"


def _build_descriptor(
    *,
    run_dir: Path,
    cohort: str,
    analysis_role: str,
    aggregation_level: str,
    scale: ScaleSpec,
    decomposition_view: str,
    grouping_stratum: str,
    frame: pd.DataFrame,
) -> tuple[dict[str, Any], DecompositionDescriptor]:
    stats = _safe_spearman(frame, scale.ac_column, scale.fragility_column)
    row = {
        "run_dir": run_dir.as_posix(),
        "cohort": cohort,
        "analysis_role": analysis_role,
        "aggregation_level": aggregation_level,
        "value_scale": scale.name,
        "decomposition_view": decomposition_view,
        "grouping_stratum": grouping_stratum,
        "observed_rho": stats["rho"],
        "n_pairs": stats["n_pairs"],
        "patient_count": _patient_count(frame),
        "interval_count": _unique_interval_count(frame),
        "status": stats["status"],
        "insufficient_reason": stats["reason"],
    }
    descriptor = DecompositionDescriptor(
        run_dir=run_dir.as_posix(),
        cohort=cohort,
        analysis_role=analysis_role,
        aggregation_level=aggregation_level,
        value_scale=scale.name,
        decomposition_view=decomposition_view,
        grouping_stratum=grouping_stratum,
        frame=frame.copy(),
        ac_column=scale.ac_column,
        fragility_column=scale.fragility_column,
        status=stats["status"],
        insufficient_reason=stats["reason"],
        observed_rho=stats["rho"],
        n_pairs=stats["n_pairs"],
        patient_count=row["patient_count"],
        interval_count=row["interval_count"],
        permutation_stratification=_permutation_stratification(decomposition_view, frame),
    )
    return row, descriptor


def _build_decomposition_rows(
    *,
    base_frame: pd.DataFrame,
    run_dir: Path,
    cohort: str,
    analysis_role: str,
    aggregation_level: str,
) -> tuple[list[dict[str, Any]], dict[tuple[str, str, str, str, str, str], DecompositionDescriptor]]:
    rows: list[dict[str, Any]] = []
    descriptors: dict[tuple[str, str, str, str, str, str], DecompositionDescriptor] = {}
    if base_frame.empty:
        return rows, descriptors

    region_values = sorted(value for value in base_frame["region"].dropna().unique().tolist()) if "region" in base_frame.columns else []
    band_values = []
    if "band" in base_frame.columns:
        band_values = [
            str(value)
            for value in sorted(base_frame["band"].dropna().astype(str).unique().tolist())
            if str(value)
        ]

    for scale in SCALE_SPECS:
        if scale.ac_column not in base_frame.columns or scale.fragility_column not in base_frame.columns:
            continue
        scale_frame = base_frame.dropna(subset=[scale.ac_column, scale.fragility_column]).copy()

        pooled_row, pooled_descriptor = _build_descriptor(
            run_dir=run_dir,
            cohort=cohort,
            analysis_role=analysis_role,
            aggregation_level=aggregation_level,
            scale=scale,
            decomposition_view="pooled",
            grouping_stratum="all",
            frame=scale_frame,
        )
        rows.append(pooled_row)
        descriptors[pooled_descriptor.key] = pooled_descriptor

        between_frame = (
            scale_frame.groupby("patient", dropna=False)[[scale.ac_column, scale.fragility_column]]
            .mean()
            .reset_index()
        )
        between_row, between_descriptor = _build_descriptor(
            run_dir=run_dir,
            cohort=cohort,
            analysis_role=analysis_role,
            aggregation_level=aggregation_level,
            scale=scale,
            decomposition_view="between_patient",
            grouping_stratum="all",
            frame=between_frame,
        )
        rows.append(between_row)
        descriptors[between_descriptor.key] = between_descriptor

        within_patient_frame = _center_within_group(scale_frame, "patient", scale.ac_column, scale.fragility_column)
        within_row, within_descriptor = _build_descriptor(
            run_dir=run_dir,
            cohort=cohort,
            analysis_role=analysis_role,
            aggregation_level=aggregation_level,
            scale=scale,
            decomposition_view="within_patient",
            grouping_stratum="all",
            frame=within_patient_frame,
        )
        rows.append(within_row)
        descriptors[within_descriptor.key] = within_descriptor

        if region_values:
            for region_value in region_values:
                region_frame = scale_frame.loc[scale_frame["region"] == region_value].copy()
                region_row, region_descriptor = _build_descriptor(
                    run_dir=run_dir,
                    cohort=cohort,
                    analysis_role=analysis_role,
                    aggregation_level=aggregation_level,
                    scale=scale,
                    decomposition_view="within_region",
                    grouping_stratum=_format_grouping_value(region_value),
                    frame=region_frame,
                )
                rows.append(region_row)
                descriptors[region_descriptor.key] = region_descriptor

        real_band_values = [value for value in band_values if value != "all"]
        if real_band_values:
            for band_value in real_band_values:
                band_frame = scale_frame.loc[scale_frame["band"].astype(str) == band_value].copy()
                band_row, band_descriptor = _build_descriptor(
                    run_dir=run_dir,
                    cohort=cohort,
                    analysis_role=analysis_role,
                    aggregation_level=aggregation_level,
                    scale=scale,
                    decomposition_view="within_band",
                    grouping_stratum=band_value,
                    frame=band_frame,
                )
                rows.append(band_row)
                descriptors[band_descriptor.key] = band_descriptor
        else:
            insufficient_row, insufficient_descriptor = _build_descriptor(
                run_dir=run_dir,
                cohort=cohort,
                analysis_role=analysis_role,
                aggregation_level=aggregation_level,
                scale=scale,
                decomposition_view="within_band",
                grouping_stratum="all",
                frame=scale_frame.iloc[0:0].copy(),
            )
            insufficient_row["status"] = "insufficient"
            insufficient_row["insufficient_reason"] = "single_band_aggregation"
            rows.append(insufficient_row)
            insufficient_descriptor.status = "insufficient"
            insufficient_descriptor.insufficient_reason = "single_band_aggregation"
            descriptors[insufficient_descriptor.key] = insufficient_descriptor

    return rows, descriptors


def _simulate_structural_frame(frame: pd.DataFrame, rng: np.random.Generator) -> pd.DataFrame:
    if frame.empty:
        return frame.copy()
    meta_columns = [
        column
        for column in frame.columns
        if column
        not in {
            "raw_average_controllability",
            "raw_fragility",
            "feature_z_average_controllability",
            "feature_z_fragility",
            "feature_z_within_band_average_controllability",
            "feature_z_within_band_fragility",
        }
    ]
    group_columns = ["patient"]
    if "band" in frame.columns:
        unique_bands = [value for value in frame["band"].dropna().astype(str).unique().tolist() if value and value != "all"]
        if unique_bands:
            group_columns = ["patient", "band"]
    simulated_parts: list[pd.DataFrame] = []
    for _, subset in frame.groupby(group_columns, dropna=False):
        node_count = int(len(subset))
        if node_count <= 0:
            continue
        matrix = rng.normal(scale=STRUCTURAL_MATRIX_SCALE, size=(node_count, node_count))
        radius = float(np.max(np.abs(np.linalg.eigvals(matrix))))
        if radius >= STRUCTURAL_SPECTRAL_RADIUS_CAP and radius > 0:
            matrix = matrix / (radius + 0.05)
        ac_values = compute_average_controllability(matrix)
        fragility_values = compute_column_fragility(matrix)
        synthetic = subset[meta_columns].copy()
        synthetic["raw_average_controllability"] = pd.Series(ac_values, index=synthetic.index, dtype=float)
        synthetic["raw_fragility"] = pd.Series(fragility_values, index=synthetic.index, dtype=float)
        simulated_parts.append(synthetic)
    if not simulated_parts:
        return frame.iloc[0:0].copy()
    simulated = pd.concat(simulated_parts, ignore_index=True, sort=False)
    simulated["feature_z_average_controllability"] = (
        simulated.groupby("patient", dropna=False)["raw_average_controllability"].transform(_zscore)
    )
    simulated["feature_z_fragility"] = simulated.groupby("patient", dropna=False)["raw_fragility"].transform(_zscore)
    band_group = ["patient"] if "band" not in simulated.columns else ["patient", "band"]
    simulated["feature_z_within_band_average_controllability"] = (
        simulated.groupby(band_group, dropna=False)["raw_average_controllability"].transform(_zscore)
    )
    simulated["feature_z_within_band_fragility"] = (
        simulated.groupby(band_group, dropna=False)["raw_fragility"].transform(_zscore)
    )
    return simulated


def _structural_null_summary(
    *,
    base_frame: pd.DataFrame,
    run_dir: Path,
    cohort: str,
    analysis_role: str,
    aggregation_level: str,
    seed: int,
) -> pd.DataFrame:
    if base_frame.empty:
        return pd.DataFrame()
    rng = np.random.default_rng(seed)
    structural_rows: list[dict[str, Any]] = []
    for replicate in range(STRUCTURAL_NULL_REPLICATES):
        synthetic = _simulate_structural_frame(base_frame, rng)
        replicate_rows, _ = _build_decomposition_rows(
            base_frame=synthetic,
            run_dir=run_dir,
            cohort=cohort,
            analysis_role=analysis_role,
            aggregation_level=aggregation_level,
        )
        for row in replicate_rows:
            if row["status"] != "complete" or row["observed_rho"] is None:
                continue
            structural_rows.append(
                {
                    "cohort": row["cohort"],
                    "analysis_role": row["analysis_role"],
                    "aggregation_level": row["aggregation_level"],
                    "value_scale": row["value_scale"],
                    "decomposition_view": row["decomposition_view"],
                    "grouping_stratum": row["grouping_stratum"],
                    "replicate": replicate,
                    "rho": row["observed_rho"],
                }
            )
    if not structural_rows:
        return pd.DataFrame()
    structural = pd.DataFrame(structural_rows)
    summary = (
        structural.groupby(
            ["cohort", "analysis_role", "aggregation_level", "value_scale", "decomposition_view", "grouping_stratum"],
            dropna=False,
        )["rho"]
        .agg(
            structural_rho_mean="mean",
            structural_rho_median="median",
            structural_rho_min="min",
            structural_rho_max="max",
            structural_replicates="count",
        )
        .reset_index()
    )
    summary["structural_seed"] = seed
    return summary


def _permute_within_groups(
    values: pd.Series,
    groups: pd.Series | None,
    rng: np.random.Generator,
) -> pd.Series:
    permuted = values.copy()
    if groups is None:
        permuted.iloc[:] = values.to_numpy()[rng.permutation(len(values))]
        return permuted
    group_codes = groups.astype(str)
    for _, index in group_codes.groupby(group_codes, sort=False).groups.items():
        index_list = list(index)
        if len(index_list) < 2:
            continue
        permuted.iloc[index_list] = values.iloc[index_list].to_numpy()[rng.permutation(len(index_list))]
    return permuted


def _permutation_summary(descriptor: DecompositionDescriptor, seed: int) -> dict[str, Any]:
    row = {
        "run_dir": descriptor.run_dir,
        "cohort": descriptor.cohort,
        "analysis_role": descriptor.analysis_role,
        "aggregation_level": descriptor.aggregation_level,
        "value_scale": descriptor.value_scale,
        "decomposition_view": descriptor.decomposition_view,
        "grouping_stratum": descriptor.grouping_stratum,
        "observed_rho": descriptor.observed_rho,
        "observed_n_pairs": descriptor.n_pairs,
        "observed_status": descriptor.status,
        "structural_rho_mean": None,
        "structural_rho_median": None,
        "structural_rho_min": None,
        "structural_rho_max": None,
        "structural_replicates": None,
        "structural_seed": None,
        "permutation_rho_mean": None,
        "permutation_rho_median": None,
        "permutation_rho_min": None,
        "permutation_rho_max": None,
        "permutation_abs_ge_rate": None,
        "permutation_replicates": None,
        "permutation_seed": seed,
        "permutation_stratification": descriptor.permutation_stratification,
    }
    if descriptor.status != "complete" or descriptor.observed_rho is None or descriptor.frame.empty:
        return row

    rng = np.random.default_rng(seed)
    frame = descriptor.frame[
        [descriptor.ac_column, descriptor.fragility_column] + (["patient"] if "patient" in descriptor.frame.columns else [])
    ].dropna().reset_index(drop=True)
    group_series = None
    if descriptor.permutation_stratification == "within_patient" and "patient" in frame.columns:
        group_series = frame["patient"]
    permutation_rhos: list[float] = []
    for _ in range(PERMUTATION_REPLICATES):
        permuted = frame.copy()
        permuted[descriptor.fragility_column] = _permute_within_groups(
            permuted[descriptor.fragility_column],
            group_series,
            rng,
        )
        stats = _safe_spearman(permuted, descriptor.ac_column, descriptor.fragility_column)
        if stats["status"] == "complete" and stats["rho"] is not None:
            permutation_rhos.append(float(stats["rho"]))
    if not permutation_rhos:
        return row
    rho_values = np.asarray(permutation_rhos, dtype=float)
    observed_abs = abs(float(descriptor.observed_rho))
    row.update(
        {
            "permutation_rho_mean": float(rho_values.mean()),
            "permutation_rho_median": float(np.median(rho_values)),
            "permutation_rho_min": float(rho_values.min()),
            "permutation_rho_max": float(rho_values.max()),
            "permutation_abs_ge_rate": float(np.mean(np.abs(rho_values) >= observed_abs)),
            "permutation_replicates": int(len(rho_values)),
        }
    )
    return row


def _gini(values: list[int]) -> float | None:
    if not values:
        return None
    array = np.asarray(sorted(values), dtype=float)
    if np.all(array == 0):
        return 0.0
    index = np.arange(1, len(array) + 1, dtype=float)
    return float((2 * np.sum(index * array) / (len(array) * np.sum(array))) - (len(array) + 1) / len(array))


def _cohort_qc_summary(frame: pd.DataFrame, run_dir: Path) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    if frame.empty:
        return pd.DataFrame(columns=QC_SUMMARY_COLUMNS)
    for cohort in REPORTING_COHORTS:
        subset = frame.loc[frame["cohort"] == cohort.name].copy()
        if subset.empty:
            rows.append(
                {
                    "run_dir": run_dir.as_posix(),
                    "cohort": cohort.name,
                    "analysis_role": cohort.analysis_role,
                    "patient_count": 0,
                    "interval_count": 0,
                    "patient_interval_gini": None,
                    "region_1_interval_count": 0,
                    "region_2_interval_count": 0,
                    "region_3_interval_count": 0,
                }
            )
            continue
        interval_counts = (
            subset[["patient", "interval_id"]]
            .dropna()
            .drop_duplicates()
            .groupby("patient", dropna=False)
            .size()
            .tolist()
        )
        region_counts = (
            subset[["patient", "interval_id", "region"]]
            .dropna(subset=["patient", "interval_id"])
            .drop_duplicates()
            .groupby("region", dropna=False)
            .size()
        )
        rows.append(
            {
                "run_dir": run_dir.as_posix(),
                "cohort": cohort.name,
                "analysis_role": cohort.analysis_role,
                "patient_count": _patient_count(subset),
                "interval_count": _unique_interval_count(subset),
                "patient_interval_gini": _gini([int(value) for value in interval_counts]),
                "region_1_interval_count": int(region_counts.get(1.0, 0)),
                "region_2_interval_count": int(region_counts.get(2.0, 0)),
                "region_3_interval_count": int(region_counts.get(3.0, 0)),
            }
        )
    return pd.DataFrame(rows, columns=QC_SUMMARY_COLUMNS)


def _paired_difference_summary(
    frame: pd.DataFrame,
    *,
    group_col: str,
    group_a: Any,
    group_b: Any,
    value_col: str,
    seed: int,
) -> dict[str, Any]:
    subset = frame.loc[frame[group_col].isin([group_a, group_b])].copy()
    if subset.empty:
        return {
            "observed_value": None,
            "p_value": None,
            "paired_patient_count": 0,
            "status": "insufficient",
            "insufficient_reason": "missing_groups",
        }
    paired = (
        subset.groupby(["patient", group_col], dropna=False)[value_col]
        .mean()
        .unstack(group_col)
    )
    if group_a not in paired.columns or group_b not in paired.columns:
        return {
            "observed_value": None,
            "p_value": None,
            "paired_patient_count": int(paired.dropna(how="all").shape[0]),
            "status": "insufficient",
            "insufficient_reason": "missing_groups",
        }
    paired = paired[[group_a, group_b]].dropna()
    paired_patient_count = int(len(paired))
    if paired_patient_count < MIN_PAIRED_PATIENTS:
        return {
            "observed_value": None,
            "p_value": None,
            "paired_patient_count": paired_patient_count,
            "status": "insufficient",
            "insufficient_reason": "too_few_paired_patients",
        }
    diffs = paired[group_b] - paired[group_a]
    observed_value = float(diffs.mean())
    rng = np.random.default_rng(seed)
    diff_values = diffs.to_numpy(dtype=float)
    null_values: list[float] = []
    for _ in range(PAIR_PERMUTATION_REPLICATES):
        signs = rng.choice([-1.0, 1.0], size=len(diff_values))
        null_values.append(float(np.mean(diff_values * signs)))
    null_array = np.asarray(null_values, dtype=float)
    p_value = float(np.mean(np.abs(null_array) >= abs(observed_value)))
    return {
        "observed_value": observed_value,
        "p_value": p_value,
        "paired_patient_count": paired_patient_count,
        "status": "complete",
        "insufficient_reason": None,
    }


def _coupling_summary_for_scan(
    frame: pd.DataFrame,
    *,
    ac_col: str,
    fragility_col: str,
    seed: int,
) -> dict[str, Any]:
    stats = _safe_spearman(frame, ac_col, fragility_col)
    if stats["status"] != "complete" or stats["rho"] is None:
        return {
            "observed_value": None,
            "p_value": None,
            "paired_patient_count": _patient_count(frame),
            "status": stats["status"],
            "insufficient_reason": stats["reason"],
        }
    descriptor = DecompositionDescriptor(
        run_dir="",
        cohort="",
        analysis_role="",
        aggregation_level="",
        value_scale="feature_z_within_band",
        decomposition_view="pooled",
        grouping_stratum="all",
        frame=frame.copy(),
        ac_column=ac_col,
        fragility_column=fragility_col,
        status="complete",
        insufficient_reason=None,
        observed_rho=float(stats["rho"]),
        n_pairs=int(stats["n_pairs"]),
        patient_count=_patient_count(frame),
        interval_count=_unique_interval_count(frame),
        permutation_stratification=_permutation_stratification("pooled", frame),
    )
    permutation = _permutation_summary(descriptor, seed)
    return {
        "observed_value": float(stats["rho"]),
        "p_value": permutation["permutation_abs_ge_rate"],
        "paired_patient_count": _patient_count(frame),
        "status": "complete",
        "insufficient_reason": None,
    }


def _direction(value: float | None) -> str | None:
    if value is None or pd.isna(value):
        return None
    if value > 0:
        return "positive"
    if value < 0:
        return "negative"
    return "zero"


def _inclusion_threshold_scan(
    full_coupling_frame: pd.DataFrame,
    full_ac_frame: pd.DataFrame,
    full_fragility_frame: pd.DataFrame,
    run_dir: Path,
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    if full_coupling_frame.empty:
        return pd.DataFrame(columns=INCLUSION_SCAN_COLUMNS)
    patient_interval_counts = (
        full_coupling_frame[["patient", "interval_id"]]
        .dropna()
        .drop_duplicates()
        .groupby("patient", dropna=False)
        .size()
    )
    for threshold in INCLUSION_THRESHOLD_GRID:
        patients = {
            str(patient)
            for patient, count in patient_interval_counts.items()
            if int(count) >= threshold
        }
        coupling_subset = subset_by_patient_set(full_coupling_frame, patients)
        ac_subset = subset_by_patient_set(full_ac_frame, patients)
        fragility_subset = subset_by_patient_set(full_fragility_frame, patients)
        eligible_patient_count = _patient_count(coupling_subset)
        eligible_interval_count = _unique_interval_count(coupling_subset)
        scan_rows = [
            (
                HEADLINE_FINDING_BY_ID["overall_coupling"],
                _coupling_summary_for_scan(
                    coupling_subset,
                    ac_col="feature_z_within_band_average_controllability",
                    fragility_col="feature_z_within_band_fragility",
                    seed=threshold,
                ),
                0,
                0,
            ),
            (
                HEADLINE_FINDING_BY_ID["region2_coupling"],
                _coupling_summary_for_scan(
                    coupling_subset.loc[coupling_subset["region"] == 2.0].copy(),
                    ac_col="feature_z_within_band_average_controllability",
                    fragility_col="feature_z_within_band_fragility",
                    seed=threshold + 100,
                ),
                _unique_interval_count(coupling_subset.loc[coupling_subset["region"] == 2.0].copy()),
                _unique_interval_count(coupling_subset.loc[coupling_subset["region"] == 1.0].copy()),
            ),
        ]
        ac_contrast = _paired_difference_summary(
            ac_subset,
            group_col="region",
            group_a=1.0,
            group_b=2.0,
            value_col=CONTRAST_VALUE_COLUMN,
            seed=threshold + 200,
        )
        fragility_contrast = _paired_difference_summary(
            fragility_subset,
            group_col="region",
            group_a=1.0,
            group_b=2.0,
            value_col=CONTRAST_VALUE_COLUMN,
            seed=threshold + 300,
        )
        scan_rows.extend(
            [
                (
                    HEADLINE_FINDING_BY_ID["region2_ac_elevation"],
                    ac_contrast,
                    _unique_interval_count(ac_subset.loc[ac_subset["region"] == 2.0].copy()),
                    _unique_interval_count(ac_subset.loc[ac_subset["region"] == 1.0].copy()),
                ),
                (
                    HEADLINE_FINDING_BY_ID["region2_fragility_reduction"],
                    fragility_contrast,
                    _unique_interval_count(fragility_subset.loc[fragility_subset["region"] == 2.0].copy()),
                    _unique_interval_count(fragility_subset.loc[fragility_subset["region"] == 1.0].copy()),
                ),
            ]
        )

        for finding, summary, boundary_count, remote_count in scan_rows:
            rows.append(
                {
                    "run_dir": run_dir.as_posix(),
                    "threshold_kind": "inclusion_min_intervals",
                    "threshold_value": int(threshold),
                    "eligible_patient_count": eligible_patient_count,
                    "eligible_interval_count": eligible_interval_count,
                    "finding_id": finding.finding_id,
                    "finding_label": finding.finding_label,
                    "finding_kind": finding.finding_kind,
                    "expected_direction": finding.expected_direction,
                    "observed_value": summary["observed_value"],
                    "p_value": summary["p_value"],
                    "paired_patient_count": summary["paired_patient_count"],
                    "boundary_interval_count": boundary_count,
                    "remote_interval_count": remote_count,
                    "status": summary["status"],
                    "insufficient_reason": summary["insufficient_reason"],
                }
            )
    return pd.DataFrame(rows, columns=INCLUSION_SCAN_COLUMNS)


def _distance_threshold_scan(
    coupling_frames_by_cohort: dict[str, pd.DataFrame],
    contrast_frames_by_cohort: dict[str, dict[str, pd.DataFrame]],
    run_dir: Path,
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for cohort in REPORTING_COHORTS:
        subset = coupling_frames_by_cohort.get(cohort.name, pd.DataFrame()).copy()
        numeric_subset = subset.loc[subset["distance_mm"].notna()].copy()
        excluded_missing_distance = _unique_interval_count(subset.loc[subset["distance_mm"].isna()].copy())
        ac_metric_frame = contrast_frames_by_cohort.get(cohort.name, {}).get("average_controllability", pd.DataFrame()).copy()
        ac_metric_frame = ac_metric_frame.loc[ac_metric_frame["distance_mm"].notna()].copy()
        fragility_metric_frame = contrast_frames_by_cohort.get(cohort.name, {}).get("fragility", pd.DataFrame()).copy()
        fragility_metric_frame = fragility_metric_frame.loc[fragility_metric_frame["distance_mm"].notna()].copy()
        for threshold in DISTANCE_THRESHOLD_GRID:
            relabeled = numeric_subset.copy()
            relabeled["distance_region"] = np.where(relabeled["distance_mm"] <= threshold, "boundary", "remote")
            boundary_subset = relabeled.loc[relabeled["distance_region"] == "boundary"].copy()
            boundary_count = _unique_interval_count(boundary_subset)
            remote_count = _unique_interval_count(relabeled.loc[relabeled["distance_region"] == "remote"].copy())
            eligible_patient_count = _patient_count(relabeled)
            eligible_interval_count = _unique_interval_count(relabeled)
            ac_relabeled = ac_metric_frame.copy()
            ac_relabeled["distance_region"] = np.where(ac_relabeled["distance_mm"] <= threshold, "boundary", "remote")
            fragility_relabeled = fragility_metric_frame.copy()
            fragility_relabeled["distance_region"] = np.where(fragility_relabeled["distance_mm"] <= threshold, "boundary", "remote")
            summaries = [
                (
                    "distance_boundary_coupling",
                    "Boundary AC-NF coupling after distance relabeling",
                    "coupling",
                    "negative",
                    _coupling_summary_for_scan(
                        boundary_subset,
                        ac_col="feature_z_within_band_average_controllability",
                        fragility_col="feature_z_within_band_fragility",
                        seed=int(threshold * 1000) + 10,
                    ),
                ),
                (
                    "distance_boundary_minus_remote_average_controllability",
                    "Boundary minus remote average controllability",
                    "contrast",
                    "positive",
                    _paired_difference_summary(
                        ac_relabeled,
                        group_col="distance_region",
                        group_a="remote",
                        group_b="boundary",
                        value_col=CONTRAST_VALUE_COLUMN,
                        seed=int(threshold * 1000) + 20,
                    ),
                ),
                (
                    "distance_boundary_minus_remote_fragility",
                    "Boundary minus remote fragility",
                    "contrast",
                    "negative",
                    _paired_difference_summary(
                        fragility_relabeled,
                        group_col="distance_region",
                        group_a="remote",
                        group_b="boundary",
                        value_col=CONTRAST_VALUE_COLUMN,
                        seed=int(threshold * 1000) + 30,
                    ),
                ),
            ]
            for finding_id, finding_label, finding_kind, expected_direction, summary in summaries:
                rows.append(
                    {
                        "run_dir": run_dir.as_posix(),
                        "cohort": cohort.name,
                        "analysis_role": cohort.analysis_role,
                        "threshold_kind": "distance_mm_boundary",
                        "threshold_value": float(threshold),
                        "eligible_patient_count": eligible_patient_count,
                        "eligible_interval_count": eligible_interval_count,
                        "excluded_missing_distance_count": excluded_missing_distance,
                        "finding_id": finding_id,
                        "finding_label": finding_label,
                        "finding_kind": finding_kind,
                        "expected_direction": expected_direction,
                        "observed_value": summary["observed_value"],
                        "p_value": summary["p_value"],
                        "paired_patient_count": summary["paired_patient_count"],
                        "boundary_interval_count": boundary_count,
                        "remote_interval_count": remote_count,
                        "status": summary["status"],
                        "insufficient_reason": summary["insufficient_reason"],
                    }
                )
    return pd.DataFrame(rows, columns=DISTANCE_SCAN_COLUMNS)


def _scan_status_summary(
    frame: pd.DataFrame,
    *,
    reference_threshold: float | int | None,
) -> dict[str, Any]:
    if reference_threshold is None:
        return {
            "direction_status": "not_applicable",
            "significance_status": "not_applicable",
            "unstable_thresholds": "",
            "insufficient_thresholds": "",
        }
    reference_row = frame.loc[frame["threshold_value"] == reference_threshold].copy()
    if reference_row.empty or reference_row["status"].iloc[0] != "complete" or pd.isna(reference_row["observed_value"].iloc[0]):
        insufficient_values = sorted(frame.loc[frame["status"] != "complete", "threshold_value"].tolist())
        return {
            "direction_status": "insufficient",
            "significance_status": "insufficient",
            "unstable_thresholds": "",
            "insufficient_thresholds": ",".join(str(value) for value in insufficient_values),
        }
    reference_value = float(reference_row["observed_value"].iloc[0])
    reference_direction = _direction(reference_value)
    reference_significant = bool(float(reference_row["p_value"].iloc[0]) < 0.05) if not pd.isna(reference_row["p_value"].iloc[0]) else False

    valid = frame.loc[frame["status"] == "complete"].copy()
    insufficient_values = sorted(frame.loc[frame["status"] != "complete", "threshold_value"].tolist())
    unstable_direction = sorted(
        value
        for value, observed in zip(valid["threshold_value"], valid["observed_value"], strict=False)
        if _direction(observed) not in {reference_direction, None}
    )
    unstable_significance: list[float | int] = []
    if reference_significant:
        unstable_significance = sorted(
            value
            for value, p_value in zip(valid["threshold_value"], valid["p_value"], strict=False)
            if pd.isna(p_value) or float(p_value) >= 0.05
        )
    direction_status = "stable" if not unstable_direction else "direction_reversal"
    if not reference_significant:
        significance_status = "reference_nonsignificant"
    else:
        significance_status = "stable" if not unstable_significance else "significance_loss"
    return {
        "direction_status": direction_status,
        "significance_status": significance_status,
        "unstable_thresholds": ",".join(str(value) for value in unstable_direction if value != reference_threshold),
        "insufficient_thresholds": ",".join(str(value) for value in insufficient_values),
    }


def _stability_matrix(
    inclusion_scan: pd.DataFrame,
    distance_scan: pd.DataFrame,
    run_dir: Path,
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for cohort in REPORTING_COHORTS:
        reference_threshold = REFERENCE_THRESHOLD_BY_COHORT[cohort.name]
        for finding in HEADLINE_FINDINGS:
            inclusion_subset = inclusion_scan.loc[inclusion_scan["finding_id"] == finding.finding_id].copy()
            inclusion_summary = _scan_status_summary(
                inclusion_subset,
                reference_threshold=reference_threshold,
            )
            distance_summary = {
                "direction_status": "not_applicable",
                "significance_status": "not_applicable",
                "unstable_thresholds": "",
                "insufficient_thresholds": "",
            }
            if finding.distance_scan_finding_id is not None:
                distance_subset = distance_scan.loc[
                    (distance_scan["cohort"] == cohort.name)
                    & (distance_scan["finding_id"] == finding.distance_scan_finding_id)
                ].copy()
                distance_summary = _scan_status_summary(
                    distance_subset,
                    reference_threshold=PRIMARY_DISTANCE_THRESHOLD_MM,
                )
            overall_status = "stable"
            if "insufficient" in {inclusion_summary["direction_status"], inclusion_summary["significance_status"], distance_summary["direction_status"], distance_summary["significance_status"]}:
                overall_status = "insufficient"
            elif "direction_reversal" in {inclusion_summary["direction_status"], distance_summary["direction_status"]}:
                overall_status = "direction_reversal"
            elif "significance_loss" in {inclusion_summary["significance_status"], distance_summary["significance_status"]}:
                overall_status = "significance_loss"
            elif all(
                status == "not_applicable"
                for status in [
                    inclusion_summary["direction_status"],
                    inclusion_summary["significance_status"],
                    distance_summary["direction_status"],
                    distance_summary["significance_status"],
                ]
            ):
                overall_status = "not_applicable"
            rows.append(
                {
                    "run_dir": run_dir.as_posix(),
                    "cohort": cohort.name,
                    "analysis_role": cohort.analysis_role,
                    "finding_id": finding.finding_id,
                    "finding_label": finding.finding_label,
                    "inclusion_reference_threshold": reference_threshold,
                    "inclusion_direction_status": inclusion_summary["direction_status"],
                    "inclusion_significance_status": inclusion_summary["significance_status"],
                    "inclusion_unstable_thresholds": inclusion_summary["unstable_thresholds"],
                    "inclusion_insufficient_thresholds": inclusion_summary["insufficient_thresholds"],
                    "distance_reference_threshold": PRIMARY_DISTANCE_THRESHOLD_MM if finding.distance_scan_finding_id is not None else None,
                    "distance_direction_status": distance_summary["direction_status"],
                    "distance_significance_status": distance_summary["significance_status"],
                    "distance_unstable_thresholds": distance_summary["unstable_thresholds"],
                    "distance_insufficient_thresholds": distance_summary["insufficient_thresholds"],
                    "overall_stability_status": overall_status,
                }
            )
    return pd.DataFrame(rows, columns=STABILITY_MATRIX_COLUMNS)


def _headline_coupling_descriptor_key(
    cohort_name: str,
    analysis_role: str,
    finding_id: str,
) -> tuple[str, str, str, str, str, str]:
    if finding_id == "overall_coupling":
        return (
            cohort_name,
            "band_aggregated_interval",
            "feature_z_within_band",
            "pooled",
            "all",
            analysis_role,
        )
    return (
        cohort_name,
        "band_aggregated_interval",
        "feature_z_within_band",
        "within_region",
        "2.0",
        analysis_role,
    )


def _coupling_status(
    observed_row: pd.Series,
    null_row: pd.Series | None,
    stability_row: pd.Series,
) -> tuple[str, float | None]:
    if observed_row["observed_status"] != "complete" or pd.isna(observed_row["observed_value"]):
        return "insufficient", None
    structural_gap = None
    if null_row is not None and not pd.isna(null_row.get("structural_rho_median")):
        structural_gap = abs(float(observed_row["observed_value"]) - float(null_row["structural_rho_median"]))
        if structural_gap < 0.10:
            return "artifact_risk", structural_gap
    if stability_row["overall_stability_status"] in {"direction_reversal", "significance_loss"}:
        return "threshold_sensitive", structural_gap
    permutation_rate = None if null_row is None else null_row.get("permutation_abs_ge_rate")
    if permutation_rate is not None and not pd.isna(permutation_rate) and float(permutation_rate) < 0.05 and (structural_gap is None or structural_gap >= 0.15):
        return "supported", structural_gap
    return "exploratory", structural_gap


def _contrast_status(observed_row: pd.Series, stability_row: pd.Series) -> str:
    if observed_row["observed_status"] != "complete" or pd.isna(observed_row["observed_value"]):
        return "insufficient"
    if stability_row["overall_stability_status"] in {"direction_reversal", "significance_loss"}:
        return "threshold_sensitive"
    if not pd.isna(observed_row["observed_p_value"]) and float(observed_row["observed_p_value"]) < 0.05:
        return "supported"
    return "exploratory"


def _cohort_headline_observations(
    frames_by_cohort: dict[str, pd.DataFrame],
    contrast_frames_by_cohort: dict[str, dict[str, pd.DataFrame]],
    descriptor_lookup: dict[tuple[str, str, str, str, str, str], DecompositionDescriptor],
    null_lookup: dict[tuple[str, str, str, str, str, str], pd.Series],
    stability_matrix: pd.DataFrame,
    run_dir: Path,
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for cohort in REPORTING_COHORTS:
        subset = frames_by_cohort.get(cohort.name, pd.DataFrame()).copy()
        if subset.empty:
            subset = pd.DataFrame(columns=["patient", "interval_id", "region", "raw_average_controllability", "raw_fragility"])
        contrast_rows = {
            "region2_ac_elevation": _paired_difference_summary(
                contrast_frames_by_cohort.get(cohort.name, {}).get("average_controllability", pd.DataFrame()).copy(),
                group_col="region",
                group_a=1.0,
                group_b=2.0,
                value_col=CONTRAST_VALUE_COLUMN,
                seed=500 + len(rows),
            ),
            "region2_fragility_reduction": _paired_difference_summary(
                contrast_frames_by_cohort.get(cohort.name, {}).get("fragility", pd.DataFrame()).copy(),
                group_col="region",
                group_a=1.0,
                group_b=2.0,
                value_col=CONTRAST_VALUE_COLUMN,
                seed=800 + len(rows),
            ),
        }
        for finding in HEADLINE_FINDINGS:
            stability_row = stability_matrix.loc[
                (stability_matrix["cohort"] == cohort.name)
                & (stability_matrix["finding_id"] == finding.finding_id)
            ].iloc[0]
            if finding.finding_kind == "coupling":
                descriptor_key = _headline_coupling_descriptor_key(
                    cohort.name,
                    cohort.analysis_role,
                    finding.finding_id,
                )
                descriptor = descriptor_lookup.get(descriptor_key)
                null_row = null_lookup.get(descriptor_key)
                observed_value = descriptor.observed_rho if descriptor is not None else None
                observed_status = descriptor.status if descriptor is not None else "insufficient"
                observed_n_pairs = descriptor.n_pairs if descriptor is not None else 0
                observed_p = None if null_row is None else null_row.get("permutation_abs_ge_rate")
                observed_series = pd.Series(
                    {
                        "observed_value": observed_value,
                        "observed_status": observed_status,
                        "observed_p_value": observed_p,
                        "observed_n_pairs": observed_n_pairs,
                    }
                )
                robustness_status, structural_gap = _coupling_status(observed_series, null_row, stability_row)
                rows.append(
                    {
                        "run_dir": run_dir.as_posix(),
                        "cohort": cohort.name,
                        "analysis_role": cohort.analysis_role,
                        "finding_id": finding.finding_id,
                        "finding_label": finding.finding_label,
                        "finding_kind": finding.finding_kind,
                        "expected_direction": finding.expected_direction,
                        "reference_threshold": REFERENCE_THRESHOLD_BY_COHORT[cohort.name],
                        "reference_distance_threshold_mm": PRIMARY_DISTANCE_THRESHOLD_MM if finding.distance_scan_finding_id else None,
                        "observed_value": observed_value,
                        "observed_p_value": observed_p,
                        "observed_status": observed_status,
                        "observed_n_pairs": observed_n_pairs,
                        "structural_rho_median": None if null_row is None else null_row.get("structural_rho_median"),
                        "structural_gap": structural_gap,
                        "permutation_abs_ge_rate": None if null_row is None else null_row.get("permutation_abs_ge_rate"),
                        "inclusion_direction_status": stability_row["inclusion_direction_status"],
                        "inclusion_significance_status": stability_row["inclusion_significance_status"],
                        "distance_direction_status": stability_row["distance_direction_status"],
                        "distance_significance_status": stability_row["distance_significance_status"],
                        "robustness_status": robustness_status,
                        "source_artifact": (
                            "10_coupling_robustness/null_comparison_summary.csv"
                            f"#{cohort.name}|band_aggregated_interval|feature_z_within_band|"
                            f"{'pooled|all' if finding.finding_id == 'overall_coupling' else 'within_region|2.0'}"
                        ),
                    }
                )
            else:
                contrast = contrast_rows[finding.finding_id]
                observed_series = pd.Series(
                    {
                        "observed_value": contrast["observed_value"],
                        "observed_status": contrast["status"],
                        "observed_p_value": contrast["p_value"],
                    }
                )
                rows.append(
                    {
                        "run_dir": run_dir.as_posix(),
                        "cohort": cohort.name,
                        "analysis_role": cohort.analysis_role,
                        "finding_id": finding.finding_id,
                        "finding_label": finding.finding_label,
                        "finding_kind": finding.finding_kind,
                        "expected_direction": finding.expected_direction,
                        "reference_threshold": REFERENCE_THRESHOLD_BY_COHORT[cohort.name],
                        "reference_distance_threshold_mm": PRIMARY_DISTANCE_THRESHOLD_MM if finding.distance_scan_finding_id else None,
                        "observed_value": contrast["observed_value"],
                        "observed_p_value": contrast["p_value"],
                        "observed_status": contrast["status"],
                        "observed_n_pairs": contrast["paired_patient_count"],
                        "structural_rho_median": None,
                        "structural_gap": None,
                        "permutation_abs_ge_rate": contrast["p_value"],
                        "inclusion_direction_status": stability_row["inclusion_direction_status"],
                        "inclusion_significance_status": stability_row["inclusion_significance_status"],
                        "distance_direction_status": stability_row["distance_direction_status"],
                        "distance_significance_status": stability_row["distance_significance_status"],
                        "robustness_status": _contrast_status(observed_series, stability_row),
                        "source_artifact": "10_coupling_robustness/inclusion_threshold_scan.csv",
                    }
                )
    return pd.DataFrame(rows, columns=ROBUSTNESS_SUMMARY_COLUMNS)


def _write_markdown_summary(
    path: Path,
    qc_summary: pd.DataFrame,
    robustness_summary: pd.DataFrame,
    stability_matrix: pd.DataFrame,
) -> None:
    lines = [
        "# Coupling Robustness Summary",
        "",
        "This stage tests whether AC-NF coupling and the core region-2 findings survive decomposition, null calibration, and threshold scans.",
        "",
        "## Cohort QC",
        "",
    ]
    if qc_summary.empty:
        lines.append("- No cohort QC summary was available.")
    else:
        for row in qc_summary.itertuples(index=False):
            lines.append(
                f"- `{row.cohort}` ({row.analysis_role}): {row.patient_count} patients, {row.interval_count} intervals, gini={row.patient_interval_gini}"
            )
    lines.extend(["", "## Headline Findings", ""])
    if robustness_summary.empty:
        lines.append("- No headline findings were classified.")
    else:
        for row in robustness_summary.itertuples(index=False):
            lines.append(
                f"- `{row.cohort}` / `{row.finding_id}`: status={row.robustness_status}, value={row.observed_value}, p={row.observed_p_value}"
            )
    lines.extend(["", "## Stability Matrix", ""])
    if stability_matrix.empty:
        lines.append("- No stability matrix was written.")
    else:
        for row in stability_matrix.itertuples(index=False):
            lines.append(
                f"- `{row.cohort}` / `{row.finding_id}`: overall={row.overall_stability_status}, inclusion={row.inclusion_direction_status}/{row.inclusion_significance_status}, distance={row.distance_direction_status}/{row.distance_significance_status}"
            )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run_coupling_robustness_stage(context: RunContext) -> dict[str, Path]:
    audit_dir = context.stage_path("dynamic_audit")
    model_tables_dir = context.stage_path("model_tables")
    band_pairs = _normalize_pair_frame(
        _load_csv(
            audit_dir / "band_aggregated_pairs.csv",
            dtype={"patient": str, "session": str, "run": str, "interval_id": str, "band": str, "cohort": str},
        )
    )
    interval_pairs = _normalize_pair_frame(
        _load_csv(
            audit_dir / "interval_summary_pairs.csv",
            dtype={"patient": str, "session": str, "run": str, "interval_id": str, "band": str, "cohort": str},
        )
    )
    model_band_metric = _normalize_metric_frame(
        _load_csv(
            model_tables_dir / "model_band_metric_long.csv",
            dtype={"patient": str, "session": str, "run": str, "interval_id": str, "band": str, "metric_family": str},
        )
    )
    if band_pairs.empty or interval_pairs.empty:
        context.write_stage_metadata(
            "coupling_robustness",
            {
                "status": "skipped",
                "reason": "missing_dynamic_audit_pairs",
            },
        )
        return {}

    frames_by_cohort = {
        cohort.name: band_pairs.loc[band_pairs["cohort"] == cohort.name].copy()
        for cohort in REPORTING_COHORTS
    }
    contrast_frames_by_cohort = _prepare_contrast_frames_by_cohort(model_band_metric)
    decomposition_rows: list[dict[str, Any]] = []
    descriptor_lookup: dict[tuple[str, str, str, str, str, str], DecompositionDescriptor] = {}
    structural_summaries: list[pd.DataFrame] = []
    for cohort in REPORTING_COHORTS:
        for aggregation_level, frame in (
            ("band_aggregated_interval", frames_by_cohort.get(cohort.name, pd.DataFrame())),
            ("interval_summary", interval_pairs.loc[interval_pairs["cohort"] == cohort.name].copy()),
        ):
            if frame.empty:
                continue
            rows, descriptors = _build_decomposition_rows(
                base_frame=frame,
                run_dir=context.run_root,
                cohort=cohort.name,
                analysis_role=cohort.analysis_role,
                aggregation_level=aggregation_level,
            )
            decomposition_rows.extend(rows)
            descriptor_lookup.update(descriptors)
            structural_summaries.append(
                _structural_null_summary(
                    base_frame=frame,
                    run_dir=context.run_root,
                    cohort=cohort.name,
                    analysis_role=cohort.analysis_role,
                    aggregation_level=aggregation_level,
                    seed=1000 + len(structural_summaries) * 17,
                )
            )

    decomposition_summary = pd.DataFrame(decomposition_rows, columns=DECOMPOSITION_COLUMNS)
    structural_summary = (
        pd.concat([frame for frame in structural_summaries if not frame.empty], ignore_index=True, sort=False)
        if structural_summaries
        else pd.DataFrame()
    )
    null_rows = [
        _permutation_summary(descriptor, seed=2000 + index * 31)
        for index, descriptor in enumerate(descriptor_lookup.values())
    ]
    null_comparison = pd.DataFrame(null_rows, columns=NULL_COMPARISON_COLUMNS)
    if not structural_summary.empty and not null_comparison.empty:
        null_comparison = null_comparison.merge(
            structural_summary,
            on=["cohort", "analysis_role", "aggregation_level", "value_scale", "decomposition_view", "grouping_stratum"],
            how="left",
            suffixes=("", "_structural"),
        )
        for column in [
            "structural_rho_mean",
            "structural_rho_median",
            "structural_rho_min",
            "structural_rho_max",
            "structural_replicates",
            "structural_seed",
        ]:
            if f"{column}_structural" in null_comparison.columns:
                null_comparison[column] = null_comparison[f"{column}_structural"]
                null_comparison = null_comparison.drop(columns=[f"{column}_structural"])
    null_lookup = {
        (
            str(row["cohort"]),
            str(row["aggregation_level"]),
            str(row["value_scale"]),
            str(row["decomposition_view"]),
            str(row["grouping_stratum"]),
            str(row["analysis_role"]),
        ): row
        for _, row in null_comparison.iterrows()
    }

    qc_summary = _cohort_qc_summary(band_pairs, context.run_root)
    full_frame = frames_by_cohort.get("full_modelable", pd.DataFrame())
    inclusion_scan = _inclusion_threshold_scan(
        full_frame,
        contrast_frames_by_cohort.get("full_modelable", {}).get("average_controllability", pd.DataFrame()).copy(),
        contrast_frames_by_cohort.get("full_modelable", {}).get("fragility", pd.DataFrame()).copy(),
        context.run_root,
    )
    distance_scan = _distance_threshold_scan(frames_by_cohort, contrast_frames_by_cohort, context.run_root)
    stability_matrix = _stability_matrix(inclusion_scan, distance_scan, context.run_root)
    robustness_summary = _cohort_headline_observations(
        frames_by_cohort,
        contrast_frames_by_cohort,
        descriptor_lookup,
        null_lookup,
        stability_matrix,
        context.run_root,
    )

    robustness_dir = context.stage_path("coupling_robustness")
    outputs: dict[str, Path] = {}
    for name, frame in (
        ("decomposition_summary", decomposition_summary),
        ("null_comparison_summary", null_comparison),
        ("inclusion_threshold_scan", inclusion_scan),
        ("distance_threshold_scan", distance_scan),
        ("stability_matrix", stability_matrix),
        ("robustness_summary", robustness_summary),
        ("cohort_qc_summary", qc_summary),
    ):
        path = robustness_dir / f"{name}.csv"
        write_dataframe(frame, path, index=False)
        outputs[name] = path
    summary_path = robustness_dir / "coupling_robustness_summary.md"
    _write_markdown_summary(summary_path, qc_summary, robustness_summary, stability_matrix)
    outputs["coupling_robustness_summary"] = summary_path

    context.write_stage_metadata(
        "coupling_robustness",
        {
            "status": "completed",
            "outputs": {name: str(path) for name, path in outputs.items()},
            "headline_findings": [
                {
                    "finding_id": finding.finding_id,
                    "label": finding.finding_label,
                    "kind": finding.finding_kind,
                    "expected_direction": finding.expected_direction,
                    "distance_scan_finding_id": finding.distance_scan_finding_id,
                }
                for finding in HEADLINE_FINDINGS
            ],
            "contrast_metrics": {
                "average_controllability": CONTRAST_AC_METRIC_FAMILY,
                "fragility": CONTRAST_FRAGILITY_METRIC_FAMILY,
                "value_column": CONTRAST_VALUE_COLUMN,
            },
            "thresholds": {
                "inclusion_min_intervals": list(INCLUSION_THRESHOLD_GRID),
                "distance_mm_boundary": list(DISTANCE_THRESHOLD_GRID),
                "primary_distance_threshold_mm": PRIMARY_DISTANCE_THRESHOLD_MM,
            },
            "null_assumptions": {
                "structural_replicates": STRUCTURAL_NULL_REPLICATES,
                "permutation_replicates": PERMUTATION_REPLICATES,
                "pair_permutation_replicates": PAIR_PERMUTATION_REPLICATES,
                "matrix_scale": STRUCTURAL_MATRIX_SCALE,
                "spectral_radius_cap": STRUCTURAL_SPECTRAL_RADIUS_CAP,
            },
        },
    )
    return outputs
