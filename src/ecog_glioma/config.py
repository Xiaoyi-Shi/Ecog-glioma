from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class BandDefinition:
    name: str
    fmin: float
    fmax: float


DEFAULT_BIDS_ROOT = Path("datas/data_02_BIDS")
DEFAULT_METADATA_XLSX = Path("datas/ele_pos.xlsx")
DEFAULT_RESULTS_ROOT = Path("results")
DEFAULT_SESSION_FILTER = "before"

STAGE_DIRS = {
    "manifest": "00_manifest",
    "qc": "01_qc",
    "static_network": "02_static_network",
    "hfo": "03_hfo",
    "controllability": "04_controllability",
    "fragility": "05_fragility",
    "model_tables": "06_model_tables",
    "stats_r": "07_stats_r",
    "figures": "08_figures",
    "dynamic_audit": "09_dynamic_audit",
    "coupling_robustness": "10_coupling_robustness",
    "logs": "logs",
}

STATIC_BANDS = (
    BandDefinition("delta", 1.0, 4.0),
    BandDefinition("theta", 4.0, 8.0),
    BandDefinition("alpha", 8.0, 13.0),
    BandDefinition("beta", 13.0, 30.0),
    BandDefinition("low_gamma", 30.0, 45.0),
    BandDefinition("high_gamma", 55.0, 80.0),
)

DYNAMIC_BANDS = (
    BandDefinition("alpha", 8.0, 13.0),
    BandDefinition("beta", 13.0, 30.0),
    BandDefinition("low_gamma", 30.0, 45.0),
)

HFO_BANDS = (
    BandDefinition("ripple", 80.0, 250.0),
    BandDefinition("fast_ripple", 250.0, 500.0),
)

DEFAULT_STATIC_EPOCH_SECONDS = 2.0
DEFAULT_DYNAMIC_WINDOW_SECONDS = 4.0
DEFAULT_DYNAMIC_STEP_SECONDS = 1.0
DEFAULT_DYNAMIC_WINDOW_OPTIONS = (2.0, 4.0, 6.0)
DEFAULT_OMEGAS = (0.5, 0.1, 1.0)
DEFAULT_MAIN_MIN_INTERVALS = 16
DEFAULT_SENSITIVITY_MIN_INTERVALS = 12
