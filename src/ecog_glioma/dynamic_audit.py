from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from .dynamic import compute_average_controllability, compute_column_fragility
from .reporting import REPORTING_COHORTS, build_cohort_manifest, cohort_patient_sets, subset_by_patient_set
from .run_context import RunContext
from .utils import read_dataframe, write_dataframe

COUPLING_COLUMNS = [
    "run_dir",
    "cohort",
    "analysis_role",
    "cohort_patient_count",
    "cohort_interval_count",
    "aggregation_level",
    "value_scale",
    "grouping_view",
    "grouping_value",
    "rho",
    "n_pairs",
    "patient_count",
    "interval_count",
]
BASELINE_COLUMNS = [
    "run_dir",
    "cohort",
    "analysis_role",
    "cohort_patient_count",
    "cohort_interval_count",
    "patient",
    "band",
    "node_count",
    "replicate",
    "rho",
    "matrix_scale",
    "spectral_radius",
    "spectral_radius_cap",
]
BASELINE_SUMMARY_COLUMNS = [
    "run_dir",
    "cohort",
    "analysis_role",
    "cohort_patient_count",
    "cohort_interval_count",
    "rho_mean",
    "rho_median",
    "rho_min",
    "rho_max",
    "replicate_count",
    "structure_count",
    "matrix_scale",
    "spectral_radius_cap",
]


def _load_csv(path: Path, dtype: dict[str, str] | None = None) -> pd.DataFrame:
    return read_dataframe(path, dtype=dtype)


def _safe_spearman(
    frame: pd.DataFrame,
    x_col: str,
    y_col: str,
) -> dict[str, float | int | None]:
    subset = frame[[x_col, y_col]].dropna()
    if len(subset) < 4 or subset[x_col].nunique() < 2 or subset[y_col].nunique() < 2:
        return {"rho": None, "n_pairs": int(len(subset))}
    rho = subset[x_col].rank(method="average").corr(subset[y_col].rank(method="average"))
    return {"rho": None if pd.isna(rho) else float(rho), "n_pairs": int(len(subset))}


def _zscore(series: pd.Series) -> pd.Series:
    if len(series) <= 1:
        return pd.Series(np.zeros(len(series)), index=series.index, dtype=float)
    std = float(series.std(ddof=0))
    if std == 0.0 or pd.isna(std):
        return pd.Series(np.zeros(len(series)), index=series.index, dtype=float)
    return ((series - float(series.mean())) / std).astype(float)


def _metric_pairs_from_band_table(band_metric: pd.DataFrame) -> pd.DataFrame:
    if band_metric.empty:
        return pd.DataFrame()
    subset = band_metric[
        band_metric["metric_family"].isin(["average_controllability_mean", "fragility_mean"])
    ].copy()
    if subset.empty:
        return pd.DataFrame()
    id_columns = [
        "patient",
        "session",
        "run",
        "band",
        "interval_id",
        "interval_index",
        "region",
        "distance_mm",
        "is_boundary_interface",
        "patient_main_included",
        "patient_sensitivity_included",
    ]
    pivot_frames: list[pd.DataFrame] = []
    for value_column, prefix in (
        ("feature_value", "raw"),
        ("feature_z", "feature_z"),
        ("feature_z_within_band", "feature_z_within_band"),
    ):
        if value_column not in subset.columns:
            continue
        grouped = (
            subset[id_columns + ["metric_family", value_column]]
            .groupby(id_columns + ["metric_family"], dropna=False, as_index=False)[value_column]
            .mean()
        )
        if grouped.empty:
            continue
        pivot = (
            grouped.set_index(id_columns + ["metric_family"])[value_column]
            .unstack("metric_family")
            .reset_index()
        )
        pivot.columns.name = None
        rename_map = {
            "average_controllability_mean": f"{prefix}_average_controllability",
            "fragility_mean": f"{prefix}_fragility",
        }
        pivot = pivot.rename(columns=rename_map)
        pivot_frames.append(pivot)
    if not pivot_frames:
        return pd.DataFrame()
    merged = pivot_frames[0]
    for extra in pivot_frames[1:]:
        merged = merged.merge(extra, on=id_columns, how="outer")
    return merged


