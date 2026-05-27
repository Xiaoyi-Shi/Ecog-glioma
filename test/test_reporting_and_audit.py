from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from ecog_glioma.coupling_robustness import run_coupling_robustness_stage
from ecog_glioma.dynamic_audit import run_dynamic_audit_stage
from ecog_glioma.reporting import build_cohort_manifest, filter_frame_for_cohort
from ecog_glioma.run_context import RunContext


def test_filter_frame_for_cohort_uses_existing_flags() -> None:
    frame = pd.DataFrame(
        {
            "patient": ["001", "002", "003"],
            "interval_id": ["1_2", "1_2", "1_2"],
            "patient_main_included": [True, False, False],
            "patient_sensitivity_included": [True, True, False],
        }
    )

    main = filter_frame_for_cohort(frame, "main")
    sensitivity = filter_frame_for_cohort(frame, "sensitivity")
    full = filter_frame_for_cohort(frame, "full_modelable")
    manifest = build_cohort_manifest(frame)

    assert set(main["patient"]) == {"001"}
    assert set(sensitivity["patient"]) == {"001", "002"}
    assert set(full["patient"]) == {"001", "002", "003"}
    assert set(manifest["cohort"]) == {"main", "sensitivity", "full_modelable"}
    assert manifest.loc[manifest["cohort"] == "main", "patient_count"].item() == 1
    assert manifest.loc[manifest["cohort"] == "sensitivity", "patient_count"].item() == 2


def test_run_dynamic_audit_stage_writes_expected_outputs(tmp_path: Path) -> None:
    context = RunContext.create(results_root=tmp_path, timestamp="20260527_150000")

    joint = pd.DataFrame(
        {
            "patient": ["001", "001", "001", "001", "002", "002", "002", "002"],
            "session": ["before"] * 8,
            "run": ["01"] * 8,
            "interval_id": ["1_2", "1_2", "2_3", "2_3", "1_2", "1_2", "2_3", "2_3"],
            "interval_index": [1, 1, 2, 2, 1, 1, 2, 2],
            "region": [1, 1, 2, 2, 1, 1, 3, 3],
            "distance_mm": [0.0, 0.0, 1.0, 1.0, 0.2, 0.2, 2.0, 2.0],
            "is_boundary_interface": [1, 1, 0, 0, 1, 1, 0, 0],
            "feature_name": [
                "alpha_average_controllability_mean",
                "alpha_fragility_mean",
                "beta_average_controllability_mean",
                "beta_fragility_mean",
                "alpha_average_controllability_mean",
                "alpha_fragility_mean",
                "beta_average_controllability_mean",
                "beta_fragility_mean",
            ],
            "feature_value": [1.0, 0.4, 1.2, 0.5, 0.9, 0.6, 1.1, 0.8],
            "feature_z": [0.8, -0.8, 1.0, -1.0, 0.4, -0.4, 0.6, -0.6],
            "feature_family": ["dynamic", "fragility", "dynamic", "fragility", "dynamic", "fragility", "dynamic", "fragility"],
            "patient_main_included": [True, True, True, True, False, False, False, False],
            "patient_sensitivity_included": [True, True, True, True, True, True, True, True],
        }
    )
    band_metric = pd.DataFrame(
        {
            "patient": ["001", "001", "001", "001", "002", "002", "002", "002"],
            "session": ["before"] * 8,
            "run": ["01"] * 8,
            "band": ["alpha", "alpha", "beta", "beta", "alpha", "alpha", "beta", "beta"],
            "interval_id": ["1_2", "1_2", "2_3", "2_3", "1_2", "1_2", "2_3", "2_3"],
            "interval_index": [1, 1, 2, 2, 1, 1, 2, 2],
            "region": [1, 1, 2, 2, 1, 1, 3, 3],
            "distance_mm": [0.0, 0.0, 1.0, 1.0, 0.2, 0.2, 2.0, 2.0],
            "is_boundary_interface": [1, 1, 0, 0, 1, 1, 0, 0],
            "metric_family": [
                "average_controllability_mean",
                "fragility_mean",
                "average_controllability_mean",
                "fragility_mean",
                "average_controllability_mean",
                "fragility_mean",
                "average_controllability_mean",
                "fragility_mean",
            ],
            "feature_value": [1.0, 0.4, 1.2, 0.5, 0.9, 0.6, 1.1, 0.8],
            "feature_z": [0.8, -0.8, 1.0, -1.0, 0.4, -0.4, 0.6, -0.6],
            "feature_z_within_band": [0.5, -0.5, 0.7, -0.7, 0.3, -0.3, 0.4, -0.4],
            "patient_main_included": [True, True, True, True, False, False, False, False],
            "patient_sensitivity_included": [True, True, True, True, True, True, True, True],
        }
    )
    window_ac = pd.DataFrame(
        {
            "subject": ["001"] * 8 + ["002"] * 8,
            "session": ["before"] * 16,
            "run": ["01"] * 16,
            "band": ["alpha", "alpha", "alpha", "alpha", "beta", "beta", "beta", "beta"] * 2,
            "window_start_s": [0.0, 0.0, 1.0, 1.0, 0.0, 0.0, 1.0, 1.0] * 2,
            "interval_id": ["1_2", "2_3", "1_2", "2_3", "1_2", "2_3", "1_2", "2_3"] * 2,
            "average_controllability": [
                1.0, 1.15, 1.1, 1.2, 1.2, 1.3, 1.25, 1.35,
                0.9, 1.0, 0.95, 1.05, 1.05, 1.15, 1.1, 1.2,
            ],
            "modal_controllability": [0.5] * 16,
        }
    )
    window_fragility = pd.DataFrame(
        {
            "subject": ["001"] * 8 + ["002"] * 8,
            "session": ["before"] * 16,
            "run": ["01"] * 16,
            "band": ["alpha", "alpha", "alpha", "alpha", "beta", "beta", "beta", "beta"] * 2,
            "window_start_s": [0.0, 0.0, 1.0, 1.0, 0.0, 0.0, 1.0, 1.0] * 2,
            "interval_id": ["1_2", "2_3", "1_2", "2_3", "1_2", "2_3", "1_2", "2_3"] * 2,
            "fragility": [
                0.4, 0.45, 0.35, 0.42, 0.5, 0.55, 0.48, 0.52,
                0.6, 0.72, 0.58, 0.7, 0.8, 0.9, 0.78, 0.88,
            ],
        }
    )

    joint.to_csv(context.stage_path("model_tables") / "model_joint_long.csv", index=False)
    band_metric.to_csv(context.stage_path("model_tables") / "model_band_metric_long.csv", index=False)
    window_ac.to_csv(context.stage_path("controllability") / "window_level_ac_mc.csv", index=False)
    window_fragility.to_csv(context.stage_path("fragility") / "window_level_fragility.csv", index=False)

    outputs = run_dynamic_audit_stage(context)

    assert {"cohort_manifest", "window_level_pairs", "interval_summary_pairs", "band_aggregated_pairs", "coupling_summary", "metric_coupling_baseline", "metric_coupling_baseline_summary", "dynamic_audit_summary"} <= set(outputs)

    cohort_manifest = pd.read_csv(outputs["cohort_manifest"])
    coupling_summary = pd.read_csv(outputs["coupling_summary"])
    baseline_summary = pd.read_csv(outputs["metric_coupling_baseline_summary"])
    band_pairs = pd.read_csv(outputs["band_aggregated_pairs"])

    assert {"run_dir", "cohort", "analysis_role", "patient_count", "interval_count"}.issubset(cohort_manifest.columns)
    assert set(cohort_manifest["cohort"]) == {"main", "sensitivity", "full_modelable"}
    assert set(coupling_summary["aggregation_level"]) == {"window_level", "interval_summary", "band_aggregated_interval"}
    assert {"main", "sensitivity", "full_modelable"}.issubset(set(coupling_summary["cohort"]))
    assert not baseline_summary.empty
    assert set(band_pairs["region"]) == {1, 2, 3}

    metadata = json.loads((context.stage_path("dynamic_audit") / "stage_metadata.json").read_text(encoding="utf-8"))
    assert metadata["status"] == "completed"
    assert metadata["baseline_assumptions"]["repeats_per_structure"] == 16


