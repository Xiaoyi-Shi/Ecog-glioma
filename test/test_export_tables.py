from __future__ import annotations

from pathlib import Path

import pandas as pd

from ecog_glioma.config import STAGE_DIRS
from ecog_glioma.export_tables import build_model_tables


class MinimalContext:
    def __init__(self, root: Path) -> None:
        self.root = root
        for folder in STAGE_DIRS.values():
            (root / folder).mkdir(parents=True, exist_ok=True)

    def stage_path(self, stage_name: str) -> Path:
        return self.root / STAGE_DIRS[stage_name]


def test_build_model_tables_includes_directed_source_sink(tmp_path: Path) -> None:
    context = MinimalContext(tmp_path)
    manifest = pd.DataFrame(
        {
            "patient_id": ["1", "1"],
            "subject": ["001", "001"],
            "session": ["before", "before"],
            "interval_id": ["1_2", "2_3"],
            "interval_index": [1, 2],
            "contact_a": [1, 2],
            "contact_b": [2, 3],
            "region": [2, 3],
            "distance_mm": [0.0, 2.0],
            "is_boundary_interface": [1, 0],
        }
    )
    interval_qc = manifest.assign(
        interval_usable=True,
        patient_main_included=True,
        patient_sensitivity_included=True,
    )
    static_nodes = pd.DataFrame(
        {
            "subject": ["001", "001"],
            "session": ["before", "before"],
            "run": ["01", "01"],
            "band": ["alpha", "alpha"],
            "interval_id": ["1_2", "2_3"],
            "metric": ["strength", "strength"],
            "value": [0.2, 0.4],
        }
    )
    directed_nodes = static_nodes.assign(
        metric="source_sink_index",
        value=[0.5, -0.5],
    )

    manifest.to_csv(context.stage_path("manifest") / "label_manifest.csv", index=False)
    interval_qc.to_csv(context.stage_path("qc") / "interval_qc_table.csv", index=False)
    static_nodes.to_csv(context.stage_path("static_network") / "node_features_static.csv", index=False)
    directed_nodes.to_csv(context.stage_path("static_network") / "directed_source_sink_features.csv", index=False)

    tables = build_model_tables(context)  # type: ignore[arg-type]
    static_long = tables["model_static_long"]

    assert "alpha_source_sink_index" in set(static_long["feature_name"])
    assert {"feature_z", "region", "distance_mm", "is_boundary_interface"}.issubset(static_long.columns)


