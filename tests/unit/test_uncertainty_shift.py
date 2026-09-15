# pyright: reportMissingTypeStubs=false, reportUnknownMemberType=false, reportUnknownArgumentType=false, reportPrivateUsage=false
"""Focused reference, leakage, and ordinary-path checks for M7."""

from __future__ import annotations

import math
from dataclasses import replace

import numpy as np
import numpy.typing as npt
import polars as pl
import pytest
from sklearn.preprocessing import StandardScaler

import mpi.models.uncertainty_shift as m7
from mpi.models.lightgbm_comparison import LightGBMSetting
from mpi.models.uncertainty_shift import (
    ScalarCandidate,
    conformal_radius,
    interval_coverage,
    mean_knn_distance,
    ranking_screen_block,
    run_uncertainty_shift,
)
from tests.unit.test_scalar_baselines import _synthetic_inputs


def _small_candidates() -> tuple[ScalarCandidate, ...]:
    return (
        ScalarCandidate("pls", components=1),
        ScalarCandidate(
            "lightgbm",
            lightgbm_setting=LightGBMSetting(7, 2, 25),
        ),
    )


def _sufficient_calibration(memberships: pl.DataFrame) -> pl.DataFrame:
    """Give the tiny M4 fixture nine calibration rows per primary fold."""
    updated = memberships
    for fold in ("holdout_experiment_15", "holdout_experiment_20", "holdout_experiment_23"):
        extra_ids = (
            updated.filter(
                (pl.col("protocol") == "primary")
                & (pl.col("fold") == fold)
                & (pl.col("role") == "fit_tune")
            )
            .sort("unit_id")
            .head(3)["unit_id"]
        )
        updated = updated.with_columns(
            pl.when(
                (pl.col("protocol") == "primary")
                & (pl.col("fold") == fold)
                & pl.col("unit_id").is_in(extra_ids.implode())
            )
            .then(pl.lit("calibration"))
            .otherwise(pl.col("role"))
            .alias("role")
        )
    return updated


def test_conformal_order_statistic_ties_and_insufficient_rows() -> None:
    errors = np.array([0.4, 0.1, 0.2, 0.1, 0.8, 0.3, 0.2, 0.7, 0.6])
    radius, rank = conformal_radius(errors)
    assert rank == math.ceil((len(errors) + 1) * 0.9) == 9
    assert radius == 0.8
    interior_radius, interior_rank = conformal_radius(np.arange(1.0, 20.0))
    assert interior_rank == 18
    assert interior_radius == 18.0
    assert interior_radius != 19.0
    np.testing.assert_array_equal(
        interval_coverage(np.array([8.0, 12.0, 7.999, 12.001]), np.full(4, 10.0), radius=2.0),
        np.array([True, True, False, False]),
    )
    with pytest.raises(ValueError, match="insufficient calibration"):
        conformal_radius(errors[:-1])


def test_distance_matches_direct_standardization_and_five_nearest() -> None:
    train = np.array([[0.0, 5.0], [1.0, 5.0], [2.0, 5.0], [3.0, 5.0], [4.0, 5.0], [8.0, 5.0]])
    query = np.array([[2.5, 99.0], [7.0, -3.0]])
    actual = mean_knn_distance(train, query)
    scaler = StandardScaler().fit(train)
    transformed_train: npt.NDArray[np.float64] = np.asarray(
        scaler.transform(train), dtype=np.float64
    )
    transformed_query: npt.NDArray[np.float64] = np.asarray(
        scaler.transform(query), dtype=np.float64
    )
    all_distances = np.linalg.norm(
        transformed_query[:, None, :] - transformed_train[None, :, :], axis=2
    )
    expected = np.mean(np.sort(all_distances, axis=1)[:, :5], axis=1)
    np.testing.assert_allclose(actual, expected, rtol=0.0, atol=1e-15)


def test_screen_pass_fail_count_and_identity_ties() -> None:
    unit_ids = ["d", "c", "b", "a"]
    distances = np.ones(4)
    passing = ranking_screen_block(unit_ids, distances, np.array([20.0, 9.0, 9.0, 1.0]))
    failing = ranking_screen_block(unit_ids, distances, np.array([1.0, 1.0, 1.0, 9.0]))
    assert passing["retained_count"] == failing["retained_count"] == 3
    assert passing["relative_reduction"] == pytest.approx(0.3504273504273504)
    assert passing["passed"] is True
    assert failing["relative_reduction"] == pytest.approx(-0.22222222222222232)
    assert failing["passed"] is False
    zero = ranking_screen_block(unit_ids, distances, np.zeros(4))
    assert zero["relative_reduction"] is None
    assert zero["passed"] is False


