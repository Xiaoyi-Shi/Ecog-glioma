from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from .bids_io import RecordingEntry, extract_contact_number


@dataclass
class BipolarRecording:
    entry: RecordingEntry
    data: np.ndarray
    interval_table: pd.DataFrame
    sfreq: float
    n_times: int
    duration_seconds: float
    bad_segments: list[tuple[float, float]]


def extract_bad_segments_from_annotations(raw) -> list[tuple[float, float]]:
    segments: list[tuple[float, float]] = []
    for annotation in raw.annotations:
        description = str(annotation["description"]).lower()
        if "bad" not in description:
            continue
        onset = float(annotation["onset"])
        duration = float(annotation["duration"])
        segments.append((onset, onset + duration))
    return segments


def derive_adjacent_bipolar(
    raw,
    channels: pd.DataFrame,
    entry: RecordingEntry,
) -> BipolarRecording:
    channel_lookup: dict[int, dict[str, object]] = {}
    for index, row in channels.iterrows():
        contact = extract_contact_number(str(row["name"]))
        if contact is None:
            continue
        channel_lookup[contact] = {
            "name": str(row["name"]),
            "index": int(index),
            "status": str(row.get("status", "good")).strip().lower(),
        }

    if not channel_lookup:
        raise ValueError(f"No numbered channels found for {entry.recording_path}")

    contact_numbers = sorted(channel_lookup)
    start_contact = min(contact_numbers)
    end_contact = max(contact_numbers)

    interval_rows: list[dict[str, object]] = []
    data_rows: list[np.ndarray] = []
    raw_data = raw.get_data()
    for contact_a in range(start_contact, end_contact):
        contact_b = contact_a + 1
        left = channel_lookup.get(contact_a)
        right = channel_lookup.get(contact_b)
        if left is None or right is None:
            continue
        endpoint_a_bad = left["status"] == "bad"
        endpoint_b_bad = right["status"] == "bad"
        interval_id = f"{contact_a}_{contact_b}"
        interval_rows.append(
            {
                "subject": entry.subject,
                "session": entry.session,
                "task": entry.task,
                "run": entry.run,
                "recording_path": str(entry.recording_path),
                "interval_id": interval_id,
                "interval_index": contact_a,
                "contact_a": contact_a,
                "contact_b": contact_b,
                "channel_a": left["name"],
                "channel_b": right["name"],
                "endpoint_a_bad": bool(endpoint_a_bad),
                "endpoint_b_bad": bool(endpoint_b_bad),
                "endpoint_bad": bool(endpoint_a_bad or endpoint_b_bad),
            }
        )
        data_rows.append(
            raw_data[int(left["index"]), :] - raw_data[int(right["index"]), :]
        )

    interval_table = pd.DataFrame(interval_rows).sort_values(
        "interval_index",
        kind="stable",
    )
    interval_table["share_endpoint_prev"] = interval_table["contact_a"] > start_contact
    interval_table["share_endpoint_next"] = interval_table["contact_b"] < end_contact

    if data_rows:
        data = np.vstack(data_rows)
    else:
        data = np.empty((0, raw.n_times), dtype=float)

    sfreq = float(raw.info["sfreq"])
    duration_seconds = float(raw.n_times / sfreq)
    return BipolarRecording(
        entry=entry,
        data=data,
        interval_table=interval_table.reset_index(drop=True),
        sfreq=sfreq,
        n_times=int(raw.n_times),
        duration_seconds=duration_seconds,
        bad_segments=extract_bad_segments_from_annotations(raw),
    )


def build_bad_sample_mask(
    n_times: int,
    sfreq: float,
    bad_segments: list[tuple[float, float]],
) -> np.ndarray:
    mask = np.zeros(n_times, dtype=bool)
    for start_s, end_s in bad_segments:
        start = max(0, int(np.floor(start_s * sfreq)))
        end = min(n_times, int(np.ceil(end_s * sfreq)))
        mask[start:end] = True
    return mask


def clean_duration_seconds(
    n_times: int,
    sfreq: float,
    bad_segments: list[tuple[float, float]],
) -> float:
    bad_mask = build_bad_sample_mask(n_times, sfreq, bad_segments)
    clean_samples = int((~bad_mask).sum())
    return clean_samples / sfreq


def extract_sliding_windows(
    data: np.ndarray,
    sfreq: float,
    bad_segments: list[tuple[float, float]],
    window_seconds: float,
    step_seconds: float,
) -> tuple[np.ndarray, np.ndarray, pd.DataFrame]:
    if data.size == 0:
        return (
            np.empty((0, 0, 0), dtype=float),
            np.empty((0,), dtype=float),
            pd.DataFrame(columns=["start_s", "end_s", "is_clean"]),
        )

    n_times = data.shape[1]
    window_samples = int(round(window_seconds * sfreq))
    step_samples = int(round(step_seconds * sfreq))
    bad_mask = build_bad_sample_mask(n_times, sfreq, bad_segments)

    windows: list[np.ndarray] = []
    starts: list[float] = []
    inventory_rows: list[dict[str, object]] = []
    for start in range(0, n_times - window_samples + 1, step_samples):
        end = start + window_samples
        is_clean = not bool(bad_mask[start:end].any())
        start_s = start / sfreq
        end_s = end / sfreq
        inventory_rows.append(
            {"start_s": start_s, "end_s": end_s, "is_clean": is_clean}
        )
        if not is_clean:
            continue
        windows.append(data[:, start:end])
        starts.append(start_s)

    if windows:
        window_array = np.stack(windows, axis=0)
        start_array = np.asarray(starts, dtype=float)
    else:
        window_array = np.empty((0, data.shape[0], window_samples), dtype=float)
        start_array = np.empty((0,), dtype=float)

    return window_array, start_array, pd.DataFrame(inventory_rows)
