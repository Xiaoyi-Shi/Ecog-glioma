from __future__ import annotations

import argparse
from pathlib import Path

from ecog_glioma.config import DEFAULT_BIDS_ROOT, DEFAULT_METADATA_XLSX, DEFAULT_RESULTS_ROOT
from ecog_glioma.pipeline import run_pipeline, run_python_pipeline


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run the Python feature-extraction stages of the boundary-gradient "
            "ECoG analysis pipeline described in "
            "docs/科研路径提纲版本2.md."
        )
    )
    parser.add_argument("--bids-root", type=Path, default=DEFAULT_BIDS_ROOT)
    parser.add_argument("--metadata-xlsx", type=Path, default=DEFAULT_METADATA_XLSX)
    parser.add_argument("--results-root", type=Path, default=DEFAULT_RESULTS_ROOT)
    parser.add_argument("--run-dir", type=Path)
    parser.add_argument(
        "--with-r",
        action="store_true",
        help="Also run R statistics and figures after Python stages complete.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.with_r:
        context = run_pipeline(
            bids_root=args.bids_root,
            metadata_xlsx=args.metadata_xlsx,
            results_root=args.results_root,
            run_dir=args.run_dir,
            skip_r=False,
        )
        print(f"Python + R pipeline complete: {context.run_root}")
        return 0
    context = run_python_pipeline(
        bids_root=args.bids_root,
        metadata_xlsx=args.metadata_xlsx,
        results_root=args.results_root,
        run_dir=args.run_dir,
    )
    print(f"Python pipeline complete: {context.run_root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
