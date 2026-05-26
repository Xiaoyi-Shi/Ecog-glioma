from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from ._mne_env import MNE_HOME  # noqa: F401
from .paths import as_repo_path

import mne


DATA_EXTENSIONS = (".edf", ".vhdr", ".fif", ".set", ".bdf")
DATA_SUFFIXES = ("ieeg", "eeg", "meg", "nirs")
CONTACT_PATTERN = re.compile(r"(\d+)$")


@dataclass(frozen=True)
class RecordingEntry:
    subject: str
    session: str
    task: str
    run: str
    description: str | None
    datatype: str
    recording_path: Path
    channels_path: Path
    events_path: Path | None


def parse_bids_entities(path: Path) -> dict[str, str]:
    entities: dict[str, str] = {}
    for token in path.stem.split("_"):
        if "-" not in token:
            continue
        key, value = token.split("-", maxsplit=1)
        entities[key] = value
    return entities


def resolve_recording_file(channels_tsv: Path) -> tuple[Path, str]:
    stem = channels_tsv.stem.removesuffix("_channels")
    for suffix in DATA_SUFFIXES:
        for extension in DATA_EXTENSIONS:
            candidate = channels_tsv.with_name(f"{stem}_{suffix}{extension}")
            if candidate.exists():
                return candidate, suffix
    raise FileNotFoundError(f"No recording file found next to {channels_tsv}")


def index_bids_recordings(bids_root: Path) -> list[RecordingEntry]:
    resolved_bids_root = as_repo_path(bids_root)
    entries: list[RecordingEntry] = []
    for channels_path in sorted(resolved_bids_root.rglob("*_channels.tsv")):
        recording_path, datatype = resolve_recording_file(channels_path)
        entities = parse_bids_entities(channels_path)
        events_path = channels_path.with_name(
            channels_path.name.replace("_channels.tsv", "_events.tsv")
        )
        entries.append(
            RecordingEntry(
                subject=entities.get("sub", ""),
                session=entities.get("ses", ""),
                task=entities.get("task", ""),
                run=entities.get("run", ""),
                description=entities.get("desc"),
                datatype=datatype,
                recording_path=recording_path,
                channels_path=channels_path,
                events_path=events_path if events_path.exists() else None,
            )
        )
    return entries


def load_channels_table(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, sep="\t")


def load_events_table(path: Path | None) -> pd.DataFrame:
    if path is None or not path.exists():
        return pd.DataFrame(columns=["onset", "duration", "trial_type"])
    return pd.read_csv(path, sep="\t")


def read_raw_recording(path: Path, preload: bool = True) -> mne.io.BaseRaw:
    return mne.io.read_raw(path, preload=preload, verbose="ERROR")


def extract_contact_number(channel_name: str) -> int | None:
    match = CONTACT_PATTERN.search(channel_name.strip())
    if match is None:
        return None
    return int(match.group(1))
