from __future__ import annotations

import numpy as np

from ecog_glioma.bipolar import clean_duration_seconds, extract_sliding_windows
from ecog_glioma.labels import parse_interval_label


def test_parse_interval_label_region_boundaries() -> None:
    assert parse_interval_label("a1")["region"] == 1

    boundary = parse_interval_label("b2[0]")
    assert boundary["label_valid"] is True
    assert boundary["region"] == 2
    assert boundary["distance_mm"] == 0.0
    assert boundary["is_boundary_interface"] == 1

    assert parse_interval_label("b2[1]")["region"] == 2
    assert parse_interval_label("b2[1.49]")["region"] == 2
    assert parse_interval_label("b2[1.5]")["region"] == 3
    assert parse_interval_label("b2[3]")["region"] == 3
    assert parse_interval_label("b2[4]")["region"] == 3
    assert parse_interval_label("b2")["parse_status"] == "missing_distance"
    assert parse_interval_label("用不了")["parse_status"] == "marked_unusable"


def test_extract_sliding_windows_excludes_bad_annotations() -> None:
    data = np.arange(20, dtype=float).reshape(1, 20)
    windows, starts, inventory = extract_sliding_windows(
        data=data,
        sfreq=10.0,
        bad_segments=[(0.4, 0.9)],
        window_seconds=0.5,
        step_seconds=0.5,
    )

    assert inventory["is_clean"].tolist() == [False, False, True, True]
    assert starts.tolist() == [1.0, 1.5]
    assert windows.shape == (2, 1, 5)
    assert clean_duration_seconds(20, 10.0, [(0.4, 0.9)]) == 1.5
