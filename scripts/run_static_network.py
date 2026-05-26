from __future__ import annotations

import argparse
from pathlib import Path

from ecog_glioma.config import DEFAULT_BIDS_ROOT, DEFAULT_RESULTS_ROOT
from ecog_glioma.pipeline import create_or_load_context, run_static_network_stage


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run static dwPLI and multilayer feature extraction.")
    parser.add_argument("--bids-root", type=Path, default=DEFAULT_BIDS_ROOT)
    parser.add_argument("--results-root", type=Path, default=DEFAULT_RESULTS_ROOT)
    parser.add_argument("--run-dir", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    context = create_or_load_context(run_dir=args.run_dir, results_root=args.results_root)
    node_features, multilayer_nodes, multilayer_patient = run_static_network_stage(
        context,
        bids_root=args.bids_root,
    )
    print(f"Run directory: {context.run_root}")
    print(f"Static node rows: {len(node_features)}")
    print(f"Multilayer node rows: {len(multilayer_nodes)}")
    print(f"Multilayer patient rows: {len(multilayer_patient)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
