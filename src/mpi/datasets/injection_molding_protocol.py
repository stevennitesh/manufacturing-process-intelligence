"""Dataset 2 predictor allowlists and reproducible evaluation memberships."""

from __future__ import annotations

import math
import os
from pathlib import Path
from typing import Final, Literal

import numpy as np
import polars as pl

from mpi.data.canonical import ManufacturingBundle

DEFAULT_MEMBERSHIP_OUTPUT: Final = Path("artifacts/m03/injection_molding_memberships.parquet")
SPLIT_SEED: Final = 42
ID_INNER_FOLDS: Final = 3
EXPECTED_EXPERIMENTS: Final = (15, 20, 23)

# Only completed-cycle machine measurements are admitted. This deliberately does
# not derive eligibility from whichever columns happen to be retained in the bundle.
SCALAR_PREDICTOR_COLUMNS: Final = (
    "cycle_duration",
    "maximum_injection_pressure",
    "switchover_injection_pressure",
    "actual_back_pressure",
    "injection_time",
    "melt_cushion",
    "dosing_time",
    "barrel_heating_zone_1",
    "barrel_heating_zone_2",
    "barrel_heating_zone_3",
    "barrel_heating_zone_4",
    "barrel_heating_zone_5",
    "barrel_heating_zone_6",
    "barrel_heating_zone_7",
    "barrel_heating_zone_8",
    "mold_heating_circuit_1",
)
TRAJECTORY_INPUT_COLUMNS: Final = (
    "unit_id",
    "operation_id",
    "sample_index",
    "elapsed_time_seconds",
    "injection_pressure",
    "injection_flow",
)

Protocol = Literal["primary", "secondary_id"]
Role = Literal["fit_tune", "calibration", "test"]


def select_scalar_predictors(process_features: pl.DataFrame) -> pl.DataFrame:
    """Select the explicit scalar predictor allowlist, never columns by exclusion."""
    return process_features.select(SCALAR_PREDICTOR_COLUMNS)


def select_trajectory_inputs(signals: pl.DataFrame) -> pl.DataFrame:
    """Select the two released trajectories with native identity and time fields."""
    return signals.select(TRAJECTORY_INPUT_COLUMNS)


def _eligible_units(units: pl.DataFrame, context: pl.DataFrame) -> pl.DataFrame:
    eligible = units.select("unit_id", "cycle_counter").join(
        context.select("unit_id", "experiment_id"), on="unit_id", how="inner", validate="1:1"
    )
    if eligible.height != units.height or eligible.height != context.height:
        raise ValueError("every unit must have exactly one experiment assignment")
    experiments = tuple(sorted(eligible["experiment_id"].unique().to_list()))
    if experiments != EXPECTED_EXPERIMENTS:
        raise ValueError(
            f"expected Dataset 2 experiments {EXPECTED_EXPERIMENTS}, observed {experiments}"
        )
    return eligible.sort("cycle_counter")


def _permuted_unit_ids(
    eligible: pl.DataFrame, experiment_id: int, protocol: Protocol, seed: int
) -> list[str]:
    subset = eligible.filter(pl.col("experiment_id") == experiment_id).sort("cycle_counter")
    unit_ids = subset["unit_id"].to_list()
    protocol_code = 1 if protocol == "primary" else 2
    generator = np.random.Generator(
        np.random.PCG64(np.random.SeedSequence([seed, protocol_code, experiment_id]))
    )
    return [unit_ids[int(index)] for index in generator.permutation(len(unit_ids))]


def _assigned_roles(unit_ids: list[str], protocol: Protocol) -> dict[str, tuple[Role, int | None]]:
    allocation = math.ceil(0.20 * len(unit_ids))
    if protocol == "primary":
        calibration = unit_ids[:allocation]
        fit_tune = unit_ids[allocation:]
        test: list[str] = []
    else:
        test = unit_ids[:allocation]
        calibration = unit_ids[allocation : 2 * allocation]
        fit_tune = unit_ids[2 * allocation :]
    assigned: dict[str, tuple[Role, int | None]] = {unit_id: ("test", None) for unit_id in test}
    assigned.update({unit_id: ("calibration", None) for unit_id in calibration})
    assigned.update(
        {
            unit_id: ("fit_tune", index % ID_INNER_FOLDS if protocol == "secondary_id" else None)
            for index, unit_id in enumerate(fit_tune)
        }
    )
    return assigned


def build_memberships(
    units: pl.DataFrame,
    context: pl.DataFrame,
    *,
    source_version: str,
    source_archive_sha256: str,
    seed: int = SPLIT_SEED,
) -> pl.DataFrame:
    """Build primary experiment holdouts and the separate within-experiment benchmark."""
    eligible = _eligible_units(units, context)
    identities = list(eligible.iter_rows(named=True))
    primary_assignments = {
        experiment: _assigned_roles(
            _permuted_unit_ids(eligible, experiment, "primary", seed), "primary"
        )
        for experiment in EXPECTED_EXPERIMENTS
    }
    secondary_assignments = {
        experiment: _assigned_roles(
            _permuted_unit_ids(eligible, experiment, "secondary_id", seed), "secondary_id"
        )
        for experiment in EXPECTED_EXPERIMENTS
    }
    lineage = {
        "seed": seed,
        "allocation_method": "numpy-pcg64-seedsequence",
        "source_version": source_version,
        "source_archive_sha256": source_archive_sha256,
    }
    rows: list[dict[str, str | int | None]] = []
    for held_out in EXPECTED_EXPERIMENTS:
        fold = f"holdout_experiment_{held_out}"
        for identity in identities:
            unit_id = identity["unit_id"]
            experiment_id = identity["experiment_id"]
            role, inner_fold = primary_assignments[experiment_id][unit_id]
            if experiment_id == held_out:
                role, inner_fold = "test", None
            elif role == "fit_tune":
                # The two development experiments are the two inner validation groups.
                inner_fold = experiment_id
            rows.append(
                {
                    "protocol": "primary",
                    "fold": fold,
                    **identity,
                    "role": role,
                    "inner_fold": inner_fold,
                    **lineage,
                }
            )
    for identity in identities:
        unit_id = identity["unit_id"]
        experiment_id = identity["experiment_id"]
        role, inner_fold = secondary_assignments[experiment_id][unit_id]
        rows.append(
            {
                "protocol": "secondary_id",
                "fold": "within_experiment",
                **identity,
                "role": role,
                "inner_fold": inner_fold,
                **lineage,
            }
        )
    return pl.DataFrame(rows, schema_overrides={"inner_fold": pl.Int64}).sort(
        "protocol", "fold", "experiment_id", "cycle_counter"
    )


def write_memberships(bundle: ManufacturingBundle, output: Path) -> pl.DataFrame:
    """Validate predictor inputs and atomically write the generated membership table."""
    select_scalar_predictors(bundle.process_features)
    select_trajectory_inputs(bundle.signals)
    memberships = build_memberships(
        bundle.units,
        bundle.context,
        source_version=bundle.metadata.source_version,
        source_archive_sha256=bundle.metadata.archive_sha256,
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(f"{output.suffix}.tmp")
    try:
        memberships.write_parquet(temporary)
        os.replace(temporary, output)
    except (OSError, pl.exceptions.PolarsError):
        temporary.unlink(missing_ok=True)
        raise
    return memberships