def _band_aggregated_pairs(interval_pairs: pd.DataFrame) -> pd.DataFrame:
    if interval_pairs.empty:
        return pd.DataFrame()
    value_columns = [
        column
        for column in interval_pairs.columns
        if column.endswith("_average_controllability") or column.endswith("_fragility")
    ]
    group_columns = [
        "patient",
        "session",
        "run",
        "interval_id",
        "interval_index",
        "region",
        "distance_mm",
        "is_boundary_interface",
        "patient_main_included",
        "patient_sensitivity_included",
    ]
    aggregated = interval_pairs.groupby(group_columns, dropna=False)[value_columns].mean().reset_index()
    aggregated["band"] = "all"
    return aggregated


def _window_pairs(
    window_ac: pd.DataFrame,
    window_fragility: pd.DataFrame,
    interval_metadata: pd.DataFrame,
) -> pd.DataFrame:
    if window_ac.empty or window_fragility.empty:
        return pd.DataFrame()
    left = window_ac.rename(columns={"subject": "patient"})
    right = window_fragility.rename(columns={"subject": "patient"})
    merged = left.merge(
        right.rename(columns={"fragility": "raw_fragility"}),
        on=["patient", "session", "run", "band", "window_start_s", "interval_id"],
        how="inner",
    )
    if merged.empty:
        return pd.DataFrame()
    merged = merged.rename(columns={"average_controllability": "raw_average_controllability"})
    merged = merged.merge(
        interval_metadata,
        on=["patient", "session", "run", "interval_id"],
        how="left",
    )
    merged["feature_z_average_controllability"] = (
        merged.groupby("patient", dropna=False)["raw_average_controllability"].transform(_zscore)
    )
    merged["feature_z_fragility"] = (
        merged.groupby("patient", dropna=False)["raw_fragility"].transform(_zscore)
    )
    merged["feature_z_within_band_average_controllability"] = (
        merged.groupby(["patient", "band"], dropna=False)["raw_average_controllability"].transform(_zscore)
    )
    merged["feature_z_within_band_fragility"] = (
        merged.groupby(["patient", "band"], dropna=False)["raw_fragility"].transform(_zscore)
    )
    return merged


def _cohort_annotate(
    frame: pd.DataFrame,
    cohort_name: str,
    analysis_role: str,
    patient_count: int,
    interval_count: int,
    run_dir: Path,
) -> pd.DataFrame:
    if frame.empty:
        return frame
    result = frame.copy()
    result.insert(0, "run_dir", run_dir.as_posix())
    result.insert(1, "cohort", cohort_name)
    result.insert(2, "analysis_role", analysis_role)
    result.insert(3, "cohort_patient_count", patient_count)
    result.insert(4, "cohort_interval_count", interval_count)
    return result


def _coupling_summary_rows(
    frame: pd.DataFrame,
    *,
    run_dir: Path,
    cohort_name: str,
    analysis_role: str,
    patient_count: int,
    interval_count: int,
    aggregation_level: str,
) -> list[dict[str, Any]]:
    if frame.empty:
        return []
    rows: list[dict[str, Any]] = []
    scale_columns = {
        "raw": ("raw_average_controllability", "raw_fragility"),
        "feature_z": ("feature_z_average_controllability", "feature_z_fragility"),
        "feature_z_within_band": (
            "feature_z_within_band_average_controllability",
            "feature_z_within_band_fragility",
        ),
    }
    grouping_options = [("overall", None), ("patient", "patient"), ("region", "region"), ("band", "band")]
    for scale_name, (ac_column, fragility_column) in scale_columns.items():
        if ac_column not in frame.columns or fragility_column not in frame.columns:
            continue
        available = frame[[ac_column, fragility_column]].dropna()
        if available.empty:
            continue
        for grouping_view, grouping_column in grouping_options:
            if grouping_column is None:
                grouped_items = [("all", frame)]
            elif grouping_column in frame.columns:
                grouped_items = list(frame.groupby(grouping_column, dropna=False))
            else:
                continue
            for grouping_value, subset in grouped_items:
                stats = _safe_spearman(subset, ac_column, fragility_column)
                row = {
                    "run_dir": run_dir.as_posix(),
                    "cohort": cohort_name,
                    "analysis_role": analysis_role,
                    "cohort_patient_count": patient_count,
                    "cohort_interval_count": interval_count,
                    "aggregation_level": aggregation_level,
                    "value_scale": scale_name,
                    "grouping_view": grouping_view,
                    "grouping_value": str(grouping_value),
                    "rho": stats["rho"],
                    "n_pairs": stats["n_pairs"],
                    "patient_count": int(subset["patient"].dropna().astype(str).nunique()) if "patient" in subset.columns else 0,
                    "interval_count": int(subset[["patient", "interval_id"]].dropna().drop_duplicates().shape[0])
                    if {"patient", "interval_id"}.issubset(subset.columns)
                    else 0,
                }
                rows.append(row)
    return rows