def test_actual_path_is_aligned_nonconstant_and_label_leakage_safe(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(m7, "scalar_candidates", _small_candidates)
    bundle, memberships = _synthetic_inputs()
    memberships = _sufficient_calibration(memberships)
    expected = run_uncertainty_shift(bundle, memberships)
    shuffled = replace(
        bundle,
        process_features=bundle.process_features.sample(fraction=1.0, shuffle=True, seed=41),
        quality=bundle.quality.sample(fraction=1.0, shuffle=True, seed=42),
    )
    actual = run_uncertainty_shift(
        shuffled, memberships.sample(fraction=1.0, shuffle=True, seed=43)
    )
    assert actual.evaluation_predictions.equals(expected.evaluation_predictions)
    assert actual.development_predictions.equals(expected.development_predictions)
    assert actual.calibration_predictions.equals(expected.calibration_predictions)
    assert actual.selections == expected.selections
    fold_filter = (pl.col("protocol") == "primary") & (pl.col("fold") == "holdout_experiment_15")
    fold_memberships = memberships.filter(fold_filter)
    calibration_ids = fold_memberships.filter(pl.col("role") == "calibration")["unit_id"]
    test_ids = fold_memberships.filter(pl.col("role") == "test")["unit_id"]
    changed = replace(
        bundle,
        quality=bundle.quality.with_columns(
            pl.when(pl.col("unit_id").is_in(calibration_ids.implode()))
            .then(pl.col("measured_value") + 1000.0)
            .otherwise(pl.col("measured_value"))
        ),
    )
    changed_result = run_uncertainty_shift(changed, memberships)
    expected_fold = expected.evaluation_predictions.filter(fold_filter)
    changed_fold = changed_result.evaluation_predictions.filter(fold_filter)
    np.testing.assert_allclose(
        changed_fold["predicted_weight_g"], expected_fold["predicted_weight_g"], rtol=0, atol=0
    )
    np.testing.assert_allclose(changed_fold["distance"], expected_fold["distance"], rtol=0, atol=0)
    assert not np.array_equal(
        changed_fold["lower_g"].to_numpy(), expected_fold["lower_g"].to_numpy()
    )
    assert not changed_result.calibration_predictions.filter(fold_filter).equals(
        expected.calibration_predictions.filter(fold_filter)
    )
    expected_selection = next(
        row
        for row in expected.selections
        if row["protocol"] == "primary" and row["fold"] == "holdout_experiment_15"
    )
    changed_selection = next(
        row
        for row in changed_result.selections
        if row["protocol"] == "primary" and row["fold"] == "holdout_experiment_15"
    )
    assert changed_selection["selected_candidate"] == expected_selection["selected_candidate"]
    assert changed_result.development_predictions.filter(fold_filter).equals(
        expected.development_predictions.filter(fold_filter)
    )
    assert next(
        row
        for row in changed_result.screens
        if row["protocol"] == "primary" and row["fold"] == "holdout_experiment_15"
    ) == next(
        row
        for row in expected.screens
        if row["protocol"] == "primary" and row["fold"] == "holdout_experiment_15"
    )
    assert np.ptp(expected_fold["predicted_weight_g"].to_numpy()) > 0.0

    evaluation_changed = replace(
        bundle,
        quality=bundle.quality.with_columns(
            pl.when(pl.col("unit_id").is_in(test_ids.implode()))
            .then(pl.col("measured_value") + 2000.0)
            .otherwise(pl.col("measured_value"))
        ),
    )
    evaluation_result = run_uncertainty_shift(evaluation_changed, memberships)
    evaluation_fold = evaluation_result.evaluation_predictions.filter(fold_filter)
    assert evaluation_result.calibration_predictions.filter(fold_filter).equals(
        expected.calibration_predictions.filter(fold_filter)
    )
    evaluation_selection = next(
        row
        for row in evaluation_result.selections
        if row["protocol"] == "primary" and row["fold"] == "holdout_experiment_15"
    )
    assert evaluation_selection == expected_selection
    assert evaluation_result.development_predictions.filter(fold_filter).equals(
        expected.development_predictions.filter(fold_filter)
    )
    evaluation_screen = next(
        row
        for row in evaluation_result.screens
        if row["protocol"] == "primary" and row["fold"] == "holdout_experiment_15"
    )
    expected_screen = next(
        row
        for row in expected.screens
        if row["protocol"] == "primary" and row["fold"] == "holdout_experiment_15"
    )
    assert evaluation_screen == expected_screen
    assert evaluation_fold.select("predicted_weight_g", "lower_g", "upper_g", "distance").equals(
        expected_fold.select("predicted_weight_g", "lower_g", "upper_g", "distance")
    )
    assert not evaluation_fold["covered"].equals(expected_fold["covered"])
    assert not evaluation_result.metrics.filter(fold_filter).equals(
        expected.metrics.filter(fold_filter)
    )


def test_evaluation_features_do_not_change_selection_or_training_transform(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(m7, "scalar_candidates", _small_candidates)
    bundle, memberships = _synthetic_inputs()
    memberships = _sufficient_calibration(memberships)
    expected = run_uncertainty_shift(bundle, memberships)
    fold_filter = (pl.col("protocol") == "primary") & (pl.col("fold") == "holdout_experiment_15")
    test_ids = memberships.filter(fold_filter & (pl.col("role") == "test"))["unit_id"]
    feature = m7.SCALAR_PREDICTOR_COLUMNS[0]
    changed_bundle = replace(
        bundle,
        process_features=bundle.process_features.with_columns(
            pl.when(pl.col("unit_id").is_in(test_ids.implode()))
            .then(pl.col(feature) + 100.0)
            .otherwise(pl.col(feature))
            .alias(feature)
        ),
    )
    changed = run_uncertainty_shift(changed_bundle, memberships)
    expected_selection = next(
        row
        for row in expected.selections
        if row["protocol"] == "primary" and row["fold"] == "holdout_experiment_15"
    )
    changed_selection = next(
        row
        for row in changed.selections
        if row["protocol"] == "primary" and row["fold"] == "holdout_experiment_15"
    )
    assert changed_selection == expected_selection
    assert changed.development_predictions.filter(fold_filter).equals(
        expected.development_predictions.filter(fold_filter)
    )
    assert not changed.evaluation_predictions.filter(fold_filter).equals(
        expected.evaluation_predictions.filter(fold_filter)
    )
