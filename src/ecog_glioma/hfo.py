from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import numpy as np
import pandas as pd
from scipy.signal import butter, sosfiltfilt

from .bipolar import BipolarRecording, build_bad_sample_mask, clean_duration_seconds
from .config import BandDefinition, HFO_BANDS


def _moving_rms(signal: np.ndarray, window_samples: int) -> np.ndarray:
    window = np.ones(window_samples, dtype=float) / window_samples
    return np.sqrt(np.convolve(signal**2, window, mode="same"))


def _detect_segments(active_mask: np.ndarray) -> list[tuple[int, int]]:
    padded = np.concatenate([[False], active_mask, [False]])
    starts = np.flatnonzero(~padded[:-1] & padded[1:])
    ends = np.flatnonzero(padded[:-1] & ~padded[1:])
    return list(zip(starts.tolist(), ends.tolist(), strict=False))


def detect_hfo_events_for_signal(
    signal: np.ndarray,
    sfreq: float,
    bad_mask: np.ndarray,
    band: BandDefinition,
    rms_window_seconds: float = 0.003,
    threshold_sd: float = 5.0,
    merge_gap_seconds: float = 0.010,
) -> list[dict[str, Any]]:
    sos = butter(
        4,
        [band.fmin, band.fmax],
        btype="bandpass",
        output="sos",
        fs=sfreq,
    )
    filtered = sosfiltfilt(sos, signal)
    rms_window_samples = max(1, int(round(rms_window_seconds * sfreq)))
    envelope = _moving_rms(filtered, rms_window_samples)
    clean_values = envelope[~bad_mask]
    if clean_values.size == 0:
        return []
    threshold = float(clean_values.mean() + threshold_sd * clean_values.std(ddof=0))
    active = (envelope > threshold) & (~bad_mask)
    segments = _detect_segments(active)

    merge_gap_samples = int(round(merge_gap_seconds * sfreq))
    merged: list[tuple[int, int]] = []
    for start, end in segments:
        if not merged:
            merged.append((start, end))
            continue
        last_start, last_end = merged[-1]
        if start - last_end <= merge_gap_samples:
            merged[-1] = (last_start, end)
        else:
            merged.append((start, end))

    min_duration_seconds = 6.0 / band.fmin
    min_duration_samples = int(round(min_duration_seconds * sfreq))
    events: list[dict[str, Any]] = []
    for start, end in merged:
        if (end - start) < min_duration_samples:
            continue
        segment = filtered[start:end]
        events.append(
            {
                "start_sample": start,
                "end_sample": end,
                "start_s": start / sfreq,
                "end_s": end / sfreq,
                "duration_s": (end - start) / sfreq,
                "peak_amplitude": float(np.max(np.abs(segment))) if segment.size else 0.0,
                "threshold": threshold,
            }
        )
    return events


def mark_common_mode_artifacts(
    events: pd.DataFrame,
    total_intervals: int,
    overlap_ratio: float = 0.5,
) -> pd.DataFrame:
    if events.empty or total_intervals <= 0:
        events["artifact_common_mode"] = False
        return events

    threshold = max(1, int(np.floor(total_intervals * overlap_ratio)) + 1)
    artifact_flags: list[bool] = []
    for row in events.itertuples(index=False):
        overlap = events[
            (events["hfo_type"] == row.hfo_type)
            & (events["start_s"] < row.end_s)
            & (events["end_s"] > row.start_s)
        ]["interval_id"].nunique()
        artifact_flags.append(overlap >= threshold)
    result = events.copy()
    result["artifact_common_mode"] = artifact_flags
    return result


def run_hfo_detection(
    recording: BipolarRecording,
    usable_interval_ids: Sequence[str],
    hfo_bands: Sequence[BandDefinition] = HFO_BANDS,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    if not usable_interval_ids:
        return pd.DataFrame(), pd.DataFrame()

    interval_lookup = {
        row.interval_id: idx
        for idx, row in enumerate(recording.interval_table.itertuples(index=False))
    }
    bad_mask = build_bad_sample_mask(
        n_times=recording.n_times,
        sfreq=recording.sfreq,
        bad_segments=recording.bad_segments,
    )
    event_rows: list[dict[str, Any]] = []
    clean_minutes = clean_duration_seconds(
        n_times=recording.n_times,
        sfreq=recording.sfreq,
        bad_segments=recording.bad_segments,
    ) / 60.0
    for interval_id in usable_interval_ids:
        interval_index = interval_lookup[interval_id]
        signal = recording.data[interval_index, :]
        for band in hfo_bands:
            detections = detect_hfo_events_for_signal(
                signal=signal,
                sfreq=recording.sfreq,
                bad_mask=bad_mask,
                band=band,
            )
            for detection in detections:
                event_rows.append(
                    {
                        "subject": recording.entry.subject,
                        "session": recording.entry.session,
                        "run": recording.entry.run,
                        "interval_id": interval_id,
                        "hfo_type": band.name,
                        **detection,
                    }
                )

    events = pd.DataFrame(event_rows)
    if events.empty:
        return events, pd.DataFrame()

    events = mark_common_mode_artifacts(events, total_intervals=len(usable_interval_ids))
    summary_rows: list[dict[str, Any]] = []
    for (interval_id, hfo_type), subset in events.groupby(["interval_id", "hfo_type"], dropna=False):
        artifact_free = subset.loc[~subset["artifact_common_mode"]]
        summary_rows.append(
            {
                "subject": recording.entry.subject,
                "session": recording.entry.session,
                "run": recording.entry.run,
                "interval_id": interval_id,
                "hfo_type": hfo_type,
                "event_count": int(len(subset)),
                "artifact_free_event_count": int(len(artifact_free)),
                "rate_per_min": float(len(artifact_free) / clean_minutes) if clean_minutes > 0 else 0.0,
                "rate_per_min_all": float(len(subset) / clean_minutes) if clean_minutes > 0 else 0.0,
                "clean_minutes": clean_minutes,
            }
        )
    return events, pd.DataFrame(summary_rows)