def test_build_model_tables_creates_unified_band_metric_long(tmp_path: Path) -> None:
    context = MinimalContext(tmp_path)
    manifest = pd.DataFrame(
        {
            "patient_id": ["1", "1"],
            "subject": ["001", "001"],
            "session": ["before", "before"],
            "interval_id": ["1_2", "2_3"],
            "interval_index": [1, 2],
            "contact_a": [1, 2],
            "contact_b": [2, 3],
            "region": [1, 2],
            "distance_mm": [0.0, 1.0],
            "is_boundary_interface": [1, 1],
        }
    )
    interval_qc = manifest.assign(
        interval_usable=True,
        patient_main_included=True,
        patient_sensitivity_included=True,
    )
    static_nodes = pd.DataFrame(
        {
            "subject": ["001", "001", "001", "001"],
            "session": ["before", "before", "before", "before"],
            "run": ["01", "01", "01", "01"],
            "band": ["alpha", "alpha", "beta", "beta"],
            "interval_id": ["1_2", "2_3", "1_2", "2_3"],
            "metric": ["strength", "strength", "strength", "strength"],
            "value": [1.0, 2.0, 101.0, 102.0],
        }
    )
    directed_nodes = pd.DataFrame(
        {
            "subject": ["001", "001", "001", "001"],
            "session": ["before", "before", "before", "before"],
            "run": ["01", "01", "01", "01"],
            "band": ["alpha", "alpha", "beta", "beta"],
            "interval_id": ["1_2", "2_3", "1_2", "2_3"],
            "metric": ["source_sink_index", "source_sink_index", "source_sink_index", "source_sink_index"],
            "value": [0.2, 0.4, 0.6, 0.8],
        }
    )
    controllability = pd.DataFrame(
        {
            "subject": ["001", "001", "001", "001"],
            "session": ["before", "before", "before", "before"],
            "run": ["01", "01", "01", "01"],
            "band": ["alpha", "alpha", "beta", "beta"],
            "interval_id": ["1_2", "2_3", "1_2", "2_3"],
            "average_controllability_mean": [1.0, 1.1, 1.2, 1.3],
            "average_controllability_std": [0.1, 0.1, 0.2, 0.2],
            "average_controllability_p75": [1.0, 1.1, 1.2, 1.3],
            "average_controllability_p90": [1.0, 1.1, 1.2, 1.3],
            "average_controllability_high_ratio": [0.2, 0.3, 0.4, 0.5],
            "modal_controllability_mean": [0.9, 1.0, 1.1, 1.2],
            "modal_controllability_std": [0.1, 0.1, 0.2, 0.2],
            "modal_controllability_p75": [0.9, 1.0, 1.1, 1.2],
            "modal_controllability_p90": [0.9, 1.0, 1.1, 1.2],
            "modal_controllability_high_ratio": [0.3, 0.4, 0.5, 0.6],
        }
    )
    fragility = pd.DataFrame(
        {
            "subject": ["001", "001", "001", "001"],
            "session": ["before", "before", "before", "before"],
            "run": ["01", "01", "01", "01"],
            "band": ["alpha", "alpha", "beta", "beta"],
            "interval_id": ["1_2", "2_3", "1_2", "2_3"],
            "fragility_mean": [0.5, 0.6, 0.7, 0.8],
            "fragility_std": [0.01, 0.02, 0.03, 0.04],
            "fragility_p75": [0.5, 0.6, 0.7, 0.8],
            "fragility_p90": [0.5, 0.6, 0.7, 0.8],
            "fragility_high_ratio": [0.2, 0.3, 0.4, 0.5],
        }
    )

    manifest.to_csv(context.stage_path("manifest") / "label_manifest.csv", index=False)
    interval_qc.to_csv(context.stage_path("qc") / "interval_qc_table.csv", index=False)
    static_nodes.to_csv(context.stage_path("static_network") / "node_features_static.csv", index=False)
    directed_nodes.to_csv(context.stage_path("static_network") / "directed_source_sink_features.csv", index=False)
    controllability.to_csv(context.stage_path("controllability") / "channel_level_ac_mc_summary.csv", index=False)
    fragility.to_csv(context.stage_path("fragility") / "channel_level_fragility_summary.csv", index=False)

    tables = build_model_tables(context)  # type: ignore[arg-type]
    band_metric_long = tables["model_band_metric_long"]
    strength_rows = band_metric_long[band_metric_long["metric_family"] == "strength"].copy()

    assert {"metric_family", "band", "feature_name", "feature_z", "feature_z_within_band"}.issubset(
        band_metric_long.columns
    )
    assert set(strength_rows["feature_name"]) == {"alpha_strength", "beta_strength"}
    assert set(strength_rows["band"]) == {"alpha", "beta"}
    assert {
        "strength",
        "source_sink_index",
        "average_controllability_mean",
        "fragility_mean",
    }.issubset(set(band_metric_long["metric_family"]))

    alpha_strength_mean = strength_rows.loc[strength_rows["band"] == "alpha", "feature_z"].mean()
    beta_strength_mean = strength_rows.loc[strength_rows["band"] == "beta", "feature_z"].mean()
    assert alpha_strength_mean < 0 < beta_strength_mean

    within_band_means = strength_rows.groupby("band", observed=True)["feature_z_within_band"].mean()
    assert (within_band_means.abs() < 1e-9).all()
