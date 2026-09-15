"""Run the fixed M5 Dataset 2 trajectory representation comparison."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import cast

import polars as pl

from mpi.datasets.injection_molding_persistence import DEFAULT_OUTPUT, load_bundle
from mpi.datasets.injection_molding_protocol import DEFAULT_MEMBERSHIP_OUTPUT
from mpi.models.trajectory_representations import (
    DEFAULT_TRAJECTORY_OUTPUT,
    run_trajectory_representations,
    write_trajectory_results,
)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--memberships", type=Path, default=DEFAULT_MEMBERSHIP_OUTPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_TRAJECTORY_OUTPUT)
    args = parser.parse_args()

    bundle = load_bundle(args.bundle)
    results = run_trajectory_representations(bundle, pl.read_parquet(args.memberships))
    record = write_trajectory_results(results, bundle, args.memberships, args.output)
    print(f"output: {args.output.resolve()}")
    for summary in cast(list[dict[str, object]], record["summaries"]):
        print(
            f"{summary['representation']}: equal-fold primary MAE "
            f"{cast(float, summary['primary_equal_fold_mean_mae_g']):.6f} g; "
            f"delta vs A {cast(float, summary['primary_equal_fold_delta_mae_vs_a_g']):+.6f} g"
        )


if __name__ == "__main__":
    main()
