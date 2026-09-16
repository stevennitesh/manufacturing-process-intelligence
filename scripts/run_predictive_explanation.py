"""Run M9 permutation importance and marginal feature-support diagnostics."""

from __future__ import annotations

import argparse
import json
from hashlib import sha256
from pathlib import Path
from typing import cast

import polars as pl

from mpi.datasets.injection_molding_persistence import DEFAULT_OUTPUT, load_bundle
from mpi.datasets.injection_molding_protocol import DEFAULT_MEMBERSHIP_OUTPUT
from mpi.models.predictive_explanation import (
    DEFAULT_EXPLANATION_OUTPUT,
    DEFAULT_M7_PREDICTIONS,
    DEFAULT_M7_RUN,
    run_predictive_explanation,
    write_predictive_explanation,
)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--memberships", type=Path, default=DEFAULT_MEMBERSHIP_OUTPUT)
    parser.add_argument("--m7-run", type=Path, default=DEFAULT_M7_RUN)
    parser.add_argument("--m7-predictions", type=Path, default=DEFAULT_M7_PREDICTIONS)
    parser.add_argument("--output", type=Path, default=DEFAULT_EXPLANATION_OUTPUT)
    args = parser.parse_args()

    bundle = load_bundle(args.bundle)
    memberships = pl.read_parquet(args.memberships)
    run_record = cast(dict[str, object], json.loads(args.m7_run.read_text(encoding="utf-8")))
    reference = pl.read_parquet(args.m7_predictions)
    results = run_predictive_explanation(
        bundle,
        memberships,
        run_record,
        reference,
        membership_sha256=sha256(args.memberships.read_bytes()).hexdigest(),
    )
    write_predictive_explanation(
        results, bundle, args.memberships, args.m7_run, args.m7_predictions, args.output
    )
    print(f"output: {args.output.resolve()}")
    print(
        f"populations: {len(results.populations)}; rows/table: "
        f"{results.permutation_importance.height}; maximum M7 prediction difference: "
        f"{results.maximum_prediction_difference_g:.3g} g"
    )


if __name__ == "__main__":
    main()
