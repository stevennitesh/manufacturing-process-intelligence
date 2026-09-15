"""Run the fixed M7 scalar uncertainty and experiment-shift evaluation."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import cast

import polars as pl

from mpi.datasets.injection_molding_persistence import DEFAULT_OUTPUT, load_bundle
from mpi.datasets.injection_molding_protocol import DEFAULT_MEMBERSHIP_OUTPUT
from mpi.models.uncertainty_shift import (
    DEFAULT_UNCERTAINTY_OUTPUT,
    run_uncertainty_shift,
    write_uncertainty_results,
)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--memberships", type=Path, default=DEFAULT_MEMBERSHIP_OUTPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_UNCERTAINTY_OUTPUT)
    args = parser.parse_args()

    bundle = load_bundle(args.bundle)
    results = run_uncertainty_shift(bundle, pl.read_parquet(args.memberships))
    record = write_uncertainty_results(results, bundle, args.memberships, args.output)
    print(f"output: {args.output.resolve()}")
    for row in results.metrics.iter_rows(named=True):
        print(
            f"{row['protocol']}/{row['fold']}: n={row['evaluation_count']}; "
            f"coverage={cast(float, row['empirical_coverage']):.3f}; "
            f"width={cast(float, row['mean_width_g']):.6f} g; "
            f"MAE={cast(float, row['mae_g']):.6f} g"
        )
    print(f"M8 eligible from fixed primary development gate: {record['m8_eligible']}")


if __name__ == "__main__":
    main()