def test_run_coupling_robustness_stage_writes_expected_outputs(tmp_path: Path) -> None:
    context = RunContext.create(results_root=tmp_path, timestamp="20260527_160000")

    band_pairs_rows: list[dict[str, object]] = []
    interval_pairs_rows: list[dict[str, object]] = []
    model_band_metric_rows: list[dict[str, object]] = []
    cohorts = [
        ("main", "primary", ["001", "002", "003", "004"]),
        ("sensitivity", "exploratory", ["001", "002", "003", "004", "005"]),
        ("full_modelable", "exploratory", ["001", "002", "003", "004", "005", "006"]),
    ]
    patient_order = ["001", "002", "003", "004", "005", "006"]
    patient_offsets = {patient: index * 0.02 for index, patient in enumerate(patient_order)}
    for cohort_name, analysis_role, patients in cohorts:
        for patient in patients:
            offset = patient_offsets[patient]
            for band in ["alpha", "beta", "low_gamma"]:
                for interval_id, region, distance_mm, ac_base, frag_base in [
                    ("i1", 1.0, 0.0, 0.84 + offset, 0.78 - offset),
                    ("i2", 1.0, 0.4, 0.88 + offset, 0.74 - offset),
                    ("i3", 2.0, 1.0, 1.24 + offset, 0.46 - offset),
                    ("i4", 2.0, 1.3, 1.28 + offset, 0.42 - offset),
                    ("i5", 3.0, 2.3, 1.00 + offset, 0.63 - offset),
                ]:
                    band_adjust = {"alpha": 0.00, "beta": 0.03, "low_gamma": 0.05}[band]
                    row = {
                        "run_dir": context.run_root.as_posix(),
                        "cohort": cohort_name,
                        "analysis_role": analysis_role,
                        "cohort_patient_count": len(patients),
                        "cohort_interval_count": len(patients) * 5,
                        "patient": patient,
                        "session": "before",
                        "run": "01",
                        "interval_id": interval_id,
                        "interval_index": int(interval_id[-1]),
                        "region": region,
                        "distance_mm": distance_mm,
                        "is_boundary_interface": 1 if region == 1.0 else 0,
                        "patient_main_included": cohort_name == "main",
                        "patient_sensitivity_included": cohort_name != "full_modelable" or patient in {"001", "002", "003", "004", "005"},
                        "raw_average_controllability": ac_base + band_adjust,
                        "raw_fragility": frag_base - band_adjust,
                        "feature_z_average_controllability": ac_base - 1.0,
                        "feature_z_fragility": frag_base - 0.6,
                        "feature_z_within_band_average_controllability": ac_base - 1.0 + band_adjust,
                        "feature_z_within_band_fragility": frag_base - 0.6 - band_adjust,
                        "band": band,
                    }
                    interval_pairs_rows.append(row.copy())
                    if band == "alpha":
                        band_row = row.copy()
                        band_row["band"] = "all"
                        band_pairs_rows.append(band_row)
                    model_band_metric_rows.extend(
                        [
                            {
                                "patient": patient,
                                "session": "before",
                                "run": "01",
                                "band": band,
                                "interval_id": interval_id,
                                "interval_index": int(interval_id[-1]),
                                "region": region,
                                "distance_mm": distance_mm,
                                "is_boundary_interface": 1 if region == 1.0 else 0,
                                "metric_family": "average_controllability_p90",
                                "feature_value": ac_base + band_adjust,
                                "feature_z": ac_base - 1.0,
                                "feature_z_within_band": ac_base - 1.0 + band_adjust,
                                "patient_main_included": cohort_name == "main",
                                "patient_sensitivity_included": cohort_name != "full_modelable" or patient in {"001", "002", "003", "004", "005"},
                            },
                            {
                                "patient": patient,
                                "session": "before",
                                "run": "01",
                                "band": band,
                                "interval_id": interval_id,
                                "interval_index": int(interval_id[-1]),
                                "region": region,
                                "distance_mm": distance_mm,
                                "is_boundary_interface": 1 if region == 1.0 else 0,
                                "metric_family": "fragility_mean",
                                "feature_value": frag_base - band_adjust,
                                "feature_z": frag_base - 0.6,
                                "feature_z_within_band": frag_base - 0.6 - band_adjust,
                                "patient_main_included": cohort_name == "main",
                                "patient_sensitivity_included": cohort_name != "full_modelable" or patient in {"001", "002", "003", "004", "005"},
                            },
                        ]
                    )

    pd.DataFrame(interval_pairs_rows).to_csv(
        context.stage_path("dynamic_audit") / "interval_summary_pairs.csv",
        index=False,
    )
    pd.DataFrame(band_pairs_rows).to_csv(
        context.stage_path("dynamic_audit") / "band_aggregated_pairs.csv",
        index=False,
    )
    pd.DataFrame(model_band_metric_rows).to_csv(
        context.stage_path("model_tables") / "model_band_metric_long.csv",
        index=False,
    )

    outputs = run_coupling_robustness_stage(context)

    assert {
        "decomposition_summary",
        "null_comparison_summary",
        "inclusion_threshold_scan",
        "distance_threshold_scan",
        "stability_matrix",
        "robustness_summary",
        "cohort_qc_summary",
        "coupling_robustness_summary",
    } <= set(outputs)

    decomposition = pd.read_csv(outputs["decomposition_summary"])
    null_summary = pd.read_csv(outputs["null_comparison_summary"])
    inclusion_scan = pd.read_csv(outputs["inclusion_threshold_scan"])
    distance_scan = pd.read_csv(outputs["distance_threshold_scan"])
    stability_matrix = pd.read_csv(outputs["stability_matrix"])
    robustness_summary = pd.read_csv(outputs["robustness_summary"])

    assert {"pooled", "between_patient", "within_patient", "within_region", "within_band"} <= set(decomposition["decomposition_view"])
    assert {"main", "sensitivity", "full_modelable"} <= set(decomposition["cohort"])
    assert not null_summary.empty
    assert set(inclusion_scan["threshold_value"]) == {8, 10, 12, 14, 16, 18}
    assert set(distance_scan["threshold_value"]) == {1.0, 1.5, 2.0, 2.5}
    assert {"stable", "direction_reversal", "significance_loss", "insufficient", "not_applicable"} & set(stability_matrix["overall_stability_status"])
    assert {"supported", "exploratory", "artifact_risk", "threshold_sensitive", "insufficient"} & set(robustness_summary["robustness_status"])

    metadata = json.loads((context.stage_path("coupling_robustness") / "stage_metadata.json").read_text(encoding="utf-8"))
    assert metadata["status"] == "completed"
    assert metadata["thresholds"]["primary_distance_threshold_mm"] == 1.5
