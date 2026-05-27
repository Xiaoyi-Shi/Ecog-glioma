from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from .bids_io import index_bids_recordings, load_channels_table, read_raw_recording
from .bipolar import clean_duration_seconds, derive_adjacent_bipolar
from .coupling_robustness import run_coupling_robustness_stage
from .config import (
    DEFAULT_BIDS_ROOT,
    DEFAULT_DYNAMIC_STEP_SECONDS,
    DEFAULT_DYNAMIC_WINDOW_OPTIONS,
    DEFAULT_DYNAMIC_WINDOW_SECONDS,
    DEFAULT_MAIN_MIN_INTERVALS,
    DEFAULT_METADATA_XLSX,
    DEFAULT_OMEGAS,
    DEFAULT_RESULTS_ROOT,
    DEFAULT_SESSION_FILTER,
    DEFAULT_SENSITIVITY_MIN_INTERVALS,
    DEFAULT_STATIC_EPOCH_SECONDS,
    DYNAMIC_BANDS,
    STATIC_BANDS,
)
from .dynamic import (
    compute_average_controllability,
    compute_column_fragility,
    compute_modal_controllability,
    estimate_dynamic_states,
    save_state_matrices,
    summarize_window_metrics,
)
from .dynamic_audit import run_dynamic_audit_stage
from .export_tables import write_model_tables
from .hfo import run_hfo_detection
from .labels import build_label_manifest
from .paths import as_repo_path, repo_root
from .reporting import REPORTING_COHORTS
from .run_context import RunContext
from .static_network import (
    compute_band_source_sink,
    compute_band_connectivity,
    compute_multilayer_features,
    compute_node_metrics,
    save_matrix,
)
from .utils import write_dataframe, write_json


ID_COLUMNS = [
    "patient_id",
    "subject",
    "session",
    "task",
    "run",
    "interval_id",
    "contact_a",
    "contact_b",
]


def create_or_load_context(
    run_dir: Path | None = None,
    results_root: Path = DEFAULT_RESULTS_ROOT,
) -> RunContext:
    if run_dir is not None:
        return RunContext.from_existing(run_dir)
    return RunContext.create(results_root=results_root)


