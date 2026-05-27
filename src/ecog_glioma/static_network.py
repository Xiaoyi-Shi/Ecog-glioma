from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import Any

import networkx as nx
import numpy as np
import pandas as pd
from mne_connectivity import spectral_connectivity_epochs
from scipy.signal import butter, sosfiltfilt

from .bipolar import BipolarRecording, extract_sliding_windows
from .config import BandDefinition, DEFAULT_OMEGAS, DEFAULT_STATIC_EPOCH_SECONDS
from .utils import write_dataframe, write_json


def leading_eigenvector_centrality(matrix: np.ndarray) -> np.ndarray:
    if matrix.size == 0:
        return np.empty((0,), dtype=float)
    eigenvalues, eigenvectors = np.linalg.eig(matrix)
    index = int(np.argmax(np.real(eigenvalues)))
    vector = np.abs(np.real(eigenvectors[:, index]))
    if np.allclose(vector.sum(), 0):
        return np.zeros(matrix.shape[0], dtype=float)
    return vector / vector.sum()


def compute_weighted_clustering(matrix: np.ndarray) -> np.ndarray:
    graph = nx.from_numpy_array(matrix)
    clustering = nx.clustering(graph, weight="weight")
    return np.asarray([clustering[index] for index in range(matrix.shape[0])], dtype=float)


def compute_band_connectivity(
    recording: BipolarRecording,
    interval_ids: list[str],
    band: BandDefinition,
    epoch_seconds: float = DEFAULT_STATIC_EPOCH_SECONDS,
) -> tuple[np.ndarray, dict[str, Any]]:
    interval_lookup = {
        row.interval_id: index
        for index, row in enumerate(recording.interval_table.itertuples(index=False))
    }
    indices = [interval_lookup[interval_id] for interval_id in interval_ids]
    data = recording.data[indices, :]
    epochs, starts, inventory = extract_sliding_windows(
        data=data,
        sfreq=recording.sfreq,
        bad_segments=recording.bad_segments,
        window_seconds=epoch_seconds,
        step_seconds=epoch_seconds,
    )
    if epochs.shape[0] < 2:
        return (
            np.zeros((len(interval_ids), len(interval_ids)), dtype=float),
            {
                "band": band.name,
                "n_epochs": int(epochs.shape[0]),
                "epoch_seconds": epoch_seconds,
                "clean_epoch_starts_s": starts.tolist(),
                "inventory_rows": int(len(inventory)),
            },
        )
    connectivity = spectral_connectivity_epochs(
        epochs,
        names=interval_ids,
        sfreq=recording.sfreq,
        method="wpli2_debiased",
        mode="multitaper",
        fmin=band.fmin,
        fmax=band.fmax,
        faverage=True,
        verbose="ERROR",
    )
    dense = connectivity.get_data(output="dense")
    matrix = np.asarray(dense[:, :, 0], dtype=float)
    matrix = np.nan_to_num(matrix, nan=0.0, posinf=0.0, neginf=0.0)
    matrix = (matrix + matrix.T) / 2.0
    matrix = np.clip(matrix, a_min=0.0, a_max=None)
    np.fill_diagonal(matrix, 0.0)
    return (
        matrix,
        {
            "band": band.name,
            "n_epochs": int(epochs.shape[0]),
            "epoch_seconds": epoch_seconds,
            "clean_epoch_starts_s": starts.tolist(),
            "inventory_rows": int(len(inventory)),
        },
    )


def compute_node_metrics(matrix: np.ndarray) -> dict[str, np.ndarray]:
    strength = matrix.sum(axis=1)
    ec = leading_eigenvector_centrality(matrix)
    clustering = compute_weighted_clustering(matrix)
    return {
        "strength": strength,
        "eigenvector_centrality": ec,
        "clustering_coefficient": clustering,
    }


def compute_lagged_source_sink_index(
    data: np.ndarray,
    sfreq: float,
    max_lag_ms: float = 20.0,
    max_lag_samples_cap: int = 64,
) -> tuple[np.ndarray, np.ndarray]:
    """Estimate directional net-flow from lagged cross-correlation asymmetry."""
    if data.size == 0 or data.shape[0] == 0 or data.shape[1] < 3:
        n_nodes = int(data.shape[0]) if data.ndim == 2 else 0
        return np.zeros(n_nodes, dtype=float), np.zeros((n_nodes, n_nodes), dtype=float)

    centered = data - data.mean(axis=1, keepdims=True)
    scale = centered.std(axis=1, keepdims=True)
    scale[scale == 0] = 1.0
    normalized = centered / scale
    max_lag_samples = int(round(max_lag_ms * sfreq / 1000.0))
    max_lag_samples = min(max_lag_samples, max_lag_samples_cap, normalized.shape[1] - 1)
    if max_lag_samples < 1:
        return np.zeros(normalized.shape[0], dtype=float), np.zeros((normalized.shape[0], normalized.shape[0]), dtype=float)

    directed = np.zeros((normalized.shape[0], normalized.shape[0]), dtype=float)
    for lag in range(1, max_lag_samples + 1):
        left = normalized[:, :-lag]
        right = normalized[:, lag:]
        correlation = (left @ right.T) / left.shape[1]
        directed = np.maximum(directed, np.abs(correlation))
    np.fill_diagonal(directed, 0.0)
    outgoing = directed.sum(axis=1)
    incoming = directed.sum(axis=0)
    source_sink = outgoing - incoming
    return source_sink.astype(float), directed


