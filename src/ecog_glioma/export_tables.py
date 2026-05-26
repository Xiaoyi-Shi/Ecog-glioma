from __future__ import annotations

from pathlib import Path

import pandas as pd

from .run_context import RunContext
from .utils import add_patient_zscore, read_dataframe, write_dataframe


def _load_csv(path: Path, dtype: dict[str, str] | None = None) -> pd.DataFrame:
    return read_dataframe(path, dtype=dtype)


def build_model_tables(context: RunContext) -> dict[str, pd.DataFrame]:
    manifest = _load_csv(
        context.stage_path("manifest") / "label_manifest.csv",
        dtype={"patient_id": str, "subject": str, "session": str, "interval_id": str},
    )
    interval_qc = _load_csv(
        context.stage_path("qc") / "interval_qc_table.csv",
        dtype={"patient_id": str, "subject": str, "session": str, "interval_id": str, "run": str},
    )
    static_nodes = _load_csv(
        context.stage_path("static_network") / "node_features_static.csv",
        dtype={"subject": str, "session": str, "run": str, "band": str, "interval_id": str, "metric": str},
    )
    multilayer_nodes = _load_csv(
        context.stage_path("static_network") / "multilayer_node_features.csv",
        dtype={"subject": str, "session": str, "run": str, "interval_id": str, "metric": str},
    )
    multilayer_patient = _load_csv(
        context.stage_path("static_network") / "multilayer_patient_features.csv",
        dtype={"subject": str, "session": str, "run": str, "metric": str, "band_a": str, "band_b": str},
    )
    hfo_summary = _load_csv(
        context.stage_path("hfo") / "hfo_channel_summary.csv",
        dtype={"subject": str, "session": str, "run": str, "interval_id": str, "hfo_type": str},
    )
    controllability = _load_csv(
        context.stage_path("controllability") / "channel_level_ac_mc_summary.csv",
        dtype={"subject": str, "session": str, "run": str, "band": str, "interval_id": str},
    )
    fragility = _load_csv(
        context.stage_path("fragility") / "channel_level_fragility_summary.csv",
        dtype={"subject": str, "session": str, "run": str, "band": str, "interval_id": str},
    )

    label_qc = manifest.merge(
        interval_qc,
        on=["subject", "session", "interval_id", "contact_a", "contact_b"],
        how="left",
        suffixes=("", "_qc"),
    )
    label_cols = [
        "patient_id",
        "subject",
        "session",
        "interval_id",
        "interval_index",
        "contact_a",
        "contact_b",
        "region",
        "distance_mm",
        "is_boundary_interface",
        "interval_usable",
        "patient_main_included",
        "patient_sensitivity_included",
    ]

    static_long = pd.DataFrame()
    if not static_nodes.empty:
        static_long = static_nodes.rename(
            columns={
                "subject": "patient",
                "metric": "feature_name",
                "value": "feature_value",
            }
        )
        static_long["feature_family"] = "static"
        static_long["feature_name"] = static_long["band"] + "_" + static_long["feature_name"]
        static_long = static_long.merge(
            label_qc[label_cols],
            left_on=["patient", "session", "interval_id"],
            right_on=["subject", "session", "interval_id"],
            how="left",
        )
        static_long = static_long.drop(columns=["subject"])
        static_long = add_patient_zscore(static_long, patient_col="patient")

    if not multilayer_nodes.empty:
        multilayer_long = multilayer_nodes.rename(
            columns={
                "subject": "patient",
                "metric": "feature_name",
                "value": "feature_value",
            }
        )
        multilayer_long["feature_family"] = "multilayer"
        multilayer_long["feature_name"] = (
            multilayer_long["feature_name"] + "_omega_" + multilayer_long["omega"].astype(str)
        )
        multilayer_long = multilayer_long.merge(
            label_qc[label_cols],
            left_on=["patient", "session", "interval_id"],
            right_on=["subject", "session", "interval_id"],
            how="left",
        )
        multilayer_long = multilayer_long.drop(columns=["subject"])
        multilayer_long = add_patient_zscore(multilayer_long, patient_col="patient")
        static_long = pd.concat([static_long, multilayer_long], ignore_index=True, sort=False)

    hfo_long = pd.DataFrame()
    if not hfo_summary.empty:
        hfo_long = hfo_summary.melt(
            id_vars=["subject", "session", "run", "interval_id", "hfo_type"],
            value_vars=["event_count", "artifact_free_event_count", "rate_per_min", "rate_per_min_all"],
            var_name="metric",
            value_name="feature_value",
        ).rename(columns={"subject": "patient"})
        hfo_long["feature_family"] = "hfo"
        hfo_long["feature_name"] = hfo_long["hfo_type"] + "_" + hfo_long["metric"]
        hfo_long = hfo_long.merge(
            label_qc[label_cols],
            left_on=["patient", "session", "interval_id"],
            right_on=["subject", "session", "interval_id"],
            how="left",
        )
        hfo_long = hfo_long.drop(columns=["subject", "metric"])
        hfo_long = add_patient_zscore(hfo_long, patient_col="patient")

    dynamic_long = pd.DataFrame()
    if not controllability.empty:
        ac_mc_long = controllability.melt(
            id_vars=["subject", "session", "run", "band", "interval_id"],
            value_vars=[
                "average_controllability_mean",
                "average_controllability_std",
                "average_controllability_p75",
                "average_controllability_p90",
                "average_controllability_high_ratio",
                "modal_controllability_mean",
                "modal_controllability_std",
                "modal_controllability_p75",
                "modal_controllability_p90",
                "modal_controllability_high_ratio",
            ],
            var_name="metric",
            value_name="feature_value",
        ).rename(columns={"subject": "patient"})
        ac_mc_long["feature_family"] = "dynamic"
        ac_mc_long["feature_name"] = ac_mc_long["band"] + "_" + ac_mc_long["metric"]
        ac_mc_long = ac_mc_long.merge(
            label_qc[label_cols],
            left_on=["patient", "session", "interval_id"],
            right_on=["subject", "session", "interval_id"],
            how="left",
        )
        dynamic_long = ac_mc_long.drop(columns=["subject", "metric"])
        dynamic_long = add_patient_zscore(dynamic_long, patient_col="patient")

    fragility_long = pd.DataFrame()
    if not fragility.empty:
        fragility_long = fragility.melt(
            id_vars=["subject", "session", "run", "band", "interval_id"],
            value_vars=[
                "fragility_mean",
                "fragility_std",
                "fragility_p75",
                "fragility_p90",
                "fragility_high_ratio",
            ],
            var_name="metric",
            value_name="feature_value",
        ).rename(columns={"subject": "patient"})
        fragility_long["feature_family"] = "fragility"
        fragility_long["feature_name"] = fragility_long["band"] + "_" + fragility_long["metric"]
        fragility_long = fragility_long.merge(
            label_qc[label_cols],
            left_on=["patient", "session", "interval_id"],
            right_on=["subject", "session", "interval_id"],
            how="left",
        )
        fragility_long = fragility_long.drop(columns=["subject", "metric"])
        fragility_long = add_patient_zscore(fragility_long, patient_col="patient")

    joint_long = pd.concat(
        [frame for frame in [static_long, hfo_long, dynamic_long, fragility_long] if not frame.empty],
        ignore_index=True,
        sort=False,
    )
    if not joint_long.empty:
        joint_long = add_patient_zscore(joint_long, patient_col="patient")

    patient_summary = pd.DataFrame()
    if not multilayer_patient.empty:
        patient_summary = multilayer_patient.copy()

    return {
        "model_static_long": static_long,
        "model_hfo_long": hfo_long,
        "model_dynamic_long": pd.concat(
            [frame for frame in [dynamic_long, fragility_long] if not frame.empty],
            ignore_index=True,
            sort=False,
        ),
        "model_joint_long": joint_long,
        "model_patient_summary": patient_summary,
    }


def write_model_tables(context: RunContext) -> dict[str, Path]:
    tables = build_model_tables(context)
    outputs: dict[str, Path] = {}
    for name, frame in tables.items():
        path = context.stage_path("model_tables") / f"{name}.csv"
        write_dataframe(frame, path, index=False)
        outputs[name] = path
    return outputs
