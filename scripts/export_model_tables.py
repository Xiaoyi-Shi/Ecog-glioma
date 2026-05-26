from __future__ import annotations

import argparse
from pathlib import Path

from ecog_glioma.config import DEFAULT_RESULTS_ROOT
from ecog_glioma.pipeline import create_or_load_context, export_model_tables_stage


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Export model-ready long tables from pipeline stage outputs.")
    parser.add_argument("--results-root", type=Path, default=DEFAULT_RESULTS_ROOT)
    parser.add_argument("--run-dir", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    context = create_or_load_context(run_dir=args.run_dir, results_root=args.results_root)
    outputs = export_model_tables_stage(context)
    print(f"Run directory: {context.run_root}")
    for name, path in outputs.items():
        print(f"{name}: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
