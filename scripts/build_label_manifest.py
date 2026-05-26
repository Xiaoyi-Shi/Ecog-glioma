from __future__ import annotations

import argparse
from pathlib import Path

from ecog_glioma.config import DEFAULT_BIDS_ROOT, DEFAULT_METADATA_XLSX, DEFAULT_RESULTS_ROOT
from ecog_glioma.pipeline import build_manifest_and_qc, create_or_load_context


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Build the interval label manifest and bipolar QC tables for the "
            "before-session ECoG analysis pipeline."
        )
    )
    parser.add_argument("--metadata-xlsx", type=Path, default=DEFAULT_METADATA_XLSX)
    parser.add_argument("--bids-root", type=Path, default=DEFAULT_BIDS_ROOT)
    parser.add_argument("--results-root", type=Path, default=DEFAULT_RESULTS_ROOT)
    parser.add_argument(
        "--run-dir",
        type=Path,
        help="Reuse an existing results/<timestamp> directory instead of creating a new one.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    context = create_or_load_context(run_dir=args.run_dir, results_root=args.results_root)
    manifest, interval_qc, patient_qc = build_manifest_and_qc(
        context,
        metadata_xlsx=args.metadata_xlsx,
        bids_root=args.bids_root,
    )
    print(f"Run directory: {context.run_root}")
    print(f"Manifest rows: {len(manifest)}")
    print(f"Interval QC rows: {len(interval_qc)}")
    print(f"Patient QC rows: {len(patient_qc)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
