from __future__ import annotations

import argparse
from pathlib import Path

from ecog_glioma.config import DEFAULT_RESULTS_ROOT
from ecog_glioma.pipeline import run_r_pipeline


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run R statistical modeling and figure rendering for an existing "
            "boundary-gradient pipeline result directory."
        )
    )
    parser.add_argument(
        "--run-dir",
        type=Path,
        required=True,
        help="Existing timestamped results directory, for example results\\20260526_161122.",
    )
    parser.add_argument("--results-root", type=Path, default=DEFAULT_RESULTS_ROOT)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    context = run_r_pipeline(
        run_dir=args.run_dir,
        results_root=args.results_root,
    )
    print(f"R reporting complete: {context.run_root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