def build_manifest_and_qc(
    context: RunContext,
    metadata_xlsx: Path = DEFAULT_METADATA_XLSX,
    bids_root: Path = DEFAULT_BIDS_ROOT,
    session_filter: str = DEFAULT_SESSION_FILTER,
    main_min_intervals: int = DEFAULT_MAIN_MIN_INTERVALS,
    sensitivity_min_intervals: int = DEFAULT_SENSITIVITY_MIN_INTERVALS,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    label_manifest = build_label_manifest(metadata_xlsx, session_filter=session_filter)
    recordings = index_bids_recordings(bids_root)
    recordings = [entry for entry in recordings if entry.session == session_filter]
    interval_qc_rows: list[dict[str, Any]] = []
    patient_qc_rows: list[dict[str, Any]] = []

    for entry in recordings:
        subject_manifest = label_manifest[
            (label_manifest["subject"] == entry.subject)
            & (label_manifest["session"] == entry.session)
        ].copy()
        channels = load_channels_table(entry.channels_path)
        raw = read_raw_recording(entry.recording_path, preload=False)
        bipolar = derive_adjacent_bipolar(raw, channels, entry)
        bipolar_table = bipolar.interval_table.copy()
        merged = subject_manifest.merge(
            bipolar_table,
            on=["subject", "session", "interval_id", "interval_index", "contact_a", "contact_b"],
            how="outer",
            suffixes=("", "_bipolar"),
        )
        merged["recording_path"] = merged["recording_path"].fillna(str(entry.recording_path))
        merged["label_valid"] = merged["label_valid"].fillna(False)
        merged["endpoint_bad"] = merged["endpoint_bad"].fillna(True)
        merged["signal_available"] = merged["channel_a"].notna() & merged["channel_b"].notna()
        merged["interval_usable"] = (
            merged["label_valid"].astype(bool)
            & merged["signal_available"].astype(bool)
            & (~merged["endpoint_bad"].astype(bool))
        )
        merged["usable_reason"] = np.select(
            [
                ~merged["label_valid"].astype(bool),
                ~merged["signal_available"].astype(bool),
                merged["endpoint_bad"].astype(bool),
            ],
            [
                "invalid_label",
                "missing_signal",
                "bad_endpoint",
            ],
            default="usable",
        )
        usable_count = int(merged["interval_usable"].sum())
        patient_qc_rows.append(
            {
                "subject": entry.subject,
                "session": entry.session,
                "run": entry.run,
                "recording_path": str(entry.recording_path),
                "usable_interval_count": usable_count,
                "patient_main_included": usable_count >= main_min_intervals,
                "patient_sensitivity_included": usable_count >= sensitivity_min_intervals,
                "clean_duration_s": clean_duration_seconds(
                    bipolar.n_times,
                    bipolar.sfreq,
                    bipolar.bad_segments,
                ),
                "bad_segment_count": len(bipolar.bad_segments),
            }
        )
        merged["patient_main_included"] = usable_count >= main_min_intervals
        merged["patient_sensitivity_included"] = usable_count >= sensitivity_min_intervals
        interval_qc_rows.extend(merged.to_dict(orient="records"))

    interval_qc = pd.DataFrame(interval_qc_rows).sort_values(
        ["subject", "interval_index"],
        kind="stable",
    )
    patient_qc = pd.DataFrame(patient_qc_rows).sort_values(["subject"], kind="stable")

    write_dataframe(label_manifest, context.stage_path("manifest") / "label_manifest.csv", index=False)
    write_dataframe(interval_qc, context.stage_path("qc") / "interval_qc_table.csv", index=False)
    write_dataframe(patient_qc, context.stage_path("qc") / "patient_qc_summary.csv", index=False)
    context.write_stage_metadata(
        "manifest",
        {
            "metadata_xlsx": str(as_repo_path(metadata_xlsx)),
            "session_filter": session_filter,
            "rows": int(len(label_manifest)),
            "subjects": sorted(label_manifest["subject"].unique().tolist()) if not label_manifest.empty else [],
        },
    )
    context.write_stage_metadata(
        "qc",
        {
            "bids_root": str(as_repo_path(bids_root)),
            "recordings": int(len(recordings)),
            "interval_rows": int(len(interval_qc)),
            "patient_rows": int(len(patient_qc)),
            "main_threshold": main_min_intervals,
            "sensitivity_threshold": sensitivity_min_intervals,
        },
    )
    return label_manifest, interval_qc, patient_qc


def _load_manifest_qc_from_context(context: RunContext) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    manifest = pd.read_csv(
        context.stage_path("manifest") / "label_manifest.csv",
        dtype={"patient_id": str, "subject": str, "session": str, "interval_id": str},
    )
    interval_qc = pd.read_csv(
        context.stage_path("qc") / "interval_qc_table.csv",
        dtype={"patient_id": str, "subject": str, "session": str, "interval_id": str, "run": str},
    )
    patient_qc = pd.read_csv(
        context.stage_path("qc") / "patient_qc_summary.csv",
        dtype={"subject": str, "session": str, "run": str},
    )
    return manifest, interval_qc, patient_qc


def run_static_network_stage(
    context: RunContext,
    bids_root: Path = DEFAULT_BIDS_ROOT,
    epoch_seconds: float = DEFAULT_STATIC_EPOCH_SECONDS,
    omegas: tuple[float, ...] = DEFAULT_OMEGAS,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    _, interval_qc, _ = _load_manifest_qc_from_context(context)
    recordings = index_bids_recordings(bids_root)
    recordings = [entry for entry in recordings if entry.session == DEFAULT_SESSION_FILTER]
    matrix_dir = context.stage_path("static_network") / "connectivity_matrices"
    matrix_dir.mkdir(parents=True, exist_ok=True)

    node_rows: list[dict[str, Any]] = []
    directed_rows: list[dict[str, Any]] = []
    multilayer_node_rows: list[dict[str, Any]] = []
    multilayer_patient_rows: list[dict[str, Any]] = []
    stage_summary: list[dict[str, Any]] = []

    for entry in recordings:
        interval_subset = interval_qc[
            (interval_qc["subject"] == entry.subject)
            & (interval_qc["session"] == entry.session)
            & (interval_qc["interval_usable"])
        ].sort_values("interval_index", kind="stable")
        usable_interval_ids = interval_subset["interval_id"].tolist()
        if len(usable_interval_ids) < 2:
            continue
        channels = load_channels_table(entry.channels_path)
        raw = read_raw_recording(entry.recording_path, preload=True)
        bipolar = derive_adjacent_bipolar(raw, channels, entry)
        matrices_by_band: dict[str, np.ndarray] = {}
        for band in STATIC_BANDS:
            matrix, metadata = compute_band_connectivity(
                recording=bipolar,
                interval_ids=usable_interval_ids,
                band=band,
                epoch_seconds=epoch_seconds,
            )
            matrices_by_band[band.name] = matrix
            save_matrix(
                matrix,
                usable_interval_ids,
                matrix_dir / f"sub-{entry.subject}_{band.name}_dwpli.csv",
            )
            metrics = compute_node_metrics(matrix)
            for metric_name, values in metrics.items():
                for interval_id, value in zip(usable_interval_ids, values, strict=False):
                    node_rows.append(
                        {
                            "subject": entry.subject,
                            "session": entry.session,
                            "run": entry.run,
                            "band": band.name,
                            "interval_id": interval_id,
                            "metric": metric_name,
                            "value": float(value),
                        }
                    )
            source_sink, directed_matrix, directed_metadata = compute_band_source_sink(
                recording=bipolar,
                interval_ids=usable_interval_ids,
                band=band,
                epoch_seconds=epoch_seconds,
            )
            save_matrix(
                directed_matrix,
                usable_interval_ids,
                matrix_dir / f"sub-{entry.subject}_{band.name}_source_sink_directed.csv",
            )
            for interval_id, value in zip(usable_interval_ids, source_sink, strict=False):
                directed_rows.append(
                    {
                        "subject": entry.subject,
                        "session": entry.session,
                        "run": entry.run,
                        "band": band.name,
                        "interval_id": interval_id,
                        "metric": "source_sink_index",
                        "value": float(value),
                    }
                )
            stage_summary.append(
                {
                    "subject": entry.subject,
                    "band": band.name,
                    **metadata,
                    "directed_method": directed_metadata["method"],
                    "directed_n_epochs": directed_metadata["n_epochs"],
                }
            )

        multilayer_nodes, multilayer_patient = compute_multilayer_features(
            matrices_by_band=matrices_by_band,
            interval_ids=usable_interval_ids,
            omegas=omegas,
        )
        if not multilayer_nodes.empty:
            multilayer_nodes.insert(0, "subject", entry.subject)
            multilayer_nodes.insert(1, "session", entry.session)
            multilayer_nodes.insert(2, "run", entry.run)
            multilayer_node_rows.extend(multilayer_nodes.to_dict(orient="records"))
        if not multilayer_patient.empty:
            multilayer_patient.insert(0, "subject", entry.subject)
            multilayer_patient.insert(1, "session", entry.session)
            multilayer_patient.insert(2, "run", entry.run)
            multilayer_patient_rows.extend(multilayer_patient.to_dict(orient="records"))

    node_features = pd.DataFrame(node_rows)
    directed_features = pd.DataFrame(directed_rows)
    multilayer_node_features = pd.DataFrame(multilayer_node_rows)
    multilayer_patient_features = pd.DataFrame(multilayer_patient_rows)
    write_dataframe(node_features, context.stage_path("static_network") / "node_features_static.csv", index=False)
    write_dataframe(directed_features, context.stage_path("static_network") / "directed_source_sink_features.csv", index=False)
    write_dataframe(multilayer_node_features, context.stage_path("static_network") / "multilayer_node_features.csv", index=False)
    write_dataframe(multilayer_patient_features, context.stage_path("static_network") / "multilayer_patient_features.csv", index=False)
    write_dataframe(pd.DataFrame(stage_summary), context.stage_path("static_network") / "connectivity_stage_summary.csv", index=False)
    context.write_stage_metadata(
        "static_network",
        {
            "epoch_seconds": epoch_seconds,
            "omegas": list(omegas),
            "node_rows": int(len(node_features)),
            "directed_rows": int(len(directed_features)),
            "multilayer_node_rows": int(len(multilayer_node_features)),
            "multilayer_patient_rows": int(len(multilayer_patient_features)),
        },
    )
    return node_features, directed_features, multilayer_node_features, multilayer_patient_features


def run_hfo_stage(
    context: RunContext,
    bids_root: Path = DEFAULT_BIDS_ROOT,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    _, interval_qc, _ = _load_manifest_qc_from_context(context)
    recordings = index_bids_recordings(bids_root)
    recordings = [entry for entry in recordings if entry.session == DEFAULT_SESSION_FILTER]
    event_rows: list[dict[str, Any]] = []
    summary_rows: list[dict[str, Any]] = []

    for entry in recordings:
        interval_subset = interval_qc[
            (interval_qc["subject"] == entry.subject)
            & (interval_qc["session"] == entry.session)
            & (interval_qc["interval_usable"])
        ].sort_values("interval_index", kind="stable")
        usable_interval_ids = interval_subset["interval_id"].tolist()
        if not usable_interval_ids:
            continue
        channels = load_channels_table(entry.channels_path)
        raw = read_raw_recording(entry.recording_path, preload=True)
        bipolar = derive_adjacent_bipolar(raw, channels, entry)
        events, summary = run_hfo_detection(
            recording=bipolar,
            usable_interval_ids=usable_interval_ids,
        )
        if not events.empty:
            event_rows.extend(events.to_dict(orient="records"))
        if not summary.empty:
            summary_rows.extend(summary.to_dict(orient="records"))

    event_frame = pd.DataFrame(event_rows)
    summary_frame = pd.DataFrame(summary_rows)
    write_dataframe(event_frame, context.stage_path("hfo") / "hfo_events.csv", index=False)
    write_dataframe(summary_frame, context.stage_path("hfo") / "hfo_channel_summary.csv", index=False)
    context.write_stage_metadata(
        "hfo",
        {
            "event_rows": int(len(event_frame)),
            "summary_rows": int(len(summary_frame)),
        },
    )
    return event_frame, summary_frame


def run_controllability_stage(
    context: RunContext,
    bids_root: Path = DEFAULT_BIDS_ROOT,
    window_seconds: float = DEFAULT_DYNAMIC_WINDOW_SECONDS,
    step_seconds: float = DEFAULT_DYNAMIC_STEP_SECONDS,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    _, interval_qc, _ = _load_manifest_qc_from_context(context)
    recordings = index_bids_recordings(bids_root)
    recordings = [entry for entry in recordings if entry.session == DEFAULT_SESSION_FILTER]
    state_dir = context.stage_path("controllability") / "state_matrices"
    state_dir.mkdir(parents=True, exist_ok=True)
    window_inventory_rows: list[dict[str, Any]] = []
    controllability_rows: list[dict[str, Any]] = []

    for entry in recordings:
        interval_subset = interval_qc[
            (interval_qc["subject"] == entry.subject)
            & (interval_qc["session"] == entry.session)
            & (interval_qc["interval_usable"])
        ].sort_values("interval_index", kind="stable")
        usable_interval_ids = interval_subset["interval_id"].tolist()
        if len(usable_interval_ids) < 2:
            continue
        channels = load_channels_table(entry.channels_path)
        raw = read_raw_recording(entry.recording_path, preload=True)
        bipolar = derive_adjacent_bipolar(raw, channels, entry)
        for band in DYNAMIC_BANDS:
            matrices, starts_s, inventory = estimate_dynamic_states(
                recording=bipolar,
                usable_interval_ids=usable_interval_ids,
                band=band,
                window_seconds=window_seconds,
                step_seconds=step_seconds,
            )
            save_state_matrices(
                state_dir / f"sub-{entry.subject}_{band.name}_state_matrices.npz",
                matrices=matrices,
                starts_s=starts_s,
                interval_ids=usable_interval_ids,
                band_name=band.name,
                window_seconds=window_seconds,
                step_seconds=step_seconds,
                subject=entry.subject,
                session=entry.session,
                run=entry.run,
            )
            inventory = inventory.assign(subject=entry.subject, session=entry.session, run=entry.run, band=band.name)
            window_inventory_rows.extend(inventory.to_dict(orient="records"))
            for matrix, start_s in zip(matrices, starts_s, strict=False):
                ac_values = compute_average_controllability(matrix)
                mc_values = compute_modal_controllability(matrix)
                for interval_id, ac_value, mc_value in zip(
                    usable_interval_ids,
                    ac_values,
                    mc_values,
                    strict=False,
                ):
                    controllability_rows.append(
                        {
                            "subject": entry.subject,
                            "session": entry.session,
                            "run": entry.run,
                            "band": band.name,
                            "window_start_s": float(start_s),
                            "interval_id": interval_id,
                            "average_controllability": float(ac_value),
                            "modal_controllability": float(mc_value),
                        }
                    )

    window_inventory = pd.DataFrame(window_inventory_rows)
    controllability = pd.DataFrame(controllability_rows)
    ac_summary = summarize_window_metrics(
        controllability.rename(columns={"average_controllability": "value"}),
        value_column="value",
        summary_prefix="average_controllability",
    )
    mc_summary = summarize_window_metrics(
        controllability.rename(columns={"modal_controllability": "value"}),
        value_column="value",
        summary_prefix="modal_controllability",
    )
    if not ac_summary.empty and not mc_summary.empty:
        summary = ac_summary.merge(
            mc_summary,
            on=["subject", "session", "run", "band", "interval_id"],
            how="outer",
        )
    else:
        summary = pd.DataFrame()

    write_dataframe(window_inventory, context.stage_path("controllability") / "window_inventory.csv", index=False)
    write_dataframe(controllability, context.stage_path("controllability") / "window_level_ac_mc.csv", index=False)
    write_dataframe(summary, context.stage_path("controllability") / "channel_level_ac_mc_summary.csv", index=False)
    context.write_stage_metadata(
        "controllability",
        {
            "window_seconds": window_seconds,
            "step_seconds": step_seconds,
            "window_rows": int(len(window_inventory)),
            "metric_rows": int(len(controllability)),
            "summary_rows": int(len(summary)),
        },
    )
    return controllability, summary


def run_fragility_stage(context: RunContext) -> tuple[pd.DataFrame, pd.DataFrame]:
    state_dir = context.stage_path("controllability") / "state_matrices"
    window_rows: list[dict[str, Any]] = []
    for state_path in sorted(state_dir.glob("*.npz")):
        payload = np.load(state_path, allow_pickle=False)
        matrices = payload["matrices"]
        starts_s = payload["starts_s"]
        interval_ids = payload["interval_ids"].tolist()
        band_name = str(payload["band"][0])
        subject = str(payload["subject"][0])
        session = str(payload["session"][0])
        run = str(payload["run"][0])
        for matrix, start_s in zip(matrices, starts_s, strict=False):
            fragility = compute_column_fragility(matrix)
            for interval_id, value in zip(interval_ids, fragility, strict=False):
                window_rows.append(
                    {
                        "subject": subject,
                        "session": session,
                        "run": run,
                        "band": band_name,
                        "window_start_s": float(start_s),
                        "interval_id": interval_id,
                        "fragility": float(value),
                    }
                )

    window_frame = pd.DataFrame(window_rows)
    summary = summarize_window_metrics(
        window_frame.rename(columns={"fragility": "value"}),
        value_column="value",
        summary_prefix="fragility",
    )
    write_dataframe(window_frame, context.stage_path("fragility") / "window_level_fragility.csv", index=False)
    write_dataframe(summary, context.stage_path("fragility") / "channel_level_fragility_summary.csv", index=False)
    context.write_stage_metadata(
        "fragility",
        {
            "window_rows": int(len(window_frame)),
            "summary_rows": int(len(summary)),
        },
    )
    return window_frame, summary


def export_model_tables_stage(context: RunContext) -> dict[str, Path]:
    outputs = write_model_tables(context)
    context.write_stage_metadata(
        "model_tables",
        {"outputs": {name: str(path) for name, path in outputs.items()}},
    )
    return outputs


def _render_rmarkdown_report(
    *,
    context: RunContext,
    script: Path,
    output_dir: Path,
    output_file: str,
    cohort_name: str,
    analysis_role: str,
    coupling_robustness_dir: Path,
) -> None:
    render_expression = (
        "rmarkdown::render("
        f"input='{script.as_posix()}', "
        f"output_file='{output_file}', "
        f"output_dir='{output_dir.as_posix()}', "
        f"params=list(run_dir='{context.run_root.as_posix()}', "
        f"script_dir='{script.parent.as_posix()}', "
        f"report_dir='{output_dir.as_posix()}', "
        f"dynamic_audit_dir='{context.stage_path('dynamic_audit').as_posix()}', "
        f"coupling_robustness_dir='{coupling_robustness_dir.as_posix()}', "
        f"cohort_name='{cohort_name}', "
        f"analysis_role='{analysis_role}'), "
        "envir=new.env(parent=globalenv()))"
    )
    completed = subprocess.run(
        ["Rscript", "-e", render_expression],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    log_path = context.stage_path("logs") / f"{script.stem}_{cohort_name}.log"
    log_path.write_text(
        completed.stdout + "\n--- STDERR ---\n" + completed.stderr,
        encoding="utf-8",
    )
    if completed.returncode != 0:
        raise RuntimeError(
            f"R stage failed for {script.name} ({cohort_name}). See {log_path}"
        )


def run_r_reporting_stage(context: RunContext) -> None:
    model_script = repo_root() / "scripts_r" / "run_boundary_models.Rmd"
    figure_script = repo_root() / "scripts_r" / "run_boundary_figures.Rmd"
    cohort_outputs: dict[str, dict[str, str]] = {}
    audit_outputs = run_dynamic_audit_stage(context)
    robustness_outputs = run_coupling_robustness_stage(context)
    coupling_robustness_dir = context.stage_path("coupling_robustness")
    for cohort in REPORTING_COHORTS:
        stats_dir = context.stage_path("stats_r") / cohort.name
        figures_dir = context.stage_path("figures") / cohort.name
        stats_dir.mkdir(parents=True, exist_ok=True)
        figures_dir.mkdir(parents=True, exist_ok=True)
        _render_rmarkdown_report(
            context=context,
            script=model_script,
            output_dir=stats_dir,
            output_file="run_boundary_models.html",
            cohort_name=cohort.name,
            analysis_role=cohort.analysis_role,
            coupling_robustness_dir=coupling_robustness_dir,
        )
        cohort_outputs.setdefault(cohort.name, {})["stats_dir"] = str(stats_dir)

    for cohort in REPORTING_COHORTS:
        figures_dir = context.stage_path("figures") / cohort.name
        _render_rmarkdown_report(
            context=context,
            script=figure_script,
            output_dir=figures_dir,
            output_file="run_boundary_figures.html",
            cohort_name=cohort.name,
            analysis_role=cohort.analysis_role,
            coupling_robustness_dir=coupling_robustness_dir,
        )
        cohort_outputs.setdefault(cohort.name, {})["figures_dir"] = str(figures_dir)

    context.write_stage_metadata(
        "stats_r",
        {
            "scripts": [str(model_script)],
            "status": "completed",
            "cohorts": [
                {
                    "cohort": cohort.name,
                    "analysis_role": cohort.analysis_role,
                    "output_dir": cohort_outputs.get(cohort.name, {}).get("stats_dir"),
                }
                for cohort in REPORTING_COHORTS
            ],
            "coupling_robustness_dir": str(coupling_robustness_dir),
            "coupling_robustness_outputs": {name: str(path) for name, path in robustness_outputs.items()},
        },
    )
    context.write_stage_metadata(
        "figures",
        {
            "scripts": [str(figure_script)],
            "status": "completed",
            "cohorts": [
                {
                    "cohort": cohort.name,
                    "analysis_role": cohort.analysis_role,
                    "output_dir": cohort_outputs.get(cohort.name, {}).get("figures_dir"),
                }
                for cohort in REPORTING_COHORTS
            ],
            "dynamic_audit_dir": str(context.stage_path("dynamic_audit")),
            "dynamic_audit_outputs": {name: str(path) for name, path in audit_outputs.items()},
            "coupling_robustness_dir": str(coupling_robustness_dir),
            "coupling_robustness_outputs": {name: str(path) for name, path in robustness_outputs.items()},
        },
    )
    context.write_run_metadata(
        {
            "reporting_cohorts": [
                {"cohort": cohort.name, "analysis_role": cohort.analysis_role}
                for cohort in REPORTING_COHORTS
            ]
        },
    )


def run_python_pipeline(
    bids_root: Path = DEFAULT_BIDS_ROOT,
    metadata_xlsx: Path = DEFAULT_METADATA_XLSX,
    results_root: Path = DEFAULT_RESULTS_ROOT,
    run_dir: Path | None = None,
) -> RunContext:
    context = create_or_load_context(run_dir=run_dir, results_root=results_root)
    build_manifest_and_qc(context, metadata_xlsx=metadata_xlsx, bids_root=bids_root)
    run_static_network_stage(context, bids_root=bids_root)
    run_hfo_stage(context, bids_root=bids_root)
    run_controllability_stage(context, bids_root=bids_root)
    run_fragility_stage(context)
    export_model_tables_stage(context)
    context.write_run_metadata({"status": "python_complete"})
    return context


def run_r_pipeline(
    run_dir: Path,
    results_root: Path = DEFAULT_RESULTS_ROOT,
) -> RunContext:
    context = create_or_load_context(run_dir=run_dir, results_root=results_root)
    run_r_reporting_stage(context)
    context.write_run_metadata({"status": "r_complete"})
    return context


def run_pipeline(
    bids_root: Path = DEFAULT_BIDS_ROOT,
    metadata_xlsx: Path = DEFAULT_METADATA_XLSX,
    results_root: Path = DEFAULT_RESULTS_ROOT,
    run_dir: Path | None = None,
    skip_r: bool = False,
) -> RunContext:
    context = run_python_pipeline(
        bids_root=bids_root,
        metadata_xlsx=metadata_xlsx,
        results_root=results_root,
        run_dir=run_dir,
    )
    if not skip_r:
        run_r_reporting_stage(context)
    context.write_run_metadata({"status": "complete", "skip_r": skip_r})
    return context
