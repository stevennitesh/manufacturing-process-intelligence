# pyright: reportMissingTypeStubs=false, reportUnknownMemberType=false, reportUnknownArgumentType=false, reportUnknownVariableType=false, reportPrivateUsage=false
"""Focused numerical and leakage checks for M5 trajectory representations."""

from __future__ import annotations

from dataclasses import replace

import numpy as np
import polars as pl
from sklearn.cross_decomposition import PLSRegression
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler

from mpi.data.canonical import ManufacturingBundle
from mpi.models.scalar_baselines import run_scalar_baselines
from mpi.models.trajectory_representations import (
    TrajectoryData,
    assemble_trajectory_data,
    fit_predict_representation,
    select_representation_candidate,
    summarize_trajectory,
)
from tests.unit.test_scalar_baselines import _synthetic_inputs


def _with_signals(bundle: ManufacturingBundle) -> ManufacturingBundle:
    rows: list[dict[str, object]] = []
    operation_by_unit = dict(bundle.process_features.select("unit_id", "operation_id").iter_rows())
    for unit_id, cycle_counter in bundle.units.sort("unit_id").iter_rows():
        time = np.arange(2048, dtype=np.float64) * 0.006
        pressure = cycle_counter * 0.001 + np.sin(time)
        flow = cycle_counter * -0.0002 + np.cos(time * 0.5)
        rows.extend(
            {
                "unit_id": unit_id,
                "operation_id": operation_by_unit[unit_id],
                "sample_index": index,
                "elapsed_time_seconds": elapsed,
                "injection_pressure": pressure[index],
                "injection_flow": flow[index],
            }
            for index, elapsed in enumerate(time)
        )
    return replace(bundle, signals=pl.DataFrame(rows))


def test_summaries_match_independent_irregular_grid_calculation() -> None:
    time = np.array([0.0, 1.0, 3.0, 4.092, 6.0, 8.184, 10.0, 12.276])
    values = np.array([0.0, 2.0, 1.0, 5.0, 4.0, 7.0, 3.0, 8.0])

    actual = summarize_trajectory(time, values)

    slopes = np.diff(values) / np.diff(time)
    expected_segments = []
    for start, end in ((0.0, 4.092), (4.092, 8.184), (8.184, 12.276)):
        included = (time >= start) & (time <= end)
        expected_segments.append(float(np.trapezoid(values[included], time[included])))
    expected = np.array(
        [
            sum(values) / len(values),
            np.sqrt(np.mean((values - np.mean(values)) ** 2)),
            8.0,
            12.276,
            *np.quantile(values, [0.1, 0.5, 0.9], method="linear"),
            np.trapezoid(values, time),
            max(slopes),
            min(slopes),
            *expected_segments,
        ]
    )
    np.testing.assert_allclose(actual, expected)


def test_segment_boundaries_are_linearly_interpolated_when_absent() -> None:
    time = np.array([0.0, 2.0, 5.0, 7.0, 9.0, 12.276])
    values = 2.0 * time + 1.0
    actual = summarize_trajectory(time, values)
    expected = [
        (end**2 + end) - (start**2 + start)
        for start, end in ((0.0, 4.092), (4.092, 8.184), (8.184, 12.276))
    ]
    np.testing.assert_allclose(actual[-3:], expected)


def test_signal_and_scalar_row_order_do_not_change_assembled_arrays() -> None:
    bare_bundle, memberships = _synthetic_inputs()
    bundle = _with_signals(bare_bundle)
    expected, _ = assemble_trajectory_data(bundle, memberships)
    shuffled = replace(
        bundle,
        signals=bundle.signals.sample(fraction=1.0, shuffle=True, seed=4),
        process_features=bundle.process_features.sample(fraction=1.0, shuffle=True, seed=5),
        quality=bundle.quality.sample(fraction=1.0, shuffle=True, seed=6),
    )
    actual, _ = assemble_trajectory_data(
        shuffled, memberships.sample(fraction=1.0, shuffle=True, seed=7)
    )
    assert actual.unit_ids == expected.unit_ids
    np.testing.assert_array_equal(actual.scalars, expected.scalars)
    np.testing.assert_array_equal(actual.summaries, expected.summaries)
    np.testing.assert_array_equal(actual.trajectories, expected.trajectories)
    np.testing.assert_array_equal(actual.targets, expected.targets)