def _baseline_simulations(
    window_pairs: pd.DataFrame,
    cohort_name: str,
    analysis_role: str,
    *,
    repeats_per_structure: int = 16,
    seed: int = 0,
) -> pd.DataFrame:
    if window_pairs.empty:
        return pd.DataFrame()
    structures = (
        window_pairs.groupby(["patient", "band"], dropna=False)["interval_id"]
        .nunique()
        .reset_index(name="node_count")
    )
    if structures.empty:
        return pd.DataFrame()
    rng = np.random.default_rng(seed)
    rows: list[dict[str, Any]] = []
    for structure in structures.itertuples(index=False):
        node_count = int(structure.node_count)
        if node_count < 2:
            continue
        for replicate in range(repeats_per_structure):
            matrix = rng.normal(scale=0.12, size=(node_count, node_count))
            radius = float(np.max(np.abs(np.linalg.eigvals(matrix))))
            if radius >= 0.95 and radius > 0:
                matrix = matrix / (radius + 0.05)
                radius = float(np.max(np.abs(np.linalg.eigvals(matrix))))
            ac_values = pd.Series(compute_average_controllability(matrix), dtype=float)
            fragility_values = pd.Series(compute_column_fragility(matrix), dtype=float)
            rho = ac_values.rank(method="average").corr(fragility_values.rank(method="average"))
            rows.append(
                {
                    "cohort": cohort_name,
                    "analysis_role": analysis_role,
                    "patient": str(structure.patient),
                    "band": str(structure.band),
                    "node_count": node_count,
                    "replicate": replicate,
                    "rho": None if pd.isna(rho) else float(rho),
                    "matrix_scale": 0.12,
                    "spectral_radius": radius,
                    "spectral_radius_cap": 0.95,
                }
            )
    return pd.DataFrame(rows)


