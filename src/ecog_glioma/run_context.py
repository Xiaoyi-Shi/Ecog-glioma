from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from .config import DEFAULT_RESULTS_ROOT, STAGE_DIRS
from .paths import as_repo_path
from .utils import append_jsonl, write_json


@dataclass
class RunContext:
    timestamp: str
    run_root: Path
    stage_dirs: dict[str, Path]
    created_at: str

    @classmethod
    def create(
        cls,
        results_root: Path = DEFAULT_RESULTS_ROOT,
        timestamp: str | None = None,
    ) -> "RunContext":
        resolved_results_root = as_repo_path(results_root)
        resolved_results_root.mkdir(parents=True, exist_ok=True)
        if timestamp is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        run_root = resolved_results_root / timestamp
        suffix = 1
        while run_root.exists():
            run_root = resolved_results_root / f"{timestamp}_{suffix:02d}"
            suffix += 1
        stage_dirs = {
            key: run_root / folder_name
            for key, folder_name in STAGE_DIRS.items()
        }
        for path in stage_dirs.values():
            path.mkdir(parents=True, exist_ok=True)
        context = cls(
            timestamp=run_root.name,
            run_root=run_root,
            stage_dirs=stage_dirs,
            created_at=datetime.now().isoformat(timespec="seconds"),
        )
        context.write_run_metadata({"status": "created"})
        return context

    @classmethod
    def from_existing(cls, run_root: Path | str) -> "RunContext":
        resolved_run_root = as_repo_path(run_root)
        stage_dirs = {
            key: resolved_run_root / folder_name
            for key, folder_name in STAGE_DIRS.items()
        }
        for path in stage_dirs.values():
            path.mkdir(parents=True, exist_ok=True)
        metadata_path = stage_dirs["logs"] / "run_metadata.json"
        created_at = datetime.now().isoformat(timespec="seconds")
        if metadata_path.exists():
            import json

            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
            created_at = metadata.get("created_at", created_at)
        return cls(
            timestamp=resolved_run_root.name,
            run_root=resolved_run_root,
            stage_dirs=stage_dirs,
            created_at=created_at,
        )

    def stage_path(self, stage_name: str) -> Path:
        return self.stage_dirs[stage_name]

    def write_stage_metadata(self, stage_name: str, payload: dict[str, Any]) -> None:
        metadata = {
            "stage": stage_name,
            "timestamp": self.timestamp,
            "created_at": datetime.now().isoformat(timespec="seconds"),
            **payload,
        }
        write_json(self.stage_path(stage_name) / "stage_metadata.json", metadata)
        self.append_log(stage_name, "stage_metadata_written", metadata)

    def append_log(
        self,
        stage_name: str,
        message: str,
        extra: dict[str, Any] | None = None,
    ) -> None:
        payload = {
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "stage": stage_name,
            "message": message,
            "extra": extra or {},
        }
        append_jsonl(self.stage_path("logs") / "run_log.jsonl", payload)

    def write_run_metadata(self, extra: dict[str, Any] | None = None) -> None:
        payload = {
            "timestamp": self.timestamp,
            "run_root": str(self.run_root),
            "created_at": self.created_at,
            "stage_dirs": {name: str(path) for name, path in self.stage_dirs.items()},
        }
        if extra:
            payload.update(extra)
        write_json(self.stage_path("logs") / "run_metadata.json", payload)