def compute_band_source_sink(
    recording: BipolarRecording,
    interval_ids: list[str],
    band: BandDefinition,
    epoch_seconds: float = DEFAULT_STATIC_EPOCH_SECONDS,
) -> tuple[np.ndarray, np.ndarray, dict[str, Any]]:
    interval_lookup = {
        row.interval_id: index
        for index, row in enumerate(recording.interval_table.itertuples(index=False))
    }
    indices = [interval_lookup[interval_id] for interval_id in interval_ids]
    data = recording.data[indices, :]
    sos = butter(
        4,
        [band.fmin, band.fmax],
        btype="bandpass",
        output="sos",
        fs=recording.sfreq,
    )
    filtered = sosfiltfilt(sos, data, axis=1)
    epochs, starts, inventory = extract_sliding_windows(
        data=filtered,
        sfreq=recording.sfreq,
        bad_segments=recording.bad_segments,
        window_seconds=epoch_seconds,
        step_seconds=epoch_seconds,
    )
    if epochs.shape[0] == 0:
        source_sink = np.zeros(len(interval_ids), dtype=float)
        directed = np.zeros((len(interval_ids), len(interval_ids)), dtype=float)
    else:
        clean_data = np.concatenate([epoch for epoch in epochs], axis=1)
        source_sink, directed = compute_lagged_source_sink_index(
            clean_data,
            sfreq=recording.sfreq,
        )
    return (
        source_sink,
        directed,
        {
            "band": band.name,
            "n_epochs": int(epochs.shape[0]),
            "epoch_seconds": epoch_seconds,
            "clean_epoch_starts_s": starts.tolist(),
            "inventory_rows": int(len(inventory)),
            "method": "lagged_cross_correlation_source_sink",
        },
    )


def compute_multiplex_participation(strength_by_band: np.ndarray) -> np.ndarray:
    if strength_by_band.shape[1] <= 1:
        return np.zeros(strength_by_band.shape[0], dtype=float)
    total = strength_by_band.sum(axis=1, keepdims=True)
    zero_total = total[:, 0] == 0
    total[zero_total, :] = np.nan
    fractions = strength_by_band / total
    mpc = (strength_by_band.shape[1] / (strength_by_band.shape[1] - 1.0)) * (
        1.0 - np.nansum(fractions**2, axis=1)
    )
    mpc[zero_total] = 0.0
    return np.nan_to_num(mpc, nan=0.0)


def compute_multilayer_features(
    matrices_by_band: dict[str, np.ndarray],
    interval_ids: list[str],
    omegas: Sequence[float] = DEFAULT_OMEGAS,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    band_names = list(matrices_by_band)
    matrices = [matrices_by_band[band_name] for band_name in band_names]
    n_layers = len(matrices)
    n_nodes = len(interval_ids)
    strength_by_band = np.stack([matrix.sum(axis=1) for matrix in matrices], axis=1)
    mpc = compute_multiplex_participation(strength_by_band)

    node_rows: list[dict[str, Any]] = []
    similarity_rows: list[dict[str, Any]] = []
    for omega in omegas:
        supra = np.zeros((n_layers * n_nodes, n_layers * n_nodes), dtype=float)
        for layer_index, matrix in enumerate(matrices):
            start = layer_index * n_nodes
            stop = start + n_nodes
            supra[start:stop, start:stop] = matrix
        for layer_index in range(n_layers - 1):
            for node_index in range(n_nodes):
                left = layer_index * n_nodes + node_index
                right = (layer_index + 1) * n_nodes + node_index
                supra[left, right] = omega
                supra[right, left] = omega
        supra_ec = leading_eigenvector_centrality(supra)
        supra_ec = supra_ec.reshape(n_layers, n_nodes)
        mec = supra_ec.mean(axis=0)
        for node_index, interval_id in enumerate(interval_ids):
            node_rows.append(
                {
                    "interval_id": interval_id,
                    "omega": omega,
                    "metric": "mec",
                    "value": float(mec[node_index]),
                }
            )
            node_rows.append(
                {
                    "interval_id": interval_id,
                    "omega": omega,
                    "metric": "mpc",
                    "value": float(mpc[node_index]),
                }
            )

    for layer_index in range(n_layers - 1):
        left = matrices[layer_index]
        right = matrices[layer_index + 1]
        left_vector = left[np.triu_indices_from(left, k=1)]
        right_vector = right[np.triu_indices_from(right, k=1)]
        denominator = float(np.linalg.norm(left_vector) * np.linalg.norm(right_vector))
        similarity = 0.0 if denominator == 0 else float(np.dot(left_vector, right_vector) / denominator)
        similarity_rows.append(
            {
                "band_a": band_names[layer_index],
                "band_b": band_names[layer_index + 1],
                "metric": "interlayer_similarity",
                "value": similarity,
            }
        )

    return pd.DataFrame(node_rows), pd.DataFrame(similarity_rows)


def save_matrix(matrix: np.ndarray, interval_ids: list[str], path: Path) -> None:
    frame = pd.DataFrame(matrix, index=interval_ids, columns=interval_ids)
    write_dataframe(frame, path, index=True)