def test_fold_local_scaling_and_compression_match_independent_pls_pipeline() -> None:
    rng = np.random.default_rng(21)
    train_scalars = rng.normal(size=(12, 3))
    train_trajectories = rng.normal(size=(12, 9))
    train_y = rng.normal(size=12)
    evaluation_scalars = rng.normal(loc=50.0, size=(4, 3))
    evaluation_trajectories = rng.normal(loc=100.0, size=(4, 9))
    train = (train_scalars, rng.normal(size=(12, 2)), train_trajectories, train_y)
    evaluation = (
        evaluation_scalars,
        rng.normal(size=(4, 2)),
        evaluation_trajectories,
        np.full(4, 999_999.0),
    )

    actual = fit_predict_representation("C-PLS", 10.0, 2, train, evaluation)

    trajectory_scaler = StandardScaler().fit(train_trajectories)
    scaled_train = np.asarray(trajectory_scaler.transform(train_trajectories), dtype=np.float64)
    pls = PLSRegression(n_components=2, scale=False).fit(scaled_train, train_y)
    combined_train = np.column_stack((train_scalars, pls.transform(scaled_train)))
    combined_evaluation = np.column_stack(
        (evaluation_scalars, pls.transform(trajectory_scaler.transform(evaluation_trajectories)))
    )
    combined_scaler = StandardScaler().fit(combined_train)
    expected = np.asarray(
        Ridge(alpha=10.0)
        .fit(combined_scaler.transform(combined_train), train_y)
        .predict(combined_scaler.transform(combined_evaluation)),
        dtype=np.float64,
    )
    np.testing.assert_allclose(actual, expected)


def test_calibration_and_outer_labels_cannot_change_selection() -> None:
    bare_bundle, memberships = _synthetic_inputs()
    data, rows = assemble_trajectory_data(_with_signals(bare_bundle), memberships)
    fold = rows.filter(
        (pl.col("protocol") == "primary") & (pl.col("fold") == "holdout_experiment_15")
    )
    fit_tune = fold.filter(pl.col("role") == "fit_tune")
    expected = select_representation_candidate("C-PLS", data, fit_tune)[:2]
    protected_ids = set(fold.filter(pl.col("role") != "fit_tune")["unit_id"])
    changed_targets = data.targets.copy()
    changed_scalars = data.scalars.copy()
    changed_summaries = data.summaries.copy()
    changed_trajectories = data.trajectories.copy()
    for index, unit_id in enumerate(data.unit_ids):
        if unit_id in protected_ids:
            changed_targets[index] += 1_000_000.0
        if unit_id in set(fold.filter(pl.col("role") == "calibration")["unit_id"]):
            changed_scalars[index] += 1_000_000.0
            changed_summaries[index] += 1_000_000.0
            changed_trajectories[index] += 1_000_000.0
    changed = replace(
        data,
        targets=changed_targets,
        scalars=changed_scalars,
        summaries=changed_summaries,
        trajectories=changed_trajectories,
    )
    changed_selection = select_representation_candidate("C-PLS", changed, fit_tune)[:2]
    assert changed_selection == expected

    evaluation = fold.filter(pl.col("role") == "test").sort("unit_id")
    fit_tune = fit_tune.sort("unit_id")

    def arrays(
        source: TrajectoryData, selected: pl.DataFrame
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        lookup = {unit_id: index for index, unit_id in enumerate(source.unit_ids)}
        indexes = np.array([lookup[item] for item in selected["unit_id"]])
        return (
            source.scalars[indexes],
            source.summaries[indexes],
            source.trajectories[indexes],
            source.targets[indexes],
        )

    components, alpha = expected
    expected_predictions = fit_predict_representation(
        "C-PLS", alpha, components, arrays(data, fit_tune), arrays(data, evaluation)
    )
    changed_predictions = fit_predict_representation(
        "C-PLS", alpha, components, arrays(changed, fit_tune), arrays(changed, evaluation)
    )
    np.testing.assert_array_equal(changed_predictions, expected_predictions)


def test_representation_a_exactly_reproduces_m4_ridge_predictions() -> None:
    bare_bundle, memberships = _synthetic_inputs()
    bundle = _with_signals(bare_bundle)
    data, rows = assemble_trajectory_data(bundle, memberships)
    m4 = run_scalar_baselines(bundle, memberships).predictions.filter(pl.col("model") == "ridge")
    for protocol, fold in (
        ("primary", "holdout_experiment_15"),
        ("secondary_id", "within_experiment"),
    ):
        fold_rows = rows.filter((pl.col("protocol") == protocol) & (pl.col("fold") == fold))
        fit_tune = fold_rows.filter(pl.col("role") == "fit_tune").sort("unit_id")
        evaluation = fold_rows.filter(pl.col("role") == "test").sort("unit_id")
        _, alpha, _ = select_representation_candidate("A", data, fit_tune)
        index = {unit_id: position for position, unit_id in enumerate(data.unit_ids)}
        train_indexes = np.array([index[item] for item in fit_tune["unit_id"]])
        test_indexes = np.array([index[item] for item in evaluation["unit_id"]])

        def arrays(
            indexes: np.ndarray,
        ) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
            return (
                data.scalars[indexes],
                data.summaries[indexes],
                data.trajectories[indexes],
                data.targets[indexes],
            )

        actual = fit_predict_representation(
            "A", alpha, None, arrays(train_indexes), arrays(test_indexes)
        )
        expected = m4.filter((pl.col("protocol") == protocol) & (pl.col("fold") == fold)).sort(
            "unit_id"
        )
        np.testing.assert_allclose(actual, expected["predicted_weight_g"].to_numpy())
