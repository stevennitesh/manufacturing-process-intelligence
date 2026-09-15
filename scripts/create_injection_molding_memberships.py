"""Create the M3 Dataset 2 evaluation-membership artifact."""

from __future__ import annotations

import argparse
from pathlib import Path

from mpi.datasets.injection_molding_persistence import DEFAULT_OUTPUT, load_bundle
from mpi.datasets.injection_molding_protocol import DEFAULT_MEMBERSHIP_OUTPUT, write_memberships


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_MEMBERSHIP_OUTPUT)
    args = parser.parse_args()

    memberships = write_memberships(load_bundle(args.bundle), args.output)
    print(f"output: {args.output.resolve()}")
    print(f"rows: {memberships.height}")
    print("protocols: primary (3 folds), secondary_id (1 fold)")
    print("seed: 42")


if __name__ == "__main__":
    main()
