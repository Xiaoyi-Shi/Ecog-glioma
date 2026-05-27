from __future__ import annotations

import numpy as np

from ecog_glioma.static_network import (
    compute_lagged_source_sink_index,
    compute_multiplex_participation,
)


def test_lagged_source_sink_detects_directed_delay() -> None:
    rng = np.random.default_rng(42)
    source = rng.normal(size=500)
    receiver = np.concatenate([np.zeros(4), source[:-4]]) + 0.02 * rng.normal(size=500)
    data = np.vstack([source, receiver])

    source_sink, directed = compute_lagged_source_sink_index(
        data,
        sfreq=1000.0,
        max_lag_ms=10.0,
    )

    assert directed.shape == (2, 2)
    assert source_sink[0] > 0
    assert source_sink[1] < 0
    assert directed[0, 1] > directed[1, 0]


def test_multiplex_participation_handles_zero_strength_nodes() -> None:
    strength_by_band = np.array(
        [
            [1.0, 1.0, 1.0],
            [0.0, 0.0, 0.0],
            [3.0, 0.0, 0.0],
        ]
    )

    mpc = compute_multiplex_participation(strength_by_band)

    assert np.isclose(mpc[0], 1.0)
    assert mpc[1] == 0.0
    assert mpc[2] == 0.0
