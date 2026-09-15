from __future__ import annotations

import math

import polars as pl

from mpi.datasets.injection_molding_protocol import (
    EXPECTED_EXPERIMENTS,
    ID_INNER_FOLDS,
    SCALAR_PREDICTOR_COLUMNS,
    TRAJECTORY_INPUT_COLUMNS,
    build_memberships,
    select_scalar_predictors,
    select_trajectory_inputs,
)


def _synthetic_identity() -> tuple[pl.DataFrame, pl.DataFrame]:
    records = [
        (f"cycle-{experiment}-{offset}", experiment * 100 + offset, experiment)
        for experiment, count in zip(EXPECTED_EXPERIMENTS, (11, 8, 14), strict=True)
        for offset in range(count)
    ]
    units = pl.DataFrame(
        records, schema=["unit_id", "cycle_counter", "experiment_id"], orient="row"
    )
    context = units.select("unit_id", "experiment_id")
    return units.drop("experiment_id"), context


def _memberships(units: pl.DataFrame, context: pl.DataFrame) -> pl.DataFrame:
    return build_memberships(
        units,
        context,
        source_version="source-version",
        source_archive_sha256="a" * 64,
    )


def test_primary_folds_are_disjoint_complete_experiment_holdouts() -> None:
    units, context = _synthetic_identity()
    memberships = _memberships(units, context)
    primary = memberships.filter(pl.col("protocol") == "primary")

    assert primary["fold"].n_unique() == len(EXPECTED_EXPERIMENTS)
    assert primary.height == units.height * len(EXPECTED_EXPERIMENTS)
    for held_out in EXPECTED_EXPERIMENTS:
        fold = primary.filter(pl.col("fold") == f"holdout_experiment_{held_out}")
        assert fold.height == units.height
        assert fold["unit_id"].n_unique() == units.height
        assert set(fold.filter(pl.col("role") == "test")["experiment_id"]) == {held_out}
        fit_tune = fold.filter(pl.col("role") == "fit_tune")
        development_experiments = set(EXPECTED_EXPERIMENTS) - {held_out}
        assert set(fit_tune["inner_fold"]) == development_experiments
        for inner_fold in development_experiments:
            validation = fit_tune.filter(pl.col("inner_fold") == inner_fold)
            training = fit_tune.filter(pl.col("inner_fold") != inner_fold)
            assert set(validation["experiment_id"]) == {inner_fold}
            assert set(training["experiment_id"]) == development_experiments - {inner_fold}
            assert set(training["unit_id"]).isdisjoint(validation["unit_id"])
        for experiment in set(EXPECTED_EXPERIMENTS) - {held_out}:
            group = fold.filter(pl.col("experiment_id") == experiment)
            calibration = group.filter(pl.col("role") == "calibration")
            assert calibration.height == math.ceil(group.height * 0.20)

    test_membership = primary.filter(pl.col("role") == "test").group_by("unit_id").len()
    assert test_membership["len"].to_list() == [1] * units.height

    experiment_15_development = [
        primary.filter(
            (pl.col("fold") == fold) & (pl.col("experiment_id") == 15) & (pl.col("role") != "test")
        )
        .select("unit_id", "role", "inner_fold")
        .sort("unit_id")
        for fold in ("holdout_experiment_20", "holdout_experiment_23")
    ]
    assert experiment_15_development[0].equals(experiment_15_development[1])

    primary_fit_tune = primary.filter(pl.col("role") == "fit_tune")
    primary_excluded = primary.filter(pl.col("role") != "fit_tune")
    assert primary_fit_tune["inner_fold"].null_count() == 0
    assert primary_excluded["inner_fold"].null_count() == primary_excluded.height


def test_secondary_split_and_inner_folds_cover_only_fit_tune() -> None:
    units, context = _synthetic_identity()
    secondary = _memberships(units, context).filter(pl.col("protocol") == "secondary_id")

    assert secondary.height == units.height
    assert secondary["unit_id"].n_unique() == units.height
    for experiment in EXPECTED_EXPERIMENTS:
        group = secondary.filter(pl.col("experiment_id") == experiment)
        expected_holdout = math.ceil(group.height * 0.20)
        assert group.filter(pl.col("role") == "test").height == expected_holdout
        assert group.filter(pl.col("role") == "calibration").height == expected_holdout

    fit_tune = secondary.filter(pl.col("role") == "fit_tune")
    excluded = secondary.filter(pl.col("role") != "fit_tune")
    assert fit_tune["inner_fold"].null_count() == 0
    assert set(fit_tune["inner_fold"]) == set(range(ID_INNER_FOLDS))
    assert excluded["inner_fold"].null_count() == excluded.height
    for experiment in EXPECTED_EXPERIMENTS:
        counts = (
            fit_tune.filter(pl.col("experiment_id") == experiment)
            .group_by("inner_fold")
            .len()["len"]
            .to_list()
        )
        assert max(counts) - min(counts) <= 1


def test_memberships_do_not_depend_on_input_row_order_or_values() -> None:
    units, context = _synthetic_identity()
    expected = _memberships(units, context)
    reordered_units = units.reverse().with_columns(pl.lit(-999.0).alias("unused_value"))
    reordered_context = context.reverse().with_columns(pl.lit(123.0).alias("another_value"))

    assert _memberships(reordered_units, reordered_context).equals(expected)


def test_scalar_selection_is_allowlisted() -> None:
    values: dict[str, list[str] | list[float]] = {
        "unit_id": ["unit-1"],
        "operation_id": ["operation-1"],
        **{column: [float(index)] for index, column in enumerate(SCALAR_PREDICTOR_COLUMNS)},
        "future_retained_process_field": [999.0],
    }
    process_features = pl.DataFrame(values)

    selected = select_scalar_predictors(process_features)

    assert "future_retained_process_field" not in selected.columns
    assert selected.columns == list(SCALAR_PREDICTOR_COLUMNS)
    assert selected.width == 16
    assert "unit_id" not in selected.columns
    assert "operation_id" not in selected.columns


def test_trajectory_selection_keeps_native_coordinates_and_drops_extra_fields() -> None:
    signals = pl.DataFrame(
        {
            **{
                column: ["identity"] if column in {"unit_id", "operation_id"} else [1.0]
                for column in TRAJECTORY_INPUT_COLUMNS
            },
            "measured_weight": [999.0],
        }
    )

    selected = select_trajectory_inputs(signals)

    assert selected.columns == list(TRAJECTORY_INPUT_COLUMNS)
    assert "measured_weight" not in selected.columns
