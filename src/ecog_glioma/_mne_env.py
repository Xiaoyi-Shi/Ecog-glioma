from __future__ import annotations

import os
from pathlib import Path


def configure_mne_home() -> Path:
    repo_root = Path(__file__).resolve().parents[2]
    fake_home_root = repo_root / ".mne_local"
    mne_home = fake_home_root / ".mne"
    mne_home.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("_MNE_FAKE_HOME_DIR", str(fake_home_root))
    os.environ.setdefault("MNE_HOME", str(mne_home))
    return mne_home


MNE_HOME = configure_mne_home()
