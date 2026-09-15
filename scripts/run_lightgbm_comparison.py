"""Run the fixed M6 Dataset 2 LightGBM representation comparison."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import cast

import polars as pl

from mpi.datasets.injection_molding_persistence import DEFAULT_OUTPUT, load_bundle
from mpi.datasets.injection_molding_protocol import DEFAULT_MEMBERSHIP_OUTPUT
from mpi.models.lightgbm_comparison import (
    DEFAULT_LIGHTGBM_OUTPUT,
    run_lightgbm_comparison,
    write_lightgbm_results,
)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--memberships", type=Path, default=DEFAULT_MEMBERSHIP_OUTPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_LIGHTGBM_OUTPUT)
    args = parser.parse_args()

    bundle = load_bundle(args.bundle)
    results = run_lightgbm_comparison(bundle, pl.read_parquet(args.memberships))
    record = write_lightgbm_results(results, bundle, args.memberships, args.output)
    print(f"output: {args.output.resolve()}")
    for summary in cast(list[dict[str, object]], record["summaries"]):
        print(
            f"{summary['representation']}: equal-fold primary MAE "
            f"{cast(float, summary['primary_equal_fold_mean_mae_g']):.6f} g; "
            f"pooled primary MAE "
            f"{cast(float, summary['primary_pooled_sample_weighted_mae_g']):.6f} g; "
            f"delta vs A "
            f"{cast(float, summary['primary_equal_fold_delta_mae_vs_a_g']):+.6f} g"
        )


if __name__ == "__main__":
    main()
