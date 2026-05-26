from __future__ import annotations

import argparse
from pathlib import Path

from ecog_glioma.config import DEFAULT_RESULTS_ROOT
from ecog_glioma.pipeline import create_or_load_context, run_fragility_stage


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run neural fragility analysis from saved state matrices.")
    parser.add_argument("--results-root", type=Path, default=DEFAULT_RESULTS_ROOT)
    parser.add_argument("--run-dir", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    context = create_or_load_context(run_dir=args.run_dir, results_root=args.results_root)
    windows, summary = run_fragility_stage(context)
    print(f"Run directory: {context.run_root}")
    print(f"Fragility window rows: {len(windows)}")
    print(f"Fragility summary rows: {len(summary)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
