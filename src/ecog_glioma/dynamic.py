from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from scipy.linalg import solve_discrete_lyapunov
from scipy.signal import butter, sosfiltfilt

from .bipolar import BipolarRecording, extract_sliding_windows
from .config import BandDefinition, DEFAULT_DYNAMIC_STEP_SECONDS, DEFAULT_DYNAMIC_WINDOW_SECONDS


def bandpass_channels(data: np.ndarray, sfreq: float, band: BandDefinition) -> np.ndarray:
    sos = butter(
        4,
        [band.fmin, band.fmax],
        btype="bandpass",
        output="sos",
        fs=sfreq,
    )
    return sosfiltfilt(sos, data, axis=1)


def estimate_state_matrix(window: np.ndarray, ridge: float = 1e-3) -> np.ndarray:
    x0 = window[:, :-1]
    x1 = window[:, 1:]
    gram = x0 @ x0.T
    regularized = gram + ridge * np.eye(gram.shape[0], dtype=float)
    a_matrix = x1 @ x0.T @ np.linalg.inv(regularized)
    eigenvalues = np.linalg.eigvals(a_matrix)
    radius = float(np.max(np.abs(eigenvalues)))
    if radius >= 0.99 and radius > 0:
        a_matrix = a_matrix / (radius + 0.01)
    return np.asarray(a_matrix, dtype=float)


def compute_average_controllability(a_matrix: np.ndarray) -> np.ndarray:
    gramian = solve_discrete_lyapunov(a_matrix, np.eye(a_matrix.shape[0], dtype=float))
    return np.diag(gramian).astype(float)


def compute_modal_controllability(a_matrix: np.ndarray) -> np.ndarray:
    eigenvalues, eigenvectors = np.linalg.eig(a_matrix)
    values = np.real(eigenvalues)
    vectors = np.real(eigenvectors)
    modal = np.sum((1.0 - values**2)[None, :] * (vectors**2), axis=1)
    return modal.astype(float)


def compute_column_fragility(a_matrix: np.ndarray, angles: int = 16) -> np.ndarray:
    n_nodes = a_matrix.shape[0]
    fragility = np.zeros(n_nodes, dtype=float)
    unit_angles = np.linspace(0.0, 2.0 * np.pi, angles, endpoint=False)
    for node_index in range(n_nodes):
        selector = np.zeros(n_nodes, dtype=complex)
        selector[node_index] = 1.0
        best = np.inf
        for theta in unit_angles:
            lam = np.exp(1j * theta)
            matrix = lam * np.eye(n_nodes, dtype=complex) - a_matrix.astype(complex)
            kkt = np.block(
                [
                    [matrix.conj().T @ matrix, selector[:, None]],
                    [selector[None, :], np.zeros((1, 1), dtype=complex)],
                ]
            )
            rhs = np.zeros(n_nodes + 1, dtype=complex)
            rhs[-1] = 1.0
            solution = np.linalg.solve(kkt, rhs)
            x_vector = solution[:n_nodes]
            delta = matrix @ x_vector
            best = min(best, float(np.linalg.norm(delta)))
        fragility[node_index] = best
    return fragility


def summarize_window_metrics(
    rows: list[dict[str, Any]],
    value_column: str,
    summary_prefix: str,
) -> pd.DataFrame:
    frame = pd.DataFrame(rows)
    if frame.empty:
        return frame
    grouped = frame.groupby(
        ["subject", "session", "run", "band", "interval_id"],
        dropna=False,
    )
    summary = grouped[value_column].agg(
        mean="mean",
        std="std",
        p75=lambda series: float(series.quantile(0.75)),
        p90=lambda series: float(series.quantile(0.90)),
    ).reset_index()
    summary["std"] = summary["std"].fillna(0.0)
    high_ratio_rows: list[dict[str, Any]] = []
    for (subject, session, run, band), subset in frame.groupby(
        ["subject", "session", "run", "band"],
        dropna=False,
    ):
        threshold = float(subset[value_column].quantile(0.75))
        interval_ratios = (
            subset.assign(is_high=subset[value_column] > threshold)
            .groupby("interval_id", dropna=False)["is_high"]
            .mean()
            .reset_index()
        )
        for row in interval_ratios.itertuples(index=False):
            high_ratio_rows.append(
                {
                    "subject": subject,
                    "session": session,
                    "run": run,
                    "band": band,
                    "interval_id": row.interval_id,
                    "high_ratio": float(row.is_high),
                }
            )
    high_ratio = pd.DataFrame(high_ratio_rows)
    summary = summary.merge(
        high_ratio,
        on=["subject", "session", "run", "band", "interval_id"],
        how="left",
    )
    summary["high_ratio"] = summary["high_ratio"].fillna(0.0)
    rename_map = {
        "mean": f"{summary_prefix}_mean",
        "std": f"{summary_prefix}_std",
        "p75": f"{summary_prefix}_p75",
        "p90": f"{summary_prefix}_p90",
        "high_ratio": f"{summary_prefix}_high_ratio",
    }
    return summary.rename(columns=rename_map)


def estimate_dynamic_states(
    recording: BipolarRecording,
    usable_interval_ids: Sequence[str],
    band: BandDefinition,
    window_seconds: float = DEFAULT_DYNAMIC_WINDOW_SECONDS,
    step_seconds: float = DEFAULT_DYNAMIC_STEP_SECONDS,
) -> tuple[np.ndarray, np.ndarray, pd.DataFrame]:
    if not usable_interval_ids:
        return (
            np.empty((0, 0, 0), dtype=float),
            np.empty((0,), dtype=float),
            pd.DataFrame(columns=["start_s", "end_s", "is_clean"]),
        )
    interval_lookup = {
        row.interval_id: index
        for index, row in enumerate(recording.interval_table.itertuples(index=False))
    }
    indices = [interval_lookup[interval_id] for interval_id in usable_interval_ids]
    filtered = bandpass_channels(recording.data[indices, :], recording.sfreq, band)
    windows, starts, inventory = extract_sliding_windows(
        data=filtered,
        sfreq=recording.sfreq,
        bad_segments=recording.bad_segments,
        window_seconds=window_seconds,
        step_seconds=step_seconds,
    )
    if windows.shape[0] == 0:
        return (
            np.empty((0, len(usable_interval_ids), len(usable_interval_ids)), dtype=float),
            starts,
            inventory,
        )
    matrices = np.stack(
        [estimate_state_matrix(window) for window in windows],
        axis=0,
    )
    return matrices, starts, inventory


def save_state_matrices(
    path: Path,
    matrices: np.ndarray,
    starts_s: np.ndarray,
    interval_ids: Sequence[str],
    band_name: str,
    window_seconds: float,
    step_seconds: float,
    subject: str,
    session: str,
    run: str,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        path,
        matrices=matrices,
        starts_s=starts_s,
        interval_ids=np.asarray(interval_ids, dtype=str),
        band=np.asarray([band_name], dtype=str),
        window_seconds=np.asarray([window_seconds], dtype=float),
        step_seconds=np.asarray([step_seconds], dtype=float),
        subject=np.asarray([subject], dtype=str),
        session=np.asarray([session], dtype=str),
        run=np.asarray([run], dtype=str),
    )
