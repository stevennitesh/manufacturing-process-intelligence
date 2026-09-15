"""Run the M4 Dataset 2 scalar baselines."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import cast

import polars as pl

from mpi.datasets.injection_molding_persistence import DEFAULT_OUTPUT, load_bundle
from mpi.datasets.injection_molding_protocol import DEFAULT_MEMBERSHIP_OUTPUT
from mpi.models.scalar_baselines import (
    DEFAULT_BASELINE_OUTPUT,
    prediction_diagnostics,
    run_scalar_baselines,
    write_scalar_baseline_results,
)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--memberships", type=Path, default=DEFAULT_MEMBERSHIP_OUTPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_BASELINE_OUTPUT)
    parser.add_argument(
        "--report-only",
        action="store_true",
        help="Update diagnostics from saved predictions without fitting",
    )
    args = parser.parse_args()

    if args.report_only:
        destination = args.output / "run.json"
        record = json.loads(destination.read_text(encoding="utf-8"))
        record["posthoc_diagnostics"] = prediction_diagnostics(
            pl.read_parquet(args.output / "predictions.parquet")
        )
        temporary = destination.with_suffix(".json.tmp")
        temporary.write_text(
            json.dumps(record, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
        os.replace(temporary, destination)
        print(f"Updated post-hoc diagnostics: {destination}")
        return

    bundle = load_bundle(args.bundle)
    results = run_scalar_baselines(bundle, pl.read_parquet(args.memberships))
    record = write_scalar_baseline_results(results, bundle, args.memberships, args.output)
    print(f"output: {args.output.resolve()}")
    print(f"model/fold results: {results.metrics.height}")
    for summary in cast(list[dict[str, object]], record["summaries"]):
        model = cast(str, summary["model"])
        equal_fold_mae = cast(float, summary["primary_equal_fold_mean_mae_g"])
        pooled_mae = cast(float, summary["primary_pooled_sample_weighted_mae_g"])
        print(
            f"{model}: equal-fold primary MAE {equal_fold_mae:.6f} g; "
            f"pooled primary MAE {pooled_mae:.6f} g"
        )


if __name__ == "__main__":
    main()
