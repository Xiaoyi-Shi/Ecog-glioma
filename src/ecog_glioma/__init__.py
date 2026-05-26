from __future__ import annotations

from pathlib import Path

from ._mne_env import MNE_HOME as MNE_HOME  # noqa: F401


def main() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    print(f"ecog-glioma workspace: {repo_root}")