def _write_markdown_summary(
    path: Path,
    cohort_manifest: pd.DataFrame,
    coupling_summary: pd.DataFrame,
    baseline_summary: pd.DataFrame,
) -> None:
    lines = [
        "# Dynamic Phenotype Audit",
        "",
        "This stage contains exploratory AC-versus-fragility robustness checks.",
        "",
        "## Cohorts",
        "",
    ]
    for row in cohort_manifest.itertuples(index=False):
        lines.append(
            f"- `{row.cohort}` ({row.analysis_role}): {row.patient_count} patients, {row.interval_count} intervals, {row.row_count} rows"
        )
    focus = pd.DataFrame()
    if not coupling_summary.empty:
        focus = coupling_summary[
            (coupling_summary["aggregation_level"] == "band_aggregated_interval")
            & (coupling_summary["value_scale"] == "feature_z")
            & (coupling_summary["grouping_view"] == "region")
        ].copy()
    lines.extend(["", "## Focus Summary", ""])
    if focus.empty:
        lines.append("- No analyzable band-aggregated feature_z coupling rows were available.")
    else:
        for row in focus.itertuples(index=False):
            lines.append(
                f"- `{row.cohort}` / region `{row.grouping_value}`: rho={row.rho}, n_pairs={row.n_pairs}"
            )
    lines.extend(["", "## Structural Baseline", ""])
    if baseline_summary.empty:
        lines.append("- No baseline simulations were written.")
    else:
        for row in baseline_summary.itertuples(index=False):
            lines.append(
                f"- `{row.cohort}`: median rho={row.rho_median}, min={row.rho_min}, max={row.rho_max}, structures={row.structure_count}"
            )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run_dynamic_audit_stage(context: RunContext) -> dict[str, Path]:
    model_tables_dir = context.stage_path("model_tables")
    controllability_dir = context.stage_path("controllability")
    fragility_dir = context.stage_path("fragility")

    joint = _load_csv(
        model_tables_dir / "model_joint_long.csv",
        dtype={"patient": str, "session": str, "run": str, "interval_id": str},
    )
    band_metric = _load_csv(
        model_tables_dir / "model_band_metric_long.csv",
        dtype={"patient": str, "session": str, "run": str, "band": str, "interval_id": str},
    )
    window_ac = _load_csv(
        controllability_dir / "window_level_ac_mc.csv",
        dtype={"subject": str, "session": str, "run": str, "band": str, "interval_id": str},
    )
    window_fragility = _load_csv(
        fragility_dir / "window_level_fragility.csv",
        dtype={"subject": str, "session": str, "run": str, "band": str, "interval_id": str},
    )

    if joint.empty:
        context.write_stage_metadata(
            "dynamic_audit",
            {"status": "skipped", "reason": "missing_model_joint_long"},
        )
        return {}

    interval_metadata = (
        joint[
            [
                "patient",
                "session",
                "run",
                "interval_id",
                "interval_index",
                "region",
                "distance_mm",
                "is_boundary_interface",
                "patient_main_included",
                "patient_sensitivity_included",
            ]
        ]
        .drop_duplicates()
        .copy()
    )
    cohort_manifest = build_cohort_manifest(interval_metadata)
    cohort_manifest.insert(0, "run_dir", context.run_root.as_posix())
    patient_sets = cohort_patient_sets(interval_metadata)

    interval_pairs = _metric_pairs_from_band_table(band_metric)
    band_aggregated_pairs = _band_aggregated_pairs(interval_pairs)
    window_pairs = _window_pairs(window_ac, window_fragility, interval_metadata)

    annotated_tables: dict[str, pd.DataFrame] = {
        "cohort_manifest": cohort_manifest.copy(),
    }
    coupling_rows: list[dict[str, Any]] = []
    baseline_frames: list[pd.DataFrame] = []
    for cohort in REPORTING_COHORTS:
        cohort_name = cohort.name
        manifest_row = cohort_manifest[cohort_manifest["cohort"] == cohort_name]
        patient_count = int(manifest_row["patient_count"].iloc[0]) if not manifest_row.empty else 0
        interval_count = int(manifest_row["interval_count"].iloc[0]) if not manifest_row.empty else 0
        patients = patient_sets.get(cohort_name, set())

        cohort_interval_pairs = _cohort_annotate(
            subset_by_patient_set(interval_pairs, patients),
            cohort_name,
            cohort.analysis_role,
            patient_count,
            interval_count,
            context.run_root,
        )
        cohort_band_aggregated = _cohort_annotate(
            subset_by_patient_set(band_aggregated_pairs, patients),
            cohort_name,
            cohort.analysis_role,
            patient_count,
            interval_count,
            context.run_root,
        )
        cohort_window_pairs = _cohort_annotate(
            subset_by_patient_set(window_pairs, patients),
            cohort_name,
            cohort.analysis_role,
            patient_count,
            interval_count,
            context.run_root,
        )

        if not cohort_interval_pairs.empty:
            annotated_tables.setdefault("interval_summary_pairs", pd.DataFrame())
            annotated_tables["interval_summary_pairs"] = pd.concat(
                [annotated_tables["interval_summary_pairs"], cohort_interval_pairs],
                ignore_index=True,
                sort=False,
            )
            coupling_rows.extend(
                _coupling_summary_rows(
                    cohort_interval_pairs,
                    run_dir=context.run_root,
                    cohort_name=cohort_name,
                    analysis_role=cohort.analysis_role,
                    patient_count=patient_count,
                    interval_count=interval_count,
                    aggregation_level="interval_summary",
                )
            )
        if not cohort_band_aggregated.empty:
            annotated_tables.setdefault("band_aggregated_pairs", pd.DataFrame())
            annotated_tables["band_aggregated_pairs"] = pd.concat(
                [annotated_tables["band_aggregated_pairs"], cohort_band_aggregated],
                ignore_index=True,
                sort=False,
            )
            coupling_rows.extend(
                _coupling_summary_rows(
                    cohort_band_aggregated,
                    run_dir=context.run_root,
                    cohort_name=cohort_name,
                    analysis_role=cohort.analysis_role,
                    patient_count=patient_count,
                    interval_count=interval_count,
                    aggregation_level="band_aggregated_interval",
                )
            )
        if not cohort_window_pairs.empty:
            annotated_tables.setdefault("window_level_pairs", pd.DataFrame())
            annotated_tables["window_level_pairs"] = pd.concat(
                [annotated_tables["window_level_pairs"], cohort_window_pairs],
                ignore_index=True,
                sort=False,
            )
            coupling_rows.extend(
                _coupling_summary_rows(
                    cohort_window_pairs,
                    run_dir=context.run_root,
                    cohort_name=cohort_name,
                    analysis_role=cohort.analysis_role,
                    patient_count=patient_count,
                    interval_count=interval_count,
                    aggregation_level="window_level",
                )
            )
            baseline = _baseline_simulations(cohort_window_pairs, cohort_name, cohort.analysis_role)
            if not baseline.empty:
                baseline.insert(0, "run_dir", context.run_root.as_posix())
                baseline.insert(3, "cohort_patient_count", patient_count)
                baseline.insert(4, "cohort_interval_count", interval_count)
                baseline_frames.append(baseline)

    coupling_summary = pd.DataFrame(coupling_rows, columns=COUPLING_COLUMNS)
    baseline_simulations = (
        pd.concat(baseline_frames, ignore_index=True, sort=False)
        if baseline_frames
        else pd.DataFrame(columns=BASELINE_COLUMNS)
    )
    baseline_summary = pd.DataFrame(columns=BASELINE_SUMMARY_COLUMNS)
    if not baseline_simulations.empty:
        grouped = baseline_simulations.groupby(
            ["run_dir", "cohort", "analysis_role", "cohort_patient_count", "cohort_interval_count"],
            dropna=False,
        )
        baseline_summary = grouped["rho"].agg(
            rho_mean="mean",
            rho_median="median",
            rho_min="min",
            rho_max="max",
            replicate_count="count",
        ).reset_index()
        structure_counts = (
            baseline_simulations[
                ["run_dir", "cohort", "analysis_role", "cohort_patient_count", "cohort_interval_count", "patient", "band"]
            ]
            .drop_duplicates()
            .groupby(
                ["run_dir", "cohort", "analysis_role", "cohort_patient_count", "cohort_interval_count"],
                dropna=False,
            )
            .size()
            .reset_index(name="structure_count")
        )
        baseline_summary = baseline_summary.merge(
            structure_counts,
            on=["run_dir", "cohort", "analysis_role", "cohort_patient_count", "cohort_interval_count"],
            how="left",
        )
        baseline_summary["matrix_scale"] = 0.12
        baseline_summary["spectral_radius_cap"] = 0.95

    audit_dir = context.stage_path("dynamic_audit")
    outputs: dict[str, Path] = {}
    for name, frame in annotated_tables.items():
        path = audit_dir / f"{name}.csv"
        write_dataframe(frame, path, index=False)
        outputs[name] = path
    for name, frame in (
        ("coupling_summary", coupling_summary),
        ("metric_coupling_baseline", baseline_simulations),
        ("metric_coupling_baseline_summary", baseline_summary),
    ):
        path = audit_dir / f"{name}.csv"
        write_dataframe(frame, path, index=False)
        outputs[name] = path
    summary_path = audit_dir / "dynamic_audit_summary.md"
    _write_markdown_summary(summary_path, cohort_manifest, coupling_summary, baseline_summary)
    outputs["dynamic_audit_summary"] = summary_path

    context.write_stage_metadata(
        "dynamic_audit",
        {
            "status": "completed",
            "outputs": {name: str(path) for name, path in outputs.items()},
            "cohorts": cohort_manifest.to_dict(orient="records"),
            "baseline_assumptions": {
                "matrix_scale": 0.12,
                "spectral_radius_cap": 0.95,
                "repeats_per_structure": 16,
            },
        },
    )
    return outputs
